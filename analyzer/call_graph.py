# analyzer/call_graph.py

import os
import javalang
import psycopg2
from config import DB_CONFIG

class CallGraphBuilder:
    def __init__(self, project_path):
        self.project_path = project_path
        self.conn = psycopg2.connect(**DB_CONFIG)

    def scan_codebase(self):
        """Walk through project and parse all Java files."""
        for root, _, files in os.walk(self.project_path):
            for file in files:
                if file.endswith(".java"):
                    file_path = os.path.join(root, file)
                    print(f"🔍 Parsing {file_path}")
                    with open(file_path, "r", encoding="utf-8") as f:
                        code = f.read()
                        self._parse_file(code)

    def _parse_file(self, code):
        try:
            tree = javalang.parse.parse(code)
        except javalang.parser.JavaSyntaxError as e:
            print(f"⚠️ Skipped file (syntax error): {e}")
            return

        # Find classes & methods
        for path, class_decl in tree.filter(javalang.tree.ClassDeclaration):
            class_name = class_decl.name

            for method in class_decl.methods:
                method_name = method.name
                self._extract_method_calls(class_name, method_name, method)

    def _extract_method_calls(self, class_name, method_name, method_node):
        """Look for all method invocations inside a method."""
        calls = []
        for path, node in method_node.filter(javalang.tree.MethodInvocation):
            called_method = node.member
            called_class = node.qualifier  # e.g., userService.authenticate()

            # Store relationship
            calls.append((class_name, method_name, called_class, called_method))

        if calls:
            self._insert_calls(calls)

    def _insert_calls(self, calls):
        with self.conn.cursor() as cur:
            cur.executemany("""
                INSERT INTO method_calls (caller_class, caller_method, called_class, called_method)
                VALUES (%s, %s, %s, %s);
            """, calls)
        self.conn.commit()
