from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from backend.app.database.session import Base

class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    upload_timestamp = Column(DateTime, default=datetime.utcnow)

    # Relationships
    sections = relationship("SDSSection", back_populates="document", cascade="all, delete-orphan")
    chunks = relationship("SDSChunk", back_populates="document", cascade="all, delete-orphan")


class SDSSection(Base):
    __tablename__ = "sds_sections"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    section_number = Column(Integer, nullable=False)  # 1 to 16, or 0 for non-standard/header/footer
    section_title = Column(String, nullable=False)
    raw_text = Column(Text, nullable=False)

    # Relationships
    document = relationship("Document", back_populates="sections")
    chunks = relationship("SDSChunk", back_populates="section", cascade="all, delete-orphan")


class SDSChunk(Base):
    __tablename__ = "sds_chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    section_id = Column(Integer, ForeignKey("sds_sections.id", ondelete="CASCADE"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    page_number = Column(Integer, nullable=False)
    text_content = Column(Text, nullable=False)

    # Relationships
    document = relationship("Document", back_populates="chunks")
    section = relationship("SDSSection", back_populates="chunks")
