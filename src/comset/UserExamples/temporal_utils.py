from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from comset.COMSETsystem.Configuration import Configuration
from comset.UserExamples.global_parameters import GlobalParameters


class TemporalUtils:
    zone: ZoneInfo
    start: datetime
    end: datetime
    num_of_time_interval: int

    def __init__(self, zone: ZoneInfo):
        """
        Initialize TemporalUtils with a time zone.
        """
        self.zone = zone
        # Convert naive datetime to timezone-aware
        self.start = GlobalParameters.TEMPORAL_START_DATETIME.replace(tzinfo=self.zone)
        self.end = GlobalParameters.TEMPORAL_END_DATETIME.replace(tzinfo=self.zone)
        # Calculate total time intervals (assumes same year)
        self.num_of_time_interval = (
            self.end.timetuple().tm_yday - self.start.timetuple().tm_yday
        ) * GlobalParameters.NUM_OF_TIME_INTERVALS_PER_DAY

    def get_time(self, epoch_second: int) -> datetime:
        """
        Convert epoch second to timezone-aware datetime.
        If epoch_second is minimum, return current time.
        """
        if epoch_second != -9223372036854775808:  # Long.MIN_VALUE
            epoch_second //= Configuration.TIME_RESOLUTION
            return datetime.fromtimestamp(epoch_second, tz=self.zone)
        return datetime.now(self.zone)

    def get_intersection_temporal_index(self, timestamp: int) -> int:
        """
        Get the time interval index for intersection calculations.
        Adjusts out-of-range dates to similar valid dates.
        """
        date_time = self.get_time(timestamp)
        day = date_time.isoweekday()  # Monday=1, Sunday=7
        hour = date_time.hour
        minute = date_time.minute
        second = date_time.second

        if not self._is_valid(date_time):
            # Adjust out-of-scope dates
            if date_time < self.start:
                gap = self.start.year - date_time.year
                date_time = date_time.replace(year=date_time.year + gap)
            if date_time > self.end:
                gap = date_time.year - self.end.year
                date_time = date_time.replace(year=date_time.year - gap)

            # Match day of week
            current_weekday = date_time.isoweekday()
            diff_day = day - current_weekday
            if abs(diff_day) >= 4:
                diff_day = diff_day - 7 if diff_day > 0 else diff_day + 7

            tmp = date_time + timedelta(days=diff_day)
            if self._is_valid(tmp):
                date_time = tmp
            else:
                # Find closest valid date near start/end
                t = date_time.timetuple().tm_yday
                s = self.start.timetuple().tm_yday
                e = self.end.timetuple().tm_yday - 1

                diff_s = min(365 + s - t, abs(s - t))
                diff_e = min(365 + e - t, abs(e - t))

                if diff_s < diff_e:  # Near start
                    plus_days = (day + 7 - self.start.isoweekday()) % 7
                    date_time = (
                        self.start
                        + timedelta(days=plus_days)
                        + timedelta(hours=hour)
                        + timedelta(minutes=minute)
                        + timedelta(seconds=second)
                    )
                else:  # Near end
                    minus_days = (self.end.isoweekday() + 6 - day) % 7
                    date_time = (
                        self.end
                        - timedelta(days=minus_days + 1)
                        + timedelta(hours=hour)
                        + timedelta(minutes=minute)
                        + timedelta(seconds=second)
                    )
        return self._get_intersection_index(date_time)

    def find_time_interval_index(self, timestamp: int) -> int:
        """
        Get the time interval index for current time.
        Adjusts out-of-range dates to similar valid dates.
        """
        date_time = self.get_time(timestamp)
        day = date_time.isoweekday()  # Monday=1, Sunday=7
        hour = date_time.hour
        minute = date_time.minute
        second = date_time.second

        if not self._is_valid(date_time):
            # Adjust out-of-scope dates
            if date_time < self.start:
                gap = self.start.year - date_time.year
                date_time = date_time.replace(year=date_time.year + gap)
            if date_time > self.end:
                gap = date_time.year - self.end.year
                date_time = date_time.replace(year=date_time.year - gap)

            # Match day of week
            current_weekday = date_time.isoweekday()
            diff_day = day - current_weekday
            if abs(diff_day) >= 4:
                diff_day = diff_day - 7 if diff_day > 0 else diff_day + 7

            tmp = date_time + timedelta(days=diff_day)
            if self._is_valid(tmp):
                date_time = tmp
            else:
                # Find closest valid date near start/end
                t = date_time.timetuple().tm_yday
                s = self.start.timetuple().tm_yday
                e = self.end.timetuple().tm_yday - 1

                diff_s = min(365 + s - t, abs(s - t))
                diff_e = min(365 + e - t, abs(e - t))

                if diff_s < diff_e:  # Near start
                    plus_days = (day + 7 - self.start.isoweekday()) % 7
                    date_time = (
                        self.start
                        + timedelta(days=plus_days)
                        + timedelta(hours=hour)
                        + timedelta(minutes=minute)
                        + timedelta(seconds=second)
                    )
                else:  # Near end
                    minus_days = (self.end.isoweekday() + 6 - day) % 7
                    date_time = (
                        self.end
                        - timedelta(days=minus_days + 1)
                        + timedelta(hours=hour)
                        + timedelta(minutes=minute)
                        + timedelta(seconds=second)
                    )
        return self._get_index(date_time)

    def _is_valid(self, date_time: datetime) -> bool:
        """Check if datetime is within [start, end) range."""
        return self.start <= date_time < self.end

    def _get_index(self, date_time: datetime) -> int:
        """Calculate time interval index."""
        days = date_time.timetuple().tm_yday - self.start.timetuple().tm_yday
        total_seconds = (
            (date_time.hour - self.start.hour) * 3600
            + (date_time.minute - self.start.minute) * 60
            + (date_time.second - self.start.second)
        )
        b = (
            total_seconds / (24 * 60 * 60)
        ) * GlobalParameters.NUM_OF_TIME_INTERVALS_PER_DAY
        return days * GlobalParameters.NUM_OF_TIME_INTERVALS_PER_DAY + int(b)

    def _get_intersection_index(self, date_time: datetime) -> int:
        """Calculate intersection time interval index."""
        days = date_time.timetuple().tm_yday - self.start.timetuple().tm_yday
        total_seconds = (
            (date_time.hour - self.start.hour) * 3600
            + (date_time.minute - self.start.minute) * 60
            + (date_time.second - self.start.second)
        )
        b = (
            total_seconds / (24 * 60 * 60)
        ) * GlobalParameters.NUM_OF_INTERSECTION_TIME_INTERVAL_PER_DAY
        return days * GlobalParameters.NUM_OF_INTERSECTION_TIME_INTERVAL_PER_DAY + int(
            b
        )
