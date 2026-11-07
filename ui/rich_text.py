import html
import re


def format_response_html(text):
    """Render a safe, readable subset of Markdown for Qt rich-text widgets."""
    lines = (text or "").strip().splitlines()
    if not lines:
        return ""

    def inline(value):
        value = html.escape(value, quote=True)
        value = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", value)
        value = re.sub(r"__(.+?)__", r"<u>\1</u>", value)
        value = re.sub(r"==(.+?)==", r"<u><b>\1</b></u>", value)
        value = re.sub(r"`([^`]+)`", r"<span style='font-family:monospace'>\1</span>", value)
        return value

    out, paragraph, list_kind = [], [], None

    def flush_paragraph():
        if paragraph:
            out.append("<p style='margin:6px 0 10px 0; line-height:1.4'>"
                       + "<br>".join(inline(x) for x in paragraph) + "</p>")
            paragraph.clear()

    def close_list():
        nonlocal list_kind
        if list_kind:
            out.append("</ul>" if list_kind == "ul" else "</ol>")
            list_kind = None

    for raw in lines:
        line = raw.strip()
        if not line:
            flush_paragraph()
            close_list()
            continue
        bullet = re.match(r"^(?:[-*•])\s+(.+)$", line)
        numbered = re.match(r"^\d+[.)]\s+(.+)$", line)
        if bullet or numbered:
            flush_paragraph()
            kind = "ul" if bullet else "ol"
            if list_kind != kind:
                close_list()
                out.append("<ul style='margin:4px 0 11px 22px; padding:0;'>"
                           if kind == "ul" else
                           "<ol style='margin:4px 0 11px 22px; padding:0;'>")
                list_kind = kind
            item = (bullet or numbered).group(1)
            out.append("<li style='margin:3px 0; line-height:1.35'>" + inline(item) + "</li>")
            continue
        heading = re.match(r"^#{1,3}\s+(.+)$", line)
        if heading:
            flush_paragraph()
            close_list()
            out.append("<p style='margin:12px 0 5px 0'><b>" + inline(heading.group(1)) + "</b></p>")
            continue
        close_list()
        paragraph.append(line)

    flush_paragraph()
    close_list()
    return "<div>" + "".join(out) + "</div>"
