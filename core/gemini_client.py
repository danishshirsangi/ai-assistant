import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types


class GeminiClient:
    """Gemini cloud chat and embedding client used by the cloud experiment."""

    DEFAULT_CHAT_MODEL = "gemini-3.8-flash"
    DEFAULT_EMBEDDING_MODEL = "gemini-embedding-2"
    EMBEDDING_DIMENSIONS = 768

    def __init__(self, api_key=None, chat_model=None, embedding_model=None):
        project_root = Path(__file__).resolve().parents[1]
        load_dotenv(project_root / ".env", override=False)

        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.chat_model = (
            chat_model or os.getenv("GEMINI_MODEL") or self.DEFAULT_CHAT_MODEL
        )
        self.embedding_model = (
            embedding_model
            or os.getenv("GEMINI_EMBEDDING_MODEL")
            or self.DEFAULT_EMBEDDING_MODEL
        )
        self.client = genai.Client(api_key=self.api_key) if self.api_key else None

    def _require_client(self):
        if self.client is None:
            raise RuntimeError(
                "Gemini API key not found. Add GEMINI_API_KEY=your_key to the "
                "project's .env file, then restart Interview Copilot. Create a key "
                "at https://aistudio.google.com/apikey."
            )
        return self.client

    def health(self):
        """Validate the API key and configured chat model without generating text."""
        client = self._require_client()
        client.models.get(model=self.chat_model)
        return {"models": [{"name": self.chat_model}]}

    def embed(self, texts, purpose="document"):
        """Create Gemini Embedding 2 vectors for resume retrieval."""
        if not texts:
            return []

        client = self._require_client()
        if purpose == "query":
            prepared = [
                f"task: search query\nquery: {text}" for text in texts
            ]
        else:
            prepared = [
                f"task: search document\ncontent: {text}" for text in texts
            ]

        contents = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=item)],
            )
            for item in prepared
        ]

        vectors = []
        # Keep requests at a moderate size for predictable API latency.
        for start in range(0, len(contents), 32):
            batch = contents[start:start + 32]
            result = client.models.embed_content(
                model=self.embedding_model,
                contents=batch,
                config=types.EmbedContentConfig(
                    output_dimensionality=self.EMBEDDING_DIMENSIONS
                ),
            )
            embeddings = getattr(result, "embeddings", None) or []
            if len(embeddings) != len(batch):
                raise RuntimeError(
                    "Gemini returned an unexpected number of resume embeddings."
                )
            vectors.extend(embedding.values for embedding in embeddings)

        return vectors

    @staticmethod
    def _format_input(messages):
        system_instruction = ""
        conversation = []

        for message in messages:
            role = message.get("role", "user")
            content = str(message.get("content", "")).strip()
            if not content:
                continue
            if role == "system":
                system_instruction = content
            elif role == "assistant":
                conversation.append("COPILOT (previous answer):\n" + content)
            else:
                conversation.append("USER / INTERVIEWER:\n" + content)

        return system_instruction, "\n\n".join(conversation)

    def chat(self, messages, temperature=0.35, on_chunk=None):
        """Generate an answer through the stateless Gemini Interactions API."""
        client = self._require_client()
        system_instruction, prompt = self._format_input(messages)
        if not prompt:
            raise ValueError("No user prompt was provided to Gemini.")

        request = {
            "model": self.chat_model,
            "input": prompt,
            "system_instruction": system_instruction or None,
            # Keep conversation content client-side rather than storing Interaction
            # records on Google's servers. This does not change free-tier data-use
            # terms for requests sent to the API.
            "store": False,
            "generation_config": {
                "temperature": temperature,
                "thinking_level": "medium",
            },
        }

        if on_chunk is None:
            interaction = client.interactions.create(**request)
            return interaction.output_text or ""

        parts = []
        stream = client.interactions.create(**request, stream=True)
        for event in stream:
            if getattr(event, "event_type", None) != "step.delta":
                continue
            delta = getattr(event, "delta", None)
            if getattr(delta, "type", None) != "text":
                continue
            token = getattr(delta, "text", "")
            if token:
                parts.append(token)
                on_chunk(token)

        return "".join(parts)
