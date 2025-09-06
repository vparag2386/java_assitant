import os
import re
from agents.orchestrator import orchestrate
from analyzer.call_graph import CallGraphBuilder
from db.vector_store import VectorStore

def scan_java_code_for_embeddings(project_path):
    """
    Scans all Java files in the project directory,
    generates embeddings, and stores them in the vector DB.
    """
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
    """
    Parses Java files and builds method call graph relationships.
    """
    print("🔍 Building call graph...")
    builder = CallGraphBuilder(project_path)
    builder.scan_codebase()
    print("✅ Call graph build complete!")

def save_generated_files(code_blob, base_path):
    """
    Parses the `// FILE:` markers and writes each file to disk.
    Normalizes paths so that headers like `com/example/.../X.java`
    are saved under `src/main/java/com/example/.../X.java`.
    """
    if not code_blob or not isinstance(code_blob, str):
        raise ValueError("❌ Developer did not produce any code.")

    def normalize_rel_path(rel_path: str) -> str:
        # unify slashes and trim
        p = rel_path.replace("\\", "/").strip()
        # drop any accidental leading slash
        if p.startswith("/"):
            p = p[1:]
        # if the header already starts with src/main/java, keep it
        if p.startswith("src/main/java/"):
            return p
        # if the header begins with a package path, prepend src/main/java/
        if p.startswith("com/") or p.startswith("org/") or p.startswith("io/") or p.startswith("net/"):
            return f"src/main/java/{p}"
        # if the header is just a filename, leave it as-is (could be resources/tests etc.)
        return p

    file_blocks = re.split(r"(?=// FILE:)", code_blob)

    for block in file_blocks:
        if not block.strip():
            continue

        header_match = re.match(r"// FILE:\s*(.+)", block)
        if not header_match:
            print(f"⚠️ Skipping block (no file marker): {block[:80]!r}")
            continue

        raw_rel_path = header_match.group(1).strip()
        # the rest of the block after the header line
        content = block.split("\n", 1)[1] if "\n" in block else ""
        rel_path = normalize_rel_path(raw_rel_path)

        file_path = os.path.join(base_path, rel_path)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content.strip())

        print(f"💾 Code saved to: {file_path}")


def run_orchestrator(project_path, feature_request):
    """
    Runs the full workflow:
    PM → Architect → (class-by-class) Developer → Reviewer → Save to disk.
    """
    print(f"\n🚀 Java Assistant Console")
    print(f"📌 Feature request: {feature_request}")

    # Run orchestrator: now handles class-by-class loop internally
    generated_code = orchestrate(feature_request, model="mistral")

    if not generated_code:
        raise ValueError("❌ No code generated. Check prompts or model output.")

    # Save each generated file to disk
    save_generated_files(generated_code, project_path)

    # Optional: print result
    # print("\n✅ Final Generated Code:\n")
    # print(generated_code)

if __name__ == "__main__":
    project_path = "codebase/src/main/java"

    print("📂 Scanning Java code for embeddings...")
    scan_java_code_for_embeddings(project_path)

    print("\n🔄 Building call graph...")
    build_call_graph(project_path)

    print("\n🎯 Starting Orchestrator workflow...")
    feature_request = input("👉 What feature do you want to add?\n> ")

    run_orchestrator("codebase", feature_request)
