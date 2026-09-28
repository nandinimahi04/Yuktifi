EXPLAIN_TEMPLATE = """You are explaining an already-computed financial result to a rural
entrepreneur in plain {language}. Use ONLY the following computed values and their
confidence tags. Do not introduce any number not present here. If the answer requires
a number not provided, say the data is not available rather than estimating.

Computed context:
{context_json}

User question: {question}
"""
