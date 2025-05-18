from typing import List, Tuple
from dataclasses import dataclass

from comset.COMSETsystem.LocationOnRoad import LocationOnRoad


class TrafficPattern:
    """
    TrafficPattern is a data structure that represents how the traffic condition changes over the time
    of a day.
    """

    @dataclass
    class TrafficPatternItem:
        epoch_begin_time: int
        speed_factor: float

        def __str__(self) -> str:
            return f"{self.epoch_begin_time},{self.speed_factor}"

    def __init__(self, step: int) -> None:
        self.step: int = step
        self.traffic_pattern: List[TrafficPattern.TrafficPatternItem] = []
        self.first_epoch_begin_time: int = 0
        self.last_epoch_begin_time: int = 0
        self.first_epoch_speed_factor: float = 0.0
        self.last_epoch_speed_factor: float = 0.0

    def add_traffic_pattern_item(
        self, epoch_begin_time: int, speed_factor: float
    ) -> None:
        traffic_pattern_item = self.TrafficPatternItem(epoch_begin_time, speed_factor)
        self.traffic_pattern.append(traffic_pattern_item)
        if len(self.traffic_pattern) == 1:
            self.first_epoch_begin_time = epoch_begin_time
            self.first_epoch_speed_factor = speed_factor
        self.last_epoch_begin_time = epoch_begin_time
        self.last_epoch_speed_factor = speed_factor

    def get_speed_factor(self, time: int) -> float:
        if time < self.first_epoch_begin_time:
            return self.first_epoch_speed_factor
        if time >= self.last_epoch_begin_time:
            return self.last_epoch_speed_factor
        pattern_index = (time - self.first_epoch_begin_time) // self.step
        return self.traffic_pattern[pattern_index].speed_factor

    def dynamic_forward_travel_time(
        self, time: float, unadjusted_speed: float, distance: float
    ) -> float:
        """compute the dynamic travel time to travel a certain distance of a link starting at a certain time."""
        total_distance = 0.0
        total_time = 0.0
        current_time = time

        while True:
            step_time: float
            if current_time >= self.last_epoch_begin_time:
                speed_factor = self.last_epoch_speed_factor
                adjusted_speed = unadjusted_speed * speed_factor
                step_time = (distance - total_distance) / adjusted_speed
                total_time += step_time
                break
            else:
                if current_time < self.first_epoch_begin_time:
                    step_time = self.first_epoch_begin_time - current_time
                    speed_factor = self.first_epoch_speed_factor
                else:
                    pattern_index = int(
                        (current_time - self.first_epoch_begin_time) // self.step
                    )
                    step_time = (
                        self.traffic_pattern[pattern_index].epoch_begin_time
                        + self.step
                        - current_time
                    )
                    speed_factor = self.traffic_pattern[pattern_index].speed_factor
                adjusted_speed = unadjusted_speed * speed_factor
                step_distance = adjusted_speed * step_time
                if total_distance + step_distance < distance:
                    # finish a full step
                    total_distance += step_distance
                    total_time += step_time
                    current_time += step_time
                else:
                    # finish a partial step
                    remaining_distance = distance - total_distance
                    remaining_time = remaining_distance / adjusted_speed
                    total_time += remaining_time
                    break
        return total_time

    def road_travel_time_to_end_intersection(
        self, time: int, loc: LocationOnRoad
    ) -> int:
        return int(
            round(self.road_travel_time_to_end_intersection_double(float(time), loc))
        )

    def road_travel_time_to_end_intersection_double(
        self, time: float, loc: LocationOnRoad
    ) -> float:
        road = loc.road
        end_intersection = LocationOnRoad.create_from_road_end(road)
        return self.road_forward_travel_time_double(time, loc, end_intersection)

    def road_travel_time_from_start_intersection(
        self, time: int, loc: LocationOnRoad
    ) -> int:
        return round(
            self.road_travel_time_from_start_intersection_double(float(time), loc)
        )

    def road_travel_time_from_start_intersection_double(
        self, time: float, loc: LocationOnRoad
    ) -> float:
        road = loc.road
        start_intersection = LocationOnRoad.create_from_road_start(road)
        return self.road_forward_travel_time_double(time, start_intersection, loc)

    def road_forward_travel_time(
        self, time: int, loc1: LocationOnRoad, loc2: LocationOnRoad
    ) -> int:
        return int(round(self.road_forward_travel_time_double(float(time), loc1, loc2)))

    def road_forward_travel_time_double(
        self, time: float, loc1: LocationOnRoad, loc2: LocationOnRoad
    ) -> float:
        assert loc1.upstream_to(loc2), "loc1 must be upstream to loc2"
        return self.dynamic_forward_travel_time(
            time, loc1.road.speed, loc1.get_displacement_on_road(loc2)
        )

    def dynamic_travel_distance(
        self,
        time: float,
        unadjusted_speed: float,
        travel_time: float,
        max_distance: float,
    ) -> Tuple[float, float]:
        """compute the travel distance along a link for a certain time starting at a given time"""
        total_distance = 0.0
        total_time = 0.0
        current_time = time

        while True:
            step_time: float
            if current_time >= self.last_epoch_begin_time:
                speed_factor = self.last_epoch_speed_factor
                adjusted_speed = unadjusted_speed * speed_factor
                distance = (travel_time - total_time) * adjusted_speed
                if total_distance + distance > max_distance:
                    remaining_distance = max_distance - total_distance
                    total_time += remaining_distance / adjusted_speed
                    total_distance = max_distance
                else:
                    total_distance += distance
                    total_time = travel_time
                break
            else:
                if current_time < self.first_epoch_begin_time:
                    step_time = self.first_epoch_begin_time - current_time
                    speed_factor = self.first_epoch_speed_factor
                else:
                    pattern_index = int(
                        (current_time - self.first_epoch_begin_time) // self.step
                    )
                    step_time = (
                        self.traffic_pattern[pattern_index].epoch_begin_time
                        + self.step
                        - current_time
                    )
                    speed_factor = self.traffic_pattern[pattern_index].speed_factor
                adjusted_speed = unadjusted_speed * speed_factor
                if total_time + step_time > travel_time:
                    remaining_time = travel_time - total_time
                    distance = adjusted_speed * remaining_time
                    total_distance += distance
                    total_time = travel_time
                    break
                else:
                    distance = adjusted_speed * step_time
                    if total_distance + distance > max_distance:
                        remaining_distance = max_distance - total_distance
                        total_time += remaining_distance / adjusted_speed
                        total_distance = max_distance
                        break
                    else:
                        total_distance += distance
                        total_time += step_time
                        current_time += step_time
        return (total_distance, total_time)

    def travel_road_for_time(
        self, time: int, location_on_road: LocationOnRoad, travel_time: int
    ) -> LocationOnRoad:
        """The location when traveling along a road from a given location for a given amount of time (double type) starting at a given time."""
        return self.travel_road_for_time_double(
            float(time), location_on_road, float(travel_time)
        )

    def travel_road_for_time_double(
        self, time: float, location_on_road: LocationOnRoad, travel_time: float
    ) -> LocationOnRoad:
        distance, time = self.dynamic_travel_distance(
            time, location_on_road.road.speed, travel_time, location_on_road.road.length
        )
        if time < travel_time:
            return LocationOnRoad.create_from_road_end(location_on_road.road)
        else:
            return LocationOnRoad(location_on_road, distance)
