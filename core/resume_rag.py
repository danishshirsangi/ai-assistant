import json
import math
import sqlite3
from pathlib import Path

from core.document_loader import load_document, chunk_text


class ResumeRAG:
    """
    Cloud-backed semantic retrieval:
    - Gemini creates embeddings.
    - SQLite stores text + vectors locally.
    - Python computes cosine similarity.
    This avoids ChromaDB/ONNX Runtime dependencies.
    """

    def __init__(self, embedding_client, persist_dir="vector_db_gemini"):
        self.embedding_client = embedding_client
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.persist_dir / "resume_vectors.sqlite3"
        self._initialize()

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_type TEXT NOT NULL,
                filename TEXT NOT NULL,
                chunk_text TEXT NOT NULL,
                embedding TEXT NOT NULL
            )
        """)
        return conn

    def _initialize(self):
        with self._connect() as conn:
            conn.commit()

    def add_file(self, path):
        text = load_document(path)
        chunks = chunk_text(text)
        if not chunks:
            raise ValueError(
                "No readable text was found. If this is a scanned PDF, "
                "we will need to add OCR."
            )

        filename = Path(path).name
        embeddings = self.embedding_client.embed(
            chunks, purpose="document", titles=[filename] * len(chunks)
        )
        if len(embeddings) != len(chunks):
            raise RuntimeError("Gemini returned an unexpected number of embeddings.")

        with self._connect() as conn:
            conn.execute("DELETE FROM chunks WHERE source_type = ?", ("resume",))
            conn.executemany(
                """INSERT INTO chunks
                   (source_type, filename, chunk_text, embedding)
                   VALUES (?, ?, ?, ?)""",
                [
                    ("resume", filename, chunk, json.dumps(vector))
                    for chunk, vector in zip(chunks, embeddings)
                ],
            )
            conn.commit()
        return len(chunks)

    @staticmethod
    def _cosine_similarity(a, b):
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))
        if not norm_a or not norm_b:
            return 0.0
        return dot / (norm_a * norm_b)

    def retrieve(self, question, n_results=4):
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT chunk_text, embedding FROM chunks WHERE source_type = ?",
                ("resume",),
            ).fetchall()

        if not rows:
            return []

        query_embedding = self.embedding_client.embed([question], purpose="query")[0]
        ranked = []
        for chunk, embedding_json in rows:
            vector = json.loads(embedding_json)
            score = self._cosine_similarity(query_embedding, vector)
            ranked.append((score, chunk))

        ranked.sort(key=lambda item: item[0], reverse=True)
        return [chunk for score, chunk in ranked[:n_results]]
