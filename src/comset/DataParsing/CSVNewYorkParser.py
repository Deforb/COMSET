import csv
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import List

from comset.MapCreation.MapCreator import MapCreator
from comset.DataParsing.Resource import Resource


class CSVNewYorkParser:
    """
    The CsvNewYorkParser class parses a New York TLC data file for a month before July of 2016.
    The following columns are extracted from each row to create a Resource object.

    1. "tpep_pickup_datetime": This time stamp is treated as the time at which the resource (passenger)
       is introduced to the system.
    2. "pickup_longitude", "pickup_latitude": The location at which the resource (passenger) is introduced.
    3. "dropoff_longitude", "dropoff_latitude": The location at which the resource (passenger) is dropped off.
    """

    def __init__(self, path: str, zone_id: ZoneInfo) -> None:
        """
        Constructor of the CsvNewYorkParser class

        Args:
            path: Full path to the resource dataset file
            zone_id: The time zone id of the studied area
        """
        self.path = path
        self.zone_id = zone_id
        self.resources: List[Resource] = []
        self._datetime_format = "%Y-%m-%d %H:%M:%S"

    def _date_conversion(self, timestamp: str) -> int:
        """
        Converts the date+time (timestamp) string into the Linux epoch.

        Args:
            timestamp: String containing formatted date and time data to be converted
        Returns:
            int: Number of seconds since January 1, 1970, 00:00:00 UTC
        """
        dt_naive = datetime.strptime(timestamp, self._datetime_format)
        dt_aware = dt_naive.replace(tzinfo=self.zone_id)
        return int(dt_aware.timestamp())

    def parse(self, time_resolution: int) -> List[Resource]:
        """
        Parse the csv file.

        Returns:
            List[Resource]: List of parsed Resource objects
        """
        try:
            with open(self.path, "r") as f:
                reader = csv.reader(f)
                next(reader)  # Skip header

                # while there are tokens in the file the scanner will scan the input
                # each line in input file will contain 4 tokens for the scanner and will be in the format : latitude longitude time type
                # per line of input file we will create a new TimestampAgRe object
                # and save the 4 tokens of each line in the corresponding field of the TimestampAgRe object
                for row in reader:
                    pickup_time_str = row[1]
                    dropoff_time_str = row[2]
                    pickup_lon = float(row[5])
                    pickup_lat = float(row[6])
                    dropoff_lon = float(row[9])
                    dropoff_lat = float(row[10])

                    # Convert timestamps
                    time = self._date_conversion(pickup_time_str) * time_resolution
                    dropoff_time = (
                        self._date_conversion(dropoff_time_str) * time_resolution
                    )

                    # Only keep the resources such that both pickup location and dropoff location are within the bounding polygon.
                    if not (
                        MapCreator.inside_polygon(pickup_lon, pickup_lat)
                        and MapCreator.inside_polygon(dropoff_lon, dropoff_lat)
                    ):
                        continue
                    if (pickup_lat, pickup_lon) == (dropoff_lat, dropoff_lon):
                        continue

                    self.resources.append(
                        Resource(
                            pickup_lat,
                            pickup_lon,
                            dropoff_lat,
                            dropoff_lon,
                            time,
                            dropoff_time,
                        )
                    )

        except Exception as e:
            import traceback

            traceback.print_exc()

        return self.resources
