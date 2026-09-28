import re

def extract_numbers(text: str) -> set[str]:
    return set(re.findall(r"\d[\d,]*\.?\d*", text))

def validate_llm_output(llm_text: str, allowed_context_numbers: set[str]) -> tuple[bool, str]:
    """
    Returns (is_valid, reason). Rejects the LLM's narration if it contains
    any number not present in the context it was given — this is the check
    that must fire in a rehearsed test (Section 40, Top-5-fixes #4).
    """
    found = extract_numbers(llm_text)
    normalized_allowed = {n.replace(",", "") for n in allowed_context_numbers}
    for n in found:
        if n.replace(",", "") not in normalized_allowed:
            return False, f"Unrecognized number '{n}' not present in provided context."
    return True, "ok"
