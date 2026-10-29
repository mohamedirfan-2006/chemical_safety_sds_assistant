from backend.app.database.session import Base, engine, SessionLocal, get_db
from backend.app.database.models import Document, SDSSection, SDSChunk

def init_db() -> None:
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)
