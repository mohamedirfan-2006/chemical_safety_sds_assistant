import os
import shutil
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session
from typing import List

from backend.app.core.config import settings
from backend.app.database import get_db, Document, SDSSection, SDSChunk
from backend.app.services.document_processor import DocumentProcessor
from backend.app.services.embedding_service import EmbeddingService
from backend.app.services.vector_store import VectorStoreManager

router = APIRouter()

@router.post("/upload")
async def upload_sds(
    file: UploadFile = File(...), 
    db: Session = Depends(get_db)
):
    """
    Upload an SDS PDF, extract its text, detect sections, chunk it,
    generate embeddings, and index it in the FAISS vector database.
    """
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    # Create storage directories
    settings.create_directories()

    # Save file to raw storage
    file_path = settings.RAW_DIR / file.filename
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        # 1. Document Processing: text extraction, section boundary splitting, chunking
        processed_data = DocumentProcessor.process_pdf(str(file_path))

        # 2. Database transaction: Save document, section, and chunk records
        db_doc = Document(filename=file.filename, file_path=str(file_path))
        db.add(db_doc)
        db.flush()  # Get database ID for relationships

        chunk_records = []
        chunk_texts = []

        for sec_num, sec_info in processed_data.items():
            # Standardize empty content sections
            raw_text = sec_info["content"]
            if not raw_text.strip():
                continue
                
            db_sec = SDSSection(
                document_id=db_doc.id,
                section_number=sec_num,
                section_title=sec_info["title"],
                raw_text=raw_text
            )
            db.add(db_sec)
            db.flush()  # Get section ID for chunks

            for idx, chunk_info in enumerate(sec_info["chunks"]):
                db_chunk = SDSChunk(
                    document_id=db_doc.id,
                    section_id=db_sec.id,
                    chunk_index=idx,
                    page_number=chunk_info["page_num"],
                    text_content=chunk_info["text"]
                )
                db.add(db_chunk)
                chunk_records.append(db_chunk)
                chunk_texts.append(chunk_info["text"])

        # Flush to populate chunk IDs
        db.flush()

        # 3. Vector database processing
        if chunk_texts:
            # Generate embeddings using Sentence Transformers
            embedding_service = EmbeddingService()
            embeddings = embedding_service.get_embeddings(chunk_texts)
            
            # Map chunk IDs to FAISS vector IDs
            chunk_ids = [chunk.id for chunk in chunk_records]
            
            # Index vectors in FAISS
            vector_store = VectorStoreManager()
            vector_store.add_vectors(embeddings, chunk_ids)

        db.commit()

        # Query actual database counts to maintain consistency
        sections_count = db.query(SDSSection).filter_by(document_id=db_doc.id).count()
        chunks_count = db.query(SDSChunk).filter_by(document_id=db_doc.id).count()
        pages_count = db.query(func.max(SDSChunk.page_number)).filter_by(document_id=db_doc.id).scalar() or 0

        return {
            "message": "SDS uploaded and processed successfully.",
            "document_id": db_doc.id,
            "filename": db_doc.filename,
            "sections_count": sections_count,
            "chunks_count": chunks_count,
            "pages_count": pages_count
        }

    except Exception as e:
        db.rollback()
        # Clean up uploaded file if processing failed
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to process and index PDF: {str(e)}"
        )


@router.get("/documents")
def list_documents(db: Session = Depends(get_db)):
    """Retrieve metadata of all processed documents."""
    docs = db.query(Document).all()
    return [
        {
            "id": doc.id,
            "filename": doc.filename,
            "upload_timestamp": doc.upload_timestamp,
            "sections_count": db.query(SDSSection).filter_by(document_id=doc.id).count(),
            "chunks_count": db.query(SDSChunk).filter_by(document_id=doc.id).count(),
            "pages_count": db.query(func.max(SDSChunk.page_number)).filter_by(document_id=doc.id).scalar() or 0
        }
        for doc in docs
    ]


@router.get("/search")
def search_sds(
    query: str = Query(..., description="Text query to search within index"),
    k: int = Query(5, description="Number of results to return"),
    db: Session = Depends(get_db)
):
    """
    Search the FAISS vector index for semantic matches, returning
    matching text chunks with full SDS document context and citations.
    """
    # 1. Compute query vector
    embedding_service = EmbeddingService()
    query_vector = embedding_service.get_embedding(query)

    # 2. Query FAISS index
    vector_store = VectorStoreManager()
    search_results = vector_store.search(query_vector, k=k)

    # 3. Build response matching indices back to database
    results = []
    for chunk_id, score in search_results:
        chunk = db.query(SDSChunk).filter_by(id=chunk_id).first()
        if chunk:
            section = chunk.section
            document = chunk.document
            results.append({
                "chunk_id": chunk.id,
                "score": score,  # L2 distance
                "text": chunk.text_content,
                "page_number": chunk.page_number,
                "section_number": section.section_number,
                "section_title": section.section_title,
                "document_id": document.id,
                "document_filename": document.filename
            })

    return {
        "query": query,
        "results": results
    }


from pydantic import BaseModel

class AskRequest(BaseModel):
    document_id: int
    question: str

@router.post("/ask")
def ask_sds(
    request: AskRequest,
    db: Session = Depends(get_db)
):
    """
    Perform RAG question answering over a specific indexed SDS document.
    """
    from backend.app.services.rag_service import RAGService
    
    rag_service = RAGService()
    try:
        result = rag_service.answer_question(
            db=db,
            document_id=request.document_id,
            question=request.question
        )
        return result
    except UnicodeError as e:
        # Internal string/stream encoding issue, should never bubble up as client 400
        raise HTTPException(status_code=500, detail=f"Text encoding error: {str(e)}")
    except ValueError as e:
        msg = str(e)
        if "not found" in msg.lower() and "document" in msg.lower():
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=400, detail=msg)
    except ConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

