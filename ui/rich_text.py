import html
import re

GREEK = {
    r"\mu": "μ", r"\sigma": "σ", r"\bar{x}": "x̄", r"\alpha": "α",
    r"\beta": "β", r"\theta": "θ", r"\pi": "π", r"\Delta": "Δ",
    r"\times": "×", r"\cdot": "·", r"\pm": "±", r"\leq": "≤",
    r"\geq": "≥", r"\neq": "≠", r"\infty": "∞", r"\approx": "≈",
}

def _read_group(source, start):
    if start >= len(source) or source[start] != "{":
        return "", start
    depth = 0
    for index in range(start, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start + 1:index], index + 1
    return source[start + 1:], len(source)

def _math_fragment(source):
    out, i = [], 0
    while i < len(source):
        if source.startswith(r"\frac", i):
            num, mid = _read_group(source, i + 5)
            den, end = _read_group(source, mid)
            if mid > i + 5 and end > mid:
                out.append("<span style='display:inline-block;vertical-align:middle;text-align:center;margin:0 3px;'>"
                           "<span style='display:block;border-bottom:1px solid #8fb8f5;padding:0 4px 2px;'>"
                           + _math_fragment(num) + "</span><span style='display:block;padding:2px 4px 0;'>"
                           + _math_fragment(den) + "</span></span>")
                i = end
                continue
        if source.startswith(r"\sqrt", i):
            val, end = _read_group(source, i + 5)
            if end > i + 5:
                out.append("√<span style='text-decoration:overline;'>" + _math_fragment(val) + "</span>")
                i = end
                continue
        if source.startswith(r"\bar", i):
            val, end = _read_group(source, i + 4)
            if end > i + 4:
                out.append(_math_fragment(val) + "̄")
                i = end
                continue
        found = False
        for command, symbol in GREEK.items():
            if source.startswith(command, i):
                out.append(symbol)
                i += len(command)
                found = True
                break
        if found:
            continue
        if source[i] in "^_":
            marker = source[i]
            if i + 1 < len(source) and source[i + 1] == "{":
                val, end = _read_group(source, i + 1)
                rendered, i = _math_fragment(val), end
            elif i + 1 < len(source):
                rendered, i = html.escape(source[i + 1]), i + 2
            else:
                out.append(marker)
                i += 1
                continue
            tag = "sup" if marker == "^" else "sub"
            out.append(f"<{tag}>{rendered}</{tag}>")
            continue
        out.append(html.escape(source[i]))
        i += 1
    return "".join(out)

def _inline(value):
    pieces = re.split(r"(\$\$.*?\$\$|\$.*?\$)", value)
    rendered = []
    for piece in pieces:
        if piece.startswith("$$") and piece.endswith("$$"):
            rendered.append("<span style='display:inline-block;background:#202f49;border:1px solid #45658f;"
                            "border-radius:6px;padding:5px 9px;color:#eaf2ff;font-size:15px;'>"
                            + _math_fragment(piece[2:-2].strip()) + "</span>")
        elif piece.startswith("$") and piece.endswith("$"):
            rendered.append("<span style='background:#202f49;color:#eaf2ff;padding:1px 4px;border-radius:3px;'>"
                            + _math_fragment(piece[1:-1]) + "</span>")
        else:
            escaped = html.escape(piece, quote=True)
            escaped = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", escaped)
            escaped = re.sub(r"__(.+?)__", r"<u>\1</u>", escaped)
            escaped = re.sub(r"==(.+?)==", r"<u><b>\1</b></u>", escaped)
            escaped = re.sub(r"\x60([^\x60]+)\x60",
                             r"<span style='font-family:monospace;background:#263449;padding:1px 3px;'>\1</span>",
                             escaped)
            rendered.append(escaped)
    return "".join(rendered)

def format_response_html(text):
    """Render safe Markdown and common LaTeX in Qt rich text."""
    lines = (text or "").strip().splitlines()
    if not lines:
        return ""
    out, paragraph, code_lines = [], [], []
    list_kind, code_language, in_code = None, "", False

    def flush_paragraph():
        if paragraph:
            out.append("<p style='margin:7px 0 10px;line-height:1.45;'>"
                       + "<br>".join(_inline(x) for x in paragraph) + "</p>")
            paragraph.clear()

    def close_list():
        nonlocal list_kind
        if list_kind:
            out.append("</ul>" if list_kind == "ul" else "</ol>")
            list_kind = None

    def flush_code():
        nonlocal code_lines, code_language
        lang = html.escape(code_language or "code")
        source = html.escape("\n".join(code_lines), quote=False)
        out.append("<p style='margin:8px 0 3px;color:#9fc5ff;'><b>" + lang + "</b></p>"
                   "<pre style='white-space:pre-wrap;background:#172235;color:#e6edf3;padding:10px;"
                   "border:1px solid #354b6b;border-radius:7px;font-family:Menlo,monospace;font-size:12px;'>"
                   + source + "</pre>")
        code_lines, code_language = [], ""

    for raw in lines:
        fence = re.match(r"^\s*\x60\x60\x60\s*([\w+#.-]*)\s*$", raw)
        if fence:
            if not in_code:
                flush_paragraph()
                close_list()
                in_code, code_language = True, fence.group(1)
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
                out.append("<ul style='margin:5px 0 12px 22px;padding:0;'>"
                           if kind == "ul" else "<ol style='margin:5px 0 12px 22px;padding:0;'>")
                list_kind = kind
            item = (bullet or numbered).group(1)
            out.append("<li style='margin:5px 0;line-height:1.4;'>" + _inline(item) + "</li>")
            continue
        heading = re.match(r"^#{1,3}\s+(.+)$", line)
        if heading:
            flush_paragraph()
            close_list()
            out.append("<p style='margin:13px 0 6px;color:#a9ccff;font-size:15px;'><b>"
                       + _inline(heading.group(1)) + "</b></p>")
            continue
        close_list()
        paragraph.append(line)
    if in_code:
        flush_code()
    flush_paragraph()
    close_list()
    return "<div>" + "".join(out) + "</div>"
