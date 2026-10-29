import re
from typing import Dict, List, Tuple, Any


# Standard 16-section SDS structure
SDS_SECTIONS = {
    1: "Identification",
    2: "Hazard(s) Identification",
    3: "Composition/Information on Ingredients",
    4: "First-Aid Measures",
    5: "Fire-Fighting Measures",
    6: "Accidental Release Measures",
    7: "Handling and Storage",
    8: "Exposure Controls / Personal Protection",
    9: "Physical and Chemical Properties",
    10: "Stability and Reactivity",
    11: "Toxicological Information",
    12: "Ecological Information",
    13: "Disposal Considerations",
    14: "Transport Information",
    15: "Regulatory Information",
    16: "Other Information",
}


class SectionDetector:

    # More flexible patterns for PDF-extracted text.
    # We intentionally allow different punctuation and spacing.
    SECTION_PATTERNS = {
        1: re.compile(
            r"\b(?:section\s*)?1\s*[\.\:\-]?\s*identification\b",
            re.IGNORECASE
        ),
        2: re.compile(
            r"\b(?:section\s*)?2\s*[\.\:\-]?\s*hazard(?:s)?(?:\s+identification)?\b",
            re.IGNORECASE
        ),
        3: re.compile(
            r"\b(?:section\s*)?3\s*[\.\:\-]?\s*(?:composition|information\s+on\s+ingredients|ingredients)\b",
            re.IGNORECASE
        ),
        4: re.compile(
            r"\b(?:section\s*)?4\s*[\.\:\-]?\s*first[\s\-]*aid\s+measures\b",
            re.IGNORECASE
        ),
        5: re.compile(
            r"\b(?:section\s*)?5\s*[\.\:\-]?\s*fire[\s\-]*fighting\s+measures\b",
            re.IGNORECASE
        ),
        6: re.compile(
            r"\b(?:section\s*)?6\s*[\.\:\-]?\s*accidental\s+release\s+measures\b",
            re.IGNORECASE
        ),
        7: re.compile(
            r"\b(?:section\s*)?7\s*[\.\:\-]?\s*handling\s+and\s+storage\b",
            re.IGNORECASE
        ),
        8: re.compile(
            r"\b(?:section\s*)?8\s*[\.\:\-]?\s*(?:exposure|personal\s+protection)\b",
            re.IGNORECASE
        ),
        9: re.compile(
            r"\b(?:section\s*)?9\s*[\.\:\-]?\s*physical\s+and\s+chemical\s+properties\b",
            re.IGNORECASE
        ),
        10: re.compile(
            r"\b(?:section\s*)?10\s*[\.\:\-]?\s*stability\s+and\s+reactivity\b",
            re.IGNORECASE
        ),
        11: re.compile(
            r"\b(?:section\s*)?11\s*[\.\:\-]?\s*toxicological\s+information\b",
            re.IGNORECASE
        ),
        12: re.compile(
            r"\b(?:section\s*)?12\s*[\.\:\-]?\s*ecological\s+information\b",
            re.IGNORECASE
        ),
        13: re.compile(
            r"\b(?:section\s*)?13\s*[\.\:\-]?\s*disposal\s+considerations\b",
            re.IGNORECASE
        ),
        14: re.compile(
            r"\b(?:section\s*)?14\s*[\.\:\-]?\s*transport\s+information\b",
            re.IGNORECASE
        ),
        15: re.compile(
            r"\b(?:section\s*)?15\s*[\.\:\-]?\s*regulatory\s+information\b",
            re.IGNORECASE
        ),
        16: re.compile(
            r"\b(?:section\s*)?16\s*[\.\:\-]?\s*other\s+information\b",
            re.IGNORECASE
        ),
    }

    @staticmethod
    def _normalize_text(text: str) -> str:
        """
        Normalize PDF-extracted text so section headers that contain
        unusual spaces, line breaks, or punctuation can be detected.
        """
        text = text.replace("\u00a0", " ")
        text = text.replace("\u2010", "-")
        text = text.replace("\u2011", "-")
        text = text.replace("\u2012", "-")
        text = text.replace("\u2013", "-")
        text = text.replace("\u2014", "-")

        # Collapse repeated whitespace/newlines.
        text = re.sub(r"\s+", " ", text)

        return text.strip()

    @classmethod
    def _detect_section(cls, line: str):
        """
        Detect a section header from a single PDF-extracted line.
        """

        normalized = cls._normalize_text(line)

        if not normalized:
            return None

        # First check all standard section patterns.
        for sec_num, pattern in cls.SECTION_PATTERNS.items():
            if pattern.search(normalized):
                return sec_num

        return None

    @classmethod
    def detect_sections(
        cls,
        pages_text: List[Tuple[int, str]]
    ) -> Dict[int, Dict[str, Any]]:
        """
        Detect SDS sections and preserve page/line information.

        Handles common PDF extraction problems such as:
        - SECTION 5: Fire-Fighting Measures
        - Section 5 - Fire-Fighting Measures
        - 5. Fire-Fighting Measures
        - irregular spaces
        - non-breaking spaces
        - Unicode hyphens
        """

        all_lines: List[Tuple[int, str]] = []

        for page_num, text in pages_text:
            for line in text.split("\n"):
                all_lines.append((page_num, line))

        sections: Dict[int, Dict[str, Any]] = {
            0: {
                "title": "Document Header / Preamble",
                "content": "",
                "page_start": pages_text[0][0] if pages_text else 1,
                "page_lines": [],
            }
        }

        for sec_num in range(1, 17):
            sections[sec_num] = {
                "title": f"Section {sec_num}: {SDS_SECTIONS[sec_num]}",
                "content": "",
                "page_start": None,
                "page_lines": [],
            }

        current_section = 0

        for page_num, original_line in all_lines:

            stripped = original_line.strip()

            # Preserve empty lines.
            if not stripped:
                sections[current_section]["page_lines"].append(
                    (page_num, original_line)
                )
                continue

            # Try direct detection.
            detected = cls._detect_section(stripped)

            if detected is not None:
                current_section = detected

                if sections[current_section]["page_start"] is None:
                    sections[current_section]["page_start"] = page_num

                # Keep the section header in the section content.
                sections[current_section]["page_lines"].append(
                    (page_num, original_line)
                )
                continue

            # Add normal content to current section.
            sections[current_section]["page_lines"].append(
                (page_num, original_line)
            )

        # Build final content strings.
        for sec_num, sec_data in sections.items():
            sec_data["content"] = "\n".join(
                line for _, line in sec_data["page_lines"]
            )

        return sections