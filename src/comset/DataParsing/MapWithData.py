from __future__ import annotations
import heapq
import random
import math
import sys
from typing import List, TYPE_CHECKING, Tuple, Optional, Dict
from tqdm import tqdm

from comset.DataParsing.CSVNewYorkParser import CSVNewYorkParser
from comset.COMSETsystem.Configuration import Configuration
from comset.COMSETsystem.AgentEvent import AgentEvent
from comset.COMSETsystem.ResourceEvent import ResourceEvent
from comset.COMSETsystem.LocationOnRoad import LocationOnRoad
from comset.COMSETsystem.TrafficPattern import TrafficPattern
from comset.utils.parallel_processor import ParallelProcessor

if TYPE_CHECKING:
    from COMSETsystem.CityMap import CityMap
    from COMSETsystem.Event import Event
    from DataParsing.Resource import Resource
    from COMSETsystem.Simulator import Simulator
    from COMSETsystem.FleetManager import FleetManager


class MapWithData:
    """
    MapWithData 类负责加载资源数据集文件，进行地图匹配，并创建resource事件列表
    """

    def __init__(
        self, map: CityMap, resource_file: str, agent_placement_random_seed: int
    ):
        self.map: CityMap = map  # 基础地图对象
        self.resource_file: str = resource_file  # 资源文件完整路径
        self.agent_placement_random_seed: int = (
            agent_placement_random_seed  # 代理放置随机种子
        )
        self.events: List[Event] = []  # 事件优先队列（使用heapq模拟）
        self.zone_id: int = map.compute_zone_id()  # 时区信息
        self.resources_parsed: List[Resource] = []  # 解析后的资源列表
        self.earliest_resource_time: int = sys.maxsize  # 最早资源出现时间
        self.latest_resource_time: int = -1  # 最晚资源结束时间

    # FIXME: Pass in configuration here too instead of accessing it with the singleton.
    def create_map_with_data(
        self,
        configuration: Configuration,
        simulator: Simulator,
        fleet_manager: FleetManager,
    ) -> int:
        """
        Maps each agent and each resource onto the nearest location on the map
        according to the agent/resource's longitude and latitude. Creates resource events
        for each passenger record obtained from the resource file and adds them to the events
        priority queue.

        Args:
            configuration: object containing run-time parameters
            simulator: object with whose methods agent and resource events can
            be created.

        Return:
            long the latest resource time
        """
        parser = CSVNewYorkParser(self.resource_file, self.zone_id)
        self.resources_parsed: List[Resource] = parser.parse(
            Configuration.TIME_RESOLUTION
        )

        events_list: List[ResourceEvent] = []
        try:
            for resource in tqdm(
                self.resources_parsed, desc="map-matching resources", mininterval=1
            ):
                #  map matching
                pickup_match: LocationOnRoad = self.map_match(
                    resource.pickup_lon, resource.pickup_lat
                )
                dropoff_match: LocationOnRoad = self.map_match(
                    resource.dropoff_lon, resource.dropoff_lat
                )

                # TODO: won't need trip time
                static_trip_time: int = simulator.map_for_agents.travel_time_between(
                    pickup_match, dropoff_match
                )

                # 设置资源位置信息
                resource.pickup_location = pickup_match
                resource.dropoff_location = dropoff_match

                # 创建资源事件
                ev = ResourceEvent(
                    pickup_match,
                    dropoff_match,
                    resource.time,
                    static_trip_time,
                    simulator,
                    fleet_manager,
                    configuration.resource_maximum_life_time,
                )

                events_list.append(ev)

                # 更新最早和最晚资源时间
                self.earliest_resource_time = min(
                    self.earliest_resource_time, resource.time
                )

                self.latest_resource_time = max(
                    self.latest_resource_time,
                    resource.time
                    + configuration.resource_maximum_life_time
                    + static_trip_time,
                )

            self.events = events_list
            # heapq.heapify(self.events)

        except Exception:
            import traceback

            traceback.print_exc()

        return self.latest_resource_time

    def map_match(self, longitude: float, latitude: float) -> LocationOnRoad:
        """地图匹配核心方法：将经纬度坐标映射到最近的道路位置"""
        link = self.map.get_nearest_link(longitude, latitude)
        xy: List[float] = self.map.projector.from_lat_lon(latitude, longitude)
        snap_result = self.snap(
            link.from_vertex.get_x(),
            link.from_vertex.get_y(),
            link.to_vertex.get_x(),
            link.to_vertex.get_y(),
            xy[0],
            xy[1],
        )

        # 计算距离起始路口的距离
        distanceFromStartIntersection = 0.0
        for aLink in link.road.links:
            if aLink.id == link.id:
                distanceFromStartIntersection += self.distance(
                    snap_result[0],
                    snap_result[1],
                    link.to_vertex.get_x(),
                    link.to_vertex.get_y(),
                )
                break
            else:
                distanceFromStartIntersection += aLink.length

        return LocationOnRoad(link.road, distanceFromStartIntersection)

    # 获取交通模式（动态交通模式构建）
    def get_traffic_pattern(
        self,
        traffic_pattern_epoch: int,
        traffic_pattern_step: int,
        dynamic_traffic_enabled: bool,
    ) -> TrafficPattern:
        print("Building traffic patterns...")
        return self.build_sliding_traffic_pattern(
            self.resources_parsed,
            traffic_pattern_epoch,
            traffic_pattern_step,
            dynamic_traffic_enabled,
        )

    # 计算点到线段的最短投影（snap算法）
    def snap(
        self, x1: float, y1: float, x2: float, y2: float, x: float, y: float
    ) -> list:
        result = [0.0, 0.0, 0.0]
        length = (x1 - x2) ** 2 + (y1 - y2) ** 2

        if length == 0:
            dist = self.distance(x1, y1, x, y)
            result[0], result[1], result[2] = x1, y1, dist
        else:
            t = ((x - x1) * (x2 - x1) + (y - y1) * (y2 - y1)) / length
            if t < 0.0:
                dist = self.distance(x1, y1, x, y)
                result[0], result[1], result[2] = x1, y1, dist
            elif t > 1.0:
                dist = self.distance(x2, y2, x, y)
                result[0], result[1], result[2] = x2, y2, dist
            else:
                proj_x = x1 + t * (x2 - x1)
                proj_y = y1 + t * (y2 - y1)
                dist = self.distance(proj_x, proj_y, x, y)
                result[0], result[1], result[2] = proj_x, proj_y, dist
        return result

    # 计算两点间欧氏距离
    @staticmethod
    def distance(x1: float, y1: float, x2: float, y2: float) -> float:
        return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)

    # 随机放置代理到地图上
    def place_agents_randomly(
        self, simulator: Simulator, fleetManager: FleetManager, number_of_agents: int
    ) -> None:
        deploy_time = self.earliest_resource_time - 1
        generator = random.Random(self.agent_placement_random_seed)

        events_list: List[AgentEvent] = []
        for _ in range(number_of_agents):
            road_id = generator.randint(0, len(self.map.roads) - 1)
            road = self.map.roads[road_id]
            distance = generator.uniform(0, road.length)
            location = LocationOnRoad(road, distance)

            ev = AgentEvent(location, deploy_time, simulator, fleetManager)
            simulator.mark_agent_empty(ev)
            # heapq.heappush(self.events, ev)

        self.events.extend(events_list)

    # 获取事件队列
    def get_events(self) -> list:
        heapq.heapify(self.events)
        return self.events

    def build_sliding_traffic_pattern(
        self, resources: List[Resource], epoch: int, step: int, dynamicTraffic: bool
    ) -> TrafficPattern:
        """
        Build a traffic pattern to adjust travel speed at each road over the time of a day.
        The travel speed is computed based on the road segment's speed limit and the TLC Trip Record data to
        reflect the traffic pattern over the time of a day. The calibration goes as follows.

        1. For every step (e.g., minute) of a day, compute the average trip duration of all trips recorded in the
        TLC Trip Record data that fall into a epoch time window (e.g., 15 minutes) starting at the current minute;
        call it the TLC_average_trip_duration.
        2. For each trip, compute the shortest travel time from the pickup location of the trip to the
        dropoff location using speed limits.
        3. Compute the average shortest travel time of all trips; call it the map_average_trip_duration.
        4. For each road segment, travel_speed_of_current_minute = speed_limit((map_average_trip_duration)/(TLC_average_trip_duration)).

        In other words, we adjust the travel speeds so that the average trip time produced by COMSET is consistent with that of the real data.

        Args:
            resources: set of resources that will be used to compute speed factors.
            epoch: the window of time that determines the speed factor
            step: the resolution of the time-of-day speed dependence.
            dynamicTraffic: true if we will be simulated with time-of-day dependent traffic.

        Return:
            traffic pattern
        """

        # sort resources by pickup
        n = len(resources)
        resources.sort(key=lambda r: r.time)
        traffic_pattern = TrafficPattern(step)
        epoch_begin_time = resources[0].pickup_time
        begin_resource_index = 0
        last_known_speed_factor = 0.3  # default to 0.3 if no trip data available

        while True:
            epoch_resources: List[Resource] = []
            epoch_end_time = epoch_begin_time + epoch
            resource_index = begin_resource_index

            while (
                resource_index < n
                and resources[resource_index].pickup_time < epoch_end_time
            ):
                if resources[resource_index].dropoff_time < epoch_end_time:
                    epoch_resources.append(resources[resource_index])
                resource_index += 1

            if not dynamicTraffic:
                speed_factor = 1.0
            else:
                if not epoch_resources:
                    # use the previous epoch if available
                    speed_factor = last_known_speed_factor
                else:
                    speed_factor = self.get_speed_factor(epoch_resources)
                    if speed_factor >= 0:  # cap speed factor to 1
                        speed_factor = min(speed_factor, 1.0)
                        last_known_speed_factor = speed_factor
                    else:  # didn't get a valid speed factor
                        speed_factor = last_known_speed_factor

            traffic_pattern.add_traffic_pattern_item(epoch_begin_time, speed_factor)

            epoch_begin_time += step
            while (
                begin_resource_index < n
                and resources[begin_resource_index].pickup_time < epoch_begin_time
            ):
                begin_resource_index += 1

            if resource_index >= n:
                break

        return traffic_pattern

    # 计算交通速度因子（实际行程时间与模拟行程时间比值）
    def get_speed_factor(self, resources: List[Resource]) -> float:
        """
        Compute speed factor from a set of resources. Speed factor is based on actual travel times
        compared to ideal travel time between pickup and dropoff location based on distance.

        Args:
            resources the set of resources that will determine the speed factor.
        Return:
            speed factor
        """
        total_actual_travel_time = 0
        total_simulated_travel_time = 0

        for resource in resources:
            actual_travel_time = resource.dropoff_time - resource.pickup_time
            simulated_travel_time = int(
                self.map.travel_time_between(
                    resource.pickup_location, resource.dropoff_location
                )
            )
            total_actual_travel_time += actual_travel_time
            total_simulated_travel_time += simulated_travel_time

        return (
            total_simulated_travel_time / total_actual_travel_time
            if total_actual_travel_time != 0
            else -1.0
        )
