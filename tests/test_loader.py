import os
import tempfile
import unittest
from pathlib import Path

from app.rag import loader


class LoaderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, name, content, mode="w"):
        p = self.dir / name
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, mode, **({} if "b" in mode else {"encoding": "utf-8"})) as f:
            f.write(content)
        return p

    def test_txt_and_md(self):
        self.assertEqual(loader.read_file_text(self.write("a.txt", "  hello  ")), "hello")
        self.assertEqual(loader.read_file_text(self.write("b.md", "# Title\nbody")), "# Title\nbody")

    def test_csv_rows_become_readable_lines(self):
        p = self.write("t.csv", "Ticker,P/E,Note\nAAA,12.5,cheap\nBBB,30,\n")
        text = loader.read_file_text(p)
        self.assertIn("Ticker: AAA; P/E: 12.5; Note: cheap", text)
        self.assertIn("Ticker: BBB; P/E: 30", text)
        self.assertNotIn("Note: ;", text)

    def test_pdf_text_extraction(self):
        from reportlab.pdfgen import canvas
        p = self.dir / "r.pdf"
        c = canvas.Canvas(str(p))
        c.drawString(72, 750, "Quarterly revenue grew twelve percent")
        c.save()
        self.assertIn("revenue grew twelve percent", loader.read_file_text(p))

    def test_unsupported_and_empty_files(self):
        self.assertEqual(loader.read_file_text(self.write("x.docx", "data")), "")
        self.assertEqual(loader.read_file_text(self.write("empty.txt", "")), "")

    def test_list_source_files_filters_sorts_and_recurses(self):
        self.write("b.txt", "1"); self.write("a.csv", "x\n1"); self.write("c.exe", "z")
        self.write("sub/d.md", "4")
        names = [p.relative_to(self.dir).as_posix() for p in loader.list_source_files(self.dir)]
        self.assertEqual(names, ["a.csv", "b.txt", "sub/d.md"])

    def test_missing_folder_is_empty_not_an_error(self):
        self.assertEqual(loader.list_source_files(self.dir / "nope"), [])


if __name__ == "__main__":
    unittest.main()
