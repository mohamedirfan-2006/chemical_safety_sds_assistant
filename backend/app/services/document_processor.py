import fitz
from typing import Dict, List, Tuple
from backend.app.services.section_detector import SectionDetector

class DocumentProcessor:
    @staticmethod
    def extract_text(pdf_path: str) -> List[Tuple[int, str]]:
        """
        Extracts plain text page-by-page from the given PDF file.
        
        Args:
            pdf_path: Absolute path to the PDF file.
            
        Returns:
            List of tuples (page_number, page_text).
        """
        pages_text: List[Tuple[int, str]] = []
        
        # Open PDF using PyMuPDF
        doc = fitz.open(pdf_path)
        for page_idx in range(len(doc)):
            page = doc.load_page(page_idx)
            text = page.get_text("text")  # Standard text extraction
            pages_text.append((page_idx + 1, text))
            
        doc.close()
        return pages_text

    @staticmethod
    def chunk_section(
        page_lines: List[Tuple[int, str]], 
        max_chunk_chars: int = 800, 
        overlap_chars: int = 150
    ) -> List[Dict[str, any]]:
        """
        Chunks the lines of a section while respecting line boundaries and preserving page numbers.
        Uses a sliding window over lines to create overlap.
        
        Args:
            page_lines: List of tuples (page_num, line_text)
            max_chunk_chars: Maximum character length for a single chunk.
            overlap_chars: Target character overlap between consecutive chunks.
            
        Returns:
            List of dicts containing:
                - text: The chunk text
                - page_num: The starting page number of the chunk
        """
        chunks: List[Dict[str, any]] = []
        if not page_lines:
            return chunks

        current_lines: List[Tuple[int, str]] = []
        current_len = 0

        for page_num, line in page_lines:
            line_len = len(line) + 1  # count the newline
            
            # If adding this line exceeds the chunk size, we finalize the current chunk
            if current_len + line_len > max_chunk_chars and current_lines:
                # Store the chunk
                chunk_text = "\n".join([text for _, text in current_lines])
                chunks.append({
                    "text": chunk_text,
                    "page_num": current_lines[0][0]  # Take page number of the first line in chunk
                })
                
                # Backtrack to build overlap
                overlap_lines = []
                overlap_len = 0
                # Iterate backwards to gather overlap lines
                for p_num, l_text in reversed(current_lines):
                    l_len = len(l_text) + 1
                    if overlap_len + l_len > overlap_chars and overlap_lines:
                        break
                    overlap_lines.insert(0, (p_num, l_text))
                    overlap_len += l_len
                    
                current_lines = overlap_lines
                current_len = overlap_len

            current_lines.append((page_num, line))
            current_len += line_len

        # Append final chunk if there are lines left
        if current_lines:
            chunk_text = "\n".join([text for _, text in current_lines])
            chunks.append({
                "text": chunk_text,
                "page_num": current_lines[0][0]
            })

        return chunks

    @classmethod
    def process_pdf(
        cls, 
        pdf_path: str, 
        max_chunk_chars: int = 800, 
        overlap_chars: int = 150
    ) -> Dict[int, Dict[str, any]]:
        """
        Runs the full document processing pipeline:
        Text Extraction -> Section Detection -> Section Chunking
        
        Args:
            pdf_path: Path to the SDS PDF file.
            max_chunk_chars: Max character length per chunk.
            overlap_chars: Target overlap character length.
            
        Returns:
            Dict containing detected sections and their computed chunks.
        """
        # 1. Extract text from PDF
        pages_text = cls.extract_text(pdf_path)
        
        # 2. Detect the 16 GHS sections
        sections = SectionDetector.detect_sections(pages_text)
        
        # 3. Chunk each section individually
        for sec_idx, sec_data in sections.items():
            page_lines = sec_data["page_lines"]
            chunks = cls.chunk_section(page_lines, max_chunk_chars, overlap_chars)
            sec_data["chunks"] = chunks
            
        return sections
