from __future__ import annotations
from typing import TYPE_CHECKING

from comset.MapCreation.MapCreator import MapCreator

if TYPE_CHECKING:
    from FleetManager import FleetManager
    from CityMap import CityMap


class Configuration:
    """
    Class to hold the configuration parameters of the simulation. Call static method Configuration.make() first to
    create a singleton configuration object, then call Configuration.get() to retrieve the singleton.
    """

    _instance = None

    TIME_RESOLUTION = 1000000

    @classmethod
    def make(
        cls,
        fleet_manager_class: FleetManager,
        map_json_file: str,
        resource_file: str,
        number_of_agents: int,
        bounding_polygon_kml_file: str,
        resource_maximum_life_time: int,
        agent_placement_seed: int,
        dynamic_traffic: bool,
        traffic_pattern_epoch: int,
        traffic_pattern_step: int,
    ):
        """创建配置实例"""
        if cls._instance is None:
            cls._instance = cls(
                fleet_manager_class=fleet_manager_class,
                map_json_file=map_json_file,
                resource_file=resource_file,
                number_of_agents=number_of_agents,
                bounding_polygon_kml_file=bounding_polygon_kml_file,
                resource_maximum_life_time=resource_maximum_life_time,
                agent_placement_seed=agent_placement_seed,
                dynamic_traffic=dynamic_traffic,
                traffic_pattern_epoch=traffic_pattern_epoch,
                traffic_pattern_step=traffic_pattern_step,
            )
        return cls._instance

    @classmethod
    def get(cls) -> Configuration:
        """获取配置实例"""
        if cls._instance is None:
            raise RuntimeError("Configuration has not been initialized")
        return cls._instance

    def __init__(self, **kwargs):
        # A class that extends BaseAgent and implements a search routing strategy
        self.fleet_manager_class: FleetManager = kwargs["fleet_manager_class"]

        # Full path to an OSM JSON map file
        self.map_json_file: str = kwargs["map_json_file"]

        # Full path to a TLC New York Yellow trip record file
        self.resource_file: str = kwargs["resource_file"]

        # FIXME: The field numberOfAgents should be protected or private. Most code, beside agent creation and placement
        # code don't need to know its value. Also the field dynamicTraffic should also be hidden.
        # The number of agents that are deployed (at the beginning of the simulation).
        self.number_of_agents: int = kwargs["number_of_agents"]

        # Full path to a KML defining the bounding polygon to crop the map
        self.bounding_polygon_kml_file: str = kwargs["bounding_polygon_kml_file"]

        # Members accessible from COMSETsystem, hidden from others, i.e. they have no business knowing them.
        self.resource_maximum_life_time_in_seconds: int = kwargs[
            "resource_maximum_life_time"
        ]
        self.resource_maximum_life_time: int = (
            self.resource_maximum_life_time_in_seconds * self.TIME_RESOLUTION
        )
        self.agent_placement_seed: int = kwargs["agent_placement_seed"]
        self.dynamic_traffic_enabled: bool = kwargs["dynamic_traffic"]

        self.traffic_pattern_epoch: int = (
            kwargs["traffic_pattern_epoch"] * self.TIME_RESOLUTION
        )
        self.traffic_pattern_step: int = (
            kwargs["traffic_pattern_step"] * self.TIME_RESOLUTION
        )

        # The map that everything will happen on.
        self.map: CityMap = self._make_city_map()

        # Pre-compute shortest travel times between all pairs of intersections.
        # 测试两种计算方法的效果
        # 方法1: calc_travel_times()
        self.map.calc_travel_times()
        travel_times_1 = self.map.immutable_path_table
        
        # 方法2: calc_travel_time_raw() 
        self.map.calc_travel_time_raw()
        travel_times_2 = self.map.immutable_path_table
        
        # 比较两种方法的结果是否相同
        if travel_times_1 == travel_times_2:
            print("两种计算方法结果相同")
        else:
            print("警告:两种计算方法结果不同,需要进一步分析差异")
            # 暂时使用 raw 方法
            self.map.calc_travel_time_raw()

    # Beside make() and get(), most methods should be static. Much safer that way to avoid initialization problems
    # where they are called before proper initialization of the singleton.
    @classmethod
    def to_seconds(cls, scaled_simulation_time: int) -> int:
        return scaled_simulation_time // cls.TIME_RESOLUTION

    @classmethod
    def to_simulated_speed(cls, distance_per_second: float) -> float:
        return distance_per_second / cls.TIME_RESOLUTION

    def _make_city_map(self) -> CityMap:
        creator = MapCreator(self)
        print("Creating map...")

        creator.create_map()
        return creator.output_city_map()
