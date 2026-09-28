from __future__ import annotations
import json, re
from datetime import datetime, timezone
from sqlalchemy import text
from app.core.db import engine

SCHEMA = """
CREATE TABLE IF NOT EXISTS yukti_rag_documents (
 id TEXT PRIMARY KEY, title TEXT NOT NULL, source TEXT, source_url TEXT, effective_date TEXT, metadata TEXT, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS yukti_rag_chunks (
 id TEXT PRIMARY KEY, document_id TEXT NOT NULL, chunk_index INTEGER NOT NULL, content TEXT NOT NULL, metadata TEXT, created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_yukti_rag_document ON yukti_rag_chunks(document_id);
"""

# Weight of a title match relative to a full body match. Kept well below 1 so
# title relevance refines body relevance rather than replacing it.
TITLE_MATCH_WEIGHT = 0.5

def ensure_schema():
    with engine.begin() as conn:
        for s in SCHEMA.split(';'):
            if s.strip(): conn.execute(text(s))

def _tokens(s: str) -> set[str]:
    return {x for x in re.findall(r"[a-zA-Z0-9_]{2,}", s.lower())}

def add_document(title: str, content: str, source: str = '', source_url: str = '', effective_date: str = '', metadata: dict | None = None, chunk_size: int = 1800, overlap: int = 250) -> dict:
    ensure_schema()
    import hashlib
    doc_id = 'doc_' + hashlib.sha256((title + source_url).encode()).hexdigest()[:20]
    now = datetime.now(timezone.utc).isoformat()
    chunks=[]
    start=0
    while start < len(content):
        end=min(len(content), start+chunk_size)
        chunks.append(content[start:end])
        if end == len(content): break
        start=max(end-overlap, start+1)
    with engine.begin() as conn:
        conn.execute(text('INSERT OR REPLACE INTO yukti_rag_documents(id,title,source,source_url,effective_date,metadata,created_at) VALUES (:id,:title,:source,:url,:date,:meta,:created)'),
                     {'id':doc_id,'title':title,'source':source,'url':source_url,'date':effective_date,'meta':json.dumps(metadata or {}),'created':now})
        conn.execute(text('DELETE FROM yukti_rag_chunks WHERE document_id=:id'), {'id':doc_id})
        for i, chunk in enumerate(chunks):
            cid=f'{doc_id}_{i}'
            conn.execute(text('INSERT INTO yukti_rag_chunks(id,document_id,chunk_index,content,metadata,created_at) VALUES (:id,:doc,:idx,:content,:meta,:created)'),
                         {'id':cid,'doc':doc_id,'idx':i,'content':chunk,'meta':json.dumps(metadata or {}),'created':now})
    return {'document_id':doc_id,'title':title,'chunks':len(chunks)}

def search(query: str, top_k: int = 5) -> list[dict]:
    ensure_schema(); q=_tokens(query)
    if not q: return []
    with engine.begin() as conn:
        rows=conn.execute(text('SELECT c.id,c.content,c.metadata,d.title,d.source,d.source_url,d.effective_date FROM yukti_rag_chunks c JOIN yukti_rag_documents d ON d.id=c.document_id')).mappings().all()
    scored=[]
    for r in rows:
        # Tokenize both content and title for overlap scoring
        toks = _tokens(r['content'])
        title_toks = _tokens(r['title'])
        overlap = len(q & toks)
        title_overlap = len(q & title_toks)
        if overlap or title_overlap:
            # Coverage of the query by the chunk body, in [0, 1].
            base_score = overlap / max(1, len(q)) if overlap else 0
            # A title match is worth a meaningful premium over a body match, but
            # it must stay on the same scale. It was previously weighted 50x,
            # which made a single shared word in a title ("Micro", "Scheme")
            # outrank a document that matched the entire query in its body.
            title_boost = TITLE_MATCH_WEIGHT * (title_overlap / max(1, len(q))) if title_overlap else 0
            # Prefer the chunk that concentrates the matched terms rather than
            # merely being long.
            length_factor = 0.15 * (overlap / max(1, len(toks))) if overlap else 0
            score = base_score + title_boost + length_factor
            scored.append((score, dict(r)))
    scored.sort(key=lambda x: (x[0], x[1]["id"]), reverse=True)
    return [dict(item, score=round(score, 4)) for score, item in scored[:max(1, min(top_k, 20))]]
