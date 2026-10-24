from datetime import date
from typing import Optional

from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    """A person who uses the app. Login is simulated, so there is no password."""

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    role: str  # "owner", "warehouse" or "cashier"


class Supplier(SQLModel, table=True):
    """A company that sells products to the shop."""

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    lead_time_days: int  # How many days a delivery takes


class Product(SQLModel, table=True):
    """A product the shop sells. Every setting is per product, so any shop can reuse the app."""

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    category: str
    unit: str  # For example "pack" or "bottle"
    unit_cost: float  # What the shop pays the supplier (RM)
    selling_price: float  # What the customer pays (RM)
    min_stock: int  # The reorder alert starts below this quantity
    reorder_quantity: int  # Default quantity to order
    supplier_id: int = Field(foreign_key="supplier.id")


class StockBatch(SQLModel, table=True):
    """One delivery of a product. Different batches can have different expiry dates."""

    id: Optional[int] = Field(default=None, primary_key=True)
    product_id: int = Field(foreign_key="product.id")
    quantity: int
    expiry_date: Optional[date] = None  # Empty for products that do not expire
    discount_percent: int = 0


class DailySale(SQLModel, table=True):
    """How many units of a product were sold on one day."""

    id: Optional[int] = Field(default=None, primary_key=True)
    product_id: int = Field(foreign_key="product.id")
    sale_date: date
    quantity_sold: int