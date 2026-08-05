from app.services.llm import build_prompt, generate_answer


def test_build_prompt_includes_context():
    prompt = build_prompt("What is X?", ["chunk one", "chunk two"], [])
    assert "chunk one" in prompt
    assert "chunk two" in prompt
    assert "What is X?" in prompt


def test_build_prompt_includes_history():
    history = [{"question": "previous q", "answer": "previous a"}]
    prompt = build_prompt("What is X?", ["chunk"], history)
    assert "previous q" in prompt
    assert "previous a" in prompt


def test_generate_answer(mock_openrouter):
    answer = generate_answer("Question", ["chunk"], [], mock_openrouter)
    assert answer == "Mocked answer"
    mock_openrouter.chat.completions.create.assert_called_once()


def test_generate_answer_uses_chat_model(mock_openrouter):
    generate_answer("Question", ["chunk"], [], mock_openrouter)
    _, kwargs = mock_openrouter.chat.completions.create.call_args
    assert kwargs["model"] == "deepseek/deepseek-chat"
    assert kwargs["messages"][0]["role"] == "user"
    assert "Question" in kwargs["messages"][0]["content"]