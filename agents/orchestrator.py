# agents/orchestrator.py

import os
import json
import re
import uuid
import datetime
from prompts.pm_prompt import pm_prompt
from prompts.architect_prompt import architect_prompt
from prompts.dev_prompt import dev_prompt
from prompts.reviewer_prompt import reviewer_prompt
from llm import call_model

# =========================
# Config / constants
# =========================

# Lock the real root to avoid drift
PACKAGE_ROOT = "com.example.userproductapp"
HEADER_PREFIX = f"src/main/java/{PACKAGE_ROOT.replace('.', '/')}/"

# Toggle full prompt/response logging: export LLM_TRACE=1
TRACE = os.getenv("LLM_TRACE", "0") == "1"
_SESSION_ID = None

# =========================
# Tracing helpers
# =========================

# Redact obvious secrets if they accidentally end up in prompts
_REDACT_PATTERNS = [
    (r"(?i)(api[_-]?key)\s*=\s*[\w\-]+", r"\1=***"),
    (r"(?i)(password)\s*=\s*[^\s\n]+", r"\1=***"),
    (r"postgresql:\/\/[^ \n]+:[^@\n]+@", "postgresql://***:***@"),
]

def _ensure_log_dir() -> str:
    """Create logs/run-YYYYmmdd-HHMMSS-<id>/ and return the path (once per process)."""
    global _SESSION_ID
    if _SESSION_ID is None:
        _SESSION_ID = f"run-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
    path = os.path.join("logs", _SESSION_ID)
    os.makedirs(path, exist_ok=True)
    return path

def _redact_safe(text: str) -> str:
    out = text or ""
    for pat, repl in _REDACT_PATTERNS:
        out = re.sub(pat, repl, out)
    return out

def log_block(stage: str, kind: str, text: str):
    """
    stage: 'pm', 'architect', 'dev:<FQCN>', 'reviewer:<FQCN>', etc.
    kind : 'input' | 'output' | 'code'
    """
    if not TRACE:
        return
    path = _ensure_log_dir()
    fname = f"{stage}.{kind}.txt"
    fp = os.path.join(path, fname)
    with open(fp, "w", encoding="utf-8") as f:
        f.write(_redact_safe(text or ""))
    print(f"📝 Logged {kind} for {stage} -> {fp}")

# =========================
# Parsing / extraction utils
# =========================

# Tolerant header: allow leading spaces and //FILE: without space
HEADER_RE = re.compile(r'^\s*//\s*FILE\s*:\s*(.+)$', re.M)

def strip_fences(text: str) -> str:
    """Remove accidental code fences like ``` / ```java."""
    return re.sub(r"```(?:\w+)?|```", "", text)

def extract_single_file_block(text: str):
    """
    Extract exactly one file block:
      // FILE: <path>
      <content ... up to next header or EOF>
    Tolerates leading whitespace and accidental code fences.
    Returns the block string or None.
    """
    clean = strip_fences(text or "").lstrip()
    matches = list(HEADER_RE.finditer(clean))
    if not matches:
        return None
    first = matches[0]
    next_match = HEADER_RE.search(clean, first.end())
    end = next_match.start() if next_match else len(clean)
    return clean[first.start():end]

def extract_json(text: str):
    """Extract the first JSON object found in text."""
    cleaned = strip_fences(text or "")
    try:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        return json.loads(match.group(0)) if match else None
    except json.JSONDecodeError:
        return None

def contains_placeholders(code: str) -> bool:
    """Detect common stub/placeholder markers."""
    patterns = [
        r"//\s*getters and setters",
        r"//\s*implement(?!ed)",
        r"//\s*other methods?",
        r"//\s*\.\.\.",
        r"//\s*add method",
        r"//\s*your code here",
        r"//\s*todo",
        r"\bto be implemented\b",
        r"\bstub\b",
    ]
    return any(re.search(p, code or "", re.IGNORECASE) for p in patterns)

def valid_package_root(dev_code: str, pkg_root=PACKAGE_ROOT) -> bool:
    return f"package {pkg_root}." in (dev_code or "")

def valid_header_path(dev_code: str, pkg_root=PACKAGE_ROOT) -> bool:
    return re.search(rf"^//\s*FILE\s*:\s*src/main/java/{pkg_root.replace('.', '/')}/", dev_code or "", re.M) is not None

def normalize_to_root(dev_code: str, target_class: str, pkg_root=PACKAGE_ROOT) -> str:
    """
    Normalize the // FILE header and package declaration to the correct root,
    based on the provided target_class.
    """
    if not dev_code:
        return dev_code
    # 1) Correct header from target_class
    correct_header = f"// FILE: src/main/java/{target_class.replace('.', '/')}.java"
    dev_code = re.sub(r"^//\s*FILE\s*:.*$", correct_header, dev_code, count=1, flags=re.M)

    # 2) Replace package declaration with package derived from target_class
    target_pkg = ".".join(target_class.split(".")[:-1])
    dev_code = re.sub(r"^\s*package\s+[a-zA-Z0-9_.]+\s*;\s*$",
                      f"package {target_pkg};",
                      dev_code, count=1, flags=re.M)

    # 3) Map common drift roots back to the correct root
    dev_code = re.sub(r"com\.example\.productreviewsystem", pkg_root, dev_code)
    return dev_code

# =========================
# Orchestration
# =========================

def orchestrate(feature_request, model="mistral"):
    print(f"📌 Feature Request: {feature_request}")

    # ---------- PM Step ----------
    print("\n📝 PM interpreting the request...")
    pm_prompt_text = pm_prompt(feature_request)
    log_block("pm", "input", pm_prompt_text)

    pm_output = call_model(pm_prompt_text, model=model)
    log_block("pm", "output", pm_output)

    pm_plan = extract_json(pm_output) or json.loads(strip_fences(pm_output))

    # ---------- Architect Step ----------
    print("\n🏗 Architect designing the solution...")
    arch_prompt_text = architect_prompt(pm_plan)
    log_block("architect", "input", arch_prompt_text)

    arch_output = call_model(arch_prompt_text, model=model)
    log_block("architect", "output", arch_output)

    # Generate one class per iteration (order can be adjusted)
    target_classes = [
        f"{PACKAGE_ROOT}.review.Review",
        f"{PACKAGE_ROOT}.review.ReviewRepository",
        f"{PACKAGE_ROOT}.review.ReviewService",
        f"{PACKAGE_ROOT}.review.ReviewController",
    ]

    # Base context for the developer (you can wire RAG in later)
    base_context = {
        "entities": "User, Product",
        "repositories": "UserRepository, ProductRepository",
        "services": "UserService, ProductService",
        "controllers": "UserController, ProductController",
        "package_root": PACKAGE_ROOT,
    }

    all_approved_code = []

    for target_class in target_classes:
        print(f"\n🔄 Generating class: {target_class}")
        review_passed = False
        attempt = 0

        while not review_passed:
            attempt += 1
            print(f"🧪 Attempt {attempt} - Developer generating {target_class}...")

            # Developer step
            dev_prompt_text = dev_prompt(pm_plan, arch_output, base_context, target_class)
            log_block(f"dev:{target_class}", "input", dev_prompt_text)

            dev_output = call_model(dev_prompt_text, model=model)
            log_block(f"dev:{target_class}", "output", dev_output)

            # Tolerant single-file extraction
            dev_code_block = extract_single_file_block(dev_output)
            if not dev_code_block:
                print("❌ Could not find a // FILE: header (allowing leading spaces/fences). Retrying…")
                continue

            # If multiple headers exist, accept the first block and warn
            headers_count = len(list(HEADER_RE.finditer(strip_fences(dev_output).lstrip())))
            if headers_count > 1:
                print("⚠️ Multiple // FILE: headers found. Using the first block and ignoring the rest.")

            dev_code = dev_code_block

            # Normalize package drift & header
            if not valid_package_root(dev_code) or not valid_header_path(dev_code):
                dev_code = normalize_to_root(dev_code, target_class)

            # Reject placeholders
            if contains_placeholders(dev_code):
                print("❌ Placeholder comments found. Retrying...")
                continue

            log_block(f"dev:{target_class}", "code", dev_code)

            # Reviewer step
            print(f"🕵️ Reviewer checking {target_class}...")
            reviewer_prompt_text = reviewer_prompt(pm_plan, dev_code)
            log_block(f"reviewer:{target_class}", "input", reviewer_prompt_text)

            reviewer_output = call_model(reviewer_prompt_text, model=model)
            log_block(f"reviewer:{target_class}", "output", reviewer_output)

            reviewer_feedback = extract_json(reviewer_output)
            if not reviewer_feedback:
                print("⚠️ Reviewer output not valid JSON.")
                continue

            status = (reviewer_feedback.get("status") or "").lower()
            if status == "approved":
                print(f"✅ {target_class} approved!\n")
                all_approved_code.append(dev_code)
                review_passed = True
            else:
                issues = reviewer_feedback.get("issues") or []
                print(f"❌ Reviewer rejected {target_class}: {issues}")

    return "\n\n".join(all_approved_code)
