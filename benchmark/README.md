# Benchmark — NIST AI RMF 1.0

[questions.jsonl](questions.jsonl): 20 câu (15 dev / 5 test) trên corpus `nist-ai-100-1` ([data/manifest.json](../data/manifest.json)).

## Trường dữ liệu

| Trường | Ý nghĩa |
| --- | --- |
| `id`, `split`, `type` | Mã câu, `dev`/`test`, loại câu |
| `question`, `expected_answer` | Câu hỏi và đáp án mong đợi |
| `gold_source_id` | Mã tài liệu gold, ở đây là `nist-ai-100-1` |
| `gold_page` | Danh sách số trang PDF (đếm từ 1); khớp bất kỳ trang nào là đúng |
| `evidence_quote` | Đoạn trích nguyên văn trên trang `gold_page[0]`, sau chuẩn hóa |
| `alt_evidence` | (Tùy chọn) đoạn trích cho các trang gold khác |
| `filter` | `null`, hoặc `{"part": ...}` lấy từ ngữ cảnh câu hỏi |

## Phân bố

| Loại | Dev | Test |
| --- | --- | --- |
| direct | q01, q02, q04, q15 | q18 |
| paraphrase | q05, q08, q09, q10, q13 | – |
| condition | q03, q12 | q19 |
| table (bảng Core) | q06, q11, q14 | q20 |
| có filter `part` | q06, q07, q08 | q16, q17 |

Dev và test không dùng chung trang gold nào. q07 (p13) và q16 (p37) cùng hỏi về *residual risk*, nhưng Part 1 và phần Core định nghĩa khác nhau, nên filter là yếu tố phân biệt.

## Kiểm chứng

```bash
python benchmark/verify_evidence.py
```

Script chuẩn hóa văn bản PDF: NFKC, bỏ header và footer, ghép từ bị ngắt dòng bằng gạch nối, gộp khoảng trắng. Sau đó script kiểm tra:

- evidence có nguyên văn trên trang gold;
- trang gold thuộc corpus;
- filter khớp trường `part`;
- số lượng câu và split đủ theo yêu cầu;
- dev và test không dùng chung trang.

Riêng q06 dùng `contextspecific` (pdf p31) đúng như văn bản sau chuẩn hóa.
