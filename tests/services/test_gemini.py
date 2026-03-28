from app.services.gemini import build_prompt, generate_answer

def test_build_prompt():
    question = "Who is the author?"
    chunks = ["Context snippet 1", "Context snippet 2"]
    history = [{"question": "Hi", "answer": "Hello there"}]

    prompt = build_prompt(question, chunks, history)
    
    assert "Context snippet 1\n\nContext snippet 2" in prompt
    assert "User: Hi" in prompt
    assert "Assistant: Hello there" in prompt
    assert "Question: Who is the author?" in prompt

def test_build_prompt_empty_history():
    question = "Summary?"
    chunks = ["Data"]
    history = []
    
    prompt = build_prompt(question, chunks, history)
    
    assert "<history>" not in prompt
    assert "Question: Summary?" in prompt

def test_generate_answer(mock_gemini):
    answer = generate_answer("Question", ["chunk"], [], mock_gemini)
    
    assert answer == "Mocked answer"
    mock_gemini.models.generate_content.assert_called_once()
