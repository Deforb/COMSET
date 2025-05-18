from __future__ import annotations
from typing import TYPE_CHECKING

from comset.MapCreation.MapCreator import MapCreator

if TYPE_CHECKING:
    from FleetManager import FleetManager
    from CityMap import CityMap


class Configuration:
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
    def get(cls):
        """获取配置实例"""
        if cls._instance is None:
            raise RuntimeError("Configuration has not been initialized")
        return cls._instance

    def __init__(self, **kwargs):
        self.fleet_manager_class = kwargs["fleet_manager_class"]

        self.map_json_file = kwargs["map_json_file"]
        self.resource_file = kwargs["resource_file"]
        self.number_of_agents = kwargs["number_of_agents"]
        self.bounding_polygon_kml_file = kwargs["bounding_polygon_kml_file"]
        self.resource_maximum_life_time = (
            kwargs["resource_maximum_life_time"] * self.TIME_RESOLUTION
        )
        self.agent_placement_seed = kwargs["agent_placement_seed"]
        self.dynamic_traffic_enabled = kwargs["dynamic_traffic"]

        self.traffic_pattern_epoch = (
            kwargs["traffic_pattern_epoch"] * self.TIME_RESOLUTION
        )
        self.traffic_pattern_step = (
            kwargs["traffic_pattern_step"] * self.TIME_RESOLUTION
        )

        self.map = self._make_city_map()

        # Pre-compute shortest travel times between all pairs of intersections.
        print("Pre-computing all pair travel times...")
        self.map.calc_travel_times()

    # Beside make() and get(), most methods should be static. Much safer that way to avoid initialization problems
    # where they are called before proper initialization of the singleton.
    @classmethod
    def to_seconds(cls, scaledSimulationTime: int):
        return scaledSimulationTime / cls.TIME_RESOLUTION

    @classmethod
    def to_simulated_speed(cls, distancePerSecond: float):
        return distancePerSecond / cls.TIME_RESOLUTION

    def _make_city_map(self) -> CityMap:
        creator = MapCreator(self)
        print("Creating map...")

        creator.create_map()
        return creator.output_city_map()
