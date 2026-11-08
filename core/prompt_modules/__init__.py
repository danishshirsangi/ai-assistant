"""Prompt module selection and composition."""

from core.prompt_modules.classifier import classify_question
from core.prompt_modules.technical import TECHNICAL_PLAYBOOKS


def build_technical_guidance(question):
    selected = classify_question(question)
    if not selected:
        return ""

    sections = [TECHNICAL_PLAYBOOKS[name] for name in selected]
    return (
        "QUESTION-SPECIFIC TECHNICAL GUIDANCE\n"
        "Apply only the relevant guidance below. Keep the answer proportional to the question; "
        "do not force every checklist item into the response.\n\n"
        + "\n\n".join(sections)
    )
