def reviewer_prompt(pm_plan, dev_code):
    """
    Strict single-file reviewer.

    Validates:
      - Exactly one // FILE: header
      - No markdown fences/backticks
      - Header path starts with src/main/java/
      - Package declaration matches the header path (package ↔ path alignment)
      - No placeholders/stubs
      - Constructor injection only (no field-level @Autowired)
      - Surface compile checks (imports & annotations sanity)
      - Reasonable Spring layering rules
    """
    return f"""
You are a strict Java/Spring Boot code reviewer.

Review the developer's SINGLE-FILE submission against the PM plan.

PM Plan:
{pm_plan}

Developer Submission:
{dev_code}

Approve ONLY if ALL checks pass:

A) Output & fencing:
   - FIRST non-empty line must be: // FILE: ...
   - There must be EXACTLY ONE // FILE: header in total.
   - REJECT if any markdown fences/backticks (e.g., ``` or ```java) appear anywhere.

B) Header & package:
   - Header path MUST start with: src/main/java/
   - Extract package from header path (after src/main/java/, replace '/' with '.').
   - The Java 'package ...;' declaration MUST equal that package.
   - REJECT if root deviates from the project (e.g., com.example.productreviewsystem) or uses pseudo-roots like ".domain.entities"/".repositories"/".domain.services".

C) No placeholders/stubs:
   - REJECT if the file contains any of: "// getters and setters", "// add method", "// ...", "// TODO", "to be implemented", "stub".
   - REJECT if file is truncated (mid-word lines like "g..." or unclosed blocks).

D) Constructor injection only:
   - REJECT if dependencies are injected via field-level @Autowired.
   - Allow @Autowired on constructor, or omit @Autowired if single constructor.

E) Surface compile sanity:
   - Required imports present for used types (basic check).
   - Annotations consistent (e.g., @Entity with @Id field; @RestController with @RequestMapping/@GetMapping/@PostMapping).
   - Repository method names look like plausible Spring Data names for the referenced domain types.

F) Layering rules:
   - Controllers call Services; Services call Repositories.
   - REJECT Controller → Repository direct calls.

Return STRICT JSON only:
{{
  "status": "approved" or "rejected",
  "issues": ["Short, concrete issues (empty if approved)"]
}}
"""
