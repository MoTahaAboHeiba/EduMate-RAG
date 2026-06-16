from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from src.api.main import app

client = TestClient(app)

def test_api_root():
    response = client.get("/api")
    assert response.status_code == 200
    assert response.json()["message"] == "EduMate RAG API is running!"

@patch('src.document_processing.vector_store.VectorStore.get_collection_info')
def test_health_check(mock_get_info):
    mock_get_info.return_value = {"collection_name": "course_materials", "count": 42}
    
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["vector_store"]["documents_indexed"] == 42

@patch('src.core.rag_chain.RAGChain.query')
def test_query_endpoint_success(mock_rag_query):
    mock_rag_query.return_value = {
        "question": "What is the CPU?",
        "answer": "Central Processing Unit",
        "sources": ["computer Architecture Book"],
        "num_context_docs": 1,
        "conversation_turn": 1,
        "conversation_id": "conv_123",
        "is_general": False,
        "timings_ms": {"total": 120.0}
    }
    
    payload = {
        "question": "What is the CPU?",
        "num_context_docs": 3
    }
    
    response = client.post("/api/query", json=payload, headers={"X-Session-Token": "test-session"})
    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "Central Processing Unit"
    assert data["sources"] == ["computer Architecture Book"]
    mock_rag_query.assert_called_once_with(
        "What is the CPU?",
        session_token="test-session",
        num_context_docs=3,
        persist_conversation=True
    )

def test_query_endpoint_validation_empty_question():
    payload = {
        "question": "   ",
        "num_context_docs": 3
    }
    response = client.post("/api/query", json=payload)
    assert response.status_code == 400
    assert "Question cannot be empty" in response.json()["detail"]

def test_query_endpoint_validation_invalid_docs():
    payload = {
        "question": "Valid question?",
        "num_context_docs": 12  # must be between 1 and 10
    }
    response = client.post("/api/query", json=payload)
    assert response.status_code == 400
    assert "num_context_docs must be between" in response.json()["detail"]

@patch('src.core.rag_chain.RAGChain.query')
def test_query_endpoint_rate_limit(mock_rag_query):
    mock_rag_query.side_effect = RuntimeError("GROQ_RATE_LIMIT: Rate limit hit")
    
    payload = {
        "question": "Rate limit test?",
        "num_context_docs": 3
    }
    
    response = client.post("/api/query", json=payload)
    assert response.status_code == 503
    assert "rate limit reached" in response.json()["detail"].lower()

@patch('src.core.rag_chain.RAGChain.query_with_history')
def test_integration_query_success(mock_query_with_history):
    mock_query_with_history.return_value = {
        "question": "What is the CPU?",
        "answer": "Central Processing Unit",
        "sources": ["computer Architecture Book"],
        "num_context_docs": 1,
        "conversation_id": "conv-456",
        "is_general": False,
        "timings_ms": {"total": 120.0}
    }

    payload = {
        "userId": "user-123",
        "conversationId": "conv-456",
        "message": "What is the CPU?",
        "messages": [
            {"question": "What is architecture?", "answer": "Computer organization topic."}
        ]
    }

    response = client.post("/api/integrations/query", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["userId"] == "user-123"
    assert data["conversationId"] == "conv-456"
    assert data["answer"] == "Central Processing Unit"
    assert data["sources"] == ["computer Architecture Book"]
    mock_query_with_history.assert_called_once_with(
        question="What is the CPU?",
        history=[{"question": "What is architecture?", "answer": "Computer organization topic."}],
        conversation_id="conv-456",
        user_id="user-123",
        num_context_docs=3,
    )

@patch('src.core.rag_chain.RAGChain.query_with_history')
def test_integration_query_caps_history_to_latest_five(mock_query_with_history):
    mock_query_with_history.return_value = {
        "question": "Current question?",
        "answer": "Answer",
        "sources": [],
        "num_context_docs": 0,
        "conversation_id": "conv-456",
        "is_general": False,
        "timings_ms": {}
    }

    payload = {
        "userId": "user-123",
        "conversationId": "conv-456",
        "message": "Current question?",
        "messages": [
            {"question": f"Q{i}", "answer": f"A{i}"}
            for i in range(7)
        ]
    }

    response = client.post("/api/integrations/query", json=payload)
    assert response.status_code == 200
    call_kwargs = mock_query_with_history.call_args.kwargs
    assert call_kwargs["history"] == [
        {"question": "Q2", "answer": "A2"},
        {"question": "Q3", "answer": "A3"},
        {"question": "Q4", "answer": "A4"},
        {"question": "Q5", "answer": "A5"},
        {"question": "Q6", "answer": "A6"},
    ]

def test_integration_query_validation_empty_user_id():
    payload = {
        "userId": " ",
        "conversationId": "conv-456",
        "message": "What is the CPU?",
        "messages": []
    }

    response = client.post("/api/integrations/query", json=payload)
    assert response.status_code == 400
    assert "userId cannot be empty" in response.json()["detail"]
