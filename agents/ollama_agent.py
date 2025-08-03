import subprocess

class OllamaAgent:
    def __init__(self, name, model="mistral", system_prompt=""):
        self.name = name
        self.model = model
        self.system_prompt = system_prompt

    def query_ollama(self, prompt):
        try:
            result = subprocess.run(
                ["ollama", "run", self.model],
                input=prompt,
                text=True,
                capture_output=True
            )
            return result.stdout.strip()
        except Exception as e:
            return f"[ERROR] {e}"

    def respond(self, message):
        full_prompt = f"{self.system_prompt}\nHuman/Other Agent: {message}\n{self.name}:"
        return self.query_ollama(full_prompt)
