from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import create_db_and_tables
from app.routes import activity_log, dashboard, orders, products, recommendations, users


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs when the server starts: make sure all tables exist."""
    create_db_and_tables()
    yield


app = FastAPI(
    title="FlowUp API",
    description="Smart stock and expiry assistant for small shops.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(users.router)
app.include_router(products.router)
app.include_router(dashboard.router)
app.include_router(recommendations.router)
app.include_router(orders.router)
app.include_router(activity_log.router)


@app.get("/")
def read_root():
    """Root endpoint, used to check that the server is running."""
    return {"message": "FlowUp API is running"}


@app.get("/health")
def health_check():
    """Simple health check used by the frontend and for testing."""
    return {"status": "ok"}