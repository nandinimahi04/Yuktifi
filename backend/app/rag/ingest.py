from pathlib import Path
from .store import add_document

def extract_text(path: str) -> str:
    p=Path(path)
    ext=p.suffix.lower()
    if ext in {'.txt','.md','.markdown','.csv','.json'}:
        return p.read_text(encoding='utf-8', errors='ignore')
    if ext == '.pdf':
        from pypdf import PdfReader
        return '\n'.join(page.extract_text() or '' for page in PdfReader(str(p)).pages)
    if ext == '.docx':
        from docx import Document
        return '\n'.join(x.text for x in Document(str(p)).paragraphs)
    raise ValueError(f'Unsupported RAG file type: {ext}')

def ingest_file(path: str, source: str = 'local', source_url: str = '', effective_date: str = '') -> dict:
    p=Path(path)
    content=extract_text(path)
    if not content.strip(): raise ValueError('No extractable text found')
    return add_document(p.name, content, source, source_url, effective_date, {'path': str(p)})
