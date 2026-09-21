import hashlib
from threading import Lock
from typing import Any, Protocol

from app.core.cache import query_embedding_cache

EMBEDDING_MANIFEST_VERSION = "e5-manifest-v1"


def embedding_fingerprint(model_name: str, dimensions: int, content: str) -> str:
    """Stable non-security fingerprint for one E5 passage embedding input."""
    source = f"{EMBEDDING_MANIFEST_VERSION}:{model_name}:{dimensions}:passage: {content}"
    return hashlib.md5(source.encode("utf-8")).hexdigest()  # noqa: S324


class EmbeddingProvider(Protocol):
    def embed_query(self, text: str) -> list[float]: ...

    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...


class LocalE5EmbeddingProvider:
    """Local multilingual E5 embeddings for asymmetric retrieval on CPU."""

    _models: dict[str, Any] = {}
    _model_lock = Lock()

    def __init__(
        self,
        model_name: str = "intfloat/multilingual-e5-base",
        dimensions: int = 768,
        batch_size: int = 16,
        model: Any | None = None,
    ) -> None:
        self.model_name = model_name
        self.dimensions = dimensions
        self.batch_size = batch_size
        self._injected_model = model

    def embed_query(self, text: str) -> list[float]:
        cache_source = f"local-e5:{self.model_name}:{self.dimensions}:{text.strip()}"
        key = hashlib.sha256(cache_source.encode()).hexdigest()
        cached = query_embedding_cache.get(key)
        if cached is not None:
            return cached
        vector = self._encode([f"query: {text}"])[0]
        query_embedding_cache.set(key, vector)
        return vector

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._encode([f"passage: {text}" for text in texts])

    def _get_model(self) -> Any:
        if self._injected_model is not None:
            return self._injected_model
        with self._model_lock:
            model = self._models.get(self.model_name)
            if model is None:
                try:
                    from huggingface_hub import snapshot_download
                    from huggingface_hub.errors import LocalEntryNotFoundError
                    from sentence_transformers import SentenceTransformer
                except ImportError as exc:
                    raise RuntimeError(
                        "sentence-transformers is required for local E5 embeddings"
                    ) from exc
                # Resolve an existing snapshot without network access first.
                # Passing a repo ID makes Hugging Face perform remote HEAD
                # requests even when all weights are already cached; on an
                # offline laptop those retries can add about 90 seconds.
                try:
                    source = snapshot_download(
                        repo_id=self.model_name,
                        local_files_only=True,
                    )
                except LocalEntryNotFoundError:
                    source = self.model_name
                model = SentenceTransformer(source, device="cpu")
                self._models[self.model_name] = model
            return model

    def _encode(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        values = self._get_model().encode(
            texts,
            batch_size=self.batch_size,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        vectors = [[float(value) for value in vector] for vector in values]
        if any(len(vector) != self.dimensions for vector in vectors):
            raise ValueError("Local E5 embedding has unexpected dimensions")
        return vectors
