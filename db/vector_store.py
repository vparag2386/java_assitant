# db/vector_store.py

import psycopg2
from psycopg2.extras import execute_values

from config import DB_CONFIG


# import ollama  # Uncomment if using Ollama for embeddings

class VectorStore:
    def __init__(self):
        self.conn = psycopg2.connect(**DB_CONFIG)
        self._create_table()

    def _create_table(self):
        with self.conn.cursor() as cur:
            cur.execute("""
                CREATE EXTENSION IF NOT EXISTS vector;
                CREATE TABLE IF NOT EXISTS java_metadata (
                    id SERIAL PRIMARY KEY,
                    file_path TEXT,
                    class_name TEXT,
                    method_name TEXT,
                    code_snippet TEXT,
                    embedding vector(1024)
                );
            """)
            self.conn.commit()

    # ✅ NEW: helper for embeddings
    def generate_embedding(self, text):
        """
        Generate an embedding vector for a given code snippet or text.
        Right now: dummy embedding for POC (returns 1024 zeros).
        Later: replace with Ollama or OpenAI embeddings.
        """
        return [0.0] * 1024   # POC placeholder

        # When you switch to Ollama:
        # result = ollama.embed(model="mistral", input=text)
        # return result['embedding']

    def insert_embeddings(self, data):
        """
        Insert a batch of code snippet embeddings into DB.
        Data format: [(file_path, class_name, method_name, code_snippet, embedding)]
        """
        with self.conn.cursor() as cur:
            execute_values(cur,
                """
                INSERT INTO java_metadata (file_path, class_name, method_name, code_snippet, embedding)
                VALUES %s
                """,
                data
            )
            self.conn.commit()

    def search(self, query_embedding, top_k=5):
        """
        Search for code snippets by embedding similarity.
        """
        with self.conn.cursor() as cur:
            vector_str = "[" + ",".join([str(x) for x in query_embedding]) + "]"
            cur.execute(
                """
                SELECT file_path, class_name, method_name, code_snippet
                FROM java_metadata
                ORDER BY embedding <-> %s::vector LIMIT %s;
                """,
                (vector_str, top_k)
            )
            return cur.fetchall()

    def search_code_snippets(self, query, top_k=5):
        """
        Search pgvector DB for code snippets relevant to the query (for RAG).
        Uses generate_embedding() internally.
        """
        embedding = self.generate_embedding(query)
        embedding_str = "[" + ",".join(map(str, embedding)) + "]"

        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT file_path, class_name, method_name, code_snippet
                FROM java_metadata
                ORDER BY embedding <-> %s::vector
                LIMIT %s;
                """,
                (embedding_str, top_k)
            )
            return cur.fetchall()
