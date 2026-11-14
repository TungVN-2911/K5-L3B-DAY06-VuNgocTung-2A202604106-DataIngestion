"""Sinh data/manifest.json cho corpus "AI Engineering" (DailyDoseofDS.com).

Chạy từ root repo: starter/.venv/Scripts/python data/build_manifest.py
Ghi số ký tự sau chuẩn hóa (dùng chung normalize với pipeline), chương lấy từ
outline (bookmark) của PDF, và quy tắc trang nào được tính vào corpus.
"""
import hashlib
import json
import re
import sys
from pathlib import Path

from pypdf import PdfReader
import pypdf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "starter"))
from src.ingestion import normalize  # noqa: E402

PDF = ROOT / "data" / "AI Engineering Guidebook.pdf"
OUT = ROOT / "data" / "manifest.json"
FRONT_MATTER_LAST_PAGE = 6  # bìa, trang quảng bá bài test, trang tiêu đề, mục lục p4–6
MIN_CHARS = 200             # dưới ngưỡng này trang gần như chỉ có hình/ảnh chụp code
NOT_CHAPTERS = {"How to make the most out of this book and your time?", "AI Engineering"}


def slug(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")


def chapter_starts(reader: PdfReader) -> list[tuple[int, str, str]]:
    """Mục cấp cao nhất có tên trong outline = chương: (pdf_page, slug, title)."""
    starts = []
    for item in reader.outline:
        if isinstance(item, list):
            continue
        title = " ".join(item.title.split())
        if slug(title) and title not in NOT_CHAPTERS:  # bỏ mục rỗng/chỉ có ký tự ẩn (​)
            starts.append((reader.get_destination_page_number(item) + 1, slug(title), title))
    return sorted(starts)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    reader = PdfReader(PDF)
    starts = chapter_starts(reader)
    pages = []
    for number, page in enumerate(reader.pages, start=1):
        text = normalize(page.extract_text() or "")
        chapter = next((c for c in reversed(starts) if c[0] <= number), None)
        entry = {
            "pdf_page": number,
            "printed_page": number - 1 if number > 1 else None,
            "chars": len(text),
            "chapter": chapter[1] if chapter else "front_matter",
        }
        if number <= FRONT_MATTER_LAST_PAGE:
            entry["excluded_reason"] = "front matter (bìa, quảng bá, tiêu đề, mục lục)"
        elif chapter and number == chapter[0]:
            entry["excluded_reason"] = "trang bìa chương"
        elif len(text) < MIN_CHARS:
            entry["excluded_reason"] = f"dưới {MIN_CHARS} ký tự sau chuẩn hóa (chủ yếu là hình)"
        entry["counted"] = "excluded_reason" not in entry
        pages.append(entry)

    counted = [p for p in pages if p["counted"]]
    manifest = {"sources": [{
        "source_id": "ai-engineering-2025",
        "title": "AI Engineering — System Design Patterns for LLMs, RAG and Agents (2025 Edition)",
        "authors": "Akshay Pachaar, Avi Chawla",
        "publisher": "Daily Dose of Data Science (DailyDoseofDS.com)",
        "version": "2025 Edition; PDF CreationDate D:20251225185846Z",
        "source_path_or_url": "data/AI Engineering Guidebook.pdf",
        "committed_to_repo": False,  # 95 MB và chưa rõ quyền tái phân phối; xem .gitignore
        "original_url": "TODO: điền URL tải chính thức từ DailyDoseofDS.com",
        "license_or_permission": (
            "Không tìm thấy điều khoản giấy phép/bản quyền trong PDF; bìa chỉ ghi 'FREE'. "
            "Chưa xác nhận quyền tái phân phối, vì vậy PDF không được commit. "
            "TODO: ghi kết quả xác nhận với giảng viên/tác giả."
        ),
        "accessed_at": "TODO: ngày tải (file cục bộ sửa lần cuối 2026-09-03)",
        "snapshot": {
            "sha256": hashlib.sha256(PDF.read_bytes()).hexdigest(),
            "bytes": PDF.stat().st_size,
        },
        "physical_pages": len(pages),
        "counted_content_pages": len(counted),
        "counted_chars": sum(p["chars"] for p in counted),
        "counting_rule": (
            f"Đếm theo trang PDF vật lý (1-based). Loại p1–{FRONT_MATTER_LAST_PAGE} (front matter), "
            f"trang bìa mỗi chương và trang dưới {MIN_CHARS} ký tự sau chuẩn hóa. "
            "printed_page = pdf_page - 1. gold_page trong benchmark dùng pdf_page."
        ),
        "extraction": {
            "tool": f"pypdf {pypdf.__version__}",
            "normalization": "starter/src/ingestion.py:normalize (NFKC, bỏ header 'DailyDoseofDS.com' và số trang cuối, ghép gạch nối, gộp khoảng trắng)",
            "ocr": "không dùng",
            "known_issues": [
                "nhiều sơ đồ và ảnh chụp code là hình: nội dung trong hình bị mất (không OCR)",
                "trung bình khoảng 650 ký tự/trang, thấp hơn sách thông thường",
                "pypdf báo 'Ignoring wrong pointing object' khi đọc file (không ảnh hưởng text)",
            ],
        },
        "filter_fields": {
            "chapter": "slug tên chương lấy từ outline (bookmark) cấp cao nhất của PDF: "
                       + ", ".join(f"{s} (p{p})" for p, s, _ in starts),
        },
        "pages": pages,
    }]}
    OUT.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"pages={len(pages)} counted={len(counted)} chars={manifest['sources'][0]['counted_chars']}")
    for p, s, t in starts:
        n = sum(1 for x in counted if x["chapter"] == s)
        print(f"  p{p:>3} {s:<22} counted={n}")


if __name__ == "__main__":
    main()
