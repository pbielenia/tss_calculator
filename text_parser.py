import logging
import re

from json_parser import JsonParser


class TextParser(JsonParser):
    def __init__(self, ftp, filepath=None):
        super().__init__(ftp, filepath)

    def parse_file(self, filepath):
        with open(filepath, encoding="utf-8") as text_file:
            for line in text_file:
                trimmed_line = self._normalize_line(line)
                if trimmed_line is None:
                    continue
                self._parse_line(trimmed_line)

    def _normalize_line(self, line):
        line_without_comment = line.split("#", 1)[0].strip()
        if not line_without_comment:
            return None
        return line_without_comment

    def _parse_line(self, line):
        steady_pattern = re.compile(
            r"^(?P<duration>\d+(?:\.\d+)?)\s*(?P<unit>[sm])\s+(?P<power_zone>S\d+|SST|S[1-5])\s*(?:(?P<repeats>\d+)x)?$",
            re.IGNORECASE
        )
        interval_pattern = re.compile(
            r"^(?P<work_duration>\d+(?:\.\d+)?)\s*(?P<work_unit>[sm])\s+(?P<work_power_zone>S\d+|SST|S[1-5])\s*/\s*(?P<rest_duration>\d+(?:\.\d+)?)\s*(?P<rest_unit>[sm])\s+(?P<rest_power_zone>S\d+|SST|S[1-5])\s*(?:(?P<repeats>\d+)x)?$",
            re.IGNORECASE
        )

        steady_match = steady_pattern.match(line)
        if steady_match:
            duration = float(steady_match.group("duration"))
            unit = steady_match.group("unit").lower()
            power_zone = steady_match.group("power_zone").upper()
            repeats = int(steady_match.group("repeats") or 1)
            for _ in range(repeats):
                self._parse_workout_block_steady(
                    self._convert_duration_to_minutes(duration, unit),
                    power_zone
                )
            return

        interval_match = interval_pattern.match(line)
        if interval_match:
            work_duration = float(interval_match.group("work_duration"))
            work_unit = interval_match.group("work_unit").lower()
            work_power_zone = interval_match.group("work_power_zone").upper()
            rest_duration = float(interval_match.group("rest_duration"))
            rest_unit = interval_match.group("rest_unit").lower()
            rest_power_zone = interval_match.group("rest_power_zone").upper()
            repeats = int(interval_match.group("repeats") or 1)

            for _ in range(repeats):
                self._parse_workout_block_steady(
                    self._convert_duration_to_minutes(work_duration, work_unit),
                    work_power_zone
                )
                self._parse_workout_block_steady(
                    self._convert_duration_to_minutes(rest_duration, rest_unit),
                    rest_power_zone
                )
            return

        logging.error("Could not parse text workout line: '{}'".format(line))

    def _convert_duration_to_minutes(self, duration_value, unit):
        if unit == 's':
            return duration_value / 60
        if unit == 'm':
            return duration_value
        raise ValueError("Unsupported time unit '{}'".format(unit))
