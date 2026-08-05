from unittest.mock import MagicMock

from app.clients import openrouter as or_mod
from app.clients.openrouter import chat, embed_texts


def _fake_embed_client(indexes, mocker):
    mock_embed = MagicMock()
    mock_embed.data = [
        MagicMock(index=i, embedding=[float(i), float(i + 1)]) for i in indexes
    ]
    mock_client = MagicMock()
    mock_client.embeddings.create.return_value = mock_embed
    mocker.patch.object(or_mod, "_embedding_client", mock_client)
    return mock_client


def test_embed_texts_returns_in_input_order(mocker):
    # OpenRouter may return embeddings out of order; embed_texts should re-order.
    _fake_embed_client([1, 0, 2], mocker)

    result = embed_texts(["a", "b", "c"])

    assert result == [[0.0, 1.0], [1.0, 2.0], [2.0, 3.0]]


def test_embed_texts_empty(mocker):
    result = embed_texts([])
    assert result == []


def test_embed_texts_uses_embedding_model(mocker):
    mock_client = _fake_embed_client([0], mocker)

    embed_texts(["a"])

    _, kwargs = mock_client.embeddings.create.call_args
    assert kwargs["model"] == or_mod.OPENROUTER_EMBEDDING_MODEL
    assert kwargs["input"] == ["a"]


def test_chat_returns_message_content(mocker):
    mock_completion = MagicMock()
    mock_completion.choices[0].message.content = "Hello from OpenRouter"
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_completion
    mocker.patch.object(or_mod, "openrouter_client", mock_client)

    answer = chat([{"role": "user", "content": "hi"}])

    assert answer == "Hello from OpenRouter"
    mock_client.chat.completions.create.assert_called_once()


def test_chat_uses_chat_model(mocker):
    mock_completion = MagicMock()
    mock_completion.choices[0].message.content = "ok"
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_completion
    mocker.patch.object(or_mod, "openrouter_client", mock_client)

    chat([{"role": "user", "content": "hi"}])

    _, kwargs = mock_client.chat.completions.create.call_args
    assert kwargs["model"] == or_mod.OPENROUTER_CHAT_MODEL