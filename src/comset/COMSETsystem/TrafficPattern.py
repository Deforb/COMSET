from typing import List, Tuple, Dict
from dataclasses import dataclass
from functools import lru_cache

from comset.COMSETsystem.LocationOnRoad import LocationOnRoad


class TrafficPattern:
    """
    TrafficPattern is a data structure that represents how the traffic condition changes over the time
    of a day.
    """

    @dataclass(frozen=True)
    class TrafficPatternItem:
        epoch_begin_time: int
        speed_factor: float

        def __str__(self) -> str:
            return f"{self.epoch_begin_time}, {self.speed_factor}"

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
        assert self.last_epoch_begin_time <= epoch_begin_time, (
            "epoch_begin_time must be greater than last_epoch_begin_time"
        )

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

    @lru_cache(maxsize=1024)
    def dynamic_forward_travel_time(
        self, time: float, unadjusted_speed: float, distance: float
    ) -> float:
        """compute the dynamic travel time to travel a certain distance of a link starting at a certain time"""
        total_distance = 0.0
        total_time = 0.0
        current_time = time

        while True:
            # 处理最后一个时间区间
            if current_time >= self.last_epoch_begin_time:
                adjusted_speed = unadjusted_speed * self.last_epoch_speed_factor
                step_time = (distance - total_distance) / adjusted_speed
                total_time += step_time
                break

            # 处理第一个时间区间前的特殊情况
            if current_time < self.first_epoch_begin_time:
                speed_factor = self.first_epoch_speed_factor
                step_time = self.first_epoch_begin_time - current_time
            else:
                # 定位当前时间所在的模式索引
                pattern_index = int(
                    (current_time - self.first_epoch_begin_time) // self.step
                )
                pattern: TrafficPattern.TrafficPatternItem = self.traffic_pattern[pattern_index]
                speed_factor = pattern.speed_factor
                # 计算当前时间到该模式结束的时间
                step_time = pattern.epoch_begin_time + self.step - current_time

            adjusted_speed = unadjusted_speed * speed_factor
            step_distance = adjusted_speed * step_time

            # 判断是否能完成完整的时间步长
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

    @lru_cache(maxsize=1024)
    def dynamic_travel_distance(
        self,
        time: float,
        unadjusted_speed: float,
        travel_time: float,
        max_distance: float,
    ) -> Tuple[float, float]:
        """compute the travel distance along a link for a certain time starting at a given time"""

        # 如果时间超出范围，使用固定速度计算
        if time >= self.last_epoch_begin_time:
            speed_factor = self.last_epoch_speed_factor
            adjusted_speed = unadjusted_speed * speed_factor
            distance = min(travel_time * adjusted_speed, max_distance)
            total_time = distance / adjusted_speed
            result = (distance, total_time)
            return result

        # 如果时间在第一个时间窗口之前，使用初始速度计算
        if time < self.first_epoch_begin_time:
            speed_factor = self.first_epoch_speed_factor
            adjusted_speed = unadjusted_speed * speed_factor
            distance = min(travel_time * adjusted_speed, max_distance)
            total_time = distance / adjusted_speed
            result = (distance, total_time)
            return result

        # 正常计算
        total_distance = 0.0
        total_time = 0.0
        current_time = time

        while total_time < travel_time and total_distance < max_distance:
            pattern_index = int(
                (current_time - self.first_epoch_begin_time) // self.step
            )
            speed_factor = self.traffic_pattern[pattern_index].speed_factor
            adjusted_speed = unadjusted_speed * speed_factor

            # 计算当前时间窗口的结束时间
            window_end_time = (
                self.traffic_pattern[pattern_index].epoch_begin_time + self.step
            )

            # 计算在当前速度下能行驶的时间
            remaining_time = travel_time - total_time
            time_in_window = window_end_time - current_time
            time_to_use = min(time_in_window, remaining_time)

            # 计算在当前速度下能行驶的距离
            distance_in_window = adjusted_speed * time_to_use
            if total_distance + distance_in_window > max_distance:
                # 超过最大距离限制
                remaining_distance = max_distance - total_distance
                time_needed = remaining_distance / adjusted_speed
                total_time += time_needed
                total_distance = max_distance
                break
            else:
                # 继续行驶
                total_distance += distance_in_window
                total_time += time_to_use
                current_time += time_to_use

        result = (total_distance, total_time)
        return result

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
