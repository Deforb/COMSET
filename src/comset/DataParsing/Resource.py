from __future__ import annotations
from typing import Optional, TYPE_CHECKING

from comset.DataParsing.TimestampAbstract import TimestampAbstract

if TYPE_CHECKING:
    from COMSETsystem.LocationOnRoad import LocationOnRoad


class Resource(TimestampAbstract):

    def __init__(
        self,
        pickup_lat: float,
        pickup_lon: float,
        dropoff_lat: float,
        dropoff_lon: float,
        time: int,
        dropoff_time: int,
    ):
        super().__init__(pickup_lat, pickup_lon, time)
        self._dropoff_lat = dropoff_lat
        self._dropoff_lon = dropoff_lon
        self._dropoff_time = dropoff_time
        self._pickup_location: Optional[LocationOnRoad] = None
        self._dropoff_location: Optional[LocationOnRoad] = None

    @property
    def dropoff_lat(self) -> float:
        return self._dropoff_lat

    @property
    def dropoff_lon(self) -> float:
        return self._dropoff_lon

    @property
    def pickup_location(self):
        return self._pickup_location

    @pickup_location.setter
    def pickup_location(self, pickup_location: LocationOnRoad):
        self._pickup_location = pickup_location

    @property
    def dropoff_location(self):
        return self._dropoff_location

    @dropoff_location.setter
    def dropoff_location(self, dropoff_location: LocationOnRoad):
        self._dropoff_location = dropoff_location

    @property
    def dropoff_time(self):
        return self._dropoff_time

    @property
    def pickup_time(self) -> int:
        return self.time
