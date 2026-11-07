from core.prompts import build_messages
from core.context_refiner import ContextRefiner


class AnswerGenerator:
    def __init__(self, ollama, rag):
        self.ollama = ollama
        self.rag = rag
        self.refiner = ContextRefiner(ollama)

    def answer(self, question, history):
        chunks = self.rag.retrieve(question)
        return self.ollama.chat(build_messages(question, chunks, history))

    def answer_from_transcript(self, transcript, history):
        cleaned = self.refiner.refine(transcript, history)
        instruction = (
            "This is a live interview conversation. Identify the latest question "
            "from the interviewer / other participants and answer it. Use the "
            "microphone speech as the user's own contribution, not as a question "
            "from the interviewer. Resolve follow-ups using recent conversation. "
            "If no clear question is present, give a concise useful response to "
            "the latest interviewer statement.\n\nCleaned transcript:\n" + cleaned
        )
        chunks = self.rag.retrieve(instruction)
        answer = self.ollama.chat(build_messages(instruction, chunks, history))
        return cleaned, answer
