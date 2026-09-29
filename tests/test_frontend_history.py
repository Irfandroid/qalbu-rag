from pathlib import Path


def test_chat_ui_keeps_local_history_controls() -> None:
    html = Path("frontend/index.html").read_text(encoding="utf-8")
    assert 'id="new-chat"' in html
    assert 'id="history-list"' in html
    assert "qalbu.chat-history.v1" in html
    assert "localStorage" in html
