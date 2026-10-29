import os
import sys
from pathlib import Path
import requests
from sqlalchemy.orm import Session

# Add the workspace directory to sys.path to allow imports from backend
workspace_dir = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(workspace_dir))

from backend.app.core.config import settings
from backend.app.database import init_db, SessionLocal, Document, SDSSection, SDSChunk
from backend.app.services.document_processor import DocumentProcessor
from backend.app.services.embedding_service import EmbeddingService
from backend.app.services.vector_store import VectorStoreManager

# List of target public URLs for Acetone SDS PDFs
TEST_SDS_URLS = [
    "https://raw.githubusercontent.com/SilbigerLab/MSDS/master/SDS/Acetone.pdf",
    "https://safety.fsu.edu/safety_manuals/sds/Acetone.pdf",
    "https://ehs.okstate.edu/site-files/docs/sds/acetone-sds.pdf"
]

def download_test_sds(dest_path: Path) -> bool:
    """Download a test Acetone SDS from university servers."""
    if dest_path.exists():
        print(f"[OK] Test PDF already exists at {dest_path}")
        return True

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    for url in TEST_SDS_URLS:
        try:
            print(f"[*] Attempting to download test SDS from: {url}")
            response = requests.get(url, headers=headers, timeout=20)
            if response.status_code == 200 and len(response.content) > 1000:
                with open(dest_path, "wb") as f:
                    f.write(response.content)
                print(f"[OK] Downloaded successfully to {dest_path}")
                return True
            else:
                print(f"[!] Warning: Response code {response.status_code} or small size from {url}")
        except Exception as e:
            print(f"[!] Failed download from {url}: {e}")
            
    return False

def test_pipeline():
    print("=" * 60)
    print("STARTING CHEMSAFE AI BACKEND DOCUMENT PROCESSING PIPELINE TEST")
    print("=" * 60)

    # 0. Initialize databases
    print("\n[*] Initializing SQLite database...")
    init_db()
    db: Session = SessionLocal()

    # Clear previous FAISS and DB records for a fresh test run
    print("[*] Resetting FAISS index...")
    vector_store = VectorStoreManager()
    vector_store.clear_index()
    
    print("[*] Clearing SQLite tables...")
    db.query(SDSChunk).delete()
    db.query(SDSSection).delete()
    db.query(Document).delete()
    db.commit()

    # 1. Download test SDS PDF
    test_pdf_name = "acetone_sds.pdf"
    test_pdf_path = settings.RAW_DIR / test_pdf_name
    
    if not download_test_sds(test_pdf_path):
        print("[FAIL] ERROR: Failed to download a test Acetone SDS PDF.")
        sys.exit(1)

    # 2. Extract Text and Detect Sections
    print("\n[*] Extracting text and parsing GHS sections...")
    try:
        pages_text = DocumentProcessor.extract_text(str(test_pdf_path))
        print(f"[OK] Extracted {len(pages_text)} pages of text.")
        
        # Output summary of pages
        for page_num, text in pages_text:
            print(f"    - Page {page_num}: {len(text)} characters")
            
        print("\n[*] Parsing GHS standard 16 sections...")
        processed_data = DocumentProcessor.process_pdf(str(test_pdf_path))
        
        detected_sections = []
        for sec_num, sec_info in processed_data.items():
            if sec_info["content"].strip():
                detected_sections.append(sec_num)
                
        print(f"[OK] Detected sections populated with text: {sorted(detected_sections)}")
        for sec_num in sorted(detected_sections):
            sec_info = processed_data[sec_num]
            start_p = sec_info["page_start"]
            c_len = len(sec_info["content"])
            chunks_cnt = len(sec_info["chunks"])
            print(f"    - Section {sec_num}: '{sec_info['title']}' (Starts Page {start_p}, Length: {c_len} chars, Chunks: {chunks_cnt})")
            
    except Exception as e:
        print(f"[FAIL] ERROR during PDF extraction & GHS parsing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # 3. Save to Database
    print("\n[*] Saving parsed records to SQLite database...")
    try:
        db_doc = Document(filename=test_pdf_name, file_path=str(test_pdf_path))
        db.add(db_doc)
        db.flush()
        
        chunk_records = []
        chunk_texts = []
        
        for sec_num, sec_info in processed_data.items():
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
            db.flush()
            
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
                
        db.flush()
        db.commit()
        print(f"[OK] SQLite Database successfully populated:")
        print(f"    - Documents: {db.query(Document).count()}")
        print(f"    - SDS Sections: {db.query(SDSSection).count()}")
        print(f"    - SDS Chunks: {db.query(SDSChunk).count()}")
        
    except Exception as e:
        db.rollback()
        print(f"[FAIL] ERROR saving to Database: {e}")
        sys.exit(1)

    # 4. Generate Embeddings & Create FAISS Index
    print("\n[*] Generating embeddings using Sentence Transformers...")
    try:
        embedding_service = EmbeddingService()
        print(f"    - Loaded model: '{settings.EMBEDDING_MODEL_NAME}'")
        
        embeddings = embedding_service.get_embeddings(chunk_texts)
        print(f"[OK] Generated {len(embeddings)} embeddings of dimension {len(embeddings[0])}.")
        
        print("\n[*] Building and saving FAISS vector index...")
        chunk_ids = [chunk.id for chunk in chunk_records]
        vector_store.add_vectors(embeddings, chunk_ids)
        print(f"[OK] Saved FAISS index with {vector_store.index.ntotal} vectors to: {settings.FAISS_INDEX_PATH}")
        
    except Exception as e:
        print(f"[FAIL] ERROR generating embeddings or FAISS index: {e}")
        sys.exit(1)

    # 5. Run Semantic Search Test Queries (Verify RAG Retrieval)
    print("\n" + "=" * 40)
    print("TESTING SEMANTIC SEARCH RETRIEVAL")
    print("=" * 40)
    
    test_queries = [
        "What first aid measures should be taken if acetone gets in the eyes?",
        "Is acetone highly flammable?",
        "What are the exposure limits for acetone?",
        "How should acetone be stored safely?"
    ]
    
    for query in test_queries:
        print(f"\n[Search Query] '{query}'")
        # Compute query vector
        query_vector = embedding_service.get_embedding(query)
        # Query FAISS index for top 2 matches
        matches = vector_store.search(query_vector, k=2)
        
        print(f"Top {len(matches)} Retrieval Matches:")
        for rank, (chunk_id, dist) in enumerate(matches, 1):
            chunk = db.query(SDSChunk).filter_by(id=chunk_id).first()
            if chunk:
                section = chunk.section
                print(f"  Rank {rank} (Distance: {dist:.4f})")
                print(f"    Citation: {section.section_title} (Page {chunk.page_number})")
                # Print a preview snippet of the chunk
                text_preview = chunk.text_content.replace("\n", " ").strip()
                if len(text_preview) > 160:
                    text_preview = text_preview[:160] + "..."
                print(f"    Snippet:  {text_preview}")
            else:
                print(f"  Rank {rank}: Chunk ID {chunk_id} not found in database (invalid mapping!)")
                
    db.close()
    print("\n" + "=" * 60)
    print("BACKEND DOCUMENT PROCESSING PIPELINE TEST COMPLETED SUCCESSFULLY")
    print("=" * 60)

if __name__ == "__main__":
    test_pipeline()
