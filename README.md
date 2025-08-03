# Java Assistant
This project scans a Java codebase, stores class/method metadata in Postgres with pgvector, 
and uses RAG (Retrieval Augmented Generation) + Ollama (Mistral/LLaMA3.2) to plan and generate new Java code.

## How to Use
1. Install Postgres & pgvector
2. Pull Ollama model: `ollama pull mistral`
3. Run: `python main.py`
