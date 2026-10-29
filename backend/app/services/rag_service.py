import sys
import re
from typing import Dict, Any

from backend.app.core.encoding import safe_print
print = safe_print

from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.database import Document, SDSSection, SDSChunk
from backend.app.services.embedding_service import EmbeddingService
from backend.app.services.vector_store import VectorStoreManager
from backend.app.services.llm_service import LLMService


class RAGService:

    def __init__(self):

        self.embedding_service = EmbeddingService()
        self.vector_store = VectorStoreManager()
        self.llm_service = LLMService()

    # ============================================================
    # SECTION DETECTION
    # ============================================================

    def _detect_relevant_sections(
        self,
        question: str
    ) -> Dict[int, float]:

        q = question.lower()

        section_scores = {}

        def add(section: int, score: float):

            section_scores[section] = (
                section_scores.get(section, 0.0)
                + score
            )

        # --------------------------------------------------------
        # SECTION 1 - IDENTIFICATION
        # --------------------------------------------------------

        sec1_keywords = [
            "product name",
            "cas number",
            "cas no",
            "cas #",
            "chemical name",
            "supplier",
            "manufacturer",
            "emergency phone",
            "emergency telephone",
            "product number",
            "identification",
            "what is this chemical",
            "what chemical is this"
        ]

        if any(word in q for word in sec1_keywords) or bool(re.search(r"\bcas\b", q)):

            add(1, 5.0)

        # --------------------------------------------------------
        # SECTION 2 - HAZARDS
        # --------------------------------------------------------

        if any(word in q for word in [
            "hazard",
            "hazards",
            "danger",
            "dangers",
            "dangerous",
            "warning",
            "flammable",
            "flammability",
            "explosive",
            "explosion",
            "ghs",
            "signal word",
            "hazard statement",
            "precautionary statement",
            "harmful",
            "is it harmful",
            "is this harmful",
            "is it dangerous",
            "is this dangerous",
            "threat",
            "threats",
            "risk",
            "risks",
            "what could happen",
            "exposed",
            "toxicity to humans",
            "is it toxic",
            "main hazards"
        ]):

            add(2, 10.0)

        # --------------------------------------------------------
        # SECTION 3 - COMPOSITION
        # --------------------------------------------------------

        if any(word in q for word in [
            "composition",
            "ingredient",
            "ingredients",
            "component",
            "concentration",
            "percentage"
        ]):

            add(3, 5.0)

        # --------------------------------------------------------
        # SECTION 4 - FIRST AID
        # --------------------------------------------------------

        if any(word in q for word in [
            "first aid",
            "injury",
            "injured",
            "eye contact",
            "eyes",
            "in my eyes",
            "into eyes",
            "gets in my eyes",
            "splash in eyes",
            "skin contact",
            "on my skin",
            "swallowed",
            "swallow",
            "if swallowed",
            "ingestion",
            "ingest",
            "inhaled",
            "inhale",
            "if inhaled",
            "breathe in",
            "breathing in",
            "exposure symptoms",
            "symptoms after exposure",
            "poisoning",
            "antidote",
            "what to do if"
        ]):

            add(4, 12.0)

        # --------------------------------------------------------
        # SECTION 5 - FIRE FIGHTING
        # --------------------------------------------------------

        if any(word in q for word in [
            "fire",
            "fire emergency",
            "chemical fire",
            "acetone fire",
            "burning",
            "flame",
            "flames",
            "firefighting",
            "fire fighting",
            "extinguish",
            "extinguishing",
            "extinguisher",
            "extinguishing media",
            "suitable extinguishing media",
            "combustible",
            "combustion",
            "firefighter",
            "firefighters",
            "fire hazard",
            "catch fire",
            "if it catches fire"
        ]):

            add(5, 12.0)

        # --------------------------------------------------------
        # SECTION 6 - ACCIDENTAL RELEASE
        # --------------------------------------------------------

        if any(word in q for word in [
            "spill",
            "spillage",
            "leak",
            "leakage",
            "accidental release",
            "cleanup",
            "clean up",
            "containment",
            "released accidentally",
            "spilled",
            "dropped on floor",
            "if there is a spill",
            "if it spills"
        ]):

            add(6, 12.0)

        # --------------------------------------------------------
        # SECTION 7 - HANDLING AND STORAGE
        # --------------------------------------------------------

        if any(word in q for word in [
            "storage",
            "store",
            "stored",
            "storing",
            "handling",
            "handle",
            "safely handle",
            "container",
            "containers",
            "keep",
            "temperature",
            "storage conditions",
            "how should it be stored",
            "how to store",
            "can i store",
            "store near",
            "together with",
            "incompatible materials",
            "precautions while handling"
        ]):

            add(7, 12.0)

        # --------------------------------------------------------
        # SECTION 8 - PPE / EXPOSURE CONTROLS
        # --------------------------------------------------------

        if any(word in q for word in [
            "ppe",
            "personal protective equipment",
            "protective equipment",
            "protective measures",
            "gloves",
            "glove",
            "what gloves",
            "what gloves do i need",
            "what gloves should i use",
            "hand protection",
            "eye protection",
            "eye protective",
            "safety glasses",
            "goggles",
            "face protection",
            "face shield",
            "respiratory protection",
            "respiratory protective",
            "respirator",
            "mask",
            "masks",
            "protective clothing",
            "protective clothes",
            "chemical resistant gloves",
            "skin protection",
            "exposure limit",
            "exposure limits",
            "exposure controls",
            "occupational exposure",
            "ventilation",
            "what should i wear",
            "what to wear",
            "how can i protect",
            "protect myself",
            "what equipment",
            "required equipment"
        ]):

            add(8, 20.0)

        # --------------------------------------------------------
        # SECTION 9 - PHYSICAL / CHEMICAL PROPERTIES
        # --------------------------------------------------------

        if any(word in q for word in [
            "boiling point",
            "melting point",
            "flash point",
            "density",
            "odor",
            "odour",
            "colour",
            "color",
            "appearance",
            "solubility",
            "vapor pressure",
            "vapour pressure",
            "physical properties",
            "physical state",
            "ph",
            "auto ignition",
            "auto-ignition"
        ]):

            add(9, 10.0)

        # --------------------------------------------------------
        # SECTION 10 - STABILITY / REACTIVITY
        # --------------------------------------------------------

        if any(word in q for word in [
            "stability",
            "reactivity",
            "reactive",
            "incompatible",
            "incompatibility",
            "decomposition",
            "conditions to avoid",
            "hazardous reactions",
            "react with",
            "decompose",
            "stable"
        ]):

            add(10, 10.0)

        # --------------------------------------------------------
        # SECTION 11 - TOXICOLOGY
        # --------------------------------------------------------

        if any(word in q for word in [
            "toxic",
            "toxicity",
            "toxicological",
            "health effects",
            "carcinogenic",
            "carcinogen",
            "mutagen",
            "reproductive",
            "symptoms",
            "acute toxicity",
            "chronic effects",
            "cancer",
            "sensitization",
            "irritation"
        ]):

            add(11, 10.0)

        # --------------------------------------------------------
        # SECTION 12 - ECOLOGICAL
        # --------------------------------------------------------

        if any(word in q for word in [
            "environment",
            "environmental",
            "ecological",
            "aquatic",
            "fish",
            "daphnia",
            "algae",
            "biodegradation",
            "bioaccumulation",
            "ecotoxicity"
        ]):

            add(12, 10.0)

        # --------------------------------------------------------
        # SECTION 13 - DISPOSAL
        # --------------------------------------------------------

        if any(word in q for word in [
            "disposal",
            "dispose",
            "waste",
            "waste disposal",
            "how should i dispose",
            "how to dispose",
            "throw away",
            "get rid of",
            "drain",
            "sewer"
        ]):

            add(13, 10.0)

        # --------------------------------------------------------
        # SECTION 14 - TRANSPORT
        # --------------------------------------------------------

        if any(word in q for word in [
            "transport",
            "transportation",
            "shipping",
            "un number",
            "un no",
            "dangerous goods",
            "transport information"
        ]):

            add(14, 10.0)

        # --------------------------------------------------------
        # SECTION 15 - REGULATORY
        # --------------------------------------------------------

        if any(word in q for word in [
            "regulation",
            "regulatory",
            "legal",
            "regulatory information",
            "legislation"
        ]):

            add(15, 10.0)

        # --------------------------------------------------------
        # SECTION 16 - OTHER INFORMATION
        # --------------------------------------------------------

        if any(word in q for word in [
            "other information",
            "revision",
            "abbreviation",
            "version",
            "date of revision"
        ]):

            add(16, 10.0)

        return section_scores

    # ============================================================
    # PRIMARY SECTION
    # ============================================================

    def _detect_primary_section(
        self,
        question: str
    ) -> int:

        scores = self._detect_relevant_sections(question)

        if not scores:
            return -1

        # Lower number = higher priority
        priority = {

            8: 1,    # PPE
            5: 2,    # Fire
            4: 3,    # First Aid
            6: 4,    # Spill
            7: 5,    # Storage
            2: 6,    # Hazards
            11: 7,   # Toxicology
            10: 8,   # Stability
            3: 9,    # Composition
            9: 10,   # Physical properties
            1: 11,   # Identification
            12: 12,  # Ecology
            13: 13,  # Disposal
            14: 14,  # Transport
            15: 15,  # Regulatory
            16: 16   # Other
        }

        sorted_sections = sorted(
            scores.items(),
            key=lambda x: (
                -x[1],
                priority.get(x[0], 99)
            )
        )

        return sorted_sections[0][0]

    # ============================================================
    # QUERY EXPANSION
    # ============================================================

    def _expand_query(
        self,
        question: str
    ) -> str:

        expanded = question

        q = question.lower()

        # --------------------------------------------------------
        # PPE
        # --------------------------------------------------------

        if re.search(
            r"\bppe\b",
            question,
            flags=re.IGNORECASE
        ):

            expanded += (
                " personal protective equipment "
                "PPE exposure controls "
                "hand protection gloves "
                "eye protection "
                "respiratory protection "
                "protective clothing"
            )

        # Also recognize natural PPE questions
        if any(word in q for word in [
            "what protection",
            "what protective equipment",
            "how should i protect",
            "how should workers protect",
            "required protection"
        ]):

            expanded += (
                " PPE personal protective equipment "
                "gloves eye protection "
                "respiratory protection "
                "protective clothing "
                "exposure controls"
            )

        # --------------------------------------------------------
        # FIRE
        # --------------------------------------------------------

        if any(word in q for word in [
            "fire",
            "firefighting",
            "fire fighting",
            "extinguish",
            "extinguishing",
            "fire extinguisher",
            "firefighter"
        ]):

            expanded += (
                " fire firefighting "
                "fire fighting "
                "extinguishing media "
                "extinguisher "
                "foam "
                "carbon dioxide "
                "CO2 "
                "dry powder "
                "firefighters "
                "self-contained breathing apparatus "
                "SCBA "
                "combustion "
                "flame"
            )

        # --------------------------------------------------------
        # FIRST AID
        # --------------------------------------------------------

        if any(word in q for word in [
            "first aid",
            "eyes",
            "eye contact",
            "skin",
            "skin contact",
            "swallowed",
            "swallow",
            "inhaled",
            "inhalation"
        ]):

            expanded += (
                " first aid "
                "eye contact "
                "skin contact "
                "inhalation "
                "ingestion "
                "exposure"
            )

        # --------------------------------------------------------
        # STORAGE
        # --------------------------------------------------------

        if any(word in q for word in [
            "storage",
            "store",
            "stored"
        ]):

            expanded += (
                " storage conditions "
                "container tightly closed "
                "dry "
                "well ventilated "
                "heat "
                "ignition"
            )

        return expanded

    # ============================================================
    # EMPTY RESPONSE
    # ============================================================

    def _build_empty_response(
        self
    ) -> Dict[str, Any]:

        fallback_phrase = (
            "The uploaded SDS does not provide enough information to answer that question."
        )

        return {
            "answer": fallback_phrase,
            "found_in_sds": False,
            "sources": [],
            "primary_section": None
        }

    # ============================================================
    # MAIN RAG FUNCTION
    # ============================================================

    def answer_question(
        self,
        db: Session,
        document_id: int,
        question: str
    ) -> Dict[str, Any]:

        # ========================================================
        # 1. VALIDATE DOCUMENT
        # ========================================================

        doc = (
            db.query(Document)
            .filter(
                Document.id == document_id
            )
            .first()
        )

        if not doc:

            raise ValueError(
                f"Document with ID {document_id} not found."
            )

        # ========================================================
        # 2. QUERY EXPANSION
        # ========================================================

        expanded_question = self._expand_query(
            question
        )

        # ========================================================
        # 3. SECTION DETECTION
        # ========================================================

        relevant_sections = (
            self._detect_relevant_sections(
                question
            )
        )

        primary_section = (
            self._detect_primary_section(
                question
            )
        )

        # ========================================================
        # DEBUG
        # ========================================================

        print("\n")
        print("========================================")
        print("CHEMSAFE RAG QUERY")
        print("========================================")

        print("Original question:")
        print(question)

        print("\nExpanded query:")
        print(expanded_question)

        print("\nRelevant sections:")
        print(relevant_sections)

        print(
            "\nPrimary section:",
            primary_section
        )

        print("========================================")

        # ========================================================
        # 4. EMBEDDING
        # ========================================================

        print("\nGenerating query embedding...")

        query_vector = (
            self.embedding_service.get_embedding(
                expanded_question
            )
        )

        # ========================================================
        # 5. FAISS SEARCH
        # ========================================================

        # Keep this small for speed
        top_k = min(
            settings.TOP_K,
            3
        )

        candidates_to_retrieve = max(
            15,
            top_k * 5
        )

        print(
            "\nFAISS candidate retrieval:",
            candidates_to_retrieve
        )

        raw_matches = (
            self.vector_store.search(
                query_vector,
                k=candidates_to_retrieve
            )
        )

        if not raw_matches:

            print(
                "No FAISS matches found."
            )

            return self._build_empty_response()

        print(
            "FAISS returned",
            len(raw_matches),
            "candidates."
        )

        # ========================================================
        # 6. DISTANCE MAP
        # ========================================================

        chunk_id_to_dist = {
            chunk_id: distance
            for chunk_id, distance
            in raw_matches
        }

        chunk_ids = list(
            chunk_id_to_dist.keys()
        )

        # ========================================================
        # 7. SQLITE CHUNKS & DIRECT SECTION RETRIEVAL
        # ========================================================

        chunks = (
            db.query(SDSChunk)
            .filter(
                SDSChunk.id.in_(chunk_ids),
                SDSChunk.document_id == document_id
            )
            .all()
        )

        # --------------------------------------------------------
        # DIRECT SECTION RETRIEVAL (Part 2 Requirement)
        # --------------------------------------------------------
        # If FAISS missed the target section, directly retrieve chunks from SQLite
        target_sections = []
        if primary_section != -1:
            target_sections.append(primary_section)
        for sec in relevant_sections.keys():
            if sec not in target_sections:
                target_sections.append(sec)

        if target_sections:
            direct_section_chunks = (
                db.query(SDSChunk)
                .join(SDSSection, SDSChunk.section_id == SDSSection.id)
                .filter(
                    SDSChunk.document_id == document_id,
                    SDSSection.section_number.in_(target_sections)
                )
                .all()
            )

            chunk_map = {c.id: c for c in chunks}
            for d_chunk in direct_section_chunks:
                if d_chunk.id not in chunk_map:
                    chunk_map[d_chunk.id] = d_chunk
                    if d_chunk.id not in chunk_id_to_dist:
                        chunk_id_to_dist[d_chunk.id] = 1.0  # Baseline distance

            chunks = list(chunk_map.values())

        if not chunks:

            print(
                "FAISS matches exist but no "
                "matching SQLite chunks."
            )

            return self._build_empty_response()

        print(
            "SQLite returned",
            len(chunks),
            "chunks (including direct section retrieval)."
        )

        # ========================================================
        # 8. SECTION-AWARE RANKING
        # ========================================================

        ranked_chunks = []

        for chunk in chunks:

            distance = (
                chunk_id_to_dist[
                    chunk.id
                ]
            )

            section_number = (
                chunk.section.section_number
            )

            ranking_score = distance

            # Strong primary-section bonus
            if (
                section_number
                == primary_section
            ):

                ranking_score -= 10.0

            # Relevant section bonus
            elif (
                section_number
                in relevant_sections
            ):

                ranking_score -= (
                    relevant_sections[
                        section_number
                    ]
                )

            ranked_chunks.append(
                (
                    chunk,
                    distance,
                    ranking_score
                )
            )

        # Lower score = better
        ranked_chunks.sort(
            key=lambda x: x[2]
        )

        # ========================================================
        # 9. SELECT RELEVANT CHUNKS
        # ========================================================

        selected_chunks = []

        # First prioritize chunks from primary_section if detected
        if primary_section != -1:
            for item in ranked_chunks:
                chunk = item[0]
                if chunk.section.section_number == primary_section:
                    selected_chunks.append(item)
                    if len(selected_chunks) >= top_k:
                        break

        # Then select chunks from other relevant sections if space remains
        if len(selected_chunks) < top_k and relevant_sections:
            selected_ids = {item[0].id for item in selected_chunks}
            for item in ranked_chunks:
                chunk = item[0]
                sec_num = chunk.section.section_number
                if sec_num in relevant_sections and chunk.id not in selected_ids:
                    selected_chunks.append(item)
                    if len(selected_chunks) >= top_k:
                        break

        # Only fall back to globally ranked chunks if no relevant section chunks were found
        if not selected_chunks:
            for item in ranked_chunks:
                selected_chunks.append(item)
                if len(selected_chunks) >= top_k:
                    break

        # ========================================================
        # 10. DEBUG SELECTED CHUNKS
        # ========================================================

        print("\nSelected chunks:")
        print("----------------------------------------")

        for (
            chunk,
            distance,
            ranking_score
        ) in selected_chunks:

            print(
                f"Chunk {chunk.id} | "
                f"Section {chunk.section.section_number} | "
                f"Page {chunk.page_number} | "
                f"Distance {distance:.4f} | "
                f"Ranking {ranking_score:.4f}"
            )

        print("----------------------------------------")

        # ========================================================
        # 11. BUILD SDS CONTEXT
        # ========================================================

        context_parts = []
        sources = []

        for (
            chunk,
            distance,
            ranking_score
        ) in selected_chunks:

            section_number = (
                chunk.section.section_number
            )

            section_title = (
                chunk.section.section_title
            )

            page_number = (
                chunk.page_number
            )

            content = (
                chunk.text_content
            )

            is_primary = (
                section_number
                == primary_section
            )

            label = (
                "PRIMARY SDS SOURCE"
                if is_primary
                else "SECONDARY SDS SOURCE"
            )

            context_parts.append(
                f"""
[{label}]
SECTION: {section_number}
TITLE: {section_title}
PAGE: {page_number}

CONTENT:
{content}

[END SOURCE]
"""
            )

            sources.append(
                {
                    "chunk_id": chunk.id,
                    "section_number": section_number,
                    "section_name": section_title,
                    "page_number": page_number,
                    "content": content,
                    "retrieval_distance": distance,
                    "ranking_score": ranking_score,
                    "is_primary": is_primary
                }
            )

        context_text = "\n".join(
            context_parts
        )

        # ========================================================
        # 12. SYSTEM PROMPT (ChatGPT-Style Explanatory Safety Assistant)
        # ========================================================

        system_prompt = """You are ChemSafe AI, an expert Chemical Safety Data Sheet (SDS) assistant.

Your role is to explain chemical safety information clearly, naturally, and accurately based strictly on the retrieved SDS.

STRICT GUIDELINES:

1. Faithful Reproduction & Zero Hallucination:
   - Answer based ONLY on the provided SDS context.
   - Reproduce retrieved SDS safety information faithfully.
   - Never invent safety instructions, never make assumptions, and never extrapolate negative precautions or prohibitions not explicitly written in the SDS.
   - For extinguishing agents: State exactly what is listed under suitable extinguishing media (e.g. CO₂, foam, dry powder) and unsuitable extinguishing media (e.g. no limitations given). Never claim that water or any other agent is prohibited or unsuitable unless the SDS explicitly designates it as unsuitable extinguishing media.
   - Do NOT combine or conflate separate statements in a way that changes their meaning.
     * Environmental runoff precautions (such as preventing fire extinguishing water from contaminating surface water or groundwater) must be presented strictly as an environmental containment measure, NOT as a prohibition against using water to extinguish fires or cool containers.
     * Container cooling instructions (such as removing containers from the danger zone and cooling with water) must be stated clearly as given.

2. No Contradictory Answers & Handling Conflicting Evidence:
   - Do NOT generate contradictory statements within your answer (e.g. never say both "do not use water" and "cool container with water").
   - Do NOT silently resolve, reinterpret, or smooth over contradictory SDS evidence.
   - If the retrieved SDS evidence appears contradictory or contains conflicting instructions, clearly say that the SDS contains conflicting instructions and present them accurately rather than choosing one.

3. Preserve Critical Technical Details:
   - When the SDS specifies exact materials, measurements, ratings, or durations (such as "butyl-rubber gloves", breakthrough time of "480 minutes", "CO₂", "foam", "dry powder", or specific standards), always preserve those exact details.
   - Do NOT oversimplify specific materials to generic terms (e.g. do not reduce "butyl-rubber gloves" to just "gloves").

4. Structured Presentation:
   - Answer the user's question directly with clean organization (headings, bullet points, bold key terms).
   - At the very end of your response, provide the source citation on its own line:
     "**Source:** SDS Section X – [Section Title], Page Y" (or list multiple sections/pages if referenced).

5. Insufficient Information:
   - If the uploaded SDS does not contain enough information to answer the question, reply with:
     "The uploaded SDS does not provide enough information to answer that question."
   - Do not guess or attempt to fill in blanks.
"""

        # ========================================================
        # 13. USER PROMPT
        # ========================================================

        user_prompt = f"""SDS CONTEXT:
================================
{context_text}
================================
END SDS CONTEXT

USER QUESTION:
{question}

INSTRUCTIONS:
1. Answer the user's question directly and clearly in structured Markdown based strictly on the SDS context above.
2. Reproduce retrieved SDS safety information faithfully without inventing safety instructions or negative rules.
3. Do NOT combine statements in a way that changes their meaning (e.g. environmental runoff precautions must be reported as environmental containment, NOT as extinguishing agent prohibitions).
4. Do NOT generate contradictory statements. If the retrieved SDS evidence appears contradictory or contains conflicting instructions, clearly state that the SDS contains conflicting instructions and present the contrasting instructions accurately rather than choosing one.
5. Keep all exact technical details from the SDS (exact chemicals, CO₂, foam, dry powder, glove materials, breakthrough times).
6. At the end of your response, cite the source: "**Source:** SDS Section [number] – [Title], Page [number]."
7. If the uploaded SDS does not provide enough information to answer the question, respond with:
"The uploaded SDS does not provide enough information to answer that question."
"""

        # ========================================================
        # 14. PROMPT DEBUG
        # ========================================================

        print("\n========================================")
        print("PROMPT DEBUG")
        print("========================================")

        print(
            "System prompt characters:",
            len(system_prompt)
        )

        print(
            "User prompt characters:",
            len(user_prompt)
        )

        print(
            "Total characters:",
            len(system_prompt)
            + len(user_prompt)
        )

        print(
            "Selected chunks:",
            len(selected_chunks)
        )

        print(
            "TOP_K:",
            top_k
        )

        print(
            "Primary section:",
            primary_section
        )

        print("========================================")

        # ========================================================
        # 15. LLM GENERATION
        # ========================================================

        print(
            "\nSending context to Ollama..."
        )

        try:

            raw_answer = (
                self.llm_service.generate(
                    user_prompt,
                    system_prompt=system_prompt
                )
            )

        except ValueError as e:

            # Empty Ollama response
            print(
                "\nLLM returned empty response:"
            )
            print(e)

            return self._build_empty_response()

        except RuntimeError as e:

            print(
                "\nLLM runtime error:"
            )
            print(e)

            raise

        # ========================================================
        # 16. EMPTY RESPONSE
        # ========================================================

        if not raw_answer:

            print(
                "LLM returned empty response."
            )

            return self._build_empty_response()

        raw_answer = raw_answer.strip()

        print("\n========================================")
        print("QWEN RESPONSE")
        print("========================================")

        print(raw_answer)

        print("========================================")

        # ========================================================
        # 17. FALLBACK DETECTION
        # ========================================================

        fallback_phrase = (
            "The uploaded SDS does not provide enough information to answer that question."
        )

        lower_answer = (
            raw_answer.lower()
        )

        not_found_indicators = [
            "not provide enough information",
            "does not provide enough information",
            "not enough information",
            "not found in the uploaded sds",
            "not found in the provided sds",
            "not found in the sds",
            "not found in the context",
            "not mentioned in the uploaded sds",
            "not mentioned in the sds",
            "not provided in the sds",
            "information was not found",
            "information is not provided",
            "information is not mentioned",
            "cannot find the information"
        ]

        is_not_found = any(
            indicator in lower_answer
            for indicator
            in not_found_indicators
        )

        # ========================================================
        # 18. CHECK PRIMARY SECTION
        # ========================================================

        has_primary_chunks = (
            primary_section != -1
            and any(
                chunk.section.section_number
                == primary_section
                for (
                    chunk,
                    _,
                    _
                ) in selected_chunks
            )
        )

        # ========================================================
        # 19. FALSE REFUSAL HANDLING
        # ========================================================

        if (
            is_not_found
            and has_primary_chunks
        ):

            print(
                "\n[RAG] Qwen indicated information not found, "
                "but primary SDS evidence exists. Retrying with conversational prompt..."
            )

            retry_prompt = f"""SDS CONTEXT:
================================
{context_text}
================================
END SDS CONTEXT

USER QUESTION:
{question}

The retrieved SDS context above contains the relevant safety information to answer this question.
Do NOT say the information is missing.
Explain the answer clearly based strictly on the context above.
Reproduce SDS safety instructions faithfully without inventing rules or combining statements to change their meaning.
Preserve all specific technical details (materials, breakthrough times, specific equipment, CO₂).
Conclude with: "**Source:** SDS Section [number] – [Title], Page [number]."
"""

            try:
                retry_answer = self.llm_service.generate(
                    retry_prompt,
                    system_prompt=system_prompt
                )

                if retry_answer:
                    retry_lower = retry_answer.strip().lower()
                    retry_is_not_found = any(
                        indicator in retry_lower
                        for indicator in not_found_indicators
                    )

                    if not retry_is_not_found:
                        raw_answer = retry_answer.strip()
                        is_not_found = False
                        print("[RAG] Retry succeeded with conversational answer.")
                    else:
                        print("[RAG] Retry still returned refusal.")
            except Exception as e:
                print(f"[RAG] Retry error: {e}")

        # ========================================================
        # 20. FINAL ANSWER RESOLUTION
        # ========================================================

        if is_not_found and has_primary_chunks:
            primary_chunk = None

            for (
                chunk,
                _,
                _
            ) in selected_chunks:

                if (
                    chunk.section.section_number
                    == primary_section
                ):
                    primary_chunk = chunk
                    break

            if primary_chunk:
                clean_lines = [
                    line.strip()
                    for line in primary_chunk.text_content.splitlines()
                    if line.strip() and not line.strip().lower().startswith("section")
                ]
                summary_items = []
                for line in clean_lines[:6]:
                    if not line.startswith(("-", "*", "•")):
                        summary_items.append(f"- {line}")
                    else:
                        summary_items.append(line)
                summary_text = "\n".join(summary_items)

                answer = (
                    f"Based on the safety guidance in the SDS for {primary_chunk.section.section_title.lower()}:\n\n"
                    f"{summary_text}\n\n"
                    f"Source: SDS Section {primary_section}, Page {primary_chunk.page_number}."
                )
                found_in_sds = True
                print("[RAG] Formatted structured fallback for primary section.")
            else:
                answer = fallback_phrase
                found_in_sds = False

        elif is_not_found:
            answer = fallback_phrase
            found_in_sds = False

        else:
            answer = raw_answer
            found_in_sds = True

        # ========================================================
        # 21. RETURN
        # ========================================================

        return {
            "answer": answer,
            "found_in_sds": found_in_sds,
            "sources": sources if found_in_sds else [],
            "primary_section": primary_section if found_in_sds else None
        }