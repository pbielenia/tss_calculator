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
            r"^(?P<duration>[^\s]+)\s+(?P<power_zone>S\d+|SST|S[1-5])\s*(?:(?P<repeats>\d+)x)?$",
            re.IGNORECASE
        )
        interval_pattern = re.compile(
            r"^(?P<work_duration>[^\s]+)\s+(?P<work_power_zone>S\d+|SST|S[1-5])\s*/\s*(?P<rest_duration>[^\s]+)\s+(?P<rest_power_zone>S\d+|SST|S[1-5])\s*(?:(?P<repeats>\d+)x)?$",
            re.IGNORECASE
        )
        ramp_pattern = re.compile(
            r"^(?P<duration>[^\s]+)\s+ramp\s+(?P<start_zone>S\d+|SST|S[1-5])\s*-\s*(?P<end_zone>S\d+|SST|S[1-5])\s*(?:(?P<repeats>\d+)x)?$",
            re.IGNORECASE
        )

        steady_match = steady_pattern.match(line)
        if steady_match:
            duration_literal = steady_match.group("duration")
            power_zone = steady_match.group("power_zone").upper()
            repeats = int(steady_match.group("repeats") or 1)
            parsed_duration = self._convert_duration_literal_to_minutes(duration_literal)
            for _ in range(repeats):
                self._parse_workout_block_steady(parsed_duration, power_zone)
            return

        interval_match = interval_pattern.match(line)
        if interval_match:
            work_duration_literal = interval_match.group("work_duration")
            work_power_zone = interval_match.group("work_power_zone").upper()
            rest_duration_literal = interval_match.group("rest_duration")
            rest_power_zone = interval_match.group("rest_power_zone").upper()
            repeats = int(interval_match.group("repeats") or 1)

            for _ in range(repeats):
                self._parse_workout_block_steady(
                    self._convert_duration_literal_to_minutes(work_duration_literal),
                    work_power_zone
                )
                self._parse_workout_block_steady(
                    self._convert_duration_literal_to_minutes(rest_duration_literal),
                    rest_power_zone
                )
            return

        ramp_match = ramp_pattern.match(line)
        if ramp_match:
            duration_literal = ramp_match.group("duration")
            start_zone = ramp_match.group("start_zone").upper()
            end_zone = ramp_match.group("end_zone").upper()
            repeats = int(ramp_match.group("repeats") or 1)
            parsed_duration = self._convert_duration_literal_to_minutes(duration_literal)
            for _ in range(repeats):
                self._parse_ramp_segment(parsed_duration, start_zone, end_zone)
            return

        logging.error("Could not parse text workout line: '{}'".format(line))

    def _parse_ramp_segment(self, duration_in_minutes, start_zone, end_zone):
        start_power = self._find_power_at_power_zone(start_zone)
        end_power = self._find_power_at_power_zone(end_zone)

        if start_power == 0 or end_power == 0:
            logging.error("Could not parse ramp '{}' -> '{}'".format(start_zone, end_zone))
            return

        rounded_start_power = int(round(start_power / 10) * 10)
        rounded_end_power = int(round(end_power / 10) * 10)
        if rounded_end_power < rounded_start_power:
            step_count = max(1, int(round((rounded_start_power - rounded_end_power) / 10)) + 1)
            power_values = [rounded_start_power - index * 10 for index in range(step_count)]
        else:
            step_count = max(1, int(round((rounded_end_power - rounded_start_power) / 10)) + 1)
            power_values = [rounded_start_power + index * 10 for index in range(step_count)]

        step_duration_in_minutes = duration_in_minutes / step_count
        for power_value in power_values:
            self._append_steady_power(step_duration_in_minutes, power_value)

    def _append_steady_power(self, duration_in_minutes, power_value):
        duration_in_seconds = int(duration_in_minutes * 60)
        self._total_duration += duration_in_seconds
        self._power_readings.extend([power_value] * duration_in_seconds)

    def _convert_duration_literal_to_minutes(self, duration_literal):
        match = re.fullmatch(
            r"(?:(?P<minutes>\d+(?:\.\d+)?)m)?(?:(?P<seconds>\d+(?:\.\d+)?)s)?",
            duration_literal.strip(),
            re.IGNORECASE
        )
        if match is None:
            raise ValueError("Invalid duration literal '{}'".format(duration_literal))

        minutes = float(match.group("minutes") or 0)
        seconds = float(match.group("seconds") or 0)
        if seconds >= 60:
            raise ValueError("Seconds must be below 60 in duration literal '{}'".format(duration_literal))
        return minutes + (seconds / 60)

    def _convert_duration_to_minutes(self, duration_value, unit):
        if unit == 's':
            return duration_value / 60
        if unit == 'm':
            return duration_value
        raise ValueError("Unsupported time unit '{}'".format(unit))
