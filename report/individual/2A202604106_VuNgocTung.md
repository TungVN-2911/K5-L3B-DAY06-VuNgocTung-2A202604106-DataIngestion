# Báo cáo cá nhân — Day 6

## Dữ liệu và pipeline
- **Chủ đề, nguồn/quyền, số trang và quy tắc tính trang:**
  - Sách *AI Engineering — System Design Patterns for LLMs, RAG and Agents* (2025 Edition), Akshay Pachaar & Avi Chawla, Daily Dose of Data Science. Nguồn: https://dailydoseofds.github.io/ai-engg-book/, truy cập ngày 2026-09-03.
  - Tài liệu không có giấy phép mở (trang phát hành ghi "© 2025 All rights reserved"). Giảng viên đã đồng ý cho dùng trong bài lab. PDF không được commit; cách lấy và `sha256` ghi trong [data/manifest.json](../../data/manifest.json).
  - PDF có 384 trang vật lý, trong đó **343 trang được tính**. Loại 6 trang front matter, 11 trang bìa chương và 24 trang có dưới 200 ký tự sau chuẩn hóa (chủ yếu là hình). `gold_page` dùng số trang PDF (đếm từ 1); số in ở chân trang = trang PDF − 1.
- **Chuẩn hóa, lỗi và giới hạn:**
  - Trích text bằng pypdf 6.21.4, không OCR.
  - `normalize_text`: NFKC (tách ligature `ﬁ`), bỏ header `DailyDoseofDS.com` và số trang ở cuối, ghép từ bị ngắt dòng bằng gạch nối, gộp khoảng trắng.
  - 41 trang bị loại được ghi kèm lý do trong `starter/results/skipped_pages.json`.
  - `load_pdf` báo lỗi nếu số ký tự sau chuẩn hóa lệch so với manifest.
  - Giới hạn:
    - nội dung nằm trong sơ đồ và ảnh chụp code bị mất;
    - trung bình chỉ khoảng 650 ký tự mỗi trang;
    - từ ghép có gạch nối thật rơi đúng cuối dòng cũng bị ghép (ví dụ `multi-agent` thành `multiagent`).
- **Embedding, vector store, metric, lệnh chạy và chi phí:**
  - Ollama 0.40.16, model `nomic-embed-text` (768 chiều), tiền tố `search_document: ` cho chunk và `search_query: ` cho câu hỏi.
  - PostgreSQL 16.16 + pgvector 0.8.7, cosine distance, exact search (không tạo index ANN).
  - Lệnh chạy: `python -m src.run` trong thư mục `starter/`.
  - Chi phí 0 (chạy local). Python 3.14.3, psycopg 3.3.8.
- **Metadata bắt buộc, trường lọc bổ sung, nguồn giá trị và lý do chọn:**
  - Bắt buộc: `document_id`, `source`, `page` (trang PDF).
  - Bổ sung: `chapter` (11 giá trị, lấy từ outline/bookmark cấp cao nhất của PDF), `printed_page`, `char_start`/`char_end` (vị trí chunk trong trang).
  - Chọn `chapter` vì một số chủ đề xuất hiện ở nhiều chương: *memory*, *KV cache*, *LoRA*, *evaluation*.

## Cấu hình và benchmark
- **A / B / C (tham số cụ thể, khác biệt duy nhất B–C):**
  - A: `fixed_size`, cửa sổ 500 ký tự, overlap 50, trong từng trang.
  - B: `by_paragraph`, gom các câu/mục `●` liên tiếp trong trang tới tối đa 1000 ký tự, không cắt ngang câu.
  - C: dùng **chính bộ chunk và vector của B**, chỉ thêm filter `chapter` khi câu hỏi có filter.
  - Mọi chiến lược dùng chung corpus, model, store, top-3.
- **20 câu, chia 15 dev / 5 test; câu filter và cách kiểm chứng evidence:**
  - Có 5 câu filter: q12, q14, q15 (dev) và q16, q18 (test).
  - Dev và test không dùng chung trang gold.
  - `benchmark/verify_evidence.py` kiểm tra evidence có nguyên văn trên trang gold sau chuẩn hóa: kết quả OK.
  - Bộ câu do AI hỗ trợ soạn nháp, học viên đã đọc lại, và được commit (`de1dc00`) **trước** khi chạy retrieval.
- **Tiêu chí chọn chiến lược, chốt trước khi xem test** (ghi trong `experiment_log.csv`): ưu tiên Evidence Hit@3 trên dev, hòa thì xét grounding trung bình, sau đó là số chunk và thời gian ingest.

## Kết quả
Số liệu tự động lấy từ lần chạy `2026-11-14T08:04:57Z` (UTC), ghi trong `starter/results/summary.json`.

| Strategy | Split | Hit@1 (n/N) | Evidence Hit@3 (n/N) | Chunk count | Thời gian | Chi phí |
|---|---|---|---|---|---|---|
| A | dev | 10/15 | 14/15 | 621 | embed 70,8 s · upsert 0,27 s | 0 |
| A | test | 4/5 | 5/5 | 621 | (cùng lần ingest) | 0 |
| B | dev | 10/15 | 13/15 | 385 | embed 34,9 s · upsert 0,16 s | 0 |
| B | test | 2/5 | 4/5 | 385 | (cùng lần ingest) | 0 |
| C | dev | 10/15 | 13/15 | 385 | dùng lại embedding của B · upsert 0,15 s | 0 |
| C | test | 2/5 | 4/5 | 385 | (cùng lần ingest) | 0 |

Ghi chú: nạp PDF mất 18,3 s, khởi động model 11,3 s. Kiểm tra nạp lại: chạy upsert 2 lần cho mỗi chiến lược, số bản ghi không đổi (A 621, B 385, C 385; 0 bản trùng). Độ dài chunk trung bình: A 379 ký tự, B/C 575 ký tự (tối đa 999).

| Strategy | Coherence trung bình /2 (n) | Metadata đủ và đúng (n/N) | Filter tuân thủ (n/N hoặc N/A) | Grounding 0/1/2 (số câu) và trung bình /2 |
|---|---|---|---|---|
| A | 1,4/2 (n=10): 4 mức 2, 6 mức 1 | 15/15 | dev 3/3 · test 1/2 | 0:0 / 1:0 / 2:5 → 2,0/2 |
| B | 2,0/2 (n=10): 10 mức 2 | 15/15 | dev 2/3 · test 1/2 | 0:1 / 1:0 / 2:4 → 1,6/2 |
| C | 2,0/2 (n=10): cùng chunk với B | 15/15 | dev 3/3 · test 2/2 | 0:1 / 1:0 / 2:4 → 1,6/2 |

Cột "Filter tuân thủ" là tỷ lệ câu có filter mà **cả top-3** thuộc đúng chương, được tính tự động. A và B không áp dụng filter nên chỉ dùng cột này để so sánh.

**Đường dẫn trace, nhãn thủ công và cách chọn mẫu:**
- Trace: `starter/results/traces_{A,B,C}.jsonl`.
- `starter/results/audit/coherence_labels.csv`: 10 vị trí là điểm giữa của 10 trang được tính đầu tiên (p8–p17), chốt trong code trước khi xem điểm. C dùng chung chunk với B nên chép nhãn của B. Lưu ý mẫu này chỉ nằm trong chương `llms`, có nhiều trang ngắn (A và B trùng nhau ở 4/10 vị trí).
- `metadata_audit.csv`: 5 câu test × top-3 × 3 chiến lược. Đối chiếu `source`, text chunk với text trang PDF, `printed_page` với số in ở chân trang, `chapter` với outline của PDF.
- `grounding_labels.csv`: 5 câu test × 3 chiến lược, chấm theo nội dung top-3 so với `expected_answer`, không dựa vào cột evidence hit tự động.
- **Phương pháp chấm:** nhãn do Claude (LLM) đề xuất sau khi đọc từng chunk, theo thang điểm của GUIDE, kèm lý do từng dòng. Học viên xem xét lại nhãn. Chấm một lần, không có người chấm độc lập thứ hai, nên có nguy cơ thiên lệch.

## Phân tích và kết luận

- **So sánh A–B và B–C; 2 ví dụ sai có ID câu và nguồn:**
  - **A–B (chỉ khác cách chunk):**
    - Hit@1 trên dev bằng nhau (10/15). A hơn B một câu ở Hit@3 dev (14/15 so với 13/15).
    - Trên test, A cũng cao hơn (Hit@1 4/5 so với 2/5), nhưng chỉ có 5 câu nên sai số rất lớn.
    - Đổi lại, B có ít chunk hơn 38% (385 so với 621) và thời gian embed chỉ bằng khoảng một nửa.
    - **Coherence: B 2,0/2, A 1,4/2.** Ở 6/10 vị trí, chunk của A bị cắt giữa từ hoặc giữa câu ở cuối (ví dụ `emerges from c`, `trained o`, `ordered str`). B không cắt ngang câu ở vị trí nào.
    - **Grounding test: A 2,0/2, B 1,6/2.** Khác biệt nằm ở q19: chunk p94 của A chứa đủ chuỗi điều kiện "không có nhãn → kiểm chứng được → RFT", trong khi top-3 của B (p68, p92, p136) không có quy tắc này.
    - Như vậy, chunk ngắn của A dễ khớp truy vấn hơn nhưng kém mạch lạc. Chunk của B mạch lạc hơn nhưng có lúc không vào được top-3.
  - **B–C (chỉ khác filter):**
    - Hit@1 và Hit@3 không đổi.
    - Filter làm top-3 tuân thủ chương: dev từ 2/3 lên 3/3, test từ 1/2 lên 2/2.
    - Ví dụ q15 (`ai_agents`): B lấy thêm một chunk từ chương `rag` (p146), C thay chunk đó bằng p197. Ví dụ q18 (`llm_deployment`): B lấy p83 thuộc `fine_tuning`, C thay bằng p364.
    - Filter giúp loại nhiễu khác chương, nhưng không làm đổi thứ hạng của chunk đúng.
    - **Metadata:** 15/15 bản ghi đúng ở cả 3 chiến lược. `page` và `char_start`/`char_end` giúp truy về đúng đoạn trong PDF. `chapter` giúp lọc như ví dụ q18. Hạn chế: `chapter` khá rộng (chương `ai_agents` có 77 trang) nên không phân biệt được các mục trong cùng chương. Ngoài ra, filter chỉ dùng được khi người dùng biết trước chương cần hỏi.
  - **Ví dụ sai 1, q13 (dev, gold p148):**
    - A xếp đúng trang p148 ở hạng 1, nhưng evidence bị cửa sổ 500 ký tự cắt ngang, nên **không** được tính Hit. Đây là lỗi do cách chunk.
    - B giữ trọn evidence trong một chunk nhưng không lấy được p148 trong top-3 (lấy p114, p140, p135 của chương `rag`). Chunk dài hơn có thể làm embedding bị "loãng".
  - **Ví dụ sai 2, q10 (dev, gold p121):**
    - A trúng ở hạng 3 (sau p122 và p120).
    - B trả về p122, p120, p123: các trang lân cận cùng nói về chunking. Evidence 308 ký tự nằm trọn trong chunk p121 của B nhưng chunk này không vào top-3.
- **Chiến lược chọn, đánh đổi, điều kiện áp dụng:**
  - Theo tiêu chí đã chốt (Hit@3 dev): **chọn A** (14/15 so với 13/15). Cách biệt chỉ là 1 câu trên 15 câu.
  - Đánh đổi: A tốn gấp khoảng 1,6 lần số chunk và gấp khoảng 2 lần thời gian embed, và coherence thấp hơn (1,4 so với 2,0). Nếu chunk được đưa thẳng cho LLM đọc, chunk cụt của A có thể làm câu trả lời thiếu ý. Khi đó B, hoặc A với `size` lớn hơn, đáng cân nhắc.
  - Nếu ứng dụng cần giới hạn phạm vi theo chương, nên bật filter như C, vì filter tăng độ tuân thủ phạm vi mà không làm giảm Hit.
- **Hạn chế:**
  - Chỉ có 20 câu (5 câu test), nên chênh lệch 1–2 câu không có ý nghĩa thống kê.
  - Benchmark do AI hỗ trợ soạn và nhãn thủ công do LLM đề xuất, chỉ một người chấm, nên có nguy cơ thiên lệch. Mẫu coherence chỉ gồm 10 trang của chương `llms`.
  - Evidence Hit đòi khớp nguyên văn, nên chunk chứa đúng nội dung nhưng cắt ngang câu vẫn bị tính trượt (trường hợp q13 với A).
  - Thời gian chỉ đo một lần, trên một máy (i5-11400H, RTX 3050). Embed 20 câu hỏi từng câu một mất 44,2 s (khoảng 2,2 s/câu), chậm hơn nhiều so với embed chunk theo lô, nên thời gian truy vấn thực tế phụ thuộc mạnh vào cách gọi Ollama.
  - Corpus và model là tiếng Anh; nội dung trong hình bị mất.
- **Nếu làm lại hoặc mở rộng, cải tiến gì?**
  - Thử B với `max_size` nhỏ hơn (ví dụ 500) để tách riêng ảnh hưởng của *độ dài* chunk với *ranh giới* chunk.
  - Thử hybrid retrieval (BM25 + dense) cho các câu như q10, q13.
  - OCR cho sơ đồ.
  - Thêm câu test để giảm sai số.

## Sử dụng AI
Dùng Claude (Claude Code) để: giải thích yêu cầu, review và hoàn thiện code (`ingestion`, `chunking`, `embeddings`, `store`, `evaluation`, `run`), soạn nháp benchmark và báo cáo, và đề xuất nhãn coherence, metadata, grounding kèm lý do. Học viên kiểm tra bằng cách chạy `verify_evidence.py`, chạy pipeline, đọc lại câu hỏi và đáp án, và xem xét lại nhãn trong `starter/results/audit/`.
