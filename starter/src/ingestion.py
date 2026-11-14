"""Đọc và chuẩn hóa corpus "AI Engineering" (DailyDoseofDS.com) theo data/manifest.json."""
from pathlib import Path
import json
import re
import unicodedata

from pypdf import PdfReader

from .models import DocumentPage

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "data" / "manifest.json"
SKIPPED_LOG = ROOT / "starter" / "results" / "skipped_pages.json"

# Mỗi trang PDF có header "DailyDoseofDS.com" ở đầu và số trang in (= pdf_page - 1) ở cuối.
HEADER = re.compile(r"^\s*DailyDoseofDS\.com\s*")
FOOTER_PAGE_NUMBER = re.compile(r"\n\s*\d{1,3}\s*$")
LINE_BREAK_HYPHEN = re.compile(r"(\w)-\s*\n\s*(\w)")


def load_pdf(path: Path, document_id: str, source: str) -> list[DocumentPage]:
    """Đọc các trang `counted` trong manifest, giữ trang PDF (1-based) và metadata truy vết.

    Trang bị loại được ghi vào starter/results/skipped_pages.json kèm lý do. Báo lỗi
    (không fallback) nếu manifest không khớp corpus, hoặc text sau chuẩn hóa lệch số
    ký tự đã ghi, tức PDF hay hàm chuẩn hóa đã đổi kể từ khi sinh manifest.
    """
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))["sources"][0]
    if manifest["source_id"] != document_id:
        raise ValueError(f"document_id={document_id} không khớp manifest source_id={manifest['source_id']}")

    reader = PdfReader(path)
    if len(reader.pages) != manifest["physical_pages"]:
        raise ValueError(f"PDF có {len(reader.pages)} trang, manifest ghi {manifest['physical_pages']}")

    pages: list[DocumentPage] = []
    skipped: list[dict] = []
    for info in manifest["pages"]:
        pdf_page = info["pdf_page"]
        if not info["counted"]:
            skipped.append({"pdf_page": pdf_page, "excluded_reason": info["excluded_reason"]})
            continue
        text = normalize_text(reader.pages[pdf_page - 1].extract_text() or "")
        if len(text) != info["chars"]:
            raise ValueError(f"Trang {pdf_page}: {len(text)} ký tự sau chuẩn hóa, manifest ghi {info['chars']}")
        pages.append(DocumentPage(
            document_id=document_id,
            source=source,
            page=pdf_page,
            text=text,
            metadata={"chapter": info["chapter"], "printed_page": info["printed_page"]},
        ))

    if not pages:
        raise ValueError("Không nạp được trang nào: kiểm tra manifest và file PDF.")
    SKIPPED_LOG.parent.mkdir(parents=True, exist_ok=True)
    SKIPPED_LOG.write_text(json.dumps(skipped, ensure_ascii=False, indent=2), encoding="utf-8")
    return pages


def normalize_text(text: str) -> str:
    """Chuẩn hóa dùng chung cho pipeline, data/build_manifest.py và benchmark/verify_evidence.py.

    NFKC (tách ligature 'ﬁ' -> 'fi'), bỏ header/footer, ghép từ bị ngắt dòng bằng
    gạch nối, gộp khoảng trắng. Hạn chế: từ ghép có gạch nối thật rơi đúng cuối
    dòng cũng bị ghép (vd 'multi-\\nagent' -> 'multiagent').
    """
    text = unicodedata.normalize("NFKC", text)
    text = HEADER.sub("", text)
    text = FOOTER_PAGE_NUMBER.sub("", text)
    text = LINE_BREAK_HYPHEN.sub(r"\1\2", text)
    return " ".join(text.split())
