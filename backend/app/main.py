from fastapi import FastAPI

# Create the application object. Everything else attaches to this object.
app = FastAPI(
    title="FlowUp API",
    description="Smart stock and expiry assistant for small shops.",
    version="0.1.0",
)


@app.get("/")
def read_root():
    """Root endpoint, used to check that the server is running."""
    return {"message": "FlowUp API is running"}


@app.get("/health")
def health_check():
    """Simple health check used by the frontend and for testing."""
    return {"status": "ok"}