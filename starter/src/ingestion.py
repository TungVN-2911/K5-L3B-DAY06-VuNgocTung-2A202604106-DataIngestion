"""Read and normalize source data. TODO: implement functions."""
from pathlib import Path
import re
import unicodedata

from .models import DocumentPage

# Corpus: "AI Engineering" (DailyDoseofDS.com). Mỗi trang PDF có header
# "DailyDoseofDS.com" ở đầu và số trang in (= pdf_page - 1) ở cuối.
HEADER = re.compile(r"^\s*DailyDoseofDS\.com\s*")
FOOTER_PAGE_NUMBER = re.compile(r"\n\s*\d{1,3}\s*$")


def normalize(text: str) -> str:
    """Chuẩn hóa dùng chung cho pipeline và benchmark/verify_evidence.py.

    NFKC (tách ligature như 'ﬁ' -> 'fi'), bỏ header/footer, ghép từ ngắt dòng
    bằng gạch nối, gộp khoảng trắng.
    """
    text = unicodedata.normalize("NFKC", text)
    text = HEADER.sub("", text)
    text = FOOTER_PAGE_NUMBER.sub("", text)
    text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", text)
    return " ".join(text.split())


def load_pdf(path: Path, document_id: str, source: str) -> list[DocumentPage]:
    """TODO: extract each physical page; keep its page number and source.

    Detect and record pages with no text. OCR, when needed, is a separate step.
    """
    raise NotImplementedError("TODO: load_pdf")


def normalize_text(text: str) -> str:
    """TODO: normalize Unicode and whitespace without discarding useful structure."""
    raise NotImplementedError("TODO: normalize_text")
