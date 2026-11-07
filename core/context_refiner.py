class ContextRefiner:
    """Clean a transcript without discarding meaningful interview context."""

    def __init__(self, ollama):
        self.ollama = ollama

    def refine(self, transcript, history=None):
        system = (
            "Clean this interview transcript. Remove filler words, stutters, accidental "
            "repeated phrases and obvious speech-recognition fragments. Preserve technical "
            "terms, numbers, names, constraints, negations, examples, speaker labels and "
            "follow-up references. Do not summarize, answer the interviewer, or invent "
            "missing words. Mark uncertain phrases [unclear]. Preserve the labels "
            "[YOU / MICROPHONE] and [OTHER PARTICIPANTS / SYSTEM AUDIO]."
        )
        recent = ""
        if history:
            recent = "\nRecent context for resolving references only; do not add it to "
            "the transcript:\n" + "\n".join(
                f"{m.get('role', '')}: {m.get('content', '')}" for m in history[-4:]
            )
        return self.ollama.chat([
            {"role": "system", "content": system},
            {"role": "user", "content": recent + "\n\nTranscript:\n" + transcript},
        ], temperature=0.1).strip()
