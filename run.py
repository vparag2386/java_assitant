from agents.orchestrator import orchestrate

if __name__ == "__main__":
    feature = input("👉 What feature do you want to add? ")
    final_code = orchestrate(feature, model="mistral")  # change model if needed
    print("\n🎉 FINAL APPROVED CODE:\n")
    print(final_code)
