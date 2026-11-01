import json
import logging

from base_parser import WorkoutParser


class JsonParser(WorkoutParser):
    KEY_INTERVAL_REPEATS = "repeats"
    KEY_INTERVAL_REST_DURATION = "restDuration"
    KEY_INTERVAL_REST_POWER_ZONE = "restPowerZone"
    KEY_INTERVAL_WORK_DURATION = "workDuration"
    KEY_INTERVAL_WORK_POWER_ZONE = "workPowerZone"

    def __init__(self, ftp, filepath=None):
        super().__init__(filepath)
        self._ftp = ftp

    def parse_file(self, filepath):
        with open(filepath) as json_file:
            json_content = json.load(json_file)
            for workout_block in json_content:
                if not JsonParser._validate_workout_block(workout_block):
                    continue
                self._parse_workout_block(workout_block)

    def _validate_workout_block(workout_block):
        if not JsonParser._validate_field("type", workout_block, lambda type: len(type) > 1):
            return False

        block_type = workout_block["type"]

        if block_type == "steady":
            return JsonParser._validate_block_type_steady(workout_block)
        elif block_type == "interval":
            return JsonParser._validate_block_type_interval(workout_block)

        logging.error("Workout block of type '{}' is not supported".format(block_type))
        return False

    def _validate_fields(workout_block, block_type: str, checks: dict):
        for field_name, check_callback in checks.items():
            if not JsonParser._validate_field(field_name, workout_block, check_callback, block_type):
                return False
        return True

    def _validate_field(name, workout_block, check_callback, block_type=None):
        if name not in workout_block:
            logging.error("Missing '{}' in a workout block{}".format(
                name, " of '{}' type".format(block_type) if block_type is not None else ""))
            return False
        if not check_callback(workout_block[name]):
            logging.error("'{}' of value '{}' is found invalid".format(name, workout_block[name]))
            return False
        return True

    def _validate_block_type_steady(workout_block):
        return JsonParser._validate_fields(
            workout_block,
            "steady",
            {
                "duration": WorkoutParser._duration_is_valid,
                "powerZone": WorkoutParser._power_zone_is_valid
            }
        )

    def _validate_block_type_interval(workout_block):
        return JsonParser._validate_fields(
            workout_block,
            "interval",
            {
                JsonParser.KEY_INTERVAL_REPEATS: lambda integer: integer > 0,
                JsonParser.KEY_INTERVAL_WORK_DURATION: WorkoutParser._duration_is_valid,
                JsonParser.KEY_INTERVAL_REST_DURATION: WorkoutParser._duration_is_valid,
                JsonParser.KEY_INTERVAL_WORK_POWER_ZONE: WorkoutParser._power_zone_is_valid,
                JsonParser.KEY_INTERVAL_REST_POWER_ZONE: WorkoutParser._power_zone_is_valid
            }
        )

    def _parse_workout_block(self, workout_block):
        block_type = workout_block["type"]
        if block_type == "steady":
            self._parse_workout_block_steady(workout_block["duration"], workout_block["powerZone"])
        elif block_type == "interval":
            self._parse_workout_block_interval(workout_block)
        else:
            logging.error(
                "Workout block of type '{}' is not supported".format(block_type))
            return

    def _parse_workout_block_steady(self, duration_in_minutes, power_zone):
        duration_in_seconds = JsonParser._convert_minutes_to_seconds(duration_in_minutes)
        self._total_duration += duration_in_seconds

        target_power = self._find_power_at_power_zone(power_zone)
        power_readings = self._generate_power_readings_steady(duration_in_seconds, target_power)
        self._power_readings += power_readings

    def _parse_workout_block_interval(self, workout_block):
        repeats = workout_block[JsonParser.KEY_INTERVAL_REPEATS]
        work_duration_in_minutes = workout_block[JsonParser.KEY_INTERVAL_WORK_DURATION]
        work_power_zone = workout_block[JsonParser.KEY_INTERVAL_WORK_POWER_ZONE]
        rest_duration_in_minutes = workout_block[JsonParser.KEY_INTERVAL_REST_DURATION]
        rest_power_zone = workout_block[JsonParser.KEY_INTERVAL_REST_POWER_ZONE]

        for _ in range(repeats):
            self._parse_workout_block_steady(work_duration_in_minutes, work_power_zone)
            self._parse_workout_block_steady(rest_duration_in_minutes, rest_power_zone)

    def _convert_minutes_to_seconds(minutes):
        return int(minutes * 60)

    def _generate_power_readings_steady(self, duration_in_seconds, power):
        return [power] * duration_in_seconds
