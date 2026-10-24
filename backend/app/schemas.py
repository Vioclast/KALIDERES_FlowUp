from datetime import date
from typing import Optional

from sqlmodel import SQLModel


class ProductStockRead(SQLModel):
    """What the API returns for one product in the stock list."""

    id: int
    name: str
    category: str
    unit: str
    selling_price: float
    min_stock: int
    supplier_name: str
    total_stock: int
    nearest_expiry: Optional[date] = None


class RecommendationPreview(SQLModel):
    """One suggested action. It is not saved or approved yet."""

    product_id: int
    product_name: str
    action: str  # "reorder", "discount" or "needs_review"
    priority: str  # "high" or "normal"
    reason: str  # Plain-language explanation shown to the owner
    suggested_quantity: Optional[int] = None  # Only for reorder
    discount_percent: Optional[int] = None  # Only for discount
    batch_id: Optional[int] = None  # Only for discount or expiry review
    estimated_amount: Optional[float] = None  # Reorder cost or value at risk (RM)


class ExpiringBatchRead(SQLModel):
    """A stock batch that will expire soon, shown on the dashboard."""

    batch_id: int
    product_name: str
    quantity: int
    expiry_date: date
    days_left: int
    discount_percent: int


class DashboardSummary(SQLModel):
    """All the numbers the dashboard needs, in one response."""

    total_products: int
    total_units_in_stock: int
    stock_value: float  # Stock valued at cost price (RM)
    low_stock_products: int  # Products below their minimum stock
    units_expiring_soon: int
    value_expiring_soon: float  # At cost price (RM)
    pending_recommendations: int
    open_orders: int
    total_order_spend: Optional[float] = None  # Only the owner can see this
    expiring_batches: list[ExpiringBatchRead]