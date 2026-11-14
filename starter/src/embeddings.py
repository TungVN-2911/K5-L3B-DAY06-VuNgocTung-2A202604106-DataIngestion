import json
import urllib.error
import urllib.request
from typing import Protocol


class Embedder(Protocol):
    model_name: str
    dimensions: int

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        ...

    def embed_query(self, question: str) -> list[float]:
        ...


# nomic-embed-text yêu cầu tiền tố nhiệm vụ (theo model card) cho document và query.
DOCUMENT_PREFIX = "search_document: "
QUERY_PREFIX = "search_query: "


class OllamaEmbedder:
    def __init__(self, model_name: str, host: str = "http://localhost:11434", batch_size: int = 32) -> None:
        if not model_name:
            raise ValueError("thiếu tên model embedding (OLLAMA_EMBED_MODEL)")
        self.model_name = model_name
        self.host = host.rstrip("/")
        self.batch_size = batch_size
        # Gọi khởi động: nạp model vào bộ nhớ (cold start) và đo số chiều thật.
        self.dimensions = len(self._embed([QUERY_PREFIX + "warm-up"])[0])

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for i in range(0, len(texts), self.batch_size):
            batch = [DOCUMENT_PREFIX + t for t in texts[i:i + self.batch_size]]
            vectors.extend(self._embed(batch))
        return vectors

    def embed_query(self, question: str) -> list[float]:
        return self._embed([QUERY_PREFIX + question])[0]

    def _embed(self, inputs: list[str]) -> list[list[float]]:
        body = json.dumps({"model": self.model_name, "input": inputs}).encode("utf-8")
        request = urllib.request.Request(
            f"{self.host}/api/embed", data=body, headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(request, timeout=300) as response:
                payload = json.load(response)
        except (urllib.error.URLError, TimeoutError) as error:
            # Không fallback sang vector giả: dừng và báo lỗi.
            raise RuntimeError(f"Ollama không phản hồi tại {self.host}: {error}") from error
        vectors = payload.get("embeddings")
        if not vectors or len(vectors) != len(inputs):
            raise RuntimeError(f"Ollama trả {len(vectors or [])} vector cho {len(inputs)} input")
        expected = getattr(self, "dimensions", len(vectors[0]))
        if any(len(v) != expected for v in vectors):
            raise RuntimeError(f"số chiều vector không đồng nhất, mong đợi {expected}")
        return vectors
