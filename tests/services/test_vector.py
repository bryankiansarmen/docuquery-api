from app.services.vector import (
    store_document_chunks, search_document_chunks,
    get_semantic_question_cache, save_semantic_question_cache
)

def test_store_document_chunks(mock_chroma, mock_gemini):
    chunks = [
        {"index": 0, "text": "test chunk 1"}, 
        {"index": 1, "text": "test chunk 2"}
    ]
    file_name = "test.pdf"
    document_id = "test-hash"
    
    store_document_chunks(chunks, file_name, mock_gemini, document_id)
    
    assert mock_gemini.models.embed_content.call_count == 2
    assert mock_chroma["docs"].add.call_count == 2
    
def test_search_document_chunks(mock_chroma, mock_gemini):
    question = "What is the answer?"
    mock_chroma["docs"].query.return_value = {
        "documents": [["Result 1", "Result 2"]]
    }
    
    results = search_document_chunks(question, mock_gemini)
    
    assert results == ["Result 1", "Result 2"]
    mock_chroma["docs"].query.assert_called_once()
    mock_gemini.models.embed_content.assert_called_once()
    
def test_search_document_chunks_empty(mock_chroma, mock_gemini):
    question = "What is the answer?"
    mock_chroma["docs"].query.return_value = {
        "documents": []
    }
    
    results = search_document_chunks(question, mock_gemini)
    
    assert results == []
    
def test_get_semantic_question_cache_hit(mock_chroma, mock_gemini):
    # Simulated hit with small distance (0.1 < 0.3 threshold)
    mock_chroma["semantic"].query.return_value = {
        "documents": [["semantic answer"]],
        "distances": [[0.1]],  
        "metadatas": [[{"source": "test.pdf"}]]
    }
    
    response = get_semantic_question_cache("question", "test.pdf", mock_gemini)
    
    assert response is not None
    assert response["answer"] == "semantic answer"
    assert response["metadata"]["source"] == "test.pdf"

def test_get_semantic_question_cache_miss_distance(mock_chroma, mock_gemini):
    # Distance is larger than the 0.3 default threshold
    mock_chroma["semantic"].query.return_value = {
        "documents": [["semantic answer"]],
        "distances": [[0.5]],  
        "metadatas": [[{"source": "test.pdf"}]]
    }
    
    response = get_semantic_question_cache("question", "test.pdf", mock_gemini)
    
    assert response is None

def test_save_semantic_question_cache(mock_chroma, mock_gemini):
    question = "q"
    answer = "a"
    file_name = "file.pdf"
    
    save_semantic_question_cache(question, answer, file_name, mock_gemini)
    
    mock_chroma["semantic"].upsert.assert_called_once()
