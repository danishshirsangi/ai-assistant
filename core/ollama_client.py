import json

import requests


class OllamaClient:
    def __init__(self, base_url="http://localhost:11434", chat_model="qwen3:8b",
                 embedding_model="nomic-embed-text"):
        self.base_url = base_url.rstrip("/")
        self.chat_model = chat_model
        self.embedding_model = embedding_model
        self.keep_alive = "30m"

    def health(self):
        r = requests.get(f"{self.base_url}/api/tags", timeout=5)
        r.raise_for_status()
        return r.json()

    def embed(self, texts):
        r = requests.post(
            f"{self.base_url}/api/embed",
            json={"model": self.embedding_model, "input": texts,
                  "keep_alive": self.keep_alive},
            timeout=120,
        )
        r.raise_for_status()
        return r.json()["embeddings"]

    def chat(self, messages, temperature=0.35, on_chunk=None):
        payload = {
            "model": self.chat_model,
            "messages": messages,
            "stream": on_chunk is not None,
            "think": False,
            "keep_alive": self.keep_alive,
            "options": {"temperature": temperature, "num_predict": 256},
        }
        if on_chunk is None:
            response = requests.post(
                f"{self.base_url}/api/chat", json=payload, timeout=300
            )
            response.raise_for_status()
            return response.json()["message"]["content"]

        parts = []
        with requests.post(
            f"{self.base_url}/api/chat", json=payload,
            timeout=(10, 300), stream=True,
        ) as response:
            response.raise_for_status()
            for line in response.iter_lines(decode_unicode=True):
                if not line:
                    continue
                event = json.loads(line)
                token = event.get("message", {}).get("content", "")
                if token:
                    parts.append(token)
                    on_chunk(token)
                if event.get("done"):
                    break
        return "".join(parts)
