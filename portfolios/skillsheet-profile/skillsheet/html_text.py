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
        self.cell_depth = 0  # 現在の表で開いている td・th の数
        self.saved: list[tuple[int, int]] = []  # 入れ子の表に入る前の (cell_count, cell_depth)

    def _flatten(self) -> bool:
        """外側の表のセルの中か（入れ子の表・改行を空白にして、外側のセルの区切りを保つ）。"""
        return self.cell_depth > 0 or any(depth for _, depth in self.saved)

    def handle_starttag(self, tag, attrs):
        if tag in _SKIP:
            self.skip_depth += 1
        elif tag == "table":
            self.parts.append(" " if self._flatten() else "\n")
            self.saved.append((self.cell_count, self.cell_depth))
            self.cell_count = self.cell_depth = 0
        elif tag in _CELL:
            nested = any(depth for _, depth in self.saved)
            if self.cell_count:
                self.parts.append(" " if nested else "\t")
            self.cell_count += 1
            self.cell_depth += 1
        elif tag in _BLOCK:
            self._block()

    def handle_startendtag(self, tag, attrs):
        if tag in _BLOCK and tag != "table":
            self._block()

    def handle_endtag(self, tag):
        if tag in _SKIP:
            self.skip_depth = max(0, self.skip_depth - 1)
        elif tag == "table":
            if self.saved:
                self.cell_count, self.cell_depth = self.saved.pop()
            else:
                self.cell_count = self.cell_depth = 0
            self.parts.append(" " if self._flatten() else "\n")
        elif tag in _CELL:
            self.cell_depth = max(0, self.cell_depth - 1)
        elif tag in _BLOCK:
            self._block()

    def handle_data(self, data):
        if not self.skip_depth:
            # ソースのインデントのタブも空白にする（タブはセルの区切りにだけ使う）
            self.parts.append(re.sub(r"[ \t\r\n\f\v]+", " ", data))

    def _block(self):
        # セルの中の改行（br・p・入れ子の表の行など）は空白にして、セルの区切り（タブ）を保つ
        if self._flatten():
            self.parts.append(" ")
            return
        self.parts.append("\n")
        self.cell_count = 0


def html_to_text(html: str) -> str:
    parser = _TextParser()
    parser.feed(html)
    parser.close()
    lines = []
    for line in "".join(parser.parts).split("\n"):
        # セル内の前後の空白を詰め、行頭・行末の空白を除く
        line = "\t".join(re.sub(" {2,}", " ", cell.strip()) for cell in line.split("\t")).strip(" ")
        if line.strip():
            lines.append(line)
    return "\n".join(lines)
