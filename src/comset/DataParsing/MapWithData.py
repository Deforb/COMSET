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
from comset.DataParsing.KdTree import KdTree
from comset.utils.parallel_processor import ParallelProcessor

if TYPE_CHECKING:
    from COMSETsystem.CityMap import CityMap
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
        self.map = map  # 基础地图对象
        self.resource_file = resource_file  # 资源文件完整路径
        self.agent_placement_random_seed = (
            agent_placement_random_seed  # 代理放置随机种子
        )
        self.events = []  # 事件优先队列（使用heapq模拟）
        self.zone_id = map.compute_zone_id()  # 时区信息
        self.resources_parsed: List[Resource] = []  # 解析后的资源列表
        self.earliest_resource_time = sys.maxsize  # 最早资源出现时间
        self.latest_resource_time = -1  # 最晚资源结束时间

    @staticmethod
    def process_single_resource_wrapper(data: Dict) -> Optional[Dict]:
        """
        处理单个资源数据的包装函数，返回处理后的完整数据。

        Args:
            data: 包含经纬度和时间信息的字典

        Returns:
            包含所有处理结果的字典，如果处理失败则返回None
        """
        try:
            # 计算距离
            distance = math.sqrt(
                (data['pickup_lon'] - data['dropoff_lon']) ** 2
                + (data['pickup_lat'] - data['dropoff_lat']) ** 2
            )

            # 估算行程时间（假设平均速度30km/h）
            estimated_time = distance * 111.32 * 3600 / 30  # 转换为秒

            return {
                'pickup_lon': data['pickup_lon'],
                'pickup_lat': data['pickup_lat'],
                'dropoff_lon': data['dropoff_lon'],
                'dropoff_lat': data['dropoff_lat'],
                'time': data['time'],
                'index': data['index'],
                'estimated_time': estimated_time,
            }
        except Exception as e:
            print(f"处理资源时出错: {str(e)}")
            return None

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
        self.resources_parsed = parser.parse(Configuration.TIME_RESOLUTION)
        total_resources = len(self.resources_parsed)
        print(f"总共解析到 {total_resources} 条资源数据")

        try:
            process_data = [
                {
                    'pickup_lon': resource.pickup_lon,
                    'pickup_lat': resource.pickup_lat,
                    'dropoff_lon': resource.dropoff_lon,
                    'dropoff_lat': resource.dropoff_lat,
                    'time': resource.time,
                    'index': i,
                }
                for i, resource in enumerate(self.resources_parsed)
            ]

            # 并行处理资源
            print("开始处理资源...")
            results = ParallelProcessor.process(
                process_data,
                self.process_single_resource_wrapper,
                use_imap=True,
                chunk_size=1000,  # 增加chunk大小
                desc="计算资源距离和时间",
            )

            success_count = 0
            events_list = []
            resource_maximum_life_time = configuration.resource_maximum_life_time

            # 批量处理地图匹配
            batch_size = 1000
            current_batch = []

            with tqdm(total=total_resources, desc="进行地图匹配和创建事件") as pbar:
                for result in results:
                    if result is None:
                        continue

                    current_batch.append(result)

                    # 当批次达到指定大小时进行处理
                    if len(current_batch) >= batch_size:
                        self._process_batch(
                            current_batch,
                            events_list,
                            resource_maximum_life_time,
                            simulator,
                            fleet_manager,
                        )
                        success_count += len(current_batch)
                        pbar.update(len(current_batch))
                        current_batch = []

                # 处理剩余的批次
                if current_batch:
                    self._process_batch(
                        current_batch,
                        events_list,
                        resource_maximum_life_time,
                        simulator,
                        fleet_manager,
                    )
                    success_count += len(current_batch)
                    pbar.update(len(current_batch))

            # 批量创建事件队列
            print("创建事件队列...")
            self.events = events_list
            heapq.heapify(self.events)

        except Exception as e:
            import traceback

            traceback.print_exc()

        return self.latest_resource_time

    def _process_batch(
        self,
        batch: List[Dict],
        events_list: List[ResourceEvent],
        resource_maximum_life_time: int,
        simulator: Simulator,
        fleet_manager: FleetManager,
    ) -> None:
        """
        批量处理地图匹配和事件创建。

        Args:
            batch: 要处理的数据批次
            events_list: 事件列表
            resource_maximum_life_time: 资源最大生命周期
            simulator: 模拟器对象
            fleet_manager: 车队管理器对象
        """
        for result in batch:
            # 地图匹配获取上下车位置
            pickup_link = self.map.get_nearest_link(
                result['pickup_lon'], result['pickup_lat']
            )
            dropoff_link = self.map.get_nearest_link(
                result['dropoff_lon'], result['dropoff_lat']
            )

            # 创建LocationOnRoad对象
            pickup_match = LocationOnRoad(pickup_link.road, pickup_link.begin_time)
            dropoff_match = LocationOnRoad(dropoff_link.road, dropoff_link.begin_time)

            # 使用估算的行程时间
            static_trip_time = int(result['estimated_time'])

            # 设置资源位置信息
            resource: Resource = self.resources_parsed[result['index']]
            resource.pickup_location = pickup_match
            resource.dropoff_location = dropoff_match

            # 创建资源事件
            ev = ResourceEvent(
                pickup_match,
                dropoff_match,
                result['time'],
                static_trip_time,
                simulator,
                fleet_manager,
                resource_maximum_life_time,
            )

            events_list.append(ev)

            # 更新最早和最晚资源时间
            if result['time'] < self.earliest_resource_time:
                self.earliest_resource_time: int = result['time']

            new_end_time: int = (
                result['time'] + resource_maximum_life_time + static_trip_time
            )
            if new_end_time > self.latest_resource_time:
                self.latest_resource_time: int = new_end_time

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

    # 地图匹配核心方法：将经纬度坐标映射到最近的道路位置
    def map_match(self, longitude: float, latitude: float) -> LocationOnRoad:
        link = self.map.get_nearest_link(longitude, latitude)
        xy = self.map.projector.from_lat_lon(latitude, longitude)
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
    def distance(self, x1: float, y1: float, x2: float, y2: float) -> float:
        return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)

    # 随机放置代理到地图上
    def place_agents_randomly(
        self, simulator: Simulator, fleetManager: FleetManager, number_of_agents: int
    ) -> None:
        deploy_time = self.earliest_resource_time - 1
        generator = random.Random(self.agent_placement_random_seed)

        for _ in range(number_of_agents):
            road_id = generator.randint(0, len(self.map.roads) - 1)
            road = self.map.roads[road_id]
            distance = generator.uniform(0, road.length)
            location = LocationOnRoad(road, distance)

            ev = AgentEvent(location, deploy_time, simulator, fleetManager)
            simulator.mark_agent_empty(ev)
            heapq.heappush(self.events, ev)

    # 获取事件队列
    def get_events(self) -> list:
        return self.events

    # 构建滑动时间窗口交通模式
    def build_sliding_traffic_pattern(
        self, resources: List[Resource], epoch: int, step: int, dynamicTraffic: bool
    ) -> TrafficPattern:
        resources.sort(key=lambda r: r.time)
        traffic_pattern = TrafficPattern(step)
        epoch_begin_time = resources[0].time
        begin_resource_index = 0
        last_known_speed_factor = 0.3  # 默认交通速度因子

        while True:
            epoch_resources = []
            epoch_end_time = epoch_begin_time + epoch
            resource_index = begin_resource_index

            while (
                resource_index < len(resources)
                and resources[resource_index].time < epoch_end_time
            ):
                if resources[resource_index].dropoff_time < epoch_end_time:
                    epoch_resources.append(resources[resource_index])
                resource_index += 1

            if dynamicTraffic:
                if not epoch_resources:
                    traffic_pattern.add_traffic_pattern_item(
                        epoch_begin_time, last_known_speed_factor
                    )
                else:
                    speed_factor = self.get_speed_factor(epoch_resources)
                    if speed_factor < 0:
                        traffic_pattern.add_traffic_pattern_item(
                            epoch_begin_time, last_known_speed_factor
                        )
                    else:
                        speed_factor = min(speed_factor, 1.0)
                        traffic_pattern.add_traffic_pattern_item(
                            epoch_begin_time, speed_factor
                        )
                        last_known_speed_factor = speed_factor
            else:
                traffic_pattern.add_traffic_pattern_item(epoch_begin_time, 1.0)

            epoch_begin_time += step
            while (
                begin_resource_index < len(resources)
                and resources[begin_resource_index].time < epoch_begin_time
            ):
                begin_resource_index += 1

            if resource_index >= len(resources):
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
