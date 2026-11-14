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

    DEFAULT_CHAT_MODEL = "gemini-3.5-flash-lite"
    DEFAULT_EMBEDDING_MODEL = "gemini-embedding-2"
    EMBEDDING_DIMENSIONS = 768

    def __init__(self, api_key=None, chat_model=None, embedding_model=None):
        project_root = Path(__file__).resolve().parents[1]
        load_dotenv(project_root / ".env", override=False)

        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        configured_model = chat_model or os.getenv("GEMINI_MODEL")
        # The previous experiment defaulted to 3.8 Flash, whose free-tier
        # output tokens are not available. Migrate that default to Flash-Lite.
        if configured_model == "gemini-3.8-flash":
            logger.warning(
                "Switching previous Gemini 3.8 Flash setting to %s for free-tier output access",
                self.DEFAULT_CHAT_MODEL,
            )
            configured_model = None
        self.chat_model = configured_model or self.DEFAULT_CHAT_MODEL
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
            # Leave enough room for long code answers. If the model still reaches
            # this limit, the loop below asks it to continue.
            max_output_tokens=8192,
            thinking_config=types.ThinkingConfig(thinking_level="minimal"),
        )

        started = time.monotonic()
        first_text_at = None
        all_parts = []
        request_messages = list(messages)
        max_continuations = 2

        logger.info(
            "Starting Gemini request: model=%s, prompt_chars=%s, "
            "max_output_tokens=%s, thinking=minimal",
            self.chat_model,
            len(prompt),
            config.max_output_tokens,
        )

        # A response can end because it is complete or because it hit the
        # model's output-token limit. Keep checking the finish reason and only
        # continue when Gemini explicitly reports MAX_TOKENS.
        for attempt in range(max_continuations + 1):
            _, request_prompt = self._format_input(request_messages)
            attempt_parts = []
            finish_reason = None

            if on_chunk is None:
                response = client.models.generate_content(
                    model=self.chat_model,
                    contents=request_prompt,
                    config=config,
                )
                text = response.text or ""
                attempt_parts.append(text)
                candidates = getattr(response, "candidates", None) or []
                if candidates:
                    finish_reason = getattr(candidates[0], "finish_reason", None)
            else:
                stream = client.models.generate_content_stream(
                    model=self.chat_model,
                    contents=request_prompt,
                    config=config,
                )
                for chunk in stream:
                    token = chunk.text or ""
                    if token:
                        if first_text_at is None:
                            first_text_at = time.monotonic()
                            logger.info(
                                "Gemini first text token after %.1fs",
                                first_text_at - started,
                            )
                        attempt_parts.append(token)
                        all_parts.append(token)
                        on_chunk(token)

                    candidates = getattr(chunk, "candidates", None) or []
                    for candidate in candidates:
                        reason = getattr(candidate, "finish_reason", None)
                        if reason is not None:
                            finish_reason = reason

            attempt_text = "".join(attempt_parts)
            if on_chunk is None:
                all_parts.append(attempt_text)

            reason_name = getattr(finish_reason, "name", str(finish_reason or ""))
            logger.info(
                "Gemini generation pass %s finished: reason=%s, chars=%s",
                attempt + 1,
                reason_name,
                len(attempt_text),
            )

            if reason_name.upper().split(".")[-1] != "MAX_TOKENS":
                break

            if attempt == max_continuations:
                warning = (
                    "\\n\\n[Gemini reached its output limit again. "
                    "This answer may still be incomplete.]"
                )
                logger.warning("Gemini response remains incomplete after continuations")
                all_parts.append(warning)
                if on_chunk is not None:
                    on_chunk(warning)
                break

            # Add the partial answer to the conversation and ask for only the
            # missing part. Streaming sends only the new text to the UI.
            request_messages.extend([
                {"role": "assistant", "content": attempt_text},
                {
                    "role": "user",
                    "content": (
                        "Your previous response stopped because it reached the "
                        "output limit. Continue exactly where it stopped. Do not "
                        "repeat any completed text or code. Finish all remaining "
                        "sections, close every code block, and do not claim the "
                        "answer is complete until it is actually complete."
                    ),
                },
            ])

        elapsed = time.monotonic() - started
        logger.info(
            "Gemini response finished in %.1fs with %s characters",
            elapsed,
            sum(len(part) for part in all_parts),
        )
        if not all_parts or not "".join(all_parts).strip():
            raise RuntimeError(
                "Gemini completed the request without returning any text. "
                "Check API quota, model availability and the terminal log."
            )
        return "".join(all_parts)
