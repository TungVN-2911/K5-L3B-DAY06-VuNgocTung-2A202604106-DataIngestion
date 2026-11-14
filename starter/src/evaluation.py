from typing import Any


def evaluate_query(question: dict[str, Any], hits: list[dict[str, Any]]) -> dict[str, Any]:
    raise NotImplementedError("TODO: evaluate_query")


def summarize(traces: list[dict[str, Any]]) -> dict[str, Any]:
    raise NotImplementedError("TODO: summarize")
