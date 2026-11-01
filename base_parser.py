import logging


class WorkoutParser:
    POWER_ZONE_FACTORS = {
        "S1": 0.5,
        "S2": 0.61,
        "S3": 0.88,
        "SST": 0.91,
        "S4": 0.98,
        "S5": 1.13,
    }

    def __init__(self, filepath=None):
        self._filepath = filepath
        self._total_duration = 0
        self._power_readings = []

    def parse(self, filepath=None):
        target_filepath = filepath or self._filepath
        if target_filepath is None:
            raise ValueError("No filepath was provided for parsing")

        self._filepath = target_filepath
        self._total_duration = 0
        self._power_readings = []
        self.parse_file(target_filepath)
        return self.get_total_duration(), self.get_power_readings()

    def parse_file(self, filepath):
        raise NotImplementedError("Concrete parser must implement parse_file()")

    def get_total_duration(self):
        return self._total_duration

    def get_power_readings(self):
        return self._power_readings

    @staticmethod
    def _power_zone_is_valid(power_zone):
        return power_zone in WorkoutParser.POWER_ZONE_FACTORS

    @staticmethod
    def _duration_is_valid(duration_in_minutes):
        return duration_in_minutes > 0 and duration_in_minutes < 400

    def _find_power_at_power_zone(self, power_zone):
        if not hasattr(self, "_ftp"):
            raise AttributeError("Power-zone lookup requires an FTP value on the parser instance")

        if power_zone not in self.POWER_ZONE_FACTORS:
            logging.error("Power zone factor not found: {}".format(power_zone))
            return 0
        return self.POWER_ZONE_FACTORS[power_zone] * self._ftp
