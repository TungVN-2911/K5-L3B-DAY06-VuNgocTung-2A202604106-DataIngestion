# Benchmark — AI Engineering (DailyDoseofDS.com, 2025 Edition)

[questions.jsonl](questions.jsonl): 20 câu (15 dev / 5 test) trên corpus `ai-engineering-2025`. Corpus mô tả trong [data/manifest.json](../data/manifest.json), sinh bằng `data/build_manifest.py`. Bộ câu cũ của NIST AI RMF đã bị thay thế khi đổi corpus; bản cũ vẫn xem được trong lịch sử git (commit `8c735aa`).

**Nguồn gốc bộ câu:** bản nháp do AI hỗ trợ (Claude) viết từ text đã chuẩn hóa, với evidence được trích nguyên văn. `verify_evidence.py` xác nhận mọi evidence có nguyên văn trên trang gold. Tác giả đã đọc lại câu hỏi và đáp án, đối chiếu với PDF trước khi chạy thử pipeline. Tách dev/test được chốt cùng lúc với bộ câu.

## Phân bố

| Loại | Dev | Test |
| --- | --- | --- |
| direct | q01, q02, q04, q06, q09 | – |
| paraphrase | q03, q08, q11, q13 | q20 |
| condition | q05, q07, q10 | q17, q19 |
| filter `chapter` | q12 (`rag`), q14 (`context_engineering`), q15 (`ai_agents`) | q16 (`llm_observability`), q18 (`llm_deployment`) |

- **Câu filter** được chọn ở các chủ đề xuất hiện ở nhiều chương: *memory* (q14, q15 thuộc hai chương khác nhau), *KV cache* (q12 ở `rag`, trong khi KV caching chủ yếu nằm ở `llm_optimization`/`llm_deployment`), *LoRA* (q18 ở `llm_deployment`, trong khi LoRA chủ yếu nằm ở `fine_tuning`), *evaluation* (q16 ở `llm_observability`, khác chương `llm_evaluation`).
- **Tách dev/test:** không dùng chung trang gold. Test dùng các chương `llm_observability`, `mcp`, `llm_deployment`, `llm_optimization` mà dev không có câu nào, cùng một câu `fine_tuning` (p94, khác trang với q06/q07 ở p68–69). Nguy cơ rò rỉ: q19 và q06/q07 cùng chương.
- **Câu có nhiều trang gold:** q11 chấp nhận p132 hoặc p133 (`alt_evidence`).
- **Evidence dài:** q10 khoảng 300 ký tự, q01 khoảng 230 ký tự, q11 khoảng 220 ký tự. Với chunk cố định 500 ký tự, các đoạn này dễ bị cắt đôi; nếu xảy ra, ghi lại làm ví dụ lỗi coherence.

## Trường dữ liệu

| Trường | Ý nghĩa |
| --- | --- |
| `id`, `split`, `type` | Mã câu, `dev`/`test`, loại câu |
| `question`, `expected_answer` | Câu hỏi và đáp án mong đợi |
| `gold_source_id` | `ai-engineering-2025` |
| `gold_page` | Danh sách số trang **PDF** (1-based, = số in ở chân trang + 1); khớp bất kỳ trang nào là đúng |
| `evidence_quote` | Trích nguyên văn trên trang `gold_page[0]` sau chuẩn hóa |
| `alt_evidence` | (Tùy chọn) `[{"page": ..., "quote": ...}]` cho trang gold khác |
| `filter` | `null`, hoặc `{"chapter": "<slug>"}` lấy từ ngữ cảnh câu hỏi |

Giá trị `chapter` hợp lệ: `llms`, `prompt_engineering`, `fine_tuning`, `rag`, `context_engineering`, `ai_agents`, `mcp`, `llm_optimization`, `llm_evaluation`, `llm_deployment`, `llm_observability`.

## Yêu cầu khi viết lại

- ≥20 câu, ≥15 dev / ≥5 test, ≥3 câu có filter (≥1 ở test).
- Chỉ dùng trang có `counted: true` trong manifest.
- Evidence phải nằm trong **text**, không nằm trong hình. Nhiều sơ đồ và ảnh chụp code của sách không trích được.

## Kiểm chứng

```bash
starter/.venv/Scripts/python benchmark/verify_evidence.py
```

Script dùng chung hàm `normalize` với pipeline ([starter/src/ingestion.py](../starter/src/ingestion.py)): NFKC, bỏ header `DailyDoseofDS.com` và số trang ở cuối, ghép gạch nối, gộp khoảng trắng. Sau đó script kiểm tra:

- evidence có nguyên văn trên trang gold;
- trang gold thuộc corpus;
- filter khớp metadata;
- số lượng câu và split đủ theo yêu cầu;
- dev và test không dùng chung trang.
