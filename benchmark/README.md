# Benchmark — AI Engineering (DailyDoseofDS.com, 2025 Edition)

> ⚠️ **Đã đổi corpus** từ NIST AI RMF 1.0 sang `ai-engineering-2025`. [questions.jsonl](questions.jsonl) hiện vẫn là 20 câu của corpus cũ (`nist-ai-100-1`). Bộ câu này cần **viết lại** trên tài liệu mới, rồi commit trước khi chạy thử pipeline. Bản cũ vẫn xem được trong lịch sử git (commit `8c735aa`).

Corpus: [data/manifest.json](../data/manifest.json), sinh bằng `data/build_manifest.py`.

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
