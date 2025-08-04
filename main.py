import os
import re
from agents.orchestrator import orchestrate
from analyzer.call_graph import CallGraphBuilder
from db.vector_store import VectorStore

def scan_java_code_for_embeddings(project_path):
    """Scans Java files and stores code snippets into pgvector DB."""
    vector_store = VectorStore()

    for root, _, files in os.walk(project_path):
        for file in files:
            if file.endswith(".java"):
                file_path = os.path.join(root, file)
                print(f"📂 Scanning: {file_path}")
                with open(file_path, "r", encoding="utf-8") as f:
                    code = f.read()
                    class_name = file.replace(".java", "")
                    vector_store.insert_embeddings([
                        (file_path, class_name, None, code, vector_store.generate_embedding(code))
                    ])

    print("✅ Embedding scan complete! All code stored in java_metadata.")

def build_call_graph(project_path):
    """Builds call graph relationships and stores them in DB."""
    print("🔍 Building call graph...")
    builder = CallGraphBuilder(project_path)
    builder.scan_codebase()
    print("✅ Call graph build complete!")

def save_generated_files(dev_code, base_path):
    """Splits the code blob into files and saves them under codebase/"""
    if not dev_code or not isinstance(dev_code, str):
        raise ValueError("❌ Developer did not produce any code.")

    file_blocks = re.split(r"(?=// FILE:)", dev_code)

    for block in file_blocks:
        if not block.strip():
            continue
        match = re.match(r"// FILE:\s*(.+)", block)
        if match:
            rel_path = match.group(1).strip()
            content = block.split("\n", 1)[1]

            file_path = os.path.join(base_path, rel_path)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content.strip())
            print(f"💾 Code saved to: {file_path}")
        else:
            print(f"⚠️ Skipping block (no file marker): {block[:50]}")

def run_orchestrator(project_path, feature_request):
    """Runs the PM → Architect → Developer → Reviewer workflow."""
    print(f"\n🚀 Java Assistant Console")
    print(f"📌 Feature request: {feature_request}")

    dev_code = orchestrate(feature_request, model="mistral")  # or codellama, gemma, etc.

    if not dev_code:
        raise ValueError("❌ No code generated. Check prompts or model output.")

    save_generated_files(dev_code, project_path)

if __name__ == "__main__":
    project_path = "codebase/src/main/java"

    print("📂 Scanning Java code for embeddings...")
    scan_java_code_for_embeddings(project_path)

    print("\n🔄 Building call graph...")
    build_call_graph(project_path)

    print("\n🎯 Starting Orchestrator workflow...")
    feature_request = input("👉 What feature do you want to add?\n> ")

    run_orchestrator("codebase", feature_request)
