import requests

class OllamaClient:
    def __init__(self, base_url="http://localhost:11434", chat_model="qwen3:8b",
                 embedding_model="nomic-embed-text"):
        self.base_url = base_url.rstrip("/")
        self.chat_model = chat_model
        self.embedding_model = embedding_model

    def health(self):
        r = requests.get(f"{self.base_url}/api/tags", timeout=5)
        r.raise_for_status()
        return r.json()

    def embed(self, texts):
        # Ollama's current /api/embed endpoint accepts a list of input strings.
        r = requests.post(
            f"{self.base_url}/api/embed",
            json={"model": self.embedding_model, "input": texts},
            timeout=120,
        )
        r.raise_for_status()
        data = r.json()
        return data["embeddings"]

    def chat(self, messages, temperature=0.35):
        r = requests.post(
            f"{self.base_url}/api/chat",
            json={
                "model": self.chat_model,
                "messages": messages,
                "stream": False,
                "think": False,
                "options": {"temperature": temperature},
            },
            timeout=300,
        )
        r.raise_for_status()
        return r.json()["message"]["content"]
