from pathlib import Path
import os
import logging
from .store import add_document

logger = logging.getLogger("yukti.rag_ingest")


def extract_text(path: str) -> str:
    p = Path(path)
    ext = p.suffix.lower()
    
    if ext in {'.txt', '.md', '.markdown', '.csv', '.json', '.xml', '.html', '.geojson'}:
        return p.read_text(encoding='utf-8', errors='ignore')
        
    if ext == '.pdf':
        try:
            from pypdf import PdfReader
            reader = PdfReader(str(p))
            pages = []
            for i, page in enumerate(reader.pages):
                text = page.extract_text()
                if text:
                    pages.append(f"--- Page {i+1} ---\n{text}")
            return '\n\n'.join(pages)
        except Exception as e:
            logger.warning("PDF extraction error for %s: %s", path, e)
            return ""
            
    if ext == '.docx':
        try:
            from docx import Document
            return '\n'.join(x.text for x in Document(str(p)).paragraphs)
        except Exception as e:
            logger.warning("DOCX extraction error for %s: %s", path, e)
            return ""
            
    if ext in {'.xlsx', '.xls'}:
        try:
            import pandas as pd
            # Read first few sheets or all sheets
            excel_file = pd.ExcelFile(str(p))
            sheets_text = []
            for sheet_name in excel_file.sheet_names[:5]: # index top sheets
                df = pd.read_excel(excel_file, sheet_name=sheet_name)
                sheets_text.append(f"=== Sheet: {sheet_name} ===\n" + df.to_string(index=False, max_rows=100))
            return '\n\n'.join(sheets_text)
        except Exception as e:
            logger.warning("Excel extraction error for %s: %s", path, e)
            return ""
            
    logger.info("Unsupported or binary RAG file type skipped: %s", ext)
    return ""


def ingest_file(path: str, source: str = 'local', source_url: str = '', effective_date: str = '') -> dict:
    p = Path(path)
    content = extract_text(path)
    if not content.strip():
        raise ValueError(f'No extractable text found in {p.name}')
    return add_document(p.name, content, source, source_url, effective_date, {'path': str(p)})


def ingest_directory(dir_path: str, source: str = 'SIH Documents') -> int:
    """Recursively ingest all supported files from a directory."""
    p = Path(dir_path)
    if not p.exists() or not p.is_dir():
        logger.warning("RAG Ingest directory not found: %s", dir_path)
        return 0
        
    indexed = 0
    for root, _, files in os.walk(str(p)):
        for f in files:
            file_path = os.path.join(root, f)
            try:
                content = extract_text(file_path)
                if content and len(content.strip()) > 50:
                    add_document(
                        title=f,
                        content=content,
                        source=source,
                        source_url=file_path,
                        effective_date="2024-01-01",
                        metadata={"filename": f, "path": file_path}
                    )
                    indexed += 1
                    logger.info("Ingested RAG document: %s (%d chars)", f, len(content))
            except Exception as exc:
                logger.warning("Failed to ingest %s: %s", file_path, exc)
                
    return indexed
