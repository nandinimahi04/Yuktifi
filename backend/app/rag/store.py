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

# Weight of a title match relative to a full body match.
TITLE_MATCH_WEIGHT = 1.5

STOPWORDS = {
    'what', 'is', 'the', 'under', 'for', 'in', 'of', 'and', 'to', 'a', 'an', 'are', 'does', 
    'with', 'on', 'at', 'by', 'from', 'as', 'that', 'this', 'it', 'or', 'be', 'how', 'why', 'can'
}

def ensure_schema():
    with engine.begin() as conn:
        for s in SCHEMA.split(';'):
            if s.strip(): conn.execute(text(s))

def _tokens(s: str, filter_stops: bool = True) -> list[str]:
    toks = [x for x in re.findall(r"[a-zA-Z0-9_]{2,}", s.lower())]
    if filter_stops:
        filtered = [x for x in toks if x not in STOPWORDS]
        return filtered if filtered else toks
    return toks

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
    import math
    from collections import Counter

    ensure_schema()
    q_terms = _tokens(query, filter_stops=True)
    if not q_terms:
        return []

    with engine.begin() as conn:
        rows = conn.execute(text(
            'SELECT c.id, c.content, c.metadata, d.title, d.source, d.source_url, d.effective_date '
            'FROM yukti_rag_chunks c JOIN yukti_rag_documents d ON d.id=c.document_id'
        )).mappings().all()

    if not rows:
        return []

    N = len(rows)
    doc_freqs = Counter()
    doc_lens = []
    chunk_tokens = []
    title_tokens = []

    for r in rows:
        c_toks = _tokens(r['content'], filter_stops=True)
        t_toks = _tokens(r['title'], filter_stops=True)
        chunk_tokens.append(c_toks)
        title_tokens.append(t_toks)
        doc_lens.append(len(c_toks) + len(t_toks))
        for t in set(c_toks + t_toks):
            doc_freqs[t] += 1

    avgdl = sum(doc_lens) / max(1, N)
    k1 = 1.5
    b = 0.75

    scored = []
    for i, r in enumerate(rows):
        c_terms = chunk_tokens[i]
        t_terms = title_tokens[i]
        dl = doc_lens[i]
        score = 0.0
        matched = 0

        for term in q_terms:
            df = doc_freqs.get(term, 0)
            if df == 0:
                continue
            idf = math.log((N - df + 0.5) / (df + 0.5) + 1.0)
            t_cnt = t_terms.count(term)
            c_cnt = c_terms.count(term)
            if t_cnt > 0 or c_cnt > 0:
                matched += 1
                tf = c_cnt + 2.5 * t_cnt
                norm_tf = (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * (dl / avgdl)))
                score += idf * norm_tf

        if score > 0 and matched > 0:
            coverage = (matched / len(q_terms)) ** 2.0
            final_score = score * coverage
            scored.append((final_score, dict(r)))

    scored.sort(key=lambda x: (x[0], x[1]["id"]), reverse=True)
    return [dict(item, score=round(score, 4)) for score, item in scored[:max(1, min(top_k, 20))]]


