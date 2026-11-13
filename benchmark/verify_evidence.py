"""Kiểm tra benchmark trước khi chạy thử nghiệm.

- evidence_quote (và alt_evidence) có nguyên văn trên trang gold sau chuẩn hóa
- trang gold thuộc corpus đã tính trong manifest
- filter khớp metadata `part` của trang gold
- đủ 20 câu, >=15 dev / >=5 test, >=3 câu filter và >=1 câu filter ở test
- cảnh báo nếu dev và test dùng chung trang gold (nguy cơ rò rỉ)

Chạy từ root repo: python benchmark/verify_evidence.py
"""
import json
import re
import sys
import unicodedata
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "data" / "NIST.AI.100-1.pdf"
MANIFEST = ROOT / "data" / "manifest.json"
QUESTIONS = ROOT / "benchmark" / "questions.jsonl"


def normalize(text: str) -> str:
    """Chuẩn hóa giống pipeline: NFKC, bỏ header/footer, ghép từ ngắt dòng, gộp khoảng trắng."""
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"^\s*NIST AI 100-1 AI RMF 1\.0\s*", "", text)
    text = re.sub(r"\s*Page \d+\s*$", "", text)
    text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", text)
    return " ".join(text.split())


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    pages = [normalize(p.extract_text() or "") for p in PdfReader(PDF).pages]
    src = json.loads(MANIFEST.read_text(encoding="utf-8"))["sources"][0]
    info = {p["pdf_page"]: p for p in src["pages"]}
    qs = [json.loads(line) for line in QUESTIONS.read_text(encoding="utf-8").splitlines() if line.strip()]
    errors, warnings = [], []

    for q in qs:
        quotes = [(q["gold_page"][0], q["evidence_quote"])]
        quotes += [(a["page"], a["quote"]) for a in q.get("alt_evidence", [])]
        for page in q["gold_page"]:
            if not info[page]["counted"]:
                errors.append(f"{q['id']}: trang {page} không thuộc corpus đã tính")
        for page, quote in quotes:
            if " ".join(unicodedata.normalize("NFKC", quote).split()) not in pages[page - 1]:
                errors.append(f"{q['id']}: evidence không khớp nguyên văn trang {page}")
        if q["filter"]:
            want = q["filter"]["part"]
            if any(info[p]["part"] != want for p in q["gold_page"]):
                errors.append(f"{q['id']}: trang gold không thuộc part={want}")

    ids = [q["id"] for q in qs]
    dev = [q for q in qs if q["split"] == "dev"]
    test = [q for q in qs if q["split"] == "test"]
    filt = [q for q in qs if q["filter"]]
    if len(set(ids)) != len(ids):
        errors.append("trùng id")
    if len(qs) < 20 or len(dev) < 15 or len(test) < 5:
        errors.append(f"không đủ câu: total={len(qs)} dev={len(dev)} test={len(test)}")
    if len(filt) < 3 or not any(q["split"] == "test" for q in filt):
        errors.append("cần >=3 câu filter và >=1 câu filter trong test")
    leak = {p for q in dev for p in q["gold_page"]} & {p for q in test for p in q["gold_page"]}
    if leak:
        warnings.append(f"dev và test dùng chung trang gold {sorted(leak)}")

    print(f"total={len(qs)} dev={len(dev)} test={len(test)} filter={len(filt)} "
          f"(trong test: {sum(q['split'] == 'test' for q in filt)})")
    for w in warnings:
        print("WARN", w)
    for e in errors:
        print("FAIL", e)
    print("OK" if not errors else f"{len(errors)} lỗi")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
