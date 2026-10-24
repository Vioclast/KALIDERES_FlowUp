from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.database import create_db_and_tables
from app.routes import activity_log, dashboard, orders, products, recommendations, users

# The "frontend" folder sits next to the "backend" folder.
FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"


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


@app.get("/health")
def health_check():
    """Simple health check used by the frontend and for testing."""
    return {"status": "ok"}


# Serve the web page. This must stay last: it answers every address the API does not use.
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")