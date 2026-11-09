"""Standalone Gemini API diagnostic; bypasses PySide, audio and resume retrieval.

Run from the repository root:
    python diagnostics/gemini_smoke_test.py
"""
import faulthandler
import logging
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.gemini_client import GeminiClient  # noqa: E402


def run_step(label, fn):
    print(f"\n[{label}] starting", flush=True)
    started = time.monotonic()
    result = fn()
    print(f"[{label}] completed in {time.monotonic() - started:.1f}s", flush=True)
    return result


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    faulthandler.dump_traceback_later(35, repeat=True)

    try:
        client = GeminiClient()
        print(f"Chat model: {client.chat_model}", flush=True)
        print(f"Embedding model: {client.embedding_model}", flush=True)
        print(f"API key loaded: {'yes' if client.api_key else 'no'}", flush=True)

        run_step("API key and model check", client.health)

        vectors = run_step(
            "Embedding API",
            lambda: client.embed(
                ["SQL window functions are used for ranking and running totals."],
                purpose="query",
            ),
        )
        if not vectors or not vectors[0]:
            raise RuntimeError("Embedding API returned an empty vector.")
        print(f"Embedding dimensions: {len(vectors[0])}", flush=True)

        def stream_text(token):
            print(token, end="", flush=True)

        answer = run_step(
            "Text generation",
            lambda: client.chat(
                [
                    {
                        "role": "system",
                        "content": "Answer in one short sentence.",
                    },
                    {
                        "role": "user",
                        "content": "What is a SQL window function?",
                    },
                ],
                on_chunk=stream_text,
            ),
        )
        print("\n", flush=True)
        if not answer.strip():
            raise RuntimeError("Gemini returned an empty text answer.")

        print("PASS: API check, embeddings and text generation all succeeded.", flush=True)
        return 0
    except Exception as exc:
        logging.exception("Gemini diagnostic failed")
        print(f"\nFAIL: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
        return 1
    finally:
        faulthandler.cancel_dump_traceback_later()


if __name__ == "__main__":
    raise SystemExit(main())
