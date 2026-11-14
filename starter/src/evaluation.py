import unicodedata
from collections import defaultdict
from typing import Any


def _norm(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text).split())


def gold_evidence(question: dict[str, Any]) -> dict[int, list[str]]:
    gold: dict[int, list[str]] = defaultdict(list)
    gold[question["gold_page"][0]].append(_norm(question["evidence_quote"]))
    for alt in question.get("alt_evidence", []):
        gold[alt["page"]].append(_norm(alt["quote"]))
    return gold


def evaluate_query(question: dict[str, Any], hits: list[dict[str, Any]]) -> dict[str, Any]:
    # Hit = đúng tài liệu + trang gold + chunk chứa ĐỦ evidence của trang đó (khớp nguyên văn sau chuẩn hóa).
    # Không suy ra nhãn grounding/coherence từ phép so khớp chuỗi: các nhãn đó chấm thủ công.
    gold = gold_evidence(question)
    gold_pages = set(question["gold_page"])
    want_filter = question.get("filter") or {}
    ranked = []
    for rank, hit in enumerate(hits, start=1):
        text = _norm(hit["text"])
        on_gold_page = hit["document_id"] == question["gold_source_id"] and hit["page"] in gold_pages
        evidence_hit = on_gold_page and any(q in text for q in gold.get(hit["page"], []))
        ranked.append({
            "rank": rank,
            "chunk_id": hit["chunk_id"],
            "document_id": hit["document_id"],
            "source": hit["source"],
            "page": hit["page"],
            "metadata": hit["metadata"],
            "score": round(hit["score"], 6),
            "on_gold_page": on_gold_page,
            "evidence_hit": evidence_hit,
            "matches_filter": all(hit["metadata"].get(k) == v for k, v in want_filter.items()) if want_filter else None,
            "text": hit["text"],
        })
    return {
        "id": question["id"],
        "split": question["split"],
        "type": question.get("type"),
        "question": question["question"],
        "expected_answer": question["expected_answer"],
        "gold_source_id": question["gold_source_id"],
        "gold_page": question["gold_page"],
        "question_filter": want_filter or None,
        "hit1": bool(ranked) and ranked[0]["evidence_hit"],
        "hit3": any(h["evidence_hit"] for h in ranked[:3]),
        "gold_page_in_top3": any(h["on_gold_page"] for h in ranked[:3]),
        "filter_compliant": all(h["matches_filter"] for h in ranked[:3]) if want_filter else None,
        "hits": ranked,
    }


def summarize(traces: list[dict[str, Any]]) -> dict[str, Any]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for t in traces:
        groups[(t["strategy"], t["split"])].append(t)
    summary: dict[str, Any] = {}
    for (strategy, split), items in sorted(groups.items()):
        n = len(items)
        filtered = [t for t in items if t["question_filter"]]

        def frac(k: int, total: int) -> str:
            return f"{k}/{total}"

        summary.setdefault(strategy, {})[split] = {
            "n": n,
            "hit1": frac(sum(t["hit1"] for t in items), n),
            "hit3": frac(sum(t["hit3"] for t in items), n),
            "gold_page_in_top3": frac(sum(t["gold_page_in_top3"] for t in items), n),
            "filter_questions": len(filtered),
            "filter_compliant_top3": frac(sum(bool(t["filter_compliant"]) for t in filtered), len(filtered))
            if filtered else "N/A",
            "hit1_ids": [t["id"] for t in items if t["hit1"]],
            "hit3_miss_ids": [t["id"] for t in items if not t["hit3"]],
        }
    return summary
