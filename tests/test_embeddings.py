from app.rag.embeddings import LocalE5EmbeddingProvider, embedding_fingerprint


class FakeE5Model:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def encode(self, texts, **kwargs):
        self.calls.append(texts)
        return [[0.1] * 768 for _ in texts]


def test_e5_uses_required_query_and_passage_prefixes():
    model = FakeE5Model()
    provider = LocalE5EmbeddingProvider(model=model)
    assert len(provider.embed_query("kecemasan")) == 768
    assert len(provider.embed_documents(["Ar-Ra'd 13:28"])) == 1
    assert model.calls == [["query: kecemasan"], ["passage: Ar-Ra'd 13:28"]]


def test_embedding_fingerprint_changes_with_embedding_input_or_model():
    current = embedding_fingerprint(
        "intfloat/multilingual-e5-base", 768, "An English Quran translation"
    )

    assert current == embedding_fingerprint(
        "intfloat/multilingual-e5-base", 768, "An English Quran translation"
    )
    assert current != embedding_fingerprint(
        "intfloat/multilingual-e5-base", 768, "Changed source text"
    )
    assert current != embedding_fingerprint("another-model", 768, "An English Quran translation")
