import argparse
import fitdecode
import logging
import os.path
import json

resources_directory = 'resources'
source_filename = '2023-11-16-20-20-52.fit'


class FitParser:
    def __init__(self):
        self._total_duration = 0
        self._power_readings = list()

    def get_total_duration(self):
        return self._total_duration

    def get_power_readings(self):
        return self._power_readings

    def parse_file(self, filepath):
        with fitdecode.FitReader(filepath) as fit:
            for frame in fit:
                self._parse_frame(frame)

    def _parse_frame(self, frame):
        if frame.frame_type != fitdecode.FIT_FRAME_DATA:
            return
        if frame.name == 'session':
            self._parse_frame_session(frame)
        if frame.name == 'record':
            self._parse_frame_record(frame)

    def _parse_frame_session(self, frame):
        if frame.has_field('total_elapsed_time'):
            self._total_duration += frame.get_value('total_elapsed_time')

    def _parse_frame_record(self, frame):
        if frame.has_field('power'):
            self._power_readings.append(frame.get_value('power'))


class JsonParser:
    KEY_INTERVAL_REPEATS = "repeats"
    KEY_INTERVAL_REST_DURATION = "restDuration"
    KEY_INTERVAL_REST_POWER_ZONE = "restPowerZone"
    KEY_INTERVAL_WORK_DURATION = "workDuration"
    KEY_INTERVAL_WORK_POWER_ZONE = "workPowerZone"

    def __init__(self, ftp):
        self._total_duration = 0
        self._power_readings = list()
        self._ftp = ftp

    def get_total_duration(self):
        return self._total_duration

    def get_power_readings(self):
        return self._power_readings

    def parse_file(self, filepath):
        with open(filepath) as json_file:
            json_content = json.load(json_file)
            for workout_block in json_content:
                print(workout_block)
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
                "duration": JsonParser._duration_is_valid,
                "powerZone": JsonParser._power_zone_is_valid
            }
        )

    def _validate_block_type_interval(workout_block):
        return JsonParser._validate_fields(
            workout_block,
            "interval",
            {
                JsonParser.KEY_INTERVAL_REPEATS: lambda integer: integer > 0,
                JsonParser.KEY_INTERVAL_WORK_DURATION: JsonParser._duration_is_valid,
                JsonParser.KEY_INTERVAL_REST_DURATION: JsonParser._duration_is_valid,
                JsonParser.KEY_INTERVAL_WORK_POWER_ZONE: JsonParser._power_zone_is_valid,
                JsonParser.KEY_INTERVAL_REST_POWER_ZONE: JsonParser._power_zone_is_valid
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

    def _duration_is_valid(duration_in_minutes):
        return duration_in_minutes > 0 and duration_in_minutes < 400

    def _power_zone_is_valid(power_zone):
        return power_zone in ("S1", "S2", "S3", "SST", "S4", "S5")

    def _find_power_at_power_zone(self, power_zone):
        power_zones_to_power = {
            "S1": 0.5,
            "S2": 0.61,
            "S3": 0.88,
            "SST": 0.91,
            "S4": 0.98,
            "S5": 1.13
        }

        if power_zone not in power_zones_to_power:
            logging.error("Power zone factor not found: {}".format(power_zone))
            return 0
        return power_zones_to_power[power_zone] * self._ftp

    def _convert_minutes_to_seconds(minutes):
        return int(minutes * 60)

    def _generate_power_readings_steady(self, duration_in_seconds, power):
        return [power] * duration_in_seconds


class NormalizedPowerCalculator:
    def __init__(self, input_data):
        self._input_data = input_data
        self._rolling_averages = list()
        self._raised_to_4th_power = list()
        self._raised_values_average = None
        self._result = None

        self._process_data()

    def get_result(self):
        return self._result

    def _process_data(self):
        self._calculate_rolling_average()
        self._raise_to_4th_power()
        self._find_average_of_raised_values()
        self._find_4th_root_of_average()

    def _calculate_rolling_average(self):
        index = 0
        window_size = 30
        round_number_of_digits = 2

        while index <= len(self._input_data) - window_size:
            window = self._input_data[index: index + window_size]
            window_average = round(
                sum(window) / window_size, round_number_of_digits)
            self._rolling_averages.append(window_average)
            index += 1

    def _raise_to_4th_power(self):
        power_value = 4

        for element in self._rolling_averages:
            raised = pow(element, power_value)
            self._raised_to_4th_power.append(raised)

    def _find_average_of_raised_values(self):
        self._raised_values_average = sum(
            self._raised_to_4th_power) / len(self._raised_to_4th_power)

    def _find_4th_root_of_average(self):
        round_number_of_digits = 2
        root_value = 0.25
        self._result = round(self._raised_values_average **
                             root_value, round_number_of_digits)


def find_intensity_factor(normalized_power, ftp):
    round_number_of_digits = 2
    return round(normalized_power / ftp, round_number_of_digits)


def find_training_stres_score(duration, normalized_power, intensity_factor, ftp):
    number_of_seconds_in_hour = 3600
    round_number_of_digits = 1
    return round((duration * normalized_power * intensity_factor) / (ftp * number_of_seconds_in_hour) * 100, round_number_of_digits)


def read_data_from_fit_files(fit_files):
    parser = FitParser()
    for file in fit_files:
        parser.parse_file(file)
    return parser.get_total_duration(), parser.get_power_readings()


def read_data_from_json_files(json_files, ftp):
    parser = JsonParser(ftp)
    for file in json_files:
        parser.parse_file(file)
    return parser.get_total_duration(), parser.get_power_readings()


def calculate_tss(ftp, duration, power_readings):
    normalized_power = NormalizedPowerCalculator(power_readings).get_result()
    intensity_factor = find_intensity_factor(normalized_power, ftp)
    training_stress_score = find_training_stres_score(
        duration, normalized_power, intensity_factor, ftp)

    table = [
        ["FTP", "{} W".format(ftp)],
        ["Total workout duration", "{:.0f} min".format(duration / 60)],
        ["{}".format('-' * 25), "{}".format('-' * 10)],
        ["Normalized Power", "{:.0f} W".format(normalized_power)],
        ["Intensity Factor", intensity_factor],
        ["Training Stress Score", training_stress_score]
    ]

    horizontal_line = '-' * 42
    print(horizontal_line)
    for row in table:
        print("| {:25} | {:^10} |".format(*row))
    print(horizontal_line)


def parse_input_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('--ftp', required=True, type=int)
    parser.add_argument('--data', action='append', required=True, nargs='*')
    args = parser.parse_args()
    return args


def input_arguments_are_valid(arguments):
    valid_ftp_min = 100
    valid_ftp_max = 400
    file_type_fit = ".fit"
    file_type_json = ".json"
    actual_file_type = None

    if arguments.ftp < valid_ftp_min or arguments.ftp > valid_ftp_max:
        logging.error("Provided FTP is out of expected range: {} not in {}..{}". format(
            arguments.ftp, valid_ftp_min, valid_ftp_max))
        return False

    for file in arguments.data[0]:
        current_file_type = None
        if not os.path.isfile(file):
            logging.error("File does not exist: {}".format(file))
            return False
        if file.endswith(file_type_fit):
            current_file_type = file_type_fit
        elif file.endswith(file_type_json):
            current_file_type = file_type_json
        else:
            logging.error(
                "Seems file '{}' has not supported extension. Supported extensions are: '{}', '{}'"
                .format(file, file_type_fit, file_type_json))
            return False

        if actual_file_type is None:
            actual_file_type = current_file_type
        elif actual_file_type != current_file_type:
            logging.error(
                "Seems that files with different extensions were provided: '{}' and '{}'."
                .format(actual_file_type, current_file_type))
            return False

    return True


if __name__ == "__main__":
    input_arguments = parse_input_arguments()
    if not input_arguments_are_valid(input_arguments):
        exit()

    duration = None
    power_readings = None

    first_file = input_arguments.data[0][0]
    if first_file.endswith('.fit'):
        duration, power_readings = read_data_from_fit_files(
            input_arguments.data[0])
    elif first_file.endswith('.json'):
        duration, power_readings = read_data_from_json_files(
            input_arguments.data[0], input_arguments.ftp)
    else:
        logging.error("File extension not supported: {}".format(first_file))

    calculate_tss(input_arguments.ftp, duration, power_readings)
