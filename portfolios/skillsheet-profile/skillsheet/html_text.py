"""HTML を本文のテキストにする（表はセルをタブ区切り・行ごとに改行）。"""

import re
from html.parser import HTMLParser

_SKIP = {"script", "style", "noscript", "template"}
_BLOCK = {
    "p", "div", "br", "li", "ul", "ol", "dl", "dt", "dd", "tr", "table", "section", "article",
    "header", "footer", "main", "aside", "nav", "h1", "h2", "h3", "h4", "h5", "h6", "pre",
    "blockquote", "hr", "title", "form", "fieldset", "caption", "thead", "tbody", "tfoot",
}
_CELL = {"td", "th"}


class _TextParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip_depth = 0
        self.cell_count = 0  # 現在の行で開いたセルの数

    def handle_starttag(self, tag, attrs):
        if tag in _SKIP:
            self.skip_depth += 1
        elif tag in _CELL:
            if self.cell_count:
                self.parts.append("\t")
            self.cell_count += 1
        elif tag in _BLOCK:
            self._newline()

    def handle_startendtag(self, tag, attrs):
        if tag in _BLOCK:
            self._newline()

    def handle_endtag(self, tag):
        if tag in _SKIP:
            self.skip_depth = max(0, self.skip_depth - 1)
        elif tag in _BLOCK:
            self._newline()

    def handle_data(self, data):
        if not self.skip_depth:
            self.parts.append(re.sub(r"[ \r\n\f\v]+", " ", data))

    def _newline(self):
        self.parts.append("\n")
        self.cell_count = 0


def html_to_text(html: str) -> str:
    parser = _TextParser()
    parser.feed(html)
    parser.close()
    lines = []
    for line in "".join(parser.parts).split("\n"):
        # セル内の前後の空白を詰め、行頭・行末の空白を除く
        line = "\t".join(cell.strip() for cell in line.split("\t")).strip(" ")
        if line.strip():
            lines.append(line)
    return "\n".join(lines)
