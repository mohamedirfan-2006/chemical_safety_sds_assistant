# ChemSafe AI: Chemical Safety & SDS Assistant Walkthrough Documentation

ChemSafe AI is a grounded Chemical Safety Data Sheet (SDS) question-answering system designed to extract, index, and query GHS-structured chemical safety sheets with high precision. By implementing Retrieval-Augmented Generation (RAG) on a local Large Language Model (LLM), the system minimizes hallucination and grounds every generated safety recommendation in the uploaded SDS context.

---

## 1. Project Overview

ChemSafe AI processes complex SDS documents and offers real-time safety querying. The system integrates the following functions:
- **PDF Extraction**: Extracts text content and retains page number associations.
- **Section Detection**: Parses text to locate the 16 GHS (Globally Harmonized System) sections.
- **Dynamic Chunking**: Breaks down text sections into overlapping semantic segments.
- **Embeddings Generation**: Translates textual blocks into vectors using the `all-MiniLM-L6-v2` model.
- **Vector Search Index**: Persists embeddings within a local **FAISS** index.
- **Metadata Management**: Stores document metadata, section definitions, and chunk references in **SQLite**.
- **Grounded Generation**: Submits retrieved text context to a local **Qwen3 4B** model via **Ollama**.
- **Safety Fallback**: Detects queries that lack matching information in the SDS and refuses to answer, preventing hallucinations.

---

## 2. System Architecture

The following block diagram outlines the flow of information from the user request to the final answer generation:

```
                      +-------------------+
                      |   User Inquirer   |
                      +-------------------+
                                | (Question / PDF Upload)
                                v
                      +-------------------+
                      |   React Frontend  |
                      +-------------------+
                                | (REST HTTP Call)
                                v
                      +-------------------+
                      |  FastAPI Backend  |
                      +-------------------+
                                | (Process File)
                                v
                      +-------------------+
                      | Document Pipeline |
                      +-------------------+
                                |
        +-----------------------+-----------------------+
        |                                               |
        v                                               v
+---------------+                               +---------------+
|PyMuPDF Text   |                               |Section        |
|Extraction     |                               |Detector       |
+---------------+                               +---------------+
        |                                               |
        +-----------------------+-----------------------+
                                |
                                v
                        +---------------+
                        |Chunking Engine|
                        +---------------+
                                |
                                v
                        +---------------+
                        |Embeddings Gen |
                        | (MiniLM-L6)   |
                        +---------------+
                                |
        +-----------------------+-----------------------+
        | (Vectors)                                     | (Metadata)
        v                                               v
+---------------+                               +---------------+
|  FAISS Index  |                               | SQLite DB     |
+---------------+                               +---------------+
        | (Vector Search)                               | (Metadata Load)
        +-----------------------+-----------------------+
                                |
                                v
                        +---------------+
                        | RAG Retrieval |
                        +---------------+
                                | (Context + Query)
                                v
                        +---------------+
                        | Ollama Server |
                        | (Qwen3 4B)    |
                        +---------------+
                                | (Grounded Text Response)
                                v
                        +---------------+
                        |   React UI    |
                        +---------------+
```

### Component Roles
1. **React Frontend**: Implements the user dashboard containing drag-and-drop file inputs, active documents metadata, custom semantic testing inputs, conversational chat logs, and safety disclaimers.
2. **FastAPI Backend**: Manages endpoint routing (`/upload`, `/documents`, `/ask`, `/search`, `/health`) and coordinates background processing.
3. **Document Processor**: Integrates PyMuPDF text extraction, section detection regular expressions, and sliding-window chunk division.
4. **SentenceTransformers (`all-MiniLM-L6-v2`)**: Generates 384-dimensional vector representations.
5. **FAISS (Facebook AI Similarity Search)**: Implements fast L2-distance nearest-neighbors retrieval.
6. **SQLite DB**: Manages structured relationships (`Document`, `SDSSection`, `SDSChunk`) and feeds retrieval context metadata.
7. **Ollama & Qwen3 4B**: A local inference platform hosting a 4-billion parameter language model to synthesize safe text answers.

---

## 3. Frontend Walkthrough

The React interface is organized into modular sections optimized for dark-mode contrast:

### A. Header
- **Logo and Branding**: Displays the "ChemSafe AI" title accompanied by an orange/amber safety shield.
- **Grounded Status Badge**: A visual indicator showing that generated answers are grounded in facts.
- **Backend Status Pill**: Shows `ONLINE` (green) when the frontend can communicate with the backend, or `OFFLINE` (red) if uvicorn is unreachable.

### B. Document Indexer
- **Drag-and-Drop Area**: A dashed drop area bounded by `border-slate-600` (hovering to `border-amber-500`) allowing PDF uploads.
- **File Validation**: Validates file types and blocks non-PDF uploads.
- **Upload Success Card**: Displays details retrieved from the backend:
  - Filename
  - Document ID
  - Pages count
  - Detected GHS Sections
  - Chunk count
  - FAISS status indicator (`✓ INDEXED` in green)

### C. Target SDS Workspace
- **Dropdown Selector**: Switch context between different indexed SDS files. Changing the selection resets the conversation.
- **Metadata Card**: Displays information about the selected document, along with a capabilities list showing active sub-components.

### D. Example Safety Queries
- High-contrast clickable buttons for quick verification:
  - *What are the main hazards of this chemical?*
  - *What PPE is required?*
  - *What should I do if the chemical gets in my eyes?*
  - *How should this chemical be stored?*

### E. Vector Similarity Search
- A debugging interface to test FAISS retrieval scores directly.
- Displays retrieved section, page number, source text, and FAISS distance (where smaller distance indicates a stronger vector similarity match).

### F. RAG Console
- **Grounded Badge**: Shows the state of the response based on vector results.
- **Citations List**: Renders citation source blocks underneath the answer bubble, displaying page numbers, chunk IDs, and similarity metrics.

---

## 4. SDS Upload Workflow

```
[Upload PDF] 
     ↓
[Extract text pages via PyMuPDF]
     ↓
[RegEx parses GHS Sections 1-16]
     ↓
[Divide text into 800-char chunks with 150-char overlap]
     ↓
[Generate 384-dim embeddings]
     ↓
[Store vectors in FAISS index] ─── (Matches vector queries)
     ↓
[Insert records in SQLite] ────── (Stores page numbers, raw text)
     ↓
[Update Workspace Dropdown]
```

### Why FAISS and SQLite are Used Together:
- **FAISS** is optimized for high-dimensional vector index operations but does not store arbitrary metadata fields (such as page numbers, document names, or raw text) efficiently.
- **SQLite** handles relational transactions, mapping FAISS nearest-neighbor vector IDs back to section numbers, document names, and actual text snippets.

---

## 5. RAG Question-Answering Workflow

The execution sequence of a safety query:

```
[User enters question]
          ↓
[Post request sent to backend /api/v1/sds/ask]
          ↓
[Check if selected document exists in SQLite]
          ↓
[Query expansion: expands acronyms like 'PPE' to full terms]
          ↓
[Determine target GHS sections matching query keywords]
          ↓
[Generate query embedding vector]
          ↓
[Search FAISS index for top-100 nearest neighbor vectors]
          ↓
[Hydrate match details from SQLite and filter by document ID]
          ↓
[Section-aware re-ranking applies ranking bonus to matching GHS sections]
          ↓
[Slice top-K (default: 5) chunks]
          ↓
[Concatenate chunks into system prompt template context]
          ↓
[Ollama feeds query + context to local Qwen3 4B model]
          ↓
[Model generates answer grounded strictly in prompt context]
          ↓
[Determine found_in_sds state by evaluating retrieval distance scores]
          ↓
[Return response JSON to React client]
          ↓
[React renders response bubble and citations list]
```

---

## 6. Section-Aware Retrieval

ChemSafe AI incorporates section-aware retrieval, which maps user question topics to GHS sections. This is used because vector search alone can sometimes rank general composition details above specific emergency guidance.

### GHS Mapping Rules:
- **First aid queries** (e.g., *inhaled*, *gets in eyes*, *skin contact*) → **Section 4: First-Aid Measures**
- **Fire queries** (e.g., *flammable*, *extinguish*, *explosion*) → **Section 5: Fire-Fighting Measures**
- **Accidental release** (e.g., *spill*, *leak*, *cleanup*) → **Section 6: Accidental Release Measures**
- **Storage/handling** (e.g., *how to store*, *containers*, *ventilation*) → **Section 7: Handling and Storage**
- **PPE/Exposure** (e.g., *PPE*, *gloves*, *respirator*, *exposure limits*) → **Section 8: Exposure Controls / Personal Protection**
- **Physical properties** (e.g., *boiling point*, *appearance*, *viscosity*) → **Section 9: Physical and Chemical Properties**
- **Stability/reactivity** (e.g., *reactive*, *decomposition*, *corrosive*) → **Section 10: Stability and Reactivity**
- **Toxicology** (e.g., *ld50*, *carcinogenicity*, *toxicity*) → **Section 11: Toxicological Information**
- **Disposal** (e.g., *waste*, *how to discard*) → **Section 13: Disposal Considerations**
- **Transport** (e.g., *shipping name*, *UN number*, *hazard class*) → **Section 14: Transport Information**
- **Regulatory** (e.g., *TSCA*, *SARA*, *regulations*) → **Section 15: Regulatory Information**

A **ranking bonus** is applied to matching sections during retrieval. If a chunk falls inside a matching target section, its retrieval distance score is reduced, elevating its priority in the final context prompt.

---

## 7. Grounded Response Logic

The system handles grounded answers in two ways:

### A. Grounded Match (`found_in_sds = true`)
- **Condition**: FAISS similarity searches yield distances within the matching threshold (L2 distance < `1.65`).
- **UI Presentation**: Displays a green status badge **"Grounded in uploaded SDS"** with a checkmark.
- **Output**: The Qwen3 generated answer is displayed along with detailed source citations.

### B. Refusal Fallback (`found_in_sds = false`)
- **Condition**: FAISS similarity search yields distance values exceeding `1.65` (indicating the query topic is not present in the indexed document).
- **UI Presentation**: Displays an amber warning badge **"Information not found in SDS"** with an alert triangle.
- **Output**: Displays the standard fallback message:
  > *"The requested information was not found in the uploaded SDS. Please refer to the official SDS or consult a qualified safety professional."*
- **Benefit**: Prevents the model from generating plausible-sounding but incorrect safety facts for unrelated topics.

---

## 8. Source Citation System

Every retrieved source can display:
- **SDS Section**: The GHS section number associated with the chunk.
- **Section Name**: The full title of the GHS section.
- **Page Number**: The original page number in the SDS PDF.
- **Chunk ID**: The SQLite database chunk primary key.
- **Retrieval Distance**: The L2 vector distance calculated by FAISS.
- **Retrieved SDS Content**: The raw text segment matched by the vector search.

---

## 9. UI Accessibility Improvements

The interface was refined for readability and accessibility in dark mode:
- **Standard Tailwind Colors**: Replaced all custom non-standard colors (e.g., `slate-850`, `slate-350`, `green-450`, `rose-450`) with standard Tailwind classes.
- **Contrast**: Text elements are styled to meet WCAG AA standards. Panel descriptions use `text-slate-400`, body text uses `text-slate-300` or `text-slate-200`, and main titles use `text-white`.
- **Border Clarity**: Borders use `border-slate-700` to define card boundaries.
- **Raw Quotes Readability**: Set to `text-slate-300` in a `bg-slate-900` card for optimal legibility.
- **Buttons and Inputs**: Inputs use `bg-slate-950 border-slate-600 text-slate-100 placeholder:text-slate-500` with focused borders in `border-amber-500` for clear visibility.

---

## 10. Safety Warning

The interface features a persistent safety warning banner:
> **Safety Warning:** ChemSafe AI provides information based on the uploaded SDS. Always verify critical safety decisions against the official SDS and consult qualified safety personnel.

This warning is important because this tool is designed to assist safety personnel, not replace official safety documentation, regulatory standards, or qualified safety professionals.

---

## 11. Testing and Validation

### Test 1: Hazards Query
- **Question**: *What are the main hazards of this chemical?*
- **Result**: `200 OK`, `found_in_sds: true`. Returns Section 2 hazard definitions (highly flammable liquid and vapor, causes serious eye irritation).

### Test 2: Fire Query
- **Question**: *What should I do in case of a fire?*
- **Result**: `200 OK`, `found_in_sds: true`. Returns Section 5 fire-fighting measures, recommending dry chemical, CO2, water spray, or alcohol-resistant foam.

### Test 3: Unrelated Question (Safety Grounding)
- **Question**: *What is the capital of France?*
- **Result**: `200 OK`, `found_in_sds: false`. Displays the amber **"Information not found in SDS"** badge and outputs the standard refusal fallback message.

### Test 4: Document Selection
- **Action**: Switch between document IDs in the dropdown.
- **Result**: Previous chat records are cleared, and document stats are updated.

### Test 5: Production Compilation
- **Command**: `npm run build` inside `frontend/`
- **Result**: Success. Outputs `dist/index.html` and compiled bundle assets.

---

## 12. Current Build Result

The React frontend compiles into production assets:
- `dist/index.html` (entry point HTML template)
- `dist/assets/index-CmyhOnVH.css` (compiled and purged CSS containing utility classes)
- `dist/assets/index-Ca3mJVVM.js` (compiled, minified React vendor and application logic)

---

## 13. Current Backend Status

- **FastAPI Port**: `8000` (`http://127.0.0.1:8000`)
- **FastAPI Documentation**: Swagger UI at `http://127.0.0.1:8000/docs`
- **Ollama Host**: Local port `11434`
- **Active Model**: `qwen3:4b`
- **Vector Database**: FAISS (using `IndexFlatL2` Euclidean distance index)
- **Database**: SQLite (managed via SQLAlchemy ORM)
- **Frontend Server**: Vite Dev Server running on port `5173`

---

## 14. Demonstration Walkthrough

Follow these steps for a live demonstration of ChemSafe AI:

1. **Start the local services**:
   ```cmd
   ollama serve
   python backend/run.py
   cd frontend && npm run dev
   ```
2. **Access the web interface**: Open `http://localhost:5173/` in a web browser.
3. **Verify the connection**: Confirm that the health indicator in the header displays **"FastAPI Backend: ONLINE"** (green).
4. **Upload a safety sheet**: Drag and drop `acetone_sds.pdf` into the indexer card on the left panel, and click **Process & Index SDS**.
5. **Inspect the document metadata**: Check the Target SDS Workspace panel. It should display **15 Detected SDS Sections** and **35 Chunks**.
6. **Query the RAG pipeline**:
   - In the chat bar, type: *"What PPE is required when handling acetone?"*
   - Verify that the loading indicator appears while Qwen3 processes the query.
   - Once loaded, verify that the green **"Grounded in uploaded SDS"** badge appears, and check the citations below the answer (referencing Section 8, Page 4).
7. **Test the safety grounding**:
   - Type: *"What is the capital of Spain?"* and submit.
   - Confirm that the response displays the amber **"Information not found in SDS"** badge and outputs the standard safety refusal message.

---

## 15. Viva Explanation

- **React**: A component-based JavaScript library used to build interactive, state-driven user interfaces.
- **FastAPI**: A high-performance Python web framework used to design RESTful APIs.
- **SQLite**: A lightweight, serverless relational database engine used to store persistent document chunk mappings.
- **FAISS**: A library developed by Facebook Research for efficient similarity searches and clustering of dense vectors.
- **Embeddings**: Vector representations of text that capture semantic meaning, allowing numerical comparison.
- **RAG (Retrieval-Augmented Generation)**: A technique that retrieves relevant reference data before passing the prompt to the LLM, reducing hallucinations.
- **Qwen3**: A local language model optimized for low-latency inference on consumer hardware.
- **Ollama**: A local service wrapper used to run open-source large language models.
- **Section-Aware Retrieval**: An optimization that prioritizes GHS sections relevant to the topic of the query.
- **Source Citations**: References containing page numbers and sections that link the model's response to the original document.

---

## 16. Key Project Advantages

- **Grounded Safety Information**: Reduces LLM hallucinations, ensuring safety information is retrieved from the uploaded document.
- **Local Data Privacy**: Keeps sensitive chemical safety and corporate documents on local hardware by running Ollama and Qwen3 locally.
- **Traceable Answers**: Source citations allow users to verify the generated answer against the original SDS.
- **Section-Aware Retrieval**: Prioritizes relevant sections to locate critical safety information.
- **Safety Fallback**: Refuses to answer unrelated queries, preventing hallucinations.

---

## 17. Final Project Status

ChemSafe AI is fully operational as a local, end-to-end Chemical Safety and SDS Question Answering System. The following features are implemented:

*   **✓ SDS upload**
*   **✓ PDF extraction**
*   **✓ GHS section detection**
*   **✓ Chunking**
*   **✓ Embeddings**
*   **✓ FAISS indexing**
*   **✓ SQLite metadata**
*   **✓ Section-aware RAG**
*   **✓ Local Qwen3 generation**
*   **✓ Grounded response detection**
*   **✓ Source citations**
*   **✓ Document switching**
*   **✓ Safety fallback**
*   **✓ React UI**
*   **✓ Accessibility/readability improvements**
*   **✓ Frontend production build**
*   **✓ Integration testing**
