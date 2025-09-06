# db/generation_store.py
import psycopg2
from psycopg2.extras import execute_values
from typing import Dict, List, Set
from config import DB_CONFIG

DDL = """
CREATE TABLE IF NOT EXISTS gen_classes (
    id SERIAL PRIMARY KEY,
    feature_id TEXT NOT NULL,
    fqcn TEXT NOT NULL,
    header_path TEXT NOT NULL,
    package TEXT NOT NULL,
    source_code TEXT NOT NULL,
    approved BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS gen_methods (
    id SERIAL PRIMARY KEY,
    feature_id TEXT NOT NULL,
    fqcn TEXT NOT NULL,
    method_name TEXT NOT NULL,
    signature TEXT DEFAULT '',
    visibility TEXT DEFAULT 'public',
    return_type TEXT DEFAULT '',
    params TEXT DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Helpful indexes
CREATE INDEX IF NOT EXISTS idx_gen_classes_feature ON gen_classes(feature_id);
CREATE INDEX IF NOT EXISTS idx_gen_methods_feature ON gen_methods(feature_id);
CREATE INDEX IF NOT EXISTS idx_gen_methods_fqcn ON gen_methods(fqcn);
"""

class GenerationStore:
    def __init__(self):
        self.conn = psycopg2.connect(**DB_CONFIG)
        self._ensure_schema()

    def _ensure_schema(self):
        with self.conn.cursor() as cur:
            cur.execute(DDL)
        self.conn.commit()

    # ---------- feature scoping ----------

    def cleanup_feature(self, feature_id: str):
        with self.conn.cursor() as cur:
            cur.execute("DELETE FROM gen_methods WHERE feature_id = %s;", (feature_id,))
            cur.execute("DELETE FROM gen_classes WHERE feature_id = %s;", (feature_id,))
        self.conn.commit()

    # ---------- classes ----------

    def insert_class(self, feature_id: str, fqcn: str, header_path: str, package: str, source_code: str, approved: bool = True):
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO gen_classes (feature_id, fqcn, header_path, package, source_code, approved)
                VALUES (%s, %s, %s, %s, %s, %s);
                """,
                (feature_id, fqcn, header_path, package, source_code, approved)
            )
        self.conn.commit()

    # ---------- methods ----------

    def insert_methods(self, feature_id: str, fqcn: str, methods: List[Dict]):
        """
        methods: list of dicts with keys: method_name, signature, visibility, return_type, params
        """
        rows = [
            (
                feature_id,
                fqcn,
                m.get("method_name", ""),
                m.get("signature", ""),
                m.get("visibility", "public"),
                m.get("return_type", ""),
                m.get("params", "")
            )
            for m in methods
        ]
        if not rows:
            return
        with self.conn.cursor() as cur:
            execute_values(
                cur,
                """
                INSERT INTO gen_methods (feature_id, fqcn, method_name, signature, visibility, return_type, params)
                VALUES %s
                """,
                rows
            )
        self.conn.commit()

    def get_contract(self, feature_id: str, fqcn: str) -> Set[str]:
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT method_name FROM gen_methods WHERE feature_id = %s AND fqcn = %s;",
                (feature_id, fqcn)
            )
            return {row[0] for row in cur.fetchall()}

    def get_all_contracts(self, feature_id: str) -> Dict[str, List[str]]:
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT fqcn, method_name FROM gen_methods WHERE feature_id = %s;",
                (feature_id,)
            )
            mapping: Dict[str, List[str]] = {}
            for fqcn, method in cur.fetchall():
                mapping.setdefault(fqcn, []).append(method)
            return mapping

    def close(self):
        try:
            self.conn.close()
        except Exception:
            pass
