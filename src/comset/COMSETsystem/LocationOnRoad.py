from typing import Union

from comset.COMSETsystem.Road import Road


class LocationOnRoad:
    """
    A class representing a location on a road, maintaining distance from the start intersection.
    """

    def __init__(
        self,
        road_or_location: Union[Road, 'LocationOnRoad'],
        distance_or_displacement: float,
    ) -> None:
        """
        初始化道路上的位置。
        
        可以通过两种方式初始化：
        1. 提供一个道路对象和从起始交叉口的距离
        2. 提供一个已有的LocationOnRoad对象和位移量
        
        Args:
            road_or_location: 道路对象或已有的LocationOnRoad对象
            distance_or_displacement: 如果第一个参数是Road，则表示从起始交叉口的距离；
                                     如果第一个参数是LocationOnRoad，则表示相对于该位置的位移
                                     
        Raises:
            TypeError: 当road_or_location参数类型无效时抛出
            AssertionError: 当计算的距离超出道路长度范围时抛出
        """
        if isinstance(road_or_location, Road):
            self.road = road_or_location
            self.distance_from_start_intersection = distance_or_displacement
        elif isinstance(road_or_location, LocationOnRoad):
            location = road_or_location
            displacement = distance_or_displacement
            self.road = location.road
            self.distance_from_start_intersection = (
                location.distance_from_start_intersection + displacement
            )
            assert (
                0 <= self.distance_from_start_intersection <= self.road.length
            ), "Distance must be within [0, road length]"
        else:
            raise TypeError("Invalid argument type for road_or_location")

    def upstream_to(self, destination: 'LocationOnRoad') -> bool:
        """
        Check if the destination is upstream from the current location.
        """
        return self.get_displacement_on_road(destination) >= 0

    def get_displacement_on_road(self, destination: 'LocationOnRoad') -> float:
        """
        Calculate displacement to the destination on the same road.
        """
        assert self.road.id == destination.road.id, "Locations must be on the same road"
        return (
            destination.distance_from_start_intersection
            - self.distance_from_start_intersection
        )

    def get_static_travel_time_on_road(self) -> int:
        """
        Calculate travel time based on distance and road speed.
        """
        return round(self.distance_from_start_intersection / self.road.speed)

    def at_end_intersection(self) -> bool:
        """
        Check if the location is at the end of the road.
        """
        return self.distance_from_start_intersection == self.road.length

    @classmethod
    def create_from_road_end(cls, road: Road) -> 'LocationOnRoad':
        """
        Create a location at the end of the road.
        """
        return cls(road, road.length)

    @classmethod
    def create_from_road_start(cls, road: Road) -> 'LocationOnRoad':
        """
        Create a location at the start of the road.
        """
        return cls(road, 0.0)

    @classmethod
    def copy_with_replaced_road(
        cls, road: Road, location_on_road: 'LocationOnRoad'
    ) -> 'LocationOnRoad':
        """
        Create a copy with a replaced road, maintaining distance.
        """
        return cls(road, location_on_road.distance_from_start_intersection)

    def __str__(self) -> str:
        return f"(road: {self.road.id}, distance_from_start_intersection: {self.distance_from_start_intersection})"
