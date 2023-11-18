import argparse
import fitdecode
import logging
import os.path

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


def calculate_tss(ftp, fit_files):
    parser = FitParser()

    for file in fit_files:
        parser.parse_file(file)

    total_duration = parser.get_total_duration()

    normalized_power = NormalizedPowerCalculator(
        parser.get_power_readings()).get_result()
    intensity_factor = find_intensity_factor(normalized_power, ftp)
    training_stress_score = find_training_stres_score(
        total_duration, normalized_power, intensity_factor, ftp)

    table = [
        ["FTP", "{} W".format(ftp)],
        ["Total workout duration", "{:.0f} min".format(total_duration / 60)],
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
    parser.add_argument('--fit', action='append', required=True, nargs='*')
    args = parser.parse_args()
    return args


def input_arguments_are_valid(arguments):
    valid_ftp_min = 100
    valid_ftp_max = 400

    if arguments.ftp < valid_ftp_min or arguments.ftp > valid_ftp_max:
        logging.error("Provided FTP is out of expected range: {} not in {}..{}". format(
            arguments.ftp, valid_ftp_min, valid_ftp_max))
        return False

    for file in arguments.fit[0]:
        if not os.path.isfile(file):
            logging.error("File does not exist: {}".format(file))
            return False

    return True


if __name__ == "__main__":
    input_arguments = parse_input_arguments()
    if not input_arguments_are_valid(input_arguments):
        print("Invalid args")
        exit()

    calculate_tss(input_arguments.ftp, input_arguments.fit[0])
