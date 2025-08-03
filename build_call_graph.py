# build_call_graph.py

from analyzer.call_graph import CallGraphBuilder

if __name__ == "__main__":
    project_path = "codebase/src/main/java"  # adjust if needed

    print(f"🔍 Building call graph for Java project at: {project_path}")
    builder = CallGraphBuilder(project_path)
    builder.scan_codebase()
    print("✅ Call graph build complete! `method_calls` table is now populated.")
