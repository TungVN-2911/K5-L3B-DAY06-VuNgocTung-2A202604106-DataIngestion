from typing import Any

import psycopg

from .models import Chunk

TABLE = "chunks"
# Chỉ các key này được phép làm filter; map sang tên cột cố định (không ghép chuỗi từ input).
FILTER_COLUMNS = {"chapter": "chapter", "document_id": "document_id", "page": "page"}


def _vector_literal(vector: list[float]) -> str:
    return "[" + ",".join(repr(float(x)) for x in vector) + "]"


class PgVectorStore:
    def __init__(self, database_url: str, dimensions: int) -> None:
        if not database_url:
            raise ValueError("thiếu DATABASE_URL")
        if dimensions <= 0:
            raise ValueError(f"số chiều không hợp lệ: {dimensions}")
        self.dimensions = dimensions
        self.conn = psycopg.connect(database_url, connect_timeout=5)

    def close(self) -> None:
        self.conn.close()

    def create_schema(self) -> None:
        with self.conn.transaction(), self.conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {TABLE} (
                    strategy      text    NOT NULL,
                    chunk_id      text    NOT NULL,
                    document_id   text    NOT NULL,
                    source        text    NOT NULL,
                    page          integer NOT NULL,
                    chapter       text    NOT NULL,
                    printed_page  integer,
                    char_start    integer NOT NULL,
                    char_end      integer NOT NULL,
                    text          text    NOT NULL,
                    embedding     vector({self.dimensions}) NOT NULL,
                    PRIMARY KEY (strategy, chunk_id)
                )""")
            cur.execute(f"CREATE INDEX IF NOT EXISTS {TABLE}_strategy_chapter ON {TABLE} (strategy, chapter)")
            cur.execute(
                "SELECT atttypmod FROM pg_attribute WHERE attrelid = %s::regclass AND attname = 'embedding'",
                (TABLE,),
            )
            stored = cur.fetchone()[0]
            if stored != self.dimensions:
                raise RuntimeError(f"bảng {TABLE} dùng vector({stored}), model trả {self.dimensions} chiều")

    def upsert(self, strategy: str, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        if len(chunks) != len(vectors):
            raise ValueError(f"{len(chunks)} chunk nhưng {len(vectors)} vector")
        if any(len(v) != self.dimensions for v in vectors):
            raise ValueError(f"có vector không đủ {self.dimensions} chiều")
        ids = [c.chunk_id for c in chunks]
        if len(set(ids)) != len(ids):
            raise ValueError("chunk_id bị trùng trong lô upsert")
        documents = sorted({c.document_id for c in chunks})
        rows = [
            (strategy, c.chunk_id, c.document_id, c.source, c.page, c.metadata["chapter"],
             c.metadata.get("printed_page"), c.metadata["char_start"], c.metadata["char_end"],
             c.text, _vector_literal(v))
            for c, v in zip(chunks, vectors)
        ]
        with self.conn.transaction(), self.conn.cursor() as cur:
            # Xóa chunk cũ của cùng tài liệu không còn trong lần nạp này (tài liệu đổi -> không để rác).
            cur.execute(
                f"DELETE FROM {TABLE} WHERE strategy = %s AND document_id = ANY(%s) AND NOT (chunk_id = ANY(%s))",
                (strategy, documents, ids),
            )
            cur.executemany(
                f"""INSERT INTO {TABLE} (strategy, chunk_id, document_id, source, page, chapter,
                        printed_page, char_start, char_end, text, embedding)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::vector)
                    ON CONFLICT (strategy, chunk_id) DO UPDATE SET
                        document_id = EXCLUDED.document_id, source = EXCLUDED.source,
                        page = EXCLUDED.page, chapter = EXCLUDED.chapter,
                        printed_page = EXCLUDED.printed_page, char_start = EXCLUDED.char_start,
                        char_end = EXCLUDED.char_end, text = EXCLUDED.text, embedding = EXCLUDED.embedding""",
                rows,
            )

    def count(self, strategy: str) -> int:
        with self.conn.cursor() as cur:
            cur.execute(f"SELECT count(*) FROM {TABLE} WHERE strategy = %s", (strategy,))
            return cur.fetchone()[0]

    def search(self, strategy: str, query_vector: list[float], top_k: int = 3,
               filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        if len(query_vector) != self.dimensions:
            raise ValueError(f"query vector có {len(query_vector)} chiều, cần {self.dimensions}")
        where, params = ["strategy = %s"], [strategy]
        for key, value in (filters or {}).items():
            if key not in FILTER_COLUMNS:
                raise ValueError(f"filter không được hỗ trợ: {key}")
            where.append(f"{FILTER_COLUMNS[key]} = %s")
            params.append(value)
        sql = f"""SELECT chunk_id, document_id, source, page, chapter, printed_page, char_start, char_end,
                         text, embedding <=> %s::vector AS distance
                  FROM {TABLE} WHERE {' AND '.join(where)}
                  ORDER BY distance LIMIT %s"""
        with self.conn.cursor() as cur:
            cur.execute(sql, [_vector_literal(query_vector), *params, top_k])
            rows = cur.fetchall()
        return [
            {
                "chunk_id": r[0], "document_id": r[1], "source": r[2], "page": r[3],
                "metadata": {"chapter": r[4], "printed_page": r[5], "char_start": r[6], "char_end": r[7]},
                "text": r[8], "score": 1 - float(r[9]),
            }
            for r in rows
        ]
