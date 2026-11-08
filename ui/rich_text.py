import html
import re
from urllib.parse import urlsplit


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
            numerator, middle = _read_group(source, i + 5)
            denominator, end = _read_group(source, middle)
            if middle > i + 5 and end > middle:
                out.append(
                    "<span style='display:inline-block;vertical-align:middle;"
                    "text-align:center;margin:0 3px;'>"
                    "<span style='display:block;border-bottom:1px solid #8fb8f5;"
                    "padding:0 4px 2px;'>"
                    + _math_fragment(numerator)
                    + "</span><span style='display:block;padding:2px 4px 0;'>"
                    + _math_fragment(denominator)
                    + "</span></span>"
                )
                i = end
                continue
        if source.startswith(r"\sqrt", i):
            value, end = _read_group(source, i + 5)
            if end > i + 5:
                out.append(
                    "√<span style='text-decoration:overline;'>"
                    + _math_fragment(value) + "</span>"
                )
                i = end
                continue
        if source.startswith(r"\bar", i):
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

        if source[i] in "^_":
            marker = source[i]
            if i + 1 < len(source) and source[i + 1] == "{":
                value, end = _read_group(source, i + 1)
                rendered, i = _math_fragment(value), end
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


def _safe_link(match, placeholders):
    label, url = match.group(1), match.group(2).strip()
    try:
        scheme = urlsplit(url).scheme.lower()
    except ValueError:
        scheme = ""
    if scheme not in {"https", "http", "mailto"}:
        return match.group(0)
    key = f"\\uFFF0LINK{len(placeholders)}\\uFFF1"
    safe_url = html.escape(url, quote=True)
    safe_label = html.escape(label)
    placeholders[key] = (
        f"<a href='{safe_url}' style='color:#91c5ff;text-decoration:underline;'>"
        f"{safe_label}</a>"
    )
    return key


def _inline_plain(source):
    placeholders = {}

    # Protect inline code and links before applying emphasis rules.
    def protect_code(match):
        key = f"\\uFFF0CODE{len(placeholders)}\\uFFF1"
        code = html.escape(match.group(1), quote=False)
        placeholders[key] = (
            "<code style='font-family:Menlo,monospace;background:#26364d;"
            "color:#e9f1ff;padding:2px 5px;border-radius:4px;'>"
            + code + "</code>"
        )
        return key

    source = re.sub(r"`([^`]+)`", protect_code, source)
    source = re.sub(
        r"\[([^\]]+)\]\((https?://[^\s)]+|mailto:[^\s)]+)\)",
        lambda match: _safe_link(match, placeholders),
        source,
    )
    rendered = html.escape(source, quote=True)

    # Emphasis, interview highlights, underline and strike-through.
    rendered = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", rendered)
    rendered = re.sub(
        r"==(.+?)==",
        r"<span style='background:#71551c;color:#fff0bd;padding:1px 4px;"
        r"border-radius:3px;'><b>\1</b></span>",
        rendered,
    )
    rendered = re.sub(r"__(.+?)__", r"<u>\1</u>", rendered)
    rendered = re.sub(r"~~(.+?)~~", r"<s>\1</s>", rendered)
    rendered = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<i>\1</i>", rendered)

    for key, value in placeholders.items():
        rendered = rendered.replace(html.escape(key), value)
    return rendered


def _inline(value):
    # Split math expressions before escaping ordinary text.
    pieces = re.split(r"(\$\$.*?\$\$|\$.*?\$)", value)
    rendered = []
    for piece in pieces:
        if piece.startswith("$$") and piece.endswith("$$"):
            rendered.append(
                "<span style='display:inline-block;background:#202f49;border:1px solid "
                "#45658f;border-radius:6px;padding:5px 9px;color:#eaf2ff;font-size:15px;'>"
                + _math_fragment(piece[2:-2].strip()) + "</span>"
            )
        elif piece.startswith("$") and piece.endswith("$"):
            rendered.append(
                "<span style='background:#202f49;color:#eaf2ff;padding:1px 4px;"
                "border-radius:3px;'>"
                + _math_fragment(piece[1:-1]) + "</span>"
            )
        else:
            rendered.append(_inline_plain(piece))
    return "".join(rendered)


def _table_cells(line):
    value = line.strip()
    if value.startswith("|"):
        value = value[1:]
    if value.endswith("|"):
        value = value[:-1]
    return [cell.strip() for cell in value.split("|")]


def _is_table_separator(line):
    cells = _table_cells(line)
    return bool(cells) and all(
        re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) for cell in cells
    )


def format_response_html(text):
    """Render safe Markdown and common LaTeX into Qt-compatible rich text."""
    lines = (text or "").strip().splitlines()
    if not lines:
        return ""

    out, paragraph, code_lines = [], [], []
    list_kind, code_language, in_code = None, "", False

    def flush_paragraph():
        if paragraph:
            out.append(
                "<p style='margin:7px 0 11px;line-height:1.5;'>"
                + "<br>".join(_inline(line) for line in paragraph)
                + "</p>"
            )
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
            "<p style='margin:9px 0 4px;color:#9fc5ff;font-size:11px;'><b>"
            + language + "</b></p>"
            "<pre style='white-space:pre-wrap;background:#101a29;color:#e6edf3;"
            "padding:12px;border:1px solid #354b6b;border-radius:8px;"
            "font-family:Menlo,monospace;font-size:12px;'>"
            + source + "</pre>"
        )
        code_lines, code_language = [], ""

    def render_table(table_lines):
        rows = [_table_cells(line) for line in table_lines]
        if len(rows) < 2:
            return
        headers = rows[0]
        body = rows[2:] if _is_table_separator(table_lines[1]) else rows[1:]
        out.append(
            "<table width='100%' cellspacing='0' cellpadding='6' "
            "style='border-collapse:collapse;margin:8px 0 13px;'>"
        )
        out.append("<tr>")
        for cell in headers:
            out.append(
                "<th align='left' style='background:#20334d;color:#cfe1ff;"
                "border:1px solid #3b5578;'>"
                + _inline(cell) + "</th>"
            )
        out.append("</tr>")
        for row in body:
            out.append("<tr>")
            for index in range(len(headers)):
                cell = row[index] if index < len(row) else ""
                out.append(
                    "<td style='background:#142238;border:1px solid #304762;"
                    "color:#e8eef8;'>"
                    + _inline(cell) + "</td>"
                )
            out.append("</tr>")
        out.append("</table>")

    index = 0
    while index < len(lines):
        raw = lines[index]
        fence = re.match(r"^\\s*```\\s*([\\w+#.-]*)\\s*$", raw)
        if fence:
            if not in_code:
                flush_paragraph()
                close_list()
                in_code, code_language = True, fence.group(1)
            else:
                flush_code()
                in_code = False
            index += 1
            continue

        if in_code:
            code_lines.append(raw)
            index += 1
            continue

        line = raw.strip()
        if not line:
            flush_paragraph()
            close_list()
            index += 1
            continue

        # Markdown table: a header followed by a separator row.
        if "|" in line and index + 1 < len(lines) and _is_table_separator(lines[index + 1]):
            flush_paragraph()
            close_list()
            table_lines = [line, lines[index + 1]]
            index += 2
            while index < len(lines) and "|" in lines[index] and lines[index].strip():
                table_lines.append(lines[index].strip())
                index += 1
            render_table(table_lines)
            continue

        if re.fullmatch(r"(?:---+|\*\*\*|___+)", line):
            flush_paragraph()
            close_list()
            out.append("<hr style='border:0;border-top:1px solid #405875;margin:10px 0;'>")
            index += 1
            continue

        quote = re.match(r"^>\s?(.*)$", line)
        if quote:
            flush_paragraph()
            close_list()
            out.append(
                "<blockquote style='margin:7px 0 11px;padding:5px 12px;"
                "border-left:3px solid #6597d2;color:#b9cbe4;background:#142238;'>"
                + _inline(quote.group(1)) + "</blockquote>"
            )
            index += 1
            continue

        bullet = re.match(r"^(?:[-*•])\s+(.+)$", line)
        numbered = re.match(r"^\d+[.)]\s+(.+)$", line)
        if bullet or numbered:
            flush_paragraph()
            kind = "ul" if bullet else "ol"
            if list_kind != kind:
                close_list()
                if kind == "ul":
                    out.append("<ul style='margin:5px 0 13px 22px;padding:0;'>")
                else:
                    out.append("<ol style='margin:5px 0 13px 22px;padding:0;'>")
                list_kind = kind
            item = (bullet or numbered).group(1)
            out.append("<li style='margin:5px 0;line-height:1.45;'>"
                       + _inline(item) + "</li>")
            index += 1
            continue

        heading = re.match(r"^(#{1,4})\s+(.+)$", line)
        if heading:
            flush_paragraph()
            close_list()
            level = len(heading.group(1))
            size = {1: "20px", 2: "17px", 3: "15px", 4: "13px"}[level]
            out.append(
                f"<p style='margin:14px 0 7px;color:#b8d5ff;font-size:{size};'>"
                "<b>" + _inline(heading.group(2)) + "</b></p>"
            )
            index += 1
            continue

        close_list()
        paragraph.append(line)
        index += 1

    if in_code:
        flush_code()
    flush_paragraph()
    close_list()
    return "<div>" + "".join(out) + "</div>"
