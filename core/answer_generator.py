from core.prompts import build_messages


class AnswerGenerator:
    def __init__(self, llm_client, rag):
        self.llm_client = llm_client
        self.rag = rag

    def answer(self, question, history, on_chunk=None):
        chunks = self.rag.retrieve(question)
        return self.llm_client.chat(
            build_messages(question, chunks, history),
            on_chunk=on_chunk,
        )

    def answer_from_transcript(self, transcript, history, on_chunk=None):
        # One generation pass: do not spend a second LLM call cleaning Whisper text.
        instruction = (
            "You are assisting during a live interview or work meeting. Identify "
            "the latest question or request from the other participants. Treat "
            "[YOU / MICROPHONE] as the user's own speech, not the interviewer's "
            "question. Resolve follow-ups using recent conversation. Ignore filler "
            "and obvious speech-recognition errors, but preserve technical terms, "
            "numbers and negations. If there is no clear question, respond usefully "
            "to the latest statement. Give a direct, natural answer that can be "
            "spoken aloud; avoid a long preamble.\n\nLive transcript:\n" + transcript
        )
        chunks = self.rag.retrieve(transcript)
        answer = self.llm_client.chat(
            build_messages(instruction, chunks, history),
            temperature=0.25,
            on_chunk=on_chunk,
        )
        return transcript, answer
