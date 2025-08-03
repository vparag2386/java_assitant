# main.py

from agents.orchestrator import AgentOrchestrator
from analyzer.call_graph import CallGraphBuilder
from db.vector_store import VectorStore
import os

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

                    # Store class-level info in DB
                    # Simple logic: extract class, method names for embeddings
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

def run_orchestrator(project_path, feature_request):
    """Runs the PM → Architect → Developer → Reviewer workflow."""
    orchestrator = AgentOrchestrator(model="codellama")

    print(f"\n🚀 Java Assistant Console")
    print(f"📌 Feature request: {feature_request}")

    # RAG: pull snippets to help planning
    snippets = orchestrator.vector_store.search_code_snippets(feature_request, top_k=10)

    # PM & Architect plan the feature
    plan = orchestrator.plan_feature(feature_request, snippets)

    # Developer writes code, Reviewer checks, code is saved into src/main/java
    orchestrator.generate_code(plan, project_path)

if __name__ == "__main__":
    project_path = "codebase/src/main/java"

    print("📂 Scanning Java code for embeddings...")
    scan_java_code_for_embeddings(project_path)

    print("\n🔄 Building call graph...")
    build_call_graph(project_path)

    print("\n🎯 Starting Orchestrator workflow...")
    feature_request = input("👉 What feature do you want to add? (e.g., 'Add login and authentication using JWT')\n> ")

    run_orchestrator("codebase", feature_request)
