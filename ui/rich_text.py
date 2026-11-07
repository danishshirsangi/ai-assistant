import html
import re


def format_response_html(text):
    """Convert a safe Markdown subset into readable Qt rich text, preserving code."""
    lines = (text or "").strip().splitlines()
    if not lines:
        return ""

    out = []
    paragraph = []
    list_kind = None
    code_lines = []
    code_language = ""

    def inline(value):
        value = html.escape(value, quote=True)
        value = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", value)
        value = re.sub(r"__(.+?)__", r"<u>\1</u>", value)
        value = re.sub(r"==(.+?)==", r"<u><b>\1</b></u>", value)
        value = re.sub(r"`([^`]+)`", r"<span style='font-family:monospace'>\1</span>", value)
        return value

    def flush_paragraph():
        if paragraph:
            out.append("<p style='margin:6px 0 10px 0'>"
                       + "<br>".join(inline(x) for x in paragraph) + "</p>")
            paragraph.clear()

    def close_list():
        nonlocal list_kind
        if list_kind:
            out.append("</ul>" if list_kind == "ul" else "</ol>")
            list_kind = None

    def flush_code():
        nonlocal code_lines, code_language
        language = html.escape(code_language or "code")
        source = html.escape("\n".join(code_lines), quote=False)
        out.append(
            "<p style='margin:8px 0 3px 0'><b>" + language + "</b></p>"
            "<pre style='white-space:pre-wrap; background-color:#202630; "
            "color:#e6edf3; padding:10px; border-radius:6px; "
            "font-family:Menlo,monospace; font-size:12px;'>" + source + "</pre>"
        )
        code_lines = []
        code_language = ""

    in_code = False
    for raw in lines:
        fence = re.match(r"^\s*```\s*([\w+#.-]*)\s*$", raw)
        if fence:
            if not in_code:
                flush_paragraph()
                close_list()
                in_code = True
                code_language = fence.group(1)
            else:
                flush_code()
                in_code = False
            continue

        if in_code:
            code_lines.append(raw)
            continue

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
            out.append("<li style='margin:3px 0'>" + inline(item) + "</li>")
            continue

        heading = re.match(r"^#{1,3}\s+(.+)$", line)
        if heading:
            flush_paragraph()
            close_list()
            out.append("<p style='margin:12px 0 5px 0'><b>" + inline(heading.group(1)) + "</b></p>")
            continue

        close_list()
        paragraph.append(line)

    if in_code:
        flush_code()
    flush_paragraph()
    close_list()
    return "<div>" + "".join(out) + "</div>"
