from unittest.mock import MagicMock

from rag_qa import embeddings


def _make_mock_client(vectors):
    mock_client = MagicMock()
    mock_embeddings = [MagicMock(values=v) for v in vectors]
    mock_client.models.embed_content.return_value = MagicMock(
        embeddings=mock_embeddings
    )
    return mock_client


def test_embed_query_uses_retrieval_query_task_type():
    mock_client = _make_mock_client([[0.1, 0.2, 0.3]])

    result = embeddings.embed_query("什麼是RAG", client=mock_client)

    assert result == [0.1, 0.2, 0.3]
    _, kwargs = mock_client.models.embed_content.call_args
    assert kwargs["config"].task_type == "RETRIEVAL_QUERY"


def test_embed_documents_uses_retrieval_document_task_type_and_preserves_order():
    mock_client = _make_mock_client([[0.1], [0.2], [0.3]])

    result = embeddings.embed_documents(["doc1", "doc2", "doc3"], client=mock_client)

    assert result == [[0.1], [0.2], [0.3]]
    _, kwargs = mock_client.models.embed_content.call_args
    assert kwargs["config"].task_type == "RETRIEVAL_DOCUMENT"
    assert kwargs["contents"] == ["doc1", "doc2", "doc3"]


def test_embed_documents_empty_list_returns_empty_without_calling_api():
    mock_client = _make_mock_client([])

    result = embeddings.embed_documents([], client=mock_client)

    assert result == []
    mock_client.models.embed_content.assert_not_called()
