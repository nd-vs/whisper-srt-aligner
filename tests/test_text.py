import unittest

from whisper_srt_aligner.text import normalize_token, tokenize, visible_text


class TextTest(unittest.TestCase):
    def test_normalizes_apostrophes_and_known_aliases(self) -> None:
        self.assertEqual("dont", normalize_token("Don’t"))
        self.assertEqual("okay", normalize_token("OK"))
        self.assertEqual("because", normalize_token("'cause"))
        self.assertEqual("uh", normalize_token("Umm"))

    def test_tokenizes_visible_text_only(self) -> None:
        self.assertEqual(
            ["hello", "dont", "panic", "42"],
            tokenize("<i>Hello</i>, don't {\\an8}panic — 42!"),
        )
        self.assertEqual("Hello, world!", visible_text("<i>Hello, world!</i>"))


if __name__ == "__main__":
    unittest.main()
