import subprocess

def call_model(prompt, model="llama2"):
    """
    Sends the prompt to Ollama model (default: llama2).
    Change model to mistral, codellama, etc. as needed.
    """
    process = subprocess.run(["ollama", "run", model],
                             input=prompt.encode(),
                             capture_output=True)
    return process.stdout.decode()
