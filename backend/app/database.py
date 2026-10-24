from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

# Store the database file inside the "backend" folder.
BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_PATH = BASE_DIR / "flowup.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# The engine is the connection to the database file.
# check_same_thread=False lets FastAPI use SQLite from different threads.
engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)


def create_db_and_tables() -> None:
    """Create every table defined in models.py (skips tables that already exist)."""
    # Importing models registers the tables with SQLModel.
    from app import models  # noqa: F401

    SQLModel.metadata.create_all(engine)


def get_session():
    """Give one database session to an API endpoint, then close it."""
    with Session(engine) as session:
        yield session