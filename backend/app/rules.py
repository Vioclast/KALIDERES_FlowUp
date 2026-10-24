from datetime import date, timedelta
from typing import Optional

from sqlmodel import Session, select

from app.models import DailySale, Product, StockBatch, Supplier
from app.schemas import RecommendationPreview

# How many past days of sales we use to estimate daily demand.
SALES_WINDOW_DAYS = 14

# Discount tiers as (maximum days until expiry, discount percent).
DISCOUNT_TIERS = [(2, 30), (5, 20), (10, 10)]

# Only discount a batch if at least this share of it may stay unsold.
MIN_UNSOLD_SHARE = 0.2

# A discount below this percentage is not worth offering.
MIN_DISCOUNT_PERCENT = 5


def get_average_daily_sales(
    session: Session, product_id: int, today: date
) -> Optional[float]:
    """Average units sold per day in the last 14 days, or None if there is no history."""
    start_date = today - timedelta(days=SALES_WINDOW_DAYS)
    sales = session.exec(
        select(DailySale)
        .where(DailySale.product_id == product_id)
        .where(DailySale.sale_date >= start_date)
    ).all()

    if not sales:
        return None
    return sum(sale.quantity_sold for sale in sales) / SALES_WINDOW_DAYS


def pick_discount_percent(days_left: int) -> int:
    """The closer the expiry date, the bigger the discount. 0 means it is too early."""
    for max_days, percent in DISCOUNT_TIERS:
        if days_left <= max_days:
            return percent
    return 0


def max_discount_without_loss(product: Product) -> int:
    """The biggest discount (in percent) that keeps the price at or above the cost."""
    margin = (product.selling_price - product.unit_cost) / product.selling_price
    return int(margin * 100)


def check_reorder(
    product: Product,
    supplier: Supplier,
    total_stock: int,
    average_sales: float,
) -> Optional[RecommendationPreview]:
    """Suggest a reorder if stock is below the minimum or will run out before delivery."""
    below_minimum = total_stock < product.min_stock

    days_of_stock = None
    runs_out_before_delivery = False
    if average_sales > 0:
        days_of_stock = total_stock / average_sales
        runs_out_before_delivery = days_of_stock <= supplier.lead_time_days

    if not below_minimum and not runs_out_before_delivery:
        return None

    reason = f"Stock is {total_stock} {product.unit}(s), minimum is {product.min_stock}."
    if days_of_stock is not None:
        reason += (
            f" At {average_sales:.1f} sold per day, stock lasts about "
            f"{days_of_stock:.1f} days, and {supplier.name} needs "
            f"{supplier.lead_time_days} days to deliver."
        )

    return RecommendationPreview(
        product_id=product.id,
        product_name=product.name,
        action="reorder",
        priority="high" if runs_out_before_delivery else "normal",
        reason=reason,
        suggested_quantity=product.reorder_quantity,
        estimated_amount=round(product.reorder_quantity * product.unit_cost, 2),
    )


def check_discounts(
    product: Product,
    batches: list[StockBatch],
    average_sales: float,
    today: date,
) -> list[RecommendationPreview]:
    """Suggest discounts for batches that will probably not sell before they expire."""
    results = []
    stock_through_previous = 0  # Units in batches that expire earlier and sell first

    batches_with_expiry = [batch for batch in batches if batch.expiry_date is not None]
    for batch in sorted(batches_with_expiry, key=lambda item: item.expiry_date):
        days_left = (batch.expiry_date - today).days

        if days_left <= 0:
            results.append(
                RecommendationPreview(
                    product_id=product.id,
                    product_name=product.name,
                    action="needs_review",
                    priority="high",
                    reason=(
                        f"A batch of {batch.quantity} expires today or has already "
                        "expired. A person must check it and remove it from the shelf."
                    ),
                    batch_id=batch.id,
                )
            )
            continue

        stock_through_batch = stock_through_previous + batch.quantity
        stock_through_previous = stock_through_batch

        expected_sales = average_sales * days_left
        unsold = min(stock_through_batch - expected_sales, batch.quantity)
        if unsold < MIN_UNSOLD_SHARE * batch.quantity:
            continue

        percent = pick_discount_percent(days_left)
        if percent == 0:
            continue
        percent = min(percent, max_discount_without_loss(product))

        if percent < MIN_DISCOUNT_PERCENT:
            results.append(
                RecommendationPreview(
                    product_id=product.id,
                    product_name=product.name,
                    action="needs_review",
                    priority="normal",
                    reason=(
                        f"About {unsold:.0f} of {batch.quantity} units may expire "
                        "unsold, but any useful discount would sell below cost. "
                        "A person must decide."
                    ),
                    batch_id=batch.id,
                )
            )
            continue

        results.append(
            RecommendationPreview(
                product_id=product.id,
                product_name=product.name,
                action="discount",
                priority="high" if days_left <= 2 else "normal",
                reason=(
                    f"About {unsold:.0f} of {batch.quantity} units may stay unsold: "
                    f"{days_left} days until expiry, but only about "
                    f"{expected_sales:.0f} are expected to sell. "
                    f"A {percent}% discount can help."
                ),
                discount_percent=percent,
                batch_id=batch.id,
                estimated_amount=round(unsold * product.unit_cost, 2),
            )
        )

    return results


def analyze_inventory(session: Session, today: date) -> list[RecommendationPreview]:
    """Check every product and return the suggested actions (nothing is saved)."""
    recommendations = []

    for product in session.exec(select(Product)).all():
        supplier = session.get(Supplier, product.supplier_id)
        batches = session.exec(
            select(StockBatch).where(StockBatch.product_id == product.id)
        ).all()
        total_stock = sum(batch.quantity for batch in batches)
        average_sales = get_average_daily_sales(session, product.id, today)

        if average_sales is None:
            # No sales history: the app cannot estimate demand, so a person decides.
            if total_stock < product.min_stock:
                recommendations.append(
                    RecommendationPreview(
                        product_id=product.id,
                        product_name=product.name,
                        action="needs_review",
                        priority="normal",
                        reason=(
                            f"Stock is {total_stock} {product.unit}(s), minimum is "
                            f"{product.min_stock}, but there is no sales history to "
                            "estimate demand. A person must decide the order quantity."
                        ),
                    )
                )
            continue

        reorder = check_reorder(product, supplier, total_stock, average_sales)
        if reorder is not None:
            recommendations.append(reorder)

        recommendations.extend(check_discounts(product, batches, average_sales, today))

    # Most urgent first. The sort is stable, so the original order is kept otherwise.
    recommendations.sort(key=lambda item: 0 if item.priority == "high" else 1)
    return recommendations