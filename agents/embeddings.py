import random
import ollama
import requests
import json
import re

# ✅ Toggle: if True, will bypass Ollama and return random vectors for dev
USE_FAKE_EMBEDDINGS = True

def check_ollama_connection():
    """Check if Ollama server is running."""
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=2)
        return r.status_code == 200
    except requests.exceptions.RequestException:
        return False

def generate_embedding(text, model="codellama"):
    """
    Generates an embedding for text.
    ✅ If USE_FAKE_EMBEDDINGS=True → returns a random 1024-dim vector instantly.
    ✅ If False → uses Ollama (chat) to generate an embedding.
    """

    # 🚀 Fast dev mode: skip Ollama entirely
    if USE_FAKE_EMBEDDINGS:
        print("⚡ Using FAKE EMBEDDINGS (random floats) for fast scanning")
        return [random.uniform(-1, 1) for _ in range(1024)]

    # ✅ Check if Ollama server is running
    if not check_ollama_connection():
        print("\n❌ ERROR: Cannot connect to Ollama server on http://localhost:11434")
        print("➡️  Make sure Ollama is running by doing one of these:")
        print("   • Open the Ollama app (it will run in the background), OR")
        print("   • Run `ollama serve` in a terminal.")
        raise ConnectionError("Ollama server is not running.")

    prompt = f"""
    Convert the following text into a JSON array of exactly 1024 floating point numbers
    between -1 and 1 (an embedding vector).
    Output ONLY the array. No explanation, no words, no markdown.

    Text: \"{text}\"
    """

    response = ollama.chat(
        model=model,
        messages=[{"role": "user", "content": prompt}]
    )

    output = response["message"]["content"]

    match = re.search(r"\[.*\]", output, re.DOTALL)
    if not match:
        raise ValueError(f"Model did not return a JSON array.\nOllama Output:\n{output}")

    try:
        embedding = json.loads(match.group(0))
        return embedding
    except json.JSONDecodeError:
        raise ValueError("Could not parse embedding JSON from Ollama response.")
