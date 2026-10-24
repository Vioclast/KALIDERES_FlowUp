from datetime import date, datetime
from typing import Optional

from pydantic import NaiveDatetime
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


class Recommendation(SQLModel, table=True):
    """A suggested action saved for a person to approve or reject."""

    id: Optional[int] = Field(default=None, primary_key=True)
    product_id: int = Field(foreign_key="product.id")
    product_name: str  # Copied here so the list is easy to read
    action: str  # "reorder", "discount" or "needs_review"
    priority: str  # "high" or "normal"
    reason: str
    suggested_quantity: Optional[int] = None
    discount_percent: Optional[int] = None
    batch_id: Optional[int] = Field(default=None, foreign_key="stockbatch.id")
    estimated_amount: Optional[float] = None
    status: str = "pending"  # "pending", "approved" or "rejected"
    created_at: NaiveDatetime = Field(default_factory=datetime.now)  # FIX
    decided_by_user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    decided_at: Optional[NaiveDatetime] = None  # FIX


class ActivityLog(SQLModel, table=True):
    """One line of the audit trail: who did what, and when."""

    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp: NaiveDatetime = Field(default_factory=datetime.now)  # FIX
    user_id: int = Field(foreign_key="user.id")
    user_name: str  # Copied here so old records keep the name used at that time
    role: str
    action: str  # For example "stock_check_run"
    details: str


class PurchaseOrder(SQLModel, table=True):
    """An order to a supplier, created after the owner approved a reorder.

    Its total cost is the expense record for that order.
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    recommendation_id: int = Field(foreign_key="recommendation.id")
    product_id: int = Field(foreign_key="product.id")
    product_name: str
    supplier_id: int = Field(foreign_key="supplier.id")
    supplier_name: str
    quantity: int
    total_cost: float  # Quantity x unit cost (RM)
    status: str = "placed"  # "placed" now, "received" in a later version
    created_at: NaiveDatetime = Field(default_factory=datetime.now)  # FIX
    approved_by_user_id: int = Field(foreign_key="user.id")