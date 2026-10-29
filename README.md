# ChemSafe AI - Chemical Safety & SDS Assistant

ChemSafe AI is a grounded Chemical Safety and Safety Data Sheet (SDS) assistant. It features a React-based frontend dashboard that integrates with a FastAPI backend, utilizing a local FAISS vector store, SQLite metadata store, Sentence Transformers, and Ollama Qwen3 4B for grounded, hallucination-free question answering.

---

## Architecture & System URLs

*   **Frontend Development Server**: `http://localhost:5173/` (React + Tailwind CSS + Vite)
*   **Backend Server**: `http://127.0.0.1:8000/` (FastAPI + SQLite + FAISS)
*   **Backend Swagger API Documentation**: `http://127.0.0.1:8000/docs`
*   **Local LLM Service**: `http://localhost:11434/` (Ollama + Qwen3 4B)

---

## Setup & Running Guide

To run the full stack locally, open three terminal sessions and start the processes in order.

### Session 1: Start Ollama LLM Service
Ensure Ollama is running and the target model is pulled:
```cmd
# Start Ollama engine
ollama serve

# In another terminal window (if not yet pulled)
ollama pull qwen3:4b
```

### Session 2: Start FastAPI Backend
Ensure Python dependencies are installed and start the FastAPI uvicorn server:
```powershell
# Navigate to workspace root (if needed)
cd c:\chemical_safety_sds_assistant

# Start the server (includes automatic database/index recreation check)
python backend/run.py
```

### Session 3: Start React Frontend
Install npm dependencies and start the Vite development server:
```powershell
# Navigate to the frontend directory
cd c:\chemical_safety_sds_assistant\frontend

# Install dependencies (if first time)
npm install

# Start Vite dev server
npm run dev
```

---

## How the Frontend Communicates with the Backend

The React application implements a clean, modular API service at [`frontend/src/services/api.js`](file:///c:/chemical_safety_sds_assistant/frontend/src/services/api.js):

1.  **SDS Upload & Indexing**:
    *   **Action**: Dragging or selecting a PDF file.
    *   **Frontend**: Posts a `multipart/form-data` payload containing the file to the backend `/api/v1/sds/upload` route.
    *   **Backend**: Runs text extraction, section splitting (detects all 15 GHS sections, including Section 8), sentence chunking, embeds them, writes vectors to FAISS, and writes metadata to SQLite.

2.  **Conversational RAG QA**:
    *   **Action**: Submitting a safety question or selecting an example question.
    *   **Frontend**: Sends a JSON POST payload to `/api/v1/sds/ask` specifying:
        ```json
        {
          "document_id": 1,
          "question": "What PPE is required when handling acetone?"
        }
        ```
    *   **Frontend query expansion**: If the user uses the abbreviation "PPE", the frontend automatically expands it to "personal protective equipment (PPE)" for vocabulary alignment.
    *   **Backend**: Computes query embeddings, retrieves nearest neighbors from FAISS, filters by `document_id`, hydrades GHS metadata from SQLite, injects safety system prompts, queries Ollama Qwen3 4B, and returns the grounded answer with sources and L2 distances.

3.  **Technical Search (Utility)**:
    *   **Action**: Querying keyword similarities directly.
    *   **Frontend**: Fetches from `/api/v1/sds/search?query=...` to display raw chunk matching parameters.
