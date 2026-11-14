import csv
import json
import os
import platform
import statistics
import time
import urllib.request
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

from dotenv import load_dotenv

from .chunking import by_paragraph, fixed_size
from .embeddings import OllamaEmbedder
from .evaluation import evaluate_query, summarize
from .ingestion import ROOT, load_pdf
from .models import Chunk
from .store import PgVectorStore

STARTER = ROOT / "starter"
RESULTS = STARTER / "results"
AUDIT = RESULTS / "audit"
QUESTIONS = ROOT / "benchmark" / "questions.jsonl"
PDF = ROOT / "data" / "AI Engineering Guidebook.pdf"
DOCUMENT_ID = "ai-engineering-2025"
SOURCE = "AI Engineering Guidebook.pdf"
TOP_K = 3
COHERENCE_PAGES = 10  # 10 trang counted đầu tiên (đã sắp xếp), vị trí = giữa trang; chốt trước khi xem điểm

CHUNKERS = {
    "fixed500-50": lambda page: fixed_size(page, 500, 50),
    "para1000": lambda page: by_paragraph(page, 1000),
}
# B và C dùng chung chunk "para1000"; khác nhau duy nhất ở use_filter.
STRATEGIES = {
    "A": {"chunker": "fixed500-50", "use_filter": False},
    "B": {"chunker": "para1000", "use_filter": False},
    "C": {"chunker": "para1000", "use_filter": True},
}


def _length_stats(chunks: list[Chunk]) -> dict:
    lengths = [len(c.text) for c in chunks]
    return {
        "chunks": len(chunks),
        "total_chars": sum(lengths),
        "min_chars": min(lengths),
        "median_chars": statistics.median(lengths),
        "mean_chars": round(statistics.mean(lengths), 1),
        "max_chars": max(lengths),
    }


def _environment(store: PgVectorStore, embedder: OllamaEmbedder, host: str) -> dict:
    with urllib.request.urlopen(f"{host}/api/version", timeout=10) as response:
        ollama_version = json.load(response)["version"]
    with store.conn.cursor() as cur:
        cur.execute("SELECT current_setting('server_version'), extversion FROM pg_extension WHERE extname = 'vector'")
        pg_version, pgvector_version = cur.fetchone()
    return {
        "python": platform.python_version(),
        "pypdf": version("pypdf"),
        "psycopg": version("psycopg"),
        "ollama": ollama_version,
        "embedding_model": embedder.model_name,
        "embedding_dimensions": embedder.dimensions,
        "embedding_prefixes": {"document": "search_document: ", "query": "search_query: "},
        "postgresql": pg_version,
        "pgvector": pgvector_version,
        "metric": "cosine distance (<=>), score = 1 - distance",
        "search": "exact (không tạo index ANN)",
        "cost_usd": 0,
    }


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _write_csv_if_missing(path: Path, header: list[str], rows: list[list]) -> bool:
    # Không ghi đè nhãn thủ công đã điền.
    if path.exists():
        return False
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)
    return True


def _audit_templates(pages, chunk_sets: dict[str, list[Chunk]], traces: list[dict]) -> list[str]:
    AUDIT.mkdir(parents=True, exist_ok=True)
    written = []

    coherence_rows = []
    for position, page in enumerate(sorted(pages, key=lambda p: p.page)[:COHERENCE_PAGES], start=1):
        offset = len(page.text) // 2
        for strategy, cfg in STRATEGIES.items():
            chunk = next(c for c in chunk_sets[cfg["chunker"]]
                         if c.page == page.page and c.metadata["char_start"] <= offset < c.metadata["char_end"])
            coherence_rows.append([f"pos{position:02d}", page.page, offset, strategy, chunk.chunk_id,
                                   len(chunk.text), chunk.text, "", ""])
    if _write_csv_if_missing(AUDIT / "coherence_labels.csv",
                             ["position_id", "page", "char_offset", "strategy", "chunk_id", "chunk_chars",
                              "chunk_text", "label_0_1_2", "reason"], coherence_rows):
        written.append("coherence_labels.csv")

    metadata_rows, grounding_rows = [], []
    for t in traces:
        if t["split"] != "test":
            continue
        for h in t["hits"]:
            metadata_rows.append([t["strategy"], t["id"], h["rank"], h["chunk_id"], h["source"], h["page"],
                                  h["metadata"]["chapter"], h["metadata"]["printed_page"],
                                  json.dumps(t["question_filter"], ensure_ascii=False) if t["question_filter"] else "",
                                  "" if h["matches_filter"] is None else h["matches_filter"], "", ""])
        grounding_rows.append([t["strategy"], t["id"], t["question"], t["expected_answer"],
                               " | ".join(h["chunk_id"] for h in t["hits"]), t["hit3"], "", ""])
    if _write_csv_if_missing(AUDIT / "metadata_audit.csv",
                             ["strategy", "question_id", "rank", "chunk_id", "source", "page", "chapter",
                              "printed_page", "question_filter", "matches_filter_auto",
                              "metadata_correct_yes_no", "note"], metadata_rows):
        written.append("metadata_audit.csv")
    if _write_csv_if_missing(AUDIT / "grounding_labels.csv",
                             ["strategy", "question_id", "question", "expected_answer", "top3_chunk_ids",
                              "evidence_hit3_auto", "label_0_1_2", "reason"], grounding_rows):
        written.append("grounding_labels.csv")
    return written


def main() -> None:
    load_dotenv(STARTER / ".env")
    host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    started_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    RESULTS.mkdir(parents=True, exist_ok=True)

    questions = [json.loads(line) for line in QUESTIONS.read_text(encoding="utf-8").splitlines() if line.strip()]
    dev = [q for q in questions if q["split"] == "dev"]
    test = [q for q in questions if q["split"] == "test"]
    if len(questions) < 20 or len(dev) < 15 or len(test) < 5:
        raise ValueError(f"benchmark chưa đủ: total={len(questions)} dev={len(dev)} test={len(test)}")

    t0 = time.perf_counter()
    pages = load_pdf(PDF, DOCUMENT_ID, SOURCE)
    load_seconds = time.perf_counter() - t0
    if len(pages) < 30:
        raise ValueError(f"corpus chỉ có {len(pages)} trang nội dung, cần >= 30")
    print(f"Đã nạp {len(pages)} trang trong {load_seconds:.1f}s")

    t0 = time.perf_counter()
    embedder = OllamaEmbedder(os.getenv("OLLAMA_EMBED_MODEL", ""), host)
    warmup_seconds = time.perf_counter() - t0
    store = PgVectorStore(os.getenv("DATABASE_URL", ""), embedder.dimensions)
    store.create_schema()
    print(f"Model {embedder.model_name} ({embedder.dimensions} chiều), warm-up {warmup_seconds:.1f}s")

    chunk_sets, vectors, chunk_seconds, embed_seconds = {}, {}, {}, {}
    for name, chunker in CHUNKERS.items():
        t0 = time.perf_counter()
        chunk_sets[name] = [c for page in pages for c in chunker(page)]
        chunk_seconds[name] = time.perf_counter() - t0
        t0 = time.perf_counter()
        vectors[name] = embedder.embed_documents([c.text for c in chunk_sets[name]])
        embed_seconds[name] = time.perf_counter() - t0
        print(f"{name}: {len(chunk_sets[name])} chunk, chunk {chunk_seconds[name]:.2f}s, embed {embed_seconds[name]:.1f}s")

    ingest = {}
    for strategy, cfg in STRATEGIES.items():
        name = cfg["chunker"]
        t0 = time.perf_counter()
        store.upsert(strategy, chunk_sets[name], vectors[name])
        upsert_seconds = time.perf_counter() - t0
        first = store.count(strategy)
        store.upsert(strategy, chunk_sets[name], vectors[name])  # nạp lại cùng phiên bản
        second = store.count(strategy)
        if first != second or first != len(chunk_sets[name]):
            raise RuntimeError(f"{strategy}: nạp lại sai số bản ghi ({first} -> {second}, mong đợi {len(chunk_sets[name])})")
        ingest[strategy] = {
            "chunker": name,
            "use_filter": cfg["use_filter"],
            **_length_stats(chunk_sets[name]),
            "chunk_seconds": round(chunk_seconds[name], 3),
            "embed_seconds": round(embed_seconds[name], 2),
            "embedding_shared_with": [s for s, c in STRATEGIES.items() if c["chunker"] == name and s != strategy],
            "upsert_seconds": round(upsert_seconds, 2),
            "reload_check": {"rows_after_first_upsert": first, "rows_after_second_upsert": second,
                             "duplicates": second - first},
        }

    query_vectors, query_seconds = {}, 0.0
    for q in questions:
        t0 = time.perf_counter()
        query_vectors[q["id"]] = embedder.embed_query(q["question"])
        query_seconds += time.perf_counter() - t0

    all_traces = []
    for strategy, cfg in STRATEGIES.items():
        traces = []
        for q in questions:
            applied = q.get("filter") if cfg["use_filter"] and q.get("filter") else None
            t0 = time.perf_counter()
            hits = store.search(strategy, query_vectors[q["id"]], TOP_K, applied)
            search_ms = (time.perf_counter() - t0) * 1000
            trace = evaluate_query(q, hits)
            trace.update({"strategy": strategy, "applied_filter": applied, "search_ms": round(search_ms, 2)})
            traces.append(trace)
        _write_jsonl(RESULTS / f"traces_{strategy}.jsonl", traces)
        all_traces.extend(traces)

    metrics = summarize(all_traces)
    summary = {
        "run_started_at_utc": started_at,
        "document_id": DOCUMENT_ID,
        "pages_loaded": len(pages),
        "questions": {"total": len(questions), "dev": len(dev), "test": len(test)},
        "top_k": TOP_K,
        "strategies": STRATEGIES,
        "environment": _environment(store, embedder, host),
        "timing_seconds": {"load_pdf": round(load_seconds, 2), "model_warmup": round(warmup_seconds, 2),
                           "embed_all_queries": round(query_seconds, 2)},
        "ingest": ingest,
        "metrics": metrics,
    }
    (RESULTS / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    written = _audit_templates(pages, chunk_sets, all_traces)
    store.close()

    print("\nStrategy Split  Hit@1   Hit@3   Filter top-3")
    for strategy, splits in metrics.items():
        for split in ("dev", "test"):
            m = splits[split]
            print(f"{strategy:<8} {split:<5} {m['hit1']:>6} {m['hit3']:>7}   {m['filter_compliant_top3']}")
    print(f"\nĐã ghi {RESULTS}: traces_A/B/C.jsonl, summary.json"
          + (f", audit/{', audit/'.join(written)}" if written else " (giữ nguyên file audit đã có)"))


if __name__ == "__main__":
    main()
