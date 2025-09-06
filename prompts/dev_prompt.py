def dev_prompt(pm_plan, arch_plan, context=None, target_class=None):
    """
    Generate EXACTLY ONE Java class that compiles on its own.

    Parameters:
      pm_plan: dict or string from PM step
      arch_plan: string from Architect step
      context: optional dict that may include:
        - package_root: e.g. "com.example.userproductapp" (default inferred from target_class or fallback)
        - entities / repositories / services / controllers: brief lists or notes
        - known_apis: { fqcn: [methodName, ...], ... } of already-approved classes (optional)
        - service_contract: [methodName, ...] for controllers to honor (optional)
      target_class: fully-qualified class name to implement, e.g. "com.example.userproductapp.review.ReviewService"
    """
    context = context or {}

    # Derive package root and header from target_class
    if target_class and "." in target_class:
        package_root_from_target = ".".join(target_class.split(".")[:3])  # e.g., com.example.userproductapp
        expected_header = f"// FILE: src/main/java/{target_class.replace('.', '/')}.java"
        expected_package = ".".join(target_class.split(".")[:-1])
    else:
        package_root_from_target = None
        expected_header = "// FILE: src/main/java/REPLACE/YourClass.java"
        expected_package = "REPLACE"

    package_root = context.get("package_root") or package_root_from_target or "com.example.userproductapp"

    known_apis = context.get("known_apis", {})
    service_contract = context.get("service_contract", [])

    return f"""
You are a senior Java/Spring Boot developer.

Your task:
- Implement EXACTLY ONE class: {target_class or "(choose one under the existing package root)"}.

OUTPUT FORMAT (STRICT):
- The FIRST non-empty line MUST be this exact header:
{expected_header}
- Immediately after the header, output the COMPLETE Java source for {target_class}.
- Do NOT include markdown fences (no ``` or ```java), explanations, extra text, or additional files.
- Produce exactly ONE // FILE: header in total.

HARD REQUIREMENTS:
1) Package and path MUST align:
   - Header path must begin with: src/main/java/{package_root.replace('.', '/')}/
   - The Java package declaration must match the path after src/main/java/ (e.g., package {expected_package};)
   - Do NOT invent alternate roots like com.example.productreviewsystem or pseudo-roots like ".domain.entities"/".repositories"/".domain.services".
2) No placeholders or stubs:
   - Forbidden anywhere in the file: "// getters and setters", "// add method", "// ...", "// TODO", "to be implemented", "stub".
   - Implement all methods fully (getters, setters, equals/hashCode if relevant, etc.).
3) Constructor injection only (no field-level @Autowired).
4) Use java.time.LocalDateTime.now() for timestamps (never System.currentTimeMillis()).
5) Only call realistic Spring Data repository methods. If you introduce a repository in this file, define the methods you call.
6) Do NOT introduce Spring Security, Authentication, or unrelated infra unless explicitly in context/plan.

Order-resilient context you MAY reuse (optional hints):
- Entities: {context.get("entities", "e.g., User, Product")}
- Repositories: {context.get("repositories", "e.g., UserRepository, ProductRepository")}
- Services: {context.get("services", "e.g., UserService, ProductService")}
- Controllers: {context.get("controllers", "e.g., UserController, ProductController")}
- Known APIs (approved classes & their public methods): {known_apis}
- Allowed service methods for this controller (if applicable): {service_contract}

Feature Plan (from PM):
{pm_plan}

Architecture (from Architect):
{arch_plan}

REMINDERS:
- Start with the header line EXACTLY as shown.
- Output ONE file only. No extra commentary. No backticks.
- Ensure the package matches the header path and the package root {package_root}.
"""
