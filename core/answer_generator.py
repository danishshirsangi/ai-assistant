from core.prompts import build_messages

class AnswerGenerator:
    def __init__(self, ollama, rag):
        self.ollama = ollama
        self.rag = rag

    def answer(self, question, history):
        chunks = self.rag.retrieve(question)
        messages = build_messages(question, chunks, history)
        return self.ollama.chat(messages)
