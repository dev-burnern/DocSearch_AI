from fastapi.testclient import TestClient

from backend.app.dev.ai_stub import app


def test_ai_stub_exposes_openai_compatible_chat_and_embeddings() -> None:
    client = TestClient(app)

    models_response = client.get("/v1/models")
    assert models_response.status_code == 200
    assert {model["id"] for model in models_response.json()["data"]} == {
        "local-dev-llm",
        "local-dev-embedding",
    }

    chat_response = client.post(
        "/v1/chat/completions",
        json={
            "model": "local-dev-llm",
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "질문:\nhello\n\n"
                        "문서 컨텍스트:\n[1] memo.txt#0\nhello context"
                    ),
                }
            ],
        },
    )
    assert chat_response.status_code == 200
    content = chat_response.json()["choices"][0]["message"]["content"]
    assert content
    assert "질문: hello" in content
    assert "문서 컨텍스트" not in content
    assert "[1]" in content

    embedding_response = client.post(
        "/v1/embeddings",
        json={
            "model": "local-dev-embedding",
            "input": ["alpha", "beta"],
        },
    )
    assert embedding_response.status_code == 200
    payload = embedding_response.json()
    assert [item["index"] for item in payload["data"]] == [0, 1]
    assert len(payload["data"][0]["embedding"]) == 8
