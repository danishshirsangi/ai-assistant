import html
import re


GREEK = {
    r"\\mu": "μ", r"\\sigma": "σ", r"\\bar{x}": "x̄",
    r"\\alpha": "α", r"\\beta": "β", r"\\theta": "θ",
    r"\\pi": "π", r"\\Delta": "Δ", r"\\sqrt": "√",
    r"\\times": "×", r"\\cdot": "·", r"\\pm": "±",
    r"\\leq": "≤", r"\\geq": "≥", r"\\neq": "≠",
    r"\\infty": "∞", r"\\approx": "≈",
}


def _read_group(source, start):
    """Read a balanced {...} group; return (contents, next_index)."""
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
    """Render the common LaTeX subset used in interview/statistics answers."""
    out = []
    i = 0
    while i < len(source):
        if source.startswith(r"\\frac", i):
            numerator, after_num = _read_group(source, i + 5)
            denominator, after_den = _read_group(source, after_num)
            if after_num > i + 5 and after_den > after_num:
                out.append(
                    "<span style='display:inline-block; vertical-align:middle; "
                    "text-align:center; margin:0 3px;'>"
                    "<span style='display:block; border-bottom:1px solid #8fb8f5; "
                    "padding:0 4px 2px 4px;'>" + _math_fragment(numerator) + "</span>"
                    "<span style='display:block; padding:2px 4px 0 4px;'>"
                    + _math_fragment(denominator) + "</span></span>"
                )
                i = after_den
                continue
        if source.startswith(r"\\sqrt", i):
            radicand, end = _read_group(source, i + 5)
            if end > i + 5:
                out.append("√<span style='text-decoration:overline;'>" +
                           _math_fragment(radicand) + "</span>")
                i = end
                continue
        if source.startswith(r"\\bar", i):
            value, end = _read_group(source, i + 4)
            if end > i + 4:
                out.append(_math_fragment(value) + "̄")
                i = end
                continue
        matched = False
        for command, symbol in GREEK.items():
            if source.startswith(command, i):
                out.append(symbol)
                i += len(command)
                matched = True
                break
        if matched:
            continue
        if source[i] == "^" or source[i] == "_":
            marker = source[i]
            if i + 1 < len(source) and source[i + 1] == "{":
                value, end = _read_group(source, i + 1)
                rendered = _math_fragment(value)
                i = end
            elif i + 1 < len(source):
                rendered = html.escape(source[i + 1])
                i += 2
            else:
                out.append(marker)
                i += 1
                continue
            tag = "sup" if marker == "^" else "sub"
            out.append(f"<{tag}>{rendered}</{tag}>")
            continue
        char = source[i]
        out.append(html.escape(char))
        i += 1
    return "".join(out)


def _inline(value):
    # Protect math spans before escaping/formatting ordinary Markdown.
    pieces = re.split(r"(\\$\\$.*?\\$\\$|\\$.*?\\$)", value)
    rendered = []
    for piece in pieces:
        if piece.startswith("$$") and piece.endswith("$$"):
            formula = _math_fragment(piece[2:-2].strip())
            rendered.append(
                "<span style='display:inline-block; background:#202f49; "
                "border:1px solid #45658f; border-radius:6px; padding:5px 9px; "
                "color:#eaf2ff; font-size:15px;'>" + formula + "</span>"
            )
        elif piece.startswith("$") and piece.endswith("$"):
            rendered.append(
                "<span style='background:#202f49; color:#eaf2ff; "
                "padding:1px 4px; border-radius:3px;'>" +
                _math_fragment(piece[1:-1]) + "</span>"
            )
        else:
            escaped = html.escape(piece, quote=True)
            escaped = re.sub(r"\\*\\*(.+?)\\*\\*", r"<b>\\1</b>", escaped)
            escaped = re.sub(r"__(.+?)__", r"<u>\\1</u>", escaped)
            escaped = re.sub(r"==(.+?)==", r"<u><b>\\1</b></u>", escaped)
            escaped = re.sub(r"`([^`]+)`", r"<span style='font-family:monospace; "
                             r"background:#263449; padding:1px 3px;'>\\1</span>", escaped)
            rendered.append(escaped)
    return "".join(rendered)


def format_response_html(text):
    """Convert a safe Markdown subset and common LaTeX into readable Qt rich text."""
    lines = (text or "").strip().splitlines()
    if not lines:
        return ""

    out = []
    paragraph = []
    list_kind = None
    code_lines = []
    code_language = ""
    in_code = False

    def flush_paragraph():
        if paragraph:
            out.append("<p style='margin:7px 0 10px 0; line-height:1.45;'>"
                       + "<br>".join(_inline(x) for x in paragraph) + "</p>")
            paragraph.clear()

    def close_list():
        nonlocal list_kind
        if list_kind:
            out.append("</ul>" if list_kind == "ul" else "</ol>")
            list_kind = None

    def flush_code():
        nonlocal code_lines, code_language
        language = html.escape(code_language or "code")
        source = html.escape("\\n".join(code_lines), quote=False)
        out.append(
            "<p style='margin:8px 0 3px 0; color:#9fc5ff;'><b>" + language + "</b></p>"
            "<pre style='white-space:pre-wrap; background-color:#172235; "
            "color:#e6edf3; padding:10px; border:1px solid #354b6b; border-radius:7px; "
            "font-family:Menlo,monospace; font-size:12px;'>" + source + "</pre>"
        )
        code_lines = []
        code_language = ""

    for raw in lines:
        fence = re.match(r"^\\s*```\\s*([\\w+#.-]*)\\s*$", raw)
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

        bullet = re.match(r"^(?:[-*•])\\s+(.+)$", line)
        numbered = re.match(r"^\\d+[.)]\\s+(.+)$", line)
        if bullet or numbered:
            flush_paragraph()
            kind = "ul" if bullet else "ol"
            if list_kind != kind:
                close_list()
                out.append("<ul style='margin:5px 0 12px 22px; padding:0;'>"
                           if kind == "ul" else
                           "<ol style='margin:5px 0 12px 22px; padding:0;'>")
                list_kind = kind
            item = (bullet or numbered).group(1)
            out.append("<li style='margin:5px 0; line-height:1.4;'>" +
                       _inline(item) + "</li>")
            continue

        heading = re.match(r"^#{1,3}\\s+(.+)$", line)
        if heading:
            flush_paragraph()
            close_list()
            out.append("<p style='margin:13px 0 6px 0; color:#a9ccff; "
                       "font-size:15px;'><b>" + _inline(heading.group(1)) + "</b></p>")
            continue

        close_list()
        paragraph.append(line)

    if in_code:
        flush_code()
    flush_paragraph()
    close_list()
    return "<div>" + "".join(out) + "</div>"
