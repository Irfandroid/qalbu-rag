from fastapi.testclient import TestClient

from app.api.dependencies import get_rag
from app.core.config import get_settings
from app.main import app
from app.models.chat import QalbuResponse


class FakeRag:
    async def ask(self, query: str, request_id: str) -> QalbuResponse:
        return QalbuResponse(answer="Refleksi", references=[])

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
    assert (
        client.post("/api/chat", json={"message": "Aku sedang sedih"}).json()["answer"]
        == "Refleksi"
    )
    themes = client.get("/api/themes")
    assert themes.status_code == 200
    assert "kecemasan" in themes.json()["themes"]
    app.dependency_overrides.clear()


def test_sse_chat_emits_only_final_validated_response():
    app.dependency_overrides[get_rag] = lambda: FakeRag()
    client = TestClient(app)
    response = client.post("/api/v1/chat", json={"message": "Aku sedang sedih"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    body = response.text
    assert "event: verses" not in body
    assert "event: token" not in body
    assert body.index("event: response") < body.index("event: done")
    app.dependency_overrides.clear()


def test_public_system_endpoints_do_not_expose_secrets():
    client = TestClient(app)
    config = client.get("/api/v1/config/public")
    assert config.status_code == 200
    assert "groq_api_key" not in config.text
    assert client.get("/api/v1/sources").status_code == 200
    assert client.get("/api/v1/eval/report").status_code == 200


def test_chat_reports_missing_configuration_as_503(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "")
    monkeypatch.setenv("SUPABASE_URL", "")
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "")
    get_settings.cache_clear()
    client = TestClient(app)
    response = client.post("/api/chat", json={"message": "Aku sedang sedih"})
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "RAG_UNAVAILABLE"
    get_settings.cache_clear()
