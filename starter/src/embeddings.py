from typing import Protocol


class Embedder(Protocol):
    model_name: str
    dimensions: int

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        ...

    def embed_query(self, question: str) -> list[float]:
        ...


class MyEmbedder:

    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        raise NotImplementedError("TODO: initialize real embedder and dimensions")

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError("TODO: embed_documents")

    def embed_query(self, question: str) -> list[float]:
        raise NotImplementedError("TODO: embed_query")
