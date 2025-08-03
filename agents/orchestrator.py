import os
import re
from agents.ollama_agent import OllamaAgent
from db.vector_store import VectorStore


class AgentOrchestrator:
    def __init__(self, model="codellama"):
        """
        Coordinates PM → Architect → Developer → Reviewer agents.
        Hardened version: loops until ALL missing pieces and TODOs are resolved.
        """

        # ✅ PM Agent
        self.pm = OllamaAgent(
            "PM",
            model=model,
            system_prompt=(
                "You are an experienced software project manager for a Java/Spring Boot project. "
                "Take vague feature requests and write a clear, structured project brief.\n\n"
                "Include:\n"
                "- Scope\n"
                "- Impacted Code Areas\n"
                "- Acceptance Criteria\n"
                "- Dependencies\n"
                "- Risks & Constraints\n"
                "Be clear and bullet‑pointed."
            )
        )

        # ✅ Architect Agent
        self.architect = OllamaAgent(
            "Architect",
            model=model,
            system_prompt=(
                "You are a senior Java/Spring Boot architect.\n\n"
                "From the PM notes, create a detailed technical design.\n\n"
                "Include:\n"
                "- Package Plan\n"
                "- Class & Interface Plan\n"
                "- Design Patterns\n"
                "- Methods & Responsibilities\n"
                "- Edge Cases\n\n"
                "Output as a structured outline."
            )
        )

        # ✅ Developer Agent (stricter: NO TODO, full implementation)
        self.developer = OllamaAgent(
            "Developer",
            model=model,
            system_prompt=(
                "You are a senior Java/Spring Boot developer.\n\n"
                "TASK:\n"
                "- Implement the requested feature completely.\n"
                "- Write ALL required Java classes, interfaces, DTOs, configs, filters, controllers, services, repositories, etc. in ONE single response.\n"
                "- DO NOT stop after one file. DO NOT drift into unrelated features.\n"
                "- Stay focused on the feature request.\n\n"
                "RULES:\n"
                "- Absolutely NO placeholders. NO 'TODO'. NO empty methods.\n"
                "- Implement every method fully and correctly.\n"
                "- Use proper Spring Boot conventions (controllers, services, repositories, DTOs, exceptions, security configs).\n"
                "- Include imports, annotations, correct package declarations.\n"
                "- If you don’t know a method body, research and provide a valid implementation.\n\n"
                "OUTPUT:\n"
                "- ONLY compilable Java code. End after the last closing curly brace '}'.\n"
                "- No markdown fences, no explanations, no example text."
            )
        )

        # ✅ Reviewer Agent (flags TODO, missing classes, empty methods)
        self.reviewer = OllamaAgent(
            "Reviewer",
            model=model,
            system_prompt=(
                "You are a senior Java/Spring Boot code reviewer.\n\n"
                "JOB:\n"
                "- Verify that all code fully implements the requested feature.\n"
                "- List any missing classes with 'MISSING:' (e.g. MISSING: JwtTokenProvider.java).\n"
                "- Flag ANY empty methods or 'TODO' comments.\n"
                "- Flag duplicate class names or wrong package declarations.\n\n"
                "If there are ANY missing pieces or TODOs, explicitly list them so the Developer must rewrite."
            )
        )

        self.vector_store = VectorStore()

    # === Planning ===
    def plan_feature(self, feature, snippets):
        """PM → Architect planning pipeline."""
        context = "\n".join([
            f"File: {s[0]}, Class: {s[1]}, Method: {s[2]}\n{s[3]}"
            for s in snippets
        ])

        print("\nPM interpreting the feature request...")
        pm_notes = self.pm.respond(
            f"Feature request:\n{feature}\n\nRelevant code context:\n{context}\n"
            "Clarify this feature into detailed steps for the team."
        )
        print(f"\nPM Output:\n{pm_notes}")

        print("\nArchitect designing the solution...")
        architecture_plan = self.architect.respond(
            f"The PM said:\n{pm_notes}\n\n"
            "Propose packages, classes, and methods to modify or create."
        )
        print(f"\nArchitect Output:\n{architecture_plan}")

        final_plan = f"{pm_notes}\n\nARCHITECT PLAN:\n{architecture_plan}"
        print("\nPlanning Phase Complete — Final Plan Ready")
        return final_plan

    # === Code Generation ===
    def generate_code(self, plan, project_path):
        """
        Developer writes full feature code.
        Reviewer checks for missing pieces and triggers rewrite until clean.
        """
        context_snippets = self.vector_store.search_code_snippets(plan, top_k=5)
        rag_context = "\n".join([
            f"File: {s[0]}, Class: {s[1]}, Method: {s[2]}\n{s[3]}" for s in context_snippets
        ])

        print("\nDeveloper is writing code...")
        code_draft = self.developer.respond(
            f"""
            Feature request plan:
            {plan}

            Relevant existing code:
            {rag_context}

            Write ALL required Java classes in one response. 
            Include imports, annotations, and correct packages.
            Output ONLY compilable Java code. 
            """
        )

        print("\nDeveloper Output:\n")
        print(code_draft)

        # 🔄 Loop until reviewer approves (no missing classes or TODOs)
        max_passes = 3
        for rewrite_round in range(1, max_passes + 1):
            print("\nReviewer is reviewing code...")
            review_feedback = self.reviewer.respond(
                f"""
                Here is the draft code:
                {code_draft}

                Does this code fully deliver the requested feature?
                List any missing classes with 'MISSING:'.
                Flag any TODOs or empty methods.
                """
            )
            print("\nReviewer Feedback:\n")
            print(review_feedback)

            if not self._needs_fix(review_feedback):
                print("✅ Reviewer approved code. All missing pieces resolved.")
                break

            print(f"\n⚠️ Reviewer flagged issues → Developer rewriting code (Pass {rewrite_round})...")
            code_draft = self.developer.respond(
                f"""
                Reviewer found issues:
                {review_feedback}

                Rewrite the ENTIRE codebase for this feature.
                - Include ALL missing classes, configs, and logic.
                - REMOVE every TODO and empty method.
                - KEEP everything previously written (do not drop earlier classes).
                Output ONLY Java code. Do NOT write explanations.
                """
            )

            print("\nDeveloper Revised Output:\n")
            print(code_draft)

        self._save_generated_code(code_draft, project_path)

    def _needs_fix(self, feedback):
        """Check if Reviewer flagged issues (missing, TODO, empty methods)."""
        keywords = [
            "missing",
            "todo",
            "not implemented",
            "needs",
            "fix",
            "empty method",
            "duplicate"
        ]
        return any(word in feedback.lower() for word in keywords)

    def _save_generated_code(self, java_code, project_path):
        """
        Cleans and saves generated Java code into correct package folders.
        Filters out meta-text like 'Overall, the code...' or explanations.
        """
        cleaned_lines = []
        stop_phrases = [
            "overall, the code",
            "here's an example",
            "this code",
            "as you can see",
            "in summary",
            "the code provided"
        ]

        for line in java_code.splitlines():
            line_stripped = line.strip().lower()

            # stop if meta-text detected
            if any(phrase in line_stripped for phrase in stop_phrases):
                print(f"⚠️ Stopping code write at line: {line}")
                break

            if line.strip().startswith("```"):
                continue

            # skip bullets, comments, etc.
            if line_stripped.startswith(("-", "*", "#")):
                continue

            # fix formatting quirks
            line = line.replace("classpublic", "public class")
            line = line.replace("interfacepublic", "public interface")
            cleaned_lines.append(line)

        final_code = "\n".join(cleaned_lines)

        # 🔍 Split into separate files by package & class
        chunks = re.split(r'(?=package |public (?:class|interface|enum) )', final_code)
        src_base = os.path.join(project_path, "src/main/java")
        os.makedirs(src_base, exist_ok=True)

        current_package = "generated"
        buffer = ""

        for chunk in chunks:
            if not chunk or not isinstance(chunk, str) or not chunk.strip():
                continue

            if chunk.startswith("package "):
                lines = chunk.splitlines()
                pkg_line = lines[0]
                current_package = pkg_line.replace("package", "").replace(";", "").strip()
                buffer += chunk
                continue

            if chunk.startswith("public "):
                buffer += chunk

                class_match = re.search(r'(class|interface|enum)\s+(\w+)', buffer)
                if not class_match:
                    print("Skipped: no class/interface/enum found.")
                    buffer = ""
                    continue

                class_name = class_match.group(2)

                pkg_path = current_package.replace(".", "/")
                full_path = os.path.join(src_base, pkg_path)
                os.makedirs(full_path, exist_ok=True)

                file_path = os.path.join(full_path, f"{class_name}.java")

                if os.path.exists(file_path):
                    print(f"⚠️ Duplicate detected: {file_path}. Skipping save.")
                    buffer = ""
                    continue

                with open(file_path, "w") as f:
                    f.write(buffer)

                print(f"📄 Saved: {file_path}")
                buffer = ""
