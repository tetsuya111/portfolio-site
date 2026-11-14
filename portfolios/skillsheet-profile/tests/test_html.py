import unittest

from skillsheet import readers
from skillsheet.html_text import html_to_text


class HtmlTest(unittest.TestCase):
    def test_table_rows_tab_separated(self):
        html = "<table><tr><th>年</th><td>2020</td></tr><tr><td>言語</td><td>Python</td></tr></table>"
        self.assertIn("年\t2020\n言語\tPython", html_to_text(html))

    def test_skips_script_style(self):
        html = "<head><style>.a{}</style><script>x=1</script></head><body><noscript>n</noscript><p>本文</p></body>"
        self.assertEqual(html_to_text(html), "本文")

    def test_blocks_newlines(self):
        text = html_to_text("<p>a</p>\n\n\n<p>b</p><br>c<div>  d  </div>")
        self.assertEqual(text, "a\nb\nc\nd")

    def test_inline_does_not_split(self):
        self.assertEqual(html_to_text("<p>Type<b>Script</b> と <a href='x'>React</a></p>"), "TypeScript と React")

    def test_entities(self):
        self.assertEqual(html_to_text("<p>A &amp; B &lt;C&gt;</p>"), "A & B <C>")

    def test_read_bytes_html(self):
        self.assertEqual(readers.read_bytes("<li>Python</li><li>Go</li>".encode("cp932"), ".htm"), "Python\nGo")


if __name__ == "__main__":
    unittest.main()
