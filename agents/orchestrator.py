import json
import re
from prompts.pm_prompt import pm_prompt
from prompts.architect_prompt import architect_prompt
from prompts.dev_prompt import dev_prompt
from prompts.reviewer_prompt import reviewer_prompt
from llm import call_model


def extract_json(text):
    """
    Extracts the first valid JSON block from the model response.
    Cleans up extra markdown fences and explanations.
    """
    try:
        # Remove markdown fences like ```json or ```
        cleaned = re.sub(r"```(json)?", "", text)

        # Find the first JSON object in the cleaned text
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    return None


def orchestrate(feature_request, model="mistral"):
    """
    Orchestrates the workflow: PM → Architect → Developer → Reviewer (iterates until approved).
    """

    print(f"📌 Feature Request: {feature_request}")

    # ✅ 1. PM Step
    print("\n📝 PM interpreting the request...")
    pm_output = call_model(pm_prompt(feature_request), model=model)
    print("✅ PM Output:")
    print(pm_output)

    try:
        pm_plan = json.loads(pm_output)
    except json.JSONDecodeError:
        print("⚠️ PM output not clean JSON. Trying extraction...")
        pm_plan = extract_json(pm_output)
        if not pm_plan:
            raise Exception("❌ PM output is not valid JSON.")

    # ✅ 2. Architect Step
    print("\n🏗 Architect designing the solution...")
    arch_output = call_model(architect_prompt(pm_plan), model=model)
    print("✅ Architect Output:")
    print(arch_output)

    # ✅ 3. Developer-Reviewer Loop
    review_passed = False
    dev_code = None
    iteration = 0
    reviewer_feedback = None

    while not review_passed:
        iteration += 1
        print(f"\n🔄 Iteration {iteration} - Developer writing code...")

        # Developer step
        dev_output = call_model(dev_prompt(pm_plan, arch_output, reviewer_feedback), model=model)
        dev_code = dev_output.strip()
        print("\n👨‍💻 Developer Output:")
        print(dev_code[:500], "...")  # show first 500 chars for preview

        # Reviewer step
        print("\n🔍 Reviewer checking code...")
        reviewer_output = call_model(reviewer_prompt(pm_plan, dev_code), model=model)
        print("✅ Reviewer Output (raw):")
        print(reviewer_output)

        reviewer_feedback = extract_json(reviewer_output)

        if not reviewer_feedback:
            print("⚠️ Reviewer output had bad JSON. Raw output below:")
            print(reviewer_output)
            raise Exception("❌ Reviewer output is not valid JSON.")

        if reviewer_feedback["status"].lower() == "approved":
            print("\n✅ Reviewer approved the code!")
            review_passed = True
        else:
            print("\n⚠️ Reviewer flagged issues. Sending feedback back to Developer...")
            print("Issues:", reviewer_feedback["issues"])

    return dev_code
