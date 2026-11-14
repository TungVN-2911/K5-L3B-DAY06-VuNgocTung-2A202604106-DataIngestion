import re

from .models import Chunk, DocumentPage

# Ranh giới đơn vị = 1 khoảng trắng: (a) sau . ! ? và trước chữ in hoa, ●, “ hoặc (
# hoặc (b) ngay trước mục ●. Không tách 'e.g., recalling' (chữ thường) hay '0.7' (không có khoảng trắng).
_BOUNDARY = re.compile(r"(?<=[.!?])\s(?=[A-Z●“(])|\s(?=●)")


def fixed_size(page: DocumentPage, size: int, overlap: int) -> list[Chunk]:
    if not 0 <= overlap < size:
        raise ValueError(f"cần 0 <= overlap < size, nhận size={size}, overlap={overlap}")
    kind = f"fixed{size}-{overlap}"
    text_len = len(page.text)
    chunks: list[Chunk] = []
    start = 0
    while start < text_len:
        end = min(start + size, text_len)
        chunks.append(_make_chunk(page, kind, len(chunks), start, end))
        if end == text_len:  # không tạo chunk đuôi chỉ chứa phần overlap
            break
        start = end - overlap
    return chunks


def by_paragraph(page: DocumentPage, max_size: int) -> list[Chunk]:
    if max_size <= 0:
        raise ValueError(f"max_size phải > 0, nhận max_size={max_size}")
    kind = f"para{max_size}"
    chunks: list[Chunk] = []
    cur_start: int | None = None  # None = chưa có chunk đang gom
    cur_end: int | None = None

    def close(s: int, e: int) -> None:
        chunks.append(_make_chunk(page, kind, len(chunks), s, e))

    for s, e in _split_units(page.text):
        if e - s > max_size:                                  # ① câu quá dài
            if cur_start is not None:
                close(cur_start, cur_end)
                cur_start = cur_end = None
            for a in range(s, e, max_size):
                close(a, min(a + max_size, e))
        elif cur_start is None or e - cur_start <= max_size:  # ② còn chỗ: mở rộng chunk
            if cur_start is None:
                cur_start = s
            cur_end = e
        else:                                                 # ③ hết chỗ: đóng, mở chunk mới
            close(cur_start, cur_end)
            cur_start, cur_end = s, e

    if cur_start is not None:                                 # đóng chunk cuối cùng
        close(cur_start, cur_end)
    return chunks


def _make_chunk(page: DocumentPage, kind: str, i: int, start: int, end: int) -> Chunk:
    if not 0 <= start < end <= len(page.text):
        raise ValueError(f"vị trí chunk không hợp lệ: start={start}, end={end}, len={len(page.text)}")
    return Chunk(
        chunk_id=f"{page.document_id}:p{page.page}:{kind}:{i}",
        document_id=page.document_id,
        source=page.source,
        page=page.page,
        text=page.text[start:end],
        metadata={
            **page.metadata,
            "chunk_index": i,
            "char_start": start,
            "char_end": end,
        },
    )


def _split_units(text: str) -> list[tuple[int, int]]:
    if not text:
        return []
    units = []
    start = 0
    for m in _BOUNDARY.finditer(text):
        units.append((start, m.start()))  # đơn vị kết thúc ngay TRƯỚC khoảng trắng
        start = m.end()                   # đơn vị mới bắt đầu ngay SAU khoảng trắng
    units.append((start, len(text)))
    return units
