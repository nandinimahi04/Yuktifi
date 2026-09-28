from app.ai_layer.numeric_validator import validate_llm_output

def test_rejects_hallucinated_number():
    context_numbers = {"84", "1,00,000"}
    bad_output = "Your score is 84 and your loan is 2,50,000."  # 2,50,000 not in context
    is_valid, _ = validate_llm_output(bad_output, context_numbers)
    assert is_valid is False

def test_accepts_grounded_numbers():
    context_numbers = {"84", "100000"}
    good_output = "Your score is 84, based on a project of 100000 rupees."
    is_valid, _ = validate_llm_output(good_output, context_numbers)
    assert is_valid is True
