from app.rag.chunking import make_chunks
from tests.conftest import document


def test_parent_generates_children_with_parent_id():
    chunks = make_chunks(document())
    assert chunks
    assert all(chunk.parent_id == "al-baqarah-286" for chunk in chunks)
    assert chunks[0].chunk_type == "themes"
