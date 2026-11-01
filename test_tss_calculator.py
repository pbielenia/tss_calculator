import os
import tempfile
import unittest

from tss_calculator import TextParser, get_parser


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

    def test_factory_returns_parser_with_common_interface(self):
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as handle:
            handle.write("2m S2\n")
            filename = handle.name

        try:
            parser = get_parser(filename, ftp=200)
            duration, power_readings = parser.parse()

            self.assertEqual(duration, 120)
            self.assertEqual(len(power_readings), 120)
            self.assertEqual(power_readings[0], 122)
            self.assertEqual(parser._find_power_at_power_zone("S2"), 122)
        finally:
            os.unlink(filename)

    def test_text_parser_handles_ramp_lines(self):
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as handle:
            handle.write("10m ramp S1-S3\n")
            filename = handle.name

        try:
            parser = get_parser(filename, ftp=100)
            duration, power_readings = parser.parse()

            self.assertEqual(duration, 600)
            self.assertEqual(len(power_readings), 600)
            self.assertEqual(power_readings[:120], [50] * 120)
            self.assertEqual(power_readings[120:240], [60] * 120)
            self.assertEqual(power_readings[240:360], [70] * 120)
            self.assertEqual(power_readings[360:480], [80] * 120)
            self.assertEqual(power_readings[480:], [90] * 120)
        finally:
            os.unlink(filename)


if __name__ == "__main__":
    unittest.main()
