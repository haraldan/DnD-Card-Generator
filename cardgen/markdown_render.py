"""A tiny Markdown subset used for card descriptions.

Supported:
  - blank-line separated paragraphs
  - a line of three or more dashes (``---``) is a horizontal rule
  - inline ``***bold italic***``, ``**bold**``, ``*italic*``
  - inline links ``[text](url)``

Everything else is treated as literal text. Output is ReportLab's mini-XML
(``<b>``/``<i>``/``<u>``/``<a href>``), suitable for a Paragraph.

Blocks are returned as tuples: ``("text", xml)``, ``("divider",)`` or
``("space",)``. Each blank line yields one ``("space",)`` so the caller can turn
it into a consistent vertical gap regardless of what surrounds it.
"""
import re

_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_BOLD_ITALIC = re.compile(r"\*\*\*(.+?)\*\*\*", re.S)
_BOLD = re.compile(r"\*\*(.+?)\*\*", re.S)
_ITALIC = re.compile(r"\*(.+?)\*", re.S)
_HR = re.compile(r"^-{3,}$")


def _inline(text: str) -> str:
    # Escape XML specials first so user text can't inject markup.
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = _LINK.sub(r'<a href="\2"><u>\1</u></a>', text)
    text = _BOLD_ITALIC.sub(r"<b><i>\1</i></b>", text)
    text = _BOLD.sub(r"<b>\1</b>", text)
    text = _ITALIC.sub(r"<i>\1</i>", text)
    return text


def parse_markdown(md: str):
    """Parse a Markdown string into a list of (kind, ...) blocks."""
    blocks = []
    paragraph = []

    def flush():
        if paragraph:
            # A single newline within a block is a hard line break; a blank
            # line (which triggers a flush) starts a new paragraph.
            html = "<br/>".join(_inline(line.strip()) for line in paragraph)
            if html:
                blocks.append(("text", html))
            paragraph.clear()

    for raw in (md or "").replace("\r\n", "\n").split("\n"):
        line = raw.strip()
        if line == "":
            flush()
            blocks.append(("space",))
        elif _HR.match(line):
            flush()
            blocks.append(("divider",))
        else:
            paragraph.append(raw)
    flush()
    return blocks
