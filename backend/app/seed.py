import random
from datetime import date, timedelta

from sqlmodel import Session, SQLModel, select

from app.database import create_db_and_tables, engine
from app.models import DailySale, Product, StockBatch, Supplier, User

# How many past days of sales history to create for each product.
SALES_HISTORY_DAYS = 14

# All data below is synthetic (invented). It does not describe any real shop.
SUPPLIER_DATA = {
    "farm": {"name": "Fresh Farm Supplies", "lead_time_days": 2},
    "grain": {"name": "Golden Grain Trading", "lead_time_days": 3},
    "bright": {"name": "Bright Wholesale Distributors", "lead_time_days": 5},
}

# "batches" is a list of (quantity, days until expiry). None means no expiry date.
# "daily_sales" is the average units sold per day. None means no sales history.
PRODUCT_DATA = [
    {   # Low stock and sells fast: urgent reorder
        "name": "Fresh Milk 1L", "category": "Dairy", "unit": "bottle",
        "unit_cost": 5.20, "selling_price": 6.90,
        "min_stock": 20, "reorder_quantity": 48, "supplier": "farm",
        "daily_sales": 12, "batches": [(6, 2), (10, 6)],
    },
    {   # Plenty of stock but expires soon: discount
        "name": "Plain Yogurt Cup", "category": "Dairy", "unit": "cup",
        "unit_cost": 1.80, "selling_price": 2.60,
        "min_stock": 24, "reorder_quantity": 48, "supplier": "farm",
        "daily_sales": 5, "batches": [(40, 3)],
    },
    {   # Healthy: no action needed
        "name": "Wholemeal Bread", "category": "Bakery", "unit": "loaf",
        "unit_cost": 2.80, "selling_price": 4.20,
        "min_stock": 15, "reorder_quantity": 30, "supplier": "grain",
        "daily_sales": 9, "batches": [(25, 3)],
    },
    {   # Healthy: no action needed
        "name": "Instant Noodles 5-pack", "category": "Dry Goods", "unit": "pack",
        "unit_cost": 3.50, "selling_price": 4.90,
        "min_stock": 30, "reorder_quantity": 60, "supplier": "grain",
        "daily_sales": 10, "batches": [(150, 200)],
    },
    {   # Low stock: reorder
        "name": "Cooking Oil 1kg", "category": "Dry Goods", "unit": "bottle",
        "unit_cost": 5.50, "selling_price": 7.20,
        "min_stock": 12, "reorder_quantity": 24, "supplier": "grain",
        "daily_sales": 3, "batches": [(8, 300)],
    },
    {   # Healthy: no action needed
        "name": "Mineral Water 600ml", "category": "Beverages", "unit": "bottle",
        "unit_cost": 0.60, "selling_price": 1.20,
        "min_stock": 60, "reorder_quantity": 120, "supplier": "bright",
        "daily_sales": 25, "batches": [(300, 400)],
    },
    {   # Slightly below minimum and never expires: low priority reorder
        "name": "Dishwashing Liquid 500ml", "category": "Household", "unit": "bottle",
        "unit_cost": 3.20, "selling_price": 4.80,
        "min_stock": 10, "reorder_quantity": 24, "supplier": "bright",
        "daily_sales": 1.5, "batches": [(9, None)],
    },
    {   # Plenty of stock but expires soon: discount
        "name": "Eggs Tray (30)", "category": "Fresh", "unit": "tray",
        "unit_cost": 11.00, "selling_price": 14.50,
        "min_stock": 10, "reorder_quantity": 20, "supplier": "farm",
        "daily_sales": 3, "batches": [(30, 4)],
    },
    {   # New product with no sales history: needs a human decision
        "name": "Oat Drink 1L", "category": "Beverages", "unit": "bottle",
        "unit_cost": 6.80, "selling_price": 9.50,
        "min_stock": 10, "reorder_quantity": 24, "supplier": "bright",
        "daily_sales": None, "batches": [(4, 90)],
    },
]


def reset_database() -> None:
    """Delete all tables and create them again, so the demo always starts clean."""
    SQLModel.metadata.drop_all(engine)
    create_db_and_tables()


def seed_users(session: Session) -> None:
    """Create three fake people, one for each role."""
    session.add_all([
        User(name="Aisyah Rahman", role="owner"),
        User(name="Hafiz Ismail", role="warehouse"),
        User(name="Mei Ling Tan", role="cashier"),
    ])
    session.commit()


def seed_suppliers(session: Session) -> dict:
    """Create the suppliers and return them, so products can point to them."""
    suppliers = {key: Supplier(**values) for key, values in SUPPLIER_DATA.items()}
    session.add_all(suppliers.values())
    session.commit()
    for supplier in suppliers.values():
        session.refresh(supplier)  # Load the id that the database created
    return suppliers


def seed_products(session: Session, suppliers: dict, today: date, rng: random.Random) -> None:
    """Create products, their stock batches and 14 days of sales history."""
    for item in PRODUCT_DATA:
        product = Product(
            name=item["name"],
            category=item["category"],
            unit=item["unit"],
            unit_cost=item["unit_cost"],
            selling_price=item["selling_price"],
            min_stock=item["min_stock"],
            reorder_quantity=item["reorder_quantity"],
            supplier_id=suppliers[item["supplier"]].id,
        )
        session.add(product)
        session.commit()
        session.refresh(product)

        for quantity, days_until_expiry in item["batches"]:
            expiry_date = None
            if days_until_expiry is not None:
                expiry_date = today + timedelta(days=days_until_expiry)
            session.add(
                StockBatch(product_id=product.id, quantity=quantity, expiry_date=expiry_date)
            )

        average_sales = item["daily_sales"]
        if average_sales is not None:
            for days_ago in range(1, SALES_HISTORY_DAYS + 1):
                # Each day varies 30% up or down from the average.
                sold = round(average_sales * rng.uniform(0.7, 1.3))
                session.add(
                    DailySale(
                        product_id=product.id,
                        sale_date=today - timedelta(days=days_ago),
                        quantity_sold=sold,
                    )
                )
        session.commit()


def run_seed() -> None:
    """Reset the database and fill it with the synthetic demo data."""
    reset_database()
    rng = random.Random(42)  # Fixed seed: the sales numbers are the same every run
    today = date.today()

    with Session(engine) as session:
        seed_users(session)
        suppliers = seed_suppliers(session)
        seed_products(session, suppliers, today, rng)

        print("Seed finished.")
        print("Users:", len(session.exec(select(User)).all()))
        print("Suppliers:", len(session.exec(select(Supplier)).all()))
        print("Products:", len(session.exec(select(Product)).all()))
        print("Stock batches:", len(session.exec(select(StockBatch)).all()))
        print("Daily sales rows:", len(session.exec(select(DailySale)).all()))


if __name__ == "__main__":
    run_seed()