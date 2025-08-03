import os
import javalang
import hashlib
import numpy as np
from db.vector_store import VectorStore

SKIP_FOLDERS = {"target", "build", "out", ".idea", ".git"}

class JavaIngestor:
    def __init__(self, root_path, model="codellama"):
        self.root_path = root_path
        self.db = VectorStore()  # No longer using Ollama for embeddings here

    def generate_fake_embedding(self, text):
        """Create a deterministic fake embedding (hash-based)."""
        hash_bytes = hashlib.sha256(text.encode("utf-8")).digest()
        # Convert hash to float array and pad to 1024-dim for pgvector
        arr = np.frombuffer(hash_bytes, dtype=np.uint8).astype(float)
        padded = np.zeros(1024)
        padded[:len(arr)] = arr[:min(len(arr), 1024)]
        return padded.tolist()

    def ingest(self):
        file_count = 0
        print(f"🔍 Starting recursive scan in: {self.root_path}")

        for subdir, dirs, files in os.walk(self.root_path):
            # Skip unwanted folders
            dirs[:] = [d for d in dirs if d not in SKIP_FOLDERS]

            for file in files:
                if file.endswith(".java"):
                    file_path = os.path.join(subdir, file)
                    print(f"📄 Scanning: {file_path}")
                    file_count += 1

                    try:
                        with open(file_path, "r") as f:
                            code = f.read()

                        try:
                            tree = javalang.parse.parse(code)
                        except Exception as parse_err:
                            print(f"⚠️ Parse error in {file_path}: {parse_err}")
                            continue

                        for path, class_decl in tree.filter(javalang.tree.ClassDeclaration):
                            for method in class_decl.methods:
                                snippet = f"{class_decl.name}.{method.name}()"
                                fake_embed = self.generate_fake_embedding(snippet)
                                self.db.insert_embeddings([(file_path, class_decl.name, method.name, snippet, fake_embed)])

                    except Exception as file_err:
                        print(f"⚠️ Could not process {file_path}: {file_err}")
                        continue

        print(f"✅ Finished scanning. Total Java files processed: {file_count}")
