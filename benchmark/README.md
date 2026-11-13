# Benchmark — NIST AI RMF 1.0

Bộ câu hỏi: [questions.jsonl](questions.jsonl), gồm 20 câu (15 dev / 5 test) trên corpus `nist-ai-100-1` ([data/manifest.json](../data/manifest.json)). Split được chốt **trước** lần chạy thử đầu tiên.

## Trường dữ liệu

`id`, `split`, `type`, `question`, `expected_answer`, `gold_source_id`, `gold_page` (list số trang PDF, 1-based, chấp nhận bất kỳ trang nào trong list), `evidence_quote` (nguyên văn trên trang `gold_page[0]` sau chuẩn hóa), `alt_evidence` (tùy chọn: evidence cho các trang gold khác), `filter` (`null` hoặc `{"part": ...}`).

## Phân bố

| Loại | Dev | Test |
|---|---|---|
| direct | q01, q02, q04, q15 | q18 |
| paraphrase | q05, q08, q09, q10, q13 | – |
| condition | q03, q12 | q19 |
| table (bảng Core) | q06, q11, q14 | q20 |
| filter / filter_disambiguation | q06, q07, q08 | q16, q17 |

Có 5 câu dùng filter, trong đó 2 câu ở test. Giá trị filter lấy từ chính câu hỏi ("in the Core…", "in the appendix…", "in the foundational part…"), không lấy từ trang gold. Với các câu có `filter: null`, cấu hình C chạy không filter.

Câu q07 (p13) và q16 (p37) tạo thành **cặp phân biệt nhờ metadata**: cả hai hỏi về *residual risk*, nhưng Part 1 và phần Core định nghĩa khác nhau.

## Chống rò rỉ dev/test

- Dev và test không dùng chung trang gold nào (script kiểm tra tự động).
- Chủ đề residual risk xuất hiện ở cả hai split (q07 dev, q16 test), nhưng khác trang và khác định nghĩa. Đây là chủ ý để kiểm tra filter. Rủi ro: tinh chỉnh filter trên q07 có thể có lợi cho q16.

## Tiêu chí chọn cấu hình (chốt trước khi xem test)

Chỉ chọn trên **dev**, theo thứ tự ưu tiên: (1) Evidence Hit@3 → (2) Hit@1 → (3) tỷ lệ tuân thủ filter → (4) số chunk/thời gian/chi phí. Sau khi chọn thì cố định cấu hình rồi mới chạy test một lần. Nếu đã xem test để sửa bài, ghi rõ vào báo cáo.

## Kiểm chứng

```bash
python benchmark/verify_evidence.py
```

Script chuẩn hóa văn bản PDF (NFKC, bỏ header `NIST AI 100-1 AI RMF 1.0` và footer `Page N`, ghép từ bị ngắt bằng gạch nối, gộp khoảng trắng). Sau đó kiểm tra evidence có nguyên văn trên trang gold, trang gold thuộc corpus, filter khớp `part`, số lượng câu và rò rỉ trang.

Lưu ý: tại pdf p31, cụm `context-specific` bị ghép thành `contextspecific` do ngắt dòng, nên evidence của q06 giữ đúng dạng sau chuẩn hóa. Pipeline ingestion cần dùng cùng quy tắc chuẩn hóa này để evidence khớp được.
