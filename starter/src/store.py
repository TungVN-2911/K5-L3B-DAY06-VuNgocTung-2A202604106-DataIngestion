from typing import Any
from .models import Chunk


class PgVectorStore:
    def __init__(self, database_url: str, dimensions: int) -> None:
        raise NotImplementedError("TODO: initialize store")

    def create_schema(self) -> None:
        raise NotImplementedError("TODO: create_schema")

    def upsert(self, strategy: str, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        raise NotImplementedError("TODO: upsert")

    def search(self, strategy: str, query_vector: list[float], top_k: int = 3,
               filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        raise NotImplementedError("TODO: search")
