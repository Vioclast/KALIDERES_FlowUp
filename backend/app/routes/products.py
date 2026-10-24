from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.database import get_session
from app.models import Product, StockBatch, Supplier
from app.schemas import ProductStockRead

router = APIRouter(prefix="/products", tags=["Products"])


@router.get("", response_model=list[ProductStockRead])
def list_products(session: Session = Depends(get_session)):
    """Return every product with its total stock and nearest expiry date."""
    products = session.exec(select(Product)).all()
    result = []

    for product in products:
        supplier = session.get(Supplier, product.supplier_id)
        batches = session.exec(
            select(StockBatch).where(StockBatch.product_id == product.id)
        ).all()

        expiry_dates = [
            batch.expiry_date for batch in batches if batch.expiry_date is not None
        ]
        result.append(
            ProductStockRead(
                id=product.id,
                name=product.name,
                category=product.category,
                unit=product.unit,
                selling_price=product.selling_price,
                min_stock=product.min_stock,
                supplier_name=supplier.name,
                total_stock=sum(batch.quantity for batch in batches),
                nearest_expiry=min(expiry_dates) if expiry_dates else None,
            )
        )

    return result


@router.get("/{product_id}/batches", response_model=list[StockBatch])
def list_product_batches(product_id: int, session: Session = Depends(get_session)):
    """Return all stock batches of one product, or 404 if the product does not exist."""
    product = session.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    return session.exec(
        select(StockBatch).where(StockBatch.product_id == product_id)
    ).all()