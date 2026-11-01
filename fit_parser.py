import fitdecode

from base_parser import WorkoutParser


class FitParser(WorkoutParser):
    def __init__(self, filepath=None):
        super().__init__(filepath)

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
