import json
import logging

import requests


logger = logging.getLogger(__name__)


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

    def _chat_once(self, messages, temperature, on_chunk):
        payload = {
            "model": self.chat_model,
            "messages": messages,
            "stream": on_chunk is not None,
            "think": False,
            "keep_alive": self.keep_alive,
            "options": {"temperature": temperature, "num_predict": 2048},
        }

        if on_chunk is None:
            response = requests.post(
                f"{self.base_url}/api/chat", json=payload, timeout=600
            )
            response.raise_for_status()
            data = response.json()
            return (
                data.get("message", {}).get("content", ""),
                data.get("done_reason"),
                data.get("eval_count"),
            )

        parts = []
        done_reason = None
        eval_count = None
        with requests.post(
            f"{self.base_url}/api/chat", json=payload,
            timeout=(10, 600), stream=True,
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
                    done_reason = event.get("done_reason")
                    eval_count = event.get("eval_count")
                    break
        return "".join(parts), done_reason, eval_count

    def chat(self, messages, temperature=0.35, on_chunk=None):
        # A length stop is a hard generation limit, not a completed answer.
        # Continue once with the existing answer as context instead of silently
        # returning a response that may end halfway through a section.
        conversation = list(messages)
        answer_parts = []
        for attempt in range(2):
            answer, done_reason, eval_count = self._chat_once(
                conversation, temperature, on_chunk
            )
            answer_parts.append(answer)
            logger.info(
                "Ollama generation finished: reason=%s, generated_tokens=%s, "
                "attempt=%s",
                done_reason, eval_count, attempt + 1,
            )
            if done_reason != "length" or attempt == 1:
                break
            conversation.extend([
                {"role": "assistant", "content": answer},
                {
                    "role": "user",
                    "content": (
                        "Continue exactly where you stopped. Do not repeat any "
                        "completed content. Finish every remaining section and "
                        "end with a complete sentence."
                    ),
                },
            ])
        return "".join(answer_parts)
