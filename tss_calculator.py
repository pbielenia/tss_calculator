import argparse
import logging
import os.path

from fit_parser import FitParser
from json_parser import JsonParser
from text_parser import TextParser


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


def get_parser(file_path, ftp=None):
    file_path_lower = file_path.lower()

    if file_path_lower.endswith('.fit'):
        return FitParser(file_path)
    if file_path_lower.endswith('.json'):
        return JsonParser(ftp, file_path)
    if file_path_lower.endswith('.txt'):
        return TextParser(ftp, file_path)

    raise ValueError("File extension not supported: {}".format(file_path))


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
    parser.add_argument('--data', nargs='+', required=True)
    args = parser.parse_args()
    return args


def input_arguments_are_valid(arguments):
    valid_ftp_min = 100
    valid_ftp_max = 400
    file_type_fit = ".fit"
    file_type_json = ".json"
    file_type_txt = ".txt"
    actual_file_type = None

    if arguments.ftp < valid_ftp_min or arguments.ftp > valid_ftp_max:
        logging.error("Provided FTP is out of expected range: {} not in {}..{}". format(
            arguments.ftp, valid_ftp_min, valid_ftp_max))
        return False

    for file in arguments.data:
        current_file_type = None
        if not os.path.isfile(file):
            logging.error("File does not exist: {}".format(file))
            return False
        if file.endswith(file_type_fit):
            current_file_type = file_type_fit
        elif file.endswith(file_type_json):
            current_file_type = file_type_json
        elif file.endswith(file_type_txt):
            current_file_type = file_type_txt
        else:
            logging.error(
                "Seems file '{}' has not supported extension. Supported extensions are: '{}', '{}', '{}'"
                .format(file, file_type_fit, file_type_json, file_type_txt))
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

    first_file = input_arguments.data[0]
    parser = get_parser(first_file, input_arguments.ftp)
    duration, power_readings = parser.parse()
    calculate_tss(input_arguments.ftp, duration, power_readings)
