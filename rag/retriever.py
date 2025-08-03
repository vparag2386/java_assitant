import hashlib
import numpy as np
from db.vector_store import VectorStore

class Retriever:
    def __init__(self, model="codellama"):
        self.db = VectorStore()

    def generate_fake_embedding(self, text):
        """Create the same deterministic fake embedding used in ingestion."""
        hash_bytes = hashlib.sha256(text.encode("utf-8")).digest()
        arr = np.frombuffer(hash_bytes, dtype=np.uint8).astype(float)
        padded = np.zeros(1024)
        padded[:len(arr)] = arr[:min(len(arr), 1024)]
        return padded.tolist()

    def ask(self, question):
        fake_embed = self.generate_fake_embedding(question)
        return self.db.search(fake_embed)
