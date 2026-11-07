from pathlib import Path
import fitz
from docx import Document

def load_document(path):
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        doc = fitz.open(path)
        return "\n".join(page.get_text("text") for page in doc)
    if suffix == ".docx":
        doc = Document(path)
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    if suffix in {".txt", ".md"}:
        return path.read_text(encoding="utf-8", errors="ignore")
    raise ValueError("Supported formats: PDF, DOCX, TXT, MD")

def chunk_text(text, chunk_size=1100, overlap=160):
    text = " ".join(text.split())
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = min(len(text), start + chunk_size)
        # Prefer ending on a sentence/space boundary.
        if end < len(text):
            boundary = max(text.rfind(". ", start, end), text.rfind("; ", start, end))
            if boundary > start + chunk_size * 0.55:
                end = boundary + 1
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = max(start + 1, end - overlap)
    return chunks
