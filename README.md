# Day 06 · Data Ingestion Engineering

## Bài làm: cách setup và chạy

| Thành phần | Lựa chọn |
|---|---|
| Corpus | *AI Engineering* (DailyDoseofDS.com, 2025), 343/384 trang nội dung, xem [data/manifest.json](data/manifest.json) |
| Benchmark | 20 câu (15 dev / 5 test), xem [benchmark/](benchmark/README.md) |
| Embedding | Ollama `nomic-embed-text`, 768 chiều, chạy local, chi phí 0, xem [docs/run_environment.md](docs/run_environment.md) |
| Vector store | PostgreSQL 16 + pgvector 0.8.7 (Docker), cosine, exact search |
| Chiến lược | A: `fixed_size` 500/50 · B: `by_paragraph` ≤1000 · C: như B + filter `chapter`, xem [artifacts/experiment_log.csv](artifacts/experiment_log.csv) |

**1. Lấy dữ liệu.** PDF không được commit (95 MB, không có giấy phép mở). Tải bản miễn phí từ https://dailydoseofds.github.io/ai-engg-book/, đặt tại `data/AI Engineering Guidebook.pdf`, rồi đối chiếu `sha256` với manifest.

**2. Cài đặt** (chạy trong `starter/`; Windows PowerShell):

```bash
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
Copy-Item .env.example .env
docker compose -p day6_student_starter up -d --wait
.venv\Scripts\python scripts/check_setup.py
ollama pull nomic-embed-text
```

**3. Kiểm chứng dữ liệu và benchmark** (chạy từ root repo):

```bash
starter/.venv/Scripts/python data/build_manifest.py
starter/.venv/Scripts/python benchmark/verify_evidence.py
```

**4. Chạy pipeline** (chạy trong `starter/`):

```bash
.venv\Scripts\python -m src.run
```

Lệnh này nạp trang, chia chunk, embed, upsert hai lần (để kiểm tra nạp lại không trùng), chạy top-3 cho cả 20 câu với A/B/C, rồi ghi kết quả vào `starter/results/`:

| File | Nội dung |
|---|---|
| `traces_A.jsonl`, `traces_B.jsonl`, `traces_C.jsonl` | Top-3 của từng câu: chunk id, text, score, trang, chương, evidence hit, tuân thủ filter |
| `summary.json` | Hit@1 và Hit@3 theo dev/test, số chunk, độ dài, thời gian, kiểm tra nạp lại, phiên bản môi trường |
| `skipped_pages.json` | Các trang bị loại kèm lý do |
| `audit/*.csv` | Mẫu chấm tay coherence, metadata, grounding. Chạy lại không ghi đè nhãn đã điền |

Báo cáo: [report/individual/](report/individual/).

---

**Lab cá nhân** · **4 giờ** · **Dữ liệu tự chọn**

Biến tài liệu thành kho tri thức có thể truy xuất cho AI agent, rồi đo xem cách chuẩn bị dữ liệu nào hiệu quả nhất.

| 📄 Dữ liệu | 🧩 Chiến lược | 🎯 Benchmark |
|---|---|---|
| Tối thiểu **30 trang nội dung** | Tối thiểu **3 cấu hình** | Tối thiểu **20 câu hỏi** |

## Bắt đầu nhanh

Dùng [starter PostgreSQL + pgvector](starter/README.md) để dựng database và hoàn thiện các hàm TODO, hoặc tự chọn vector store tương đương. Starter chỉ là khung: **bạn tự hiện thực pipeline và benchmark**.

## 1. Xây pipeline

![Đọc tài liệu, chuẩn hóa, chia chunk, tạo vector, lưu và kiểm tra](assets/ingestion-pipeline.svg)

Chọn tài liệu được phép sử dụng; giữ **ID tài liệu, nguồn, trang/vị trí** và metadata phù hợp. Dùng embedding model thật qua API hoặc chạy local; lưu và truy xuất bằng pgvector, Qdrant, Chroma hoặc một store tương đương.

## 2. So sánh và đánh giá

![Ba chiến lược được đánh giá trên cùng corpus và benchmark dev/test](assets/benchmark-workflow.svg)

Dùng cùng dữ liệu, model và câu hỏi cho cả ba cấu hình. Tách **15 câu dev / 5 câu test** trước khi chạy; chọn cấu hình trên dev, rồi đánh giá test sau khi cố định. Mỗi câu hỏi cần có đoạn bằng chứng và trang nguồn; thiết kế bộ câu hỏi và đánh giá theo [BENCHMARK.md](BENCHMARK.md).

Đánh giá theo năm khía cạnh: **độ chính xác truy xuất**, **tính mạch lạc của chunk**, **tính hữu dụng của metadata**, **chất lượng grounding** và **tác động của chiến lược dữ liệu**. Giải thích lựa chọn bằng kết quả, ví dụ lỗi và các đánh đổi.

## 3. Chuẩn bị bài nộp

1. Chạy pipeline và lưu cấu hình, kết quả top-3, trace cùng nhãn đánh giá thủ công.
2. Điền [thông tin học viên](STUDENT.md), [nhật ký thí nghiệm](artifacts/experiment_log.csv) và bản sao [mẫu báo cáo cá nhân](report/individual/MSSV_HoTen.md).
3. Kiểm tra mã nguồn, cách chạy, manifest dữ liệu và checklist trong [SUBMISSION.md](SUBMISSION.md).

## Tài liệu hướng dẫn

| Bạn cần tìm | Tài liệu |
|---|---|
| Setup baseline PostgreSQL + pgvector | [starter/README.md](starter/README.md) |
| Các bước làm và cách tính chỉ số | [GUIDE.md](GUIDE.md) |
| Tiến độ trong 4 giờ | [CHECKPOINTS.md](CHECKPOINTS.md) |
| Năm tiêu chí benchmark và bộ câu hỏi | [BENCHMARK.md](BENCHMARK.md) |
| Tiêu chí chấm điểm | [RUBRIC.md](RUBRIC.md) |
| Quy tắc sử dụng dữ liệu, AI và API | [RULES.md](RULES.md) |
| Cách nộp bài | [SUBMISSION.md](SUBMISSION.md) |

[data/format-example.json](data/format-example.json) chỉ minh họa định dạng, không phải corpus đủ điều kiện. Phần xử lý và benchmark do bạn tự hiện thực; không bắt buộc xây chatbot.
