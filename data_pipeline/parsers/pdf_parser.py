"""
PDF Document Parser & Semantic Chunker.
Extracts pages, text blocks, headings, and tables from official PDF monographs
(DCHB Solapur, MoSPI HCES Factsheets, ISRO Bhuvan Standards, etc.).
"""
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple
from pypdf import PdfReader

def parse_pdf_document(filepath: Path, max_pages: int = 150) -> Tuple[List[Dict[str, Any]], Dict[str, Any], str]:
    """
    Extracts text per page and extracts semantic chunks.
    Returns (chunks, metadata, status).
    """
    if filepath.stat().st_size == 0:
        return [], {}, "EMPTY_FILE_0_BYTES"

    try:
        reader = PdfReader(str(filepath))
        total_pages = len(reader.pages)
        pages_to_read = min(total_pages, max_pages)

        doc_meta = {
            "total_pages": total_pages,
            "parsed_pages": pages_to_read,
            "title": filepath.stem.replace("_", " "),
            "author": reader.metadata.author if reader.metadata and reader.metadata.author else "Official Authority",
            "creation_date": str(reader.metadata.creation_date) if reader.metadata and reader.metadata.creation_date else None
        }

        chunks: List[Dict[str, Any]] = []
        chunk_idx = 0

        for page_num in range(pages_to_read):
            page = reader.pages[page_num]
            text = (page.extract_text() or "").strip()
            if not text:
                continue

            # Detect sections / headings by line patterns
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            current_section = f"Page {page_num + 1}"
            buffer = []

            for line in lines:
                # Simple heading detection: uppercase lines or lines ending with colon or starting with numbers
                if (line.isupper() and len(line) < 80) or re.match(r"^(SECTION|CHAPTER|TABLE|STATEMENT|\d+\.)", line, re.IGNORECASE):
                    if buffer:
                        chunk_text = "\n".join(buffer).strip()
                        if len(chunk_text) > 40:
                            chunks.append({
                                "chunk_index": chunk_idx,
                                "page": page_num + 1,
                                "section": current_section,
                                "text": chunk_text,
                                "token_count": len(chunk_text.split()),
                                "is_table": "TABLE" in current_section.upper() or "|" in chunk_text or "\t" in chunk_text
                            })
                            chunk_idx += 1
                        buffer = []
                    current_section = line
                else:
                    buffer.append(line)

            if buffer:
                chunk_text = "\n".join(buffer).strip()
                if len(chunk_text) > 40:
                    chunks.append({
                        "chunk_index": chunk_idx,
                        "page": page_num + 1,
                        "section": current_section,
                        "text": chunk_text,
                        "token_count": len(chunk_text.split()),
                        "is_table": "TABLE" in current_section.upper() or "|" in chunk_text or "\t" in chunk_text
                    })
                    chunk_idx += 1

        return chunks, doc_meta, "SUCCESS"
    except Exception as e:
        return [], {}, f"PARSING_FAILED: {str(e)}"
