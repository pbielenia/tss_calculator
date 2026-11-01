import os
import tempfile
import unittest

from tss_calculator import TextParser


class TextParserTests(unittest.TestCase):
    def test_text_parser_handles_steady_and_interval_lines(self):
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as handle:
            handle.write("2m S2 # steady\n")
            handle.write("2m S3\n")
            handle.write("30s S3 / 15s S1 4x # interval\n")
            filename = handle.name

        try:
            parser = TextParser(ftp=200)
            parser.parse_file(filename)

            self.assertEqual(parser.get_total_duration(), 420)
            self.assertEqual(len(parser.get_power_readings()), 420)
            self.assertEqual(parser.get_power_readings()[0], 122)
            self.assertEqual(parser.get_power_readings()[120], 176)
            self.assertEqual(parser.get_power_readings()[240], 176)
            self.assertEqual(parser.get_power_readings()[270], 100)
        finally:
            os.unlink(filename)


if __name__ == "__main__":
    unittest.main()
