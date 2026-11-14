# Môi trường chạy

Bài này dùng **embedding model chạy local qua Ollama**, không dùng API trả phí. Đề bài cho phép cách này: "Dùng embedding model thật qua API hoặc chạy local". Cả 3 cấu hình A/B/C dùng chung model, vector store và metric.

## Embedding model

| Thông số | Giá trị |
| --- | --- |
| Runtime | Ollama 0.40.16 (Windows), `http://localhost:11434` |
| Model | `nomic-embed-text:latest` (ID `0a109f422b47`) |
| Kiến trúc / kích thước | nomic-bert, 137M tham số, F16, khoảng 274 MB |
| Số chiều vector | 768 (đã kiểm tra bằng lệnh gọi `/api/embed`) |
| Context length | 2048 token. Chunk lớn nhất khoảng 1.000 ký tự, nằm trong giới hạn |
| Giấy phép | Apache License 2.0 |
| Endpoint | `POST /api/embed` với `{"model": "nomic-embed-text", "input": [...]}` |
| Tiền tố bắt buộc theo model card | Document: `search_document: <text>`; Query: `search_query: <text>` |
| Độ đo | Cosine distance (`<=>` trong pgvector) |
| Ngôn ngữ | Chủ yếu tiếng Anh, khớp với corpus và câu hỏi tiếng Anh |
| Chi phí | 0 (chạy local, không gửi dữ liệu ra ngoài) |
| Xử lý lỗi | Ollama không phản hồi hoặc sai số chiều thì dừng và báo lỗi, **không** chuyển sang vector giả |

Lần gọi đầu mất khoảng 26 giây để nạp model vào bộ nhớ (cold start). Khi đo thời gian ingest, cần gọi khởi động trước hoặc báo riêng thời gian nạp model.

Cài đặt và tải model:

```bash
# Cài Ollama: https://ollama.com/download
ollama pull nomic-embed-text
ollama list          # kiểm tra có nomic-embed-text:latest
```

## Vector store

| Thông số | Giá trị |
| --- | --- |
| Database | PostgreSQL 16.16 + pgvector 0.8.7 (image `pgvector/pgvector:0.8.7-pg16`) |
| Khởi động | `docker compose -p day6_student_starter up -d --wait` (trong `starter/`) |
| Kết nối | `DATABASE_URL` trong `starter/.env`, cổng `127.0.0.1:55433` |
| Docker | 29.0.1 |

## Python

| Gói | Phiên bản |
| --- | --- |
| Python | 3.14.3 (venv `starter/.venv`) |
| pypdf | 6.21.4 |
| psycopg / psycopg-binary | 3.3.8 |
| python-dotenv | 1.2.4 |

Gọi Ollama bằng thư viện chuẩn `urllib`, không cần cài SDK.

## Phần cứng (để đọc số đo thời gian)

| Thành phần | Giá trị |
| --- | --- |
| CPU | Intel Core i5-11400H, 6 nhân |
| RAM | 15.8 GB |
| GPU | NVIDIA GeForce RTX 3050 Laptop GPU |
| OS | Windows 11 Home 10.0.26200 |
