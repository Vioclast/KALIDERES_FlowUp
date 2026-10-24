from datetime import date

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.auth import require_roles
from app.database import get_session
from app.models import Product, PurchaseOrder, Recommendation, StockBatch, User
from app.schemas import DashboardSummary, ExpiringBatchRead

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

# Batches that expire within this many days count as "expiring soon".
EXPIRY_WINDOW_DAYS = 7


@router.get("/summary", response_model=DashboardSummary)
def get_dashboard_summary(
    user: User = Depends(require_roles("owner", "warehouse")),
    session: Session = Depends(get_session),
):
    """Numbers for the dashboard. Only the owner can see the money spent on orders."""
    today = date.today()
    products = session.exec(select(Product)).all()
    batches = session.exec(select(StockBatch)).all()
    product_by_id = {product.id: product for product in products}

    stock_by_product = {}
    total_units = 0
    stock_value = 0.0
    expiring_batches = []
    units_expiring = 0
    value_expiring = 0.0

    for batch in batches:
        product = product_by_id[batch.product_id]
        batch_value = batch.quantity * product.unit_cost

        total_units += batch.quantity
        stock_value += batch_value
        stock_by_product[product.id] = stock_by_product.get(product.id, 0) + batch.quantity

        if batch.expiry_date is None:
            continue  # Products without an expiry date are never "expiring soon"
        days_left = (batch.expiry_date - today).days
        if days_left <= EXPIRY_WINDOW_DAYS:
            units_expiring += batch.quantity
            value_expiring += batch_value
            expiring_batches.append(
                ExpiringBatchRead(
                    batch_id=batch.id,
                    product_name=product.name,
                    quantity=batch.quantity,
                    expiry_date=batch.expiry_date,
                    days_left=days_left,
                    discount_percent=batch.discount_percent,
                )
            )

    low_stock_products = sum(
        1
        for product in products
        if stock_by_product.get(product.id, 0) < product.min_stock
    )
    expiring_batches.sort(key=lambda item: item.days_left)

    pending = session.exec(
        select(Recommendation).where(Recommendation.status == "pending")
    ).all()
    orders = session.exec(select(PurchaseOrder)).all()

    total_spend = None
    if user.role == "owner":
        total_spend = round(sum(order.total_cost for order in orders), 2)

    return DashboardSummary(
        total_products=len(products),
        total_units_in_stock=total_units,
        stock_value=round(stock_value, 2),
        low_stock_products=low_stock_products,
        units_expiring_soon=units_expiring,
        value_expiring_soon=round(value_expiring, 2),
        pending_recommendations=len(pending),
        open_orders=sum(1 for order in orders if order.status == "placed"),
        total_order_spend=total_spend,
        expiring_batches=expiring_batches,
    )