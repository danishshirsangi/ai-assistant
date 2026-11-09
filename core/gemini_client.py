import logging
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types


logger = logging.getLogger(__name__)


class GeminiClient:
    """Gemini cloud chat and embeddings client for the cloud experiment."""

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
        self.client = (
            genai.Client(
                api_key=self.api_key,
                http_options=types.HttpOptions(timeout=90_000),
            )
            if self.api_key else None
        )

    def _require_client(self):
        if self.client is None:
            raise RuntimeError(
                "Gemini API key not found. Add GEMINI_API_KEY=your_key to the "
                "project's .env file, then restart Interview Copilot. Create a key "
                "at https://aistudio.google.com/apikey."
            )
        return self.client

    def health(self):
        """Check API access and the configured model without generating a response."""
        client = self._require_client()
        client.models.get(model=self.chat_model)
        return {"models": [{"name": self.chat_model}]}

    def embed(self, texts, purpose="document", titles=None):
        """Create Gemini Embedding 2 vectors for resume retrieval."""
        if not texts:
            return []

        client = self._require_client()
        titles = titles or []
        prepared = []
        for index, text in enumerate(texts):
            if purpose == "query":
                prepared.append(f"task: search result | query: {text}")
            else:
                title = titles[index] if index < len(titles) else "none"
                prepared.append(f"title: {title} | text: {text}")

        vectors = []
        for item in prepared:
            result = client.models.embed_content(
                model=self.embedding_model,
                contents=item,
                config=types.EmbedContentConfig(
                    output_dimensionality=self.EMBEDDING_DIMENSIONS
                ),
            )
            embeddings = getattr(result, "embeddings", None) or []
            if len(embeddings) != 1:
                raise RuntimeError(
                    "Gemini returned an unexpected number of resume embeddings."
                )
            vectors.append(embeddings[0].values)

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
        """Generate text with the supported Generate Content streaming interface."""
        del temperature  # Gemini 3.x recommends leaving sampling parameters at defaults.
        client = self._require_client()
        system_instruction, prompt = self._format_input(messages)
        if not prompt:
            raise ValueError("No user prompt was provided to Gemini.")

        config = types.GenerateContentConfig(
            system_instruction=system_instruction or None,
            thinking_config=types.ThinkingConfig(thinking_level="low"),
        )

        started = time.monotonic()
        first_text_at = None
        parts = []
        logger.info(
            "Starting Gemini request: model=%s, prompt_chars=%s, thinking=low",
            self.chat_model,
            len(prompt),
        )

        if on_chunk is None:
            response = client.models.generate_content(
                model=self.chat_model,
                contents=prompt,
                config=config,
            )
            text = response.text or ""
            logger.info(
                "Gemini response completed in %.1fs",
                time.monotonic() - started,
            )
            return text

        # Google documents generate_content_stream as yielding response chunks
        # whose .text property contains newly generated text.
        stream = client.models.generate_content_stream(
            model=self.chat_model,
            contents=prompt,
            config=config,
        )
        for chunk in stream:
            token = chunk.text or ""
            if not token:
                continue
            if first_text_at is None:
                first_text_at = time.monotonic()
                logger.info(
                    "Gemini first text token after %.1fs",
                    first_text_at - started,
                )
            parts.append(token)
            on_chunk(token)

        elapsed = time.monotonic() - started
        logger.info(
            "Gemini stream completed in %.1fs with %s text chunks",
            elapsed,
            len(parts),
        )
        if not parts:
            raise RuntimeError(
                "Gemini completed the request without returning any text. "
                "Check API quota, model availability and the terminal log."
            )
        return "".join(parts)
