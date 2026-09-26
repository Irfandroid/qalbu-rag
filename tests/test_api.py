from fastapi.testclient import TestClient

from app.api.dependencies import get_rag
from app.core.config import get_settings
from app.main import app


class FakeRag:
    async def stream_events(self, request, request_id):
        yield "response", {
            "answer": "Refleksi ringkas",
            "references": [],
            "evidence": [],
            "safety_note": None,
        }
        yield "done", {"profile": "local", "request_id": request_id}


def test_health_and_chat():
    app.dependency_overrides[get_rag] = lambda: FakeRag()
    client = TestClient(app)
    assert client.get("/api/health").status_code == 200
    response = client.post("/api/v1/chat", json={"message": "Aku sedang sedih"})
    assert response.status_code == 200
    assert "Refleksi ringkas" in response.text
    app.dependency_overrides.clear()


def test_sse_chat_emits_only_final_validated_response():
    app.dependency_overrides[get_rag] = lambda: FakeRag()
    response = TestClient(app).post("/api/v1/chat", json={"message": "Aku sedang sedih"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: verses" not in response.text
    assert "event: token" not in response.text
    assert response.text.index("event: response") < response.text.index("event: done")
    app.dependency_overrides.clear()


def test_removed_non_mvp_routes_are_not_registered():
    client = TestClient(app)
    assert client.get("/api/themes").status_code == 404
    assert client.get("/api/v1/sources").status_code == 404
    assert client.get("/api/v1/eval/report").status_code == 404
    assert client.post("/api/v1/feedback", json={}).status_code in {404, 405}


def test_chat_reports_missing_configuration_as_503(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "")
    monkeypatch.setenv("JINA_API_KEY", "")
    monkeypatch.setenv("SUPABASE_URL", "")
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "")
    get_settings.cache_clear()
    response = TestClient(app).post("/api/v1/chat", json={"message": "Aku sedang sedih"})
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "RAG_UNAVAILABLE"
    get_settings.cache_clear()
