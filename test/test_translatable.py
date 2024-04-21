import unittest
import sys

sys.path.append(".")
from app.main.translatable import Document
from app.main.translatable import TAG, WHITESPACE, WORD

class TestTranslatable(unittest.TestCase):
    test_sent = 'This text\t\t\tis   <g id="1">a <g id="2">sample</g> text</g>'
    segs = [
        ("This", WORD),
        (" ", WHITESPACE),
        ("text", WORD),
        ("\t\t\t", WHITESPACE),
        ("is", WORD),
        ("   ", WHITESPACE),
        ('<g id="1">', TAG),
        ("a", WORD),
        (" ", WHITESPACE),
        ('<g id="2">', TAG),
        ("sample", WORD),
        ("</g>", TAG),
        (" ", WHITESPACE),
        ("text", WORD),
        ("</g>", TAG),
    ]
    segs_no_wspaces = [
        ("This", WORD),
        ("text", WORD),
        ('<x equiv-text="\t\t\t"/>', TAG),
        ("is", WORD),
        ('<x equiv-text="   "/>', TAG),
        ('<g id="1">', TAG),
        ("a", WORD),
        ('<x equiv-text=" "/>', TAG),
        ('<g id="2">', TAG),
        ("sample", WORD),
        ("</g>", TAG),
        ('<x equiv-text=" "/>', TAG),
        ("text", WORD),
        ("</g>", TAG),
    ]

    def setUp(self):
        self.document = Document("test/test_data/test.docx")

    def test_tags_words_whitespaces(self):
        f = self.document.tags_words_whitespaces

        self.assertEqual(
            f(("Hello \tWorld!")),
            [("Hello", WORD), (" \t", WHITESPACE), ("World!", WORD)],
        )

        self.assertEqual(f(self.test_sent), self.segs)

    def test_whitespaces_to_tags(self):
        segs_no_wspaces = self.document.whitespaces_to_tags(self.segs)
        self.assertEqual(segs_no_wspaces, self.segs_no_wspaces)

    def test_remove_tags(self):
        pass


if __name__ == "__main__":
    unittest.main()
