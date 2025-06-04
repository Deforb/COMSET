import math
import random
from bisect import bisect_left
from collections import defaultdict, deque
from typing import Dict, List, Optional, Set, Tuple, override

import h3
from ortools.graph import pywrapgraph

from src.comset.COMSETsystem.AgentAction import AgentAction
from src.comset.COMSETsystem.CityMap import CityMap
from src.comset.COMSETsystem.Configuration import Configuration
from src.comset.COMSETsystem.FleetManager import FleetManager, ResourceState
from src.comset.COMSETsystem.Intersection import Intersection
from src.comset.COMSETsystem.LocationOnRoad import LocationOnRoad
from src.comset.COMSETsystem.Resource import Resource
from src.comset.COMSETsystem.Road import Road
from global_parameters import GlobalParameters
from region import Region


class MCFFleetManager(FleetManager):
    def __init__(self, city_map: CityMap):
        super().__init__(city_map)
        self.agent_last_appear_time: Dict[int, int] = {}
        self.agent_last_location: Dict[int, LocationOnRoad] = {}
        self.resource_assignment: Dict[int, Resource] = {}
        self.waiting_resources: Set[Resource] = set()  # ordered by id
        self.available_agent: Set[int] = set()
        self.occupied_agent: Set[int] = set()
        self.agent_rnd: Dict[int, random.Random] = {}
        self.assignment_for_occupied: Dict[int, Resource] = {}
        self.agent_routes: Dict[int, deque[Intersection]] = defaultdict(deque)

        self.temporal_utils = TemporalUtils(city_map.compute_zone_id())
        self.traffic_pattern_pred = TrafficPatternPred(
            GlobalParameters.TRAFFIC_PATTERN_PRED_FILE
        )
        self.h3 = h3.api.basic_str
        self.agent_start_search_time: Dict[int, int] = {}
        self.region_list: List[Region] = []
        self.hex_addr_to_region: Dict[str, int] = {}
        # Candidate agents for repositioning task
        self.candidate_agents: Set[int] = set()
        self.has_repositioned: List[bool] = [
            False
        ] * self.temporal_utils.num_of_time_interval
        self.intersection_resource_map: Dict[int, List[int]] = defaultdict(list)

    @override
    def on_agent_introduced(
        self, agent_id: int, current_loc: LocationOnRoad, time: int
    ):
        self.agent_last_appear_time[agent_id] = time
        self.agent_last_location[agent_id] = current_loc
        self.available_agent.add(agent_id)
        self.agent_start_search_time[agent_id] = time
        self._add_agent_to_region(agent_id, current_loc)

    @override
    def on_resource_availability_change(
        self,
        resource: Resource,
        state: ResourceState,
        current_loc: LocationOnRoad,
        time: int,
    ) -> AgentAction:
        action = AgentAction.do_nothing()

        match state:
            case ResourceState.AVAILABLE:
                assigned_agent = self._get_nearest_agent(resource, time)
                if assigned_agent is not None:
                    self.resource_assignment[assigned_agent] = resource
                    self.agent_routes[assigned_agent] = deque()
                    self.available_agent.remove(assigned_agent)
                    self.candidate_agents.discard(assigned_agent)
                    action = AgentAction.assign_to(assigned_agent, resource.id)
                    self._remove_agent_from_region(assigned_agent)
                else:
                    self.waiting_resources.add(resource)
                    self._add_resource_to_region(resource)

            case ResourceState.DROPPED_OFF:
                best_resource = None
                earliest = float("inf")

                if resource.assigned_agent_id in self.assignment_for_occupied:
                    best_resource = self.assignment_for_occupied[
                        resource.assigned_agent_id
                    ]
                else:
                    for res in self.waiting_resources:
                        # If res is in waitingResources, then it must have not expired yet
                        if res in self.assignment_for_occupied.values():
                            continue

                        travel_time: int = self.map.travel_time_between(
                            current_loc, res.pickup_loc
                        )
                        speed_factor = self._get_speed_factor(time)
                        adjusted_travel_time = int(travel_time / speed_factor)

                        # if the resource is reachable before expiration
                        arrive_time = time + adjusted_travel_time
                        if (
                            arrive_time <= res.expiration_time
                            and arrive_time < earliest
                        ):
                            earliest = arrive_time
                            best_resource = res

                if best_resource is not None:
                    self.waiting_resources.remove(best_resource)
                    self._remove_resource_from_region(best_resource)
                    action = AgentAction.assign_to(
                        resource.assigned_agent_id, best_resource.id
                    )
                else:
                    self.available_agent.add(resource.assigned_agent_id)
                    self._add_agent_to_region(resource.assigned_agent_id, current_loc)
                    self.agent_start_search_time[resource.assigned_agent_id] = time
                    action = AgentAction.do_nothing()

                self.assignment_for_occupied.pop(resource.assigned_agent_id, None)
                self.occupied_agent.discard(resource.assigned_agent_id)
                self.resource_assignment[resource.assigned_agent_id] = best_resource
                self.agent_last_location[resource.assigned_agent_id] = current_loc
                self.agent_last_appear_time[resource.assigned_agent_id] = time

            case ResourceState.EXPIRED:
                self.waiting_resources.discard(resource)
                self._remove_resource_from_region(resource)
                if resource.assigned_agent_id != -1:
                    self.agent_routes[resource.assigned_agent_id] = deque()
                    self.available_agent.add(resource.assigned_agent_id)
                    self._add_agent_to_region(resource.assigned_agent_id, current_loc)
                    self.agent_start_search_time[resource.assigned_agent_id] = time
                    self.resource_assignment.pop(resource.assigned_agent_id, None)

            case ResourceState.PICKED_UP:
                self.agent_routes[resource.assigned_agent_id] = deque()
                self.occupied_agent.add(resource.assigned_agent_id)

        return action

    @override
    def on_reach_intersection(
        self, agent_id: int, time: int, current_loc: LocationOnRoad
    ) -> Intersection:
        if agent_id == 240902 and time == 1464800008:
            print("here")

        last_loc = self.agent_last_location[agent_id]
        last_lat, last_lon = self._get_location_lat_lon(last_loc)
        current_lat, current_lon = self._get_location_lat_lon(current_loc)
        last_addr = self.h3.geo_to_h3(last_lat, last_lon, 8)
        current_addr = self.h3.geo_to_h3(current_lat, current_lon, 8)

        if last_addr != current_addr and agent_id in self.available_agent:
            self._remove_agent_from_region(agent_id)
            if agent_id in self.available_agent:
                self._add_agent_to_region(agent_id, current_loc)

        self.agent_last_appear_time[agent_id] = time
        time_index = self.temporal_utils.find_time_interval_index(time)
        searched_time = (
            time - self.agent_start_search_time[agent_id]
        ) // Configuration.TIME_RESOLUTION

        if (
            searched_time > GlobalParameters.CRUISING_THRESHOLD
            and agent_id in self.available_agent
        ):
            self.candidate_agents.add(agent_id)

        if self.candidate_agents and not self.has_repositioned[time_index]:
            self._driver_reposition(time)
            self.has_repositioned[time_index] = True

        route: deque[Intersection] = self.agent_routes.get(agent_id, deque())
        if not route:
            route = self.plan_route(agent_id, current_loc, time)
            self.agent_routes[agent_id] = route

        next_location: Intersection = route.popleft()
        next_road = current_loc.road.to.road_to(next_location)
        location_on_road = LocationOnRoad.create_from_road_start(next_road)
        self.agent_last_location[agent_id] = location_on_road
        return next_location

    @override
    def on_reach_intersection_with_resource(
        self, agent_id: int, time: int, current_loc: LocationOnRoad, resource: Resource
    ) -> Intersection:
        self.agent_last_appear_time[agent_id] = time
        route = self.agent_routes.get(agent_id, deque())

        if not route:
            route = self.plan_route_to_target(resource.pickup_loc, resource.dropoff_loc)
            self.agent_routes[agent_id] = route

        next_location = route.popleft()
        next_road = current_loc.road.to.road_to(next_location)
        location_on_road = LocationOnRoad.create_from_road_start(next_road)
        self.agent_last_location[agent_id] = location_on_road
        return next_location

    def plan_route(
        self, agent_id: int, current_location: LocationOnRoad, time: int
    ) -> deque[Intersection]:
        assigned_res = self.resource_assignment.get(agent_id)

        if assigned_res is None:
            return self.get_stp_route(agent_id, current_location, time)

        source_intersection = current_location.road.to
        destination_intersection = assigned_res.pickup_loc.road.from_
        shortest_path: deque[Intersection] = self.map.shortest_travel_time_path(
            source_intersection, destination_intersection
        )
        shortest_path.popleft()  # Remove first element
        return shortest_path

    def plan_route_to_target(
        self, source: LocationOnRoad, destination: LocationOnRoad
    ) -> deque[Intersection]:
        source_intersection = source.road.to
        destination_intersection = destination.road.from_
        shortest_path: deque[Intersection] = self.map.shortest_travel_time_path(
            source_intersection, destination_intersection
        )
        shortest_path.popleft()
        return shortest_path

    def get_stp_route(
        self, agent_id: int, current_location: LocationOnRoad, time: int
    ) -> deque[Intersection]:
        """
        Call this method to find a search route for an idle agent

        Args:
            agent_id: the unique id of the agent
            current_location: current location of agent
            time: current simulation time
        Returns:
            the search route for idle agent
        """
        source_intersection = current_location.road.to
        rnd = self.agent_rnd.get(agent_id, random.Random(agent_id))
        self.agent_rnd[agent_id] = rnd

        candidate_regions: set[Region] = set()
        k_neighbors: list[Region] = self._get_k_neighbor_regions(
            self.get_region(source_intersection), GlobalParameters.K
        )

        while len(candidate_regions) < GlobalParameters.N:
            region = self._sample_a_region(k_neighbors, time, rnd)
            candidate_regions.add(region)
            k_neighbors.remove(region)

        speed_factor = self._get_speed_factor(time)
        destination_region = self._sample_by_distance(
            candidate_regions,
            current_location,
            speed_factor,
            GlobalParameters.GAMMA,
            rnd,
        )

        destination_intersection = self._get_destination(destination_region, time)
        if destination_intersection == source_intersection:
            # destination cannot be the source
            # if destination is the source, choose a neighbor to be the destination
            roads_from: list[Road] = list(source_intersection.roads_map_from.values())
            destination_intersection = roads_from[0].to

        shortest_path = self.map.shortest_travel_time_path(
            source_intersection, destination_intersection
        )
        shortest_path.popleft()
        return shortest_path

    def _get_location_lat_lon(self, location: LocationOnRoad) -> Tuple[float, float]:
        """Convert location to latitude and longitude"""
        proportion = (
            location.get_static_travel_time_on_road() / location.road.travel_time
        )
        proportion = max(0, min(1, proportion))

        lat = (
            location.road.from_.latitude
            + (location.road.to.latitude - location.road.from_.latitude) * proportion
        )
        lon = (
            location.road.from_.longitude
            + (location.road.to.longitude - location.road.from_.longitude) * proportion
        )
        return lat, lon

    def _remove_resource_from_region(self, resource: Resource):
        lat, lon = self._get_location_lat_lon(resource.pickup_loc)
        hex_addr: str = self.h3.geo_to_h3(lat, lon, 8)
        if hex_addr in self.hex_addr_to_region:
            self.region_list[
                self.hex_addr_to_region[hex_addr]
            ].waiting_resources.discard(resource)

    def _add_agent_to_region(self, agent_id: int, current_loc: LocationOnRoad):
        lat, lon = self._get_location_lat_lon(current_loc)
        hex_addr: str = self.h3.geo_to_h3(lat, lon, 8)
        if hex_addr in self.hex_addr_to_region:
            self.region_list[self.hex_addr_to_region[hex_addr]].available_agents.add(
                agent_id
            )

    def _remove_agent_from_region(self, agent_id: int):
        lat, lon = self._get_location_lat_lon(self.agent_last_location[agent_id])
        hex_addr: str = self.h3.geo_to_h3(lat, lon, 8)
        if hex_addr in self.hex_addr_to_region:
            self.region_list[
                self.hex_addr_to_region[hex_addr]
            ].available_agents.discard(agent_id)

    def _add_resource_to_region(self, resource: Resource):
        lat, lon = self._get_location_lat_lon(resource.pickup_loc)
        hex_addr: str = self.h3.geo_to_h3(lat, lon, 8)
        if hex_addr in self.hex_addr_to_region:
            self.region_list[self.hex_addr_to_region[hex_addr]].waiting_resources.add(
                resource
            )

    def _read_region_file(self, file_name: str):
        try:
            with open(file_name, "r") as file:
                for line in file:
                    region = Region(line.strip())
                    self.region_list.append(region)
                    self.hex_addr_to_region[line.strip()] = len(self.region_list) - 1

            for intersection in self.map.intersections.values():
                lat, lon = intersection.latitude, intersection.longitude
                hex_addr: str = self.h3.geo_to_h3(lat, lon, 8)
                self.region_list[
                    self.hex_addr_to_region[hex_addr]
                ].intersection_list.append(intersection)
                self.intersection_resource_map[intersection.id] = []
        except Exception as e:
            import traceback

            traceback.print_exc()
            raise e

    def _read_pickup_matrix(self, file_name: str):
        try:
            with open(file_name, "r") as file:
                for line in file:
                    region_data = line.strip().split(",")
                    for i in range(len(region_data)):
                        self.region_list[i].resource_quantity.append(
                            int(float(region_data[i]))
                        )
        except Exception as e:
            import traceback

            traceback.print_exc()
            raise e

    def _read_dropoff_matrix(self, file_name: str):
        try:
            with open(file_name, "r") as file:
                for line in file:
                    region_data = line.strip().split(",")
                    for i in range(len(region_data)):
                        self.region_list[i].destination_quantity.append(
                            int(float(region_data[i]))
                        )
        except Exception as e:
            import traceback

            traceback.print_exc()
            raise e

    def _read_intersection_resource_file(self, file_name: str):
        try:
            intersection_list = list(self.map.intersections.values())
            with open(file_name, "r") as file:
                for line in file:
                    region_data = line.strip().split(",")
                    for i in range(len(region_data)):
                        self.intersection_resource_map[intersection_list[i].id].append(
                            int(float(region_data[i]))
                        )
        except Exception as e:
            import traceback

            traceback.print_exc()
            raise e

    def _get_speed_factor(self, time: int) -> float:
        """
        Call this method to get the predicted speed factor of current time

        Args:
            time: current simulation time
        Returns:
            the predicted speed factor
        """
        index = self.temporal_utils.find_time_interval_index(time)
        return self.traffic_pattern_pred.get_speed_factor(index)

    def _get_travel_time_between_locations(
        self, source: LocationOnRoad, destination: LocationOnRoad, time: int
    ) -> int:
        travel_time = self.map.travel_time_between(source, destination)
        return int(travel_time / self._get_speed_factor(time))

    def _get_travel_time_between_intersections(
        self, source: Intersection, destination: Intersection, time: int
    ) -> int:
        travel_time = self.map.travel_time_between(source, destination)
        return int(travel_time / self._get_speed_factor(time))

    def _get_travel_time_between_location_intersection(
        self, source: LocationOnRoad, destination: Intersection, time: int
    ) -> int:
        travel_time = (
            self.map.travel_time_between(source.road.to, destination)
            + source.road.travel_time
            - source.get_static_travel_time_on_road()
        )
        return int(travel_time / self._get_speed_factor(time))

    def get_region(self, intersection: Intersection) -> Optional[Region]:
        """return the region of intersection"""
        hex_addr: str = self.h3.geo_to_h3(
            intersection.latitude, intersection.longitude, 8
        )
        return (
            self.region_list[self.hex_addr_to_region[hex_addr]]
            if hex_addr in self.hex_addr_to_region
            else None
        )

    def _driver_reposition(self, time: int):
        """Reposition all candidate agents together"""

        # Solve the minimum flow problem to get the optimal assignments
        agent_node_map: Dict[int, int] = {}
        region_node_map: Dict[Region, int] = {}
        node_agent_map: Dict[int, int] = {}
        node_region_map: Dict[int, Region] = {}
        agent_destinations: Dict[int, Set[Region]] = defaultdict(set)
        candidate_regions: Set[Region] = set()

        for agent in self.candidate_agents:
            regions = list(self.region_list)
            region_set: Set[Region] = set()
            rnd = self.agent_rnd.get(agent, random.Random(agent))

            while len(region_set) < GlobalParameters.N:
                region = self._sample_a_region(regions, time, rnd)
                region_set.add(region)
                candidate_regions.add(region)
                regions.remove(region)

            agent_destinations[agent] = region_set

        start_nodes: list[int] = []
        end_nodes: list[int] = []
        capacities: list[int] = []
        costs: list[int] = []
        source = 0
        sink = len(self.candidate_agents) + len(candidate_regions) + 1
        supplies = [0] * (sink + 1)

        k = 1
        for agent in self.candidate_agents:
            agent_node_map[agent] = k
            node_agent_map[k] = agent
            k += 1

        for region in candidate_regions:
            region_node_map[region] = k
            node_region_map[k] = region
            k += 1

        for agent in self.candidate_agents:
            start_nodes.append(source)
            end_nodes.append(agent_node_map[agent])
            capacities.append(1)
            costs.append(0)

        for agent in self.candidate_agents:
            for region in agent_destinations[agent]:
                start_nodes.append(agent_node_map[agent])
                end_nodes.append(region_node_map[region])
                capacities.append(1)
                costs.append(self._get_cost(agent, region, time))

        region_capacity_map: dict[Region, int] = self._calculate_regions_capacities(
            candidate_regions, len(self.candidate_agents), time
        )

        for region in candidate_regions:
            start_nodes.append(region_node_map[region])
            end_nodes.append(sink)
            capacities.append(region_capacity_map[region])
            costs.append(0)

        supplies[source] = len(self.candidate_agents)
        supplies[sink] = -len(self.candidate_agents)

        min_cost_flow = pywrapgraph.SimpleMinCostFlow()
        for i in range(len(start_nodes)):
            min_cost_flow.AddArcWithCapacityAndUnitCost(
                start_nodes[i], end_nodes[i], capacities[i], costs[i]
            )

        for i in range(len(supplies)):
            min_cost_flow.SetNodeSupply(i, supplies[i])

        if min_cost_flow.Solve() == min_cost_flow.OPTIMAL:
            for i in range(min_cost_flow.NumArcs()):
                if (
                    min_cost_flow.Tail(i) != source
                    and min_cost_flow.Head(i) != sink
                    and min_cost_flow.Flow(i) > 0
                ):
                    agent = node_agent_map[min_cost_flow.Tail(i)]
                    region = node_region_map[min_cost_flow.Head(i)]
                    self._guide_agent_to_region(agent, region, time)
                    self.agent_start_search_time[agent] = time

        self.candidate_agents.clear()

    def get_nearest_available_agent(
        self, resource: Resource, current_time: int
    ) -> Optional[int]:
        earliest = float("inf")
        best_agent = None

        for agent_id in self.available_agent:
            if agent_id not in self.agent_last_location:
                continue

            cur_loc: LocationOnRoad = self.get_current_location(
                self.agent_last_appear_time[agent_id],
                self.agent_last_location[agent_id],
                current_time,
            )
            # Warning: map.travel_time_between returns the travel time based on speed limits, not
            # the dynamic travel time. Thus, the travel time returned by map.travel_time_between may be different
            # from the actual travel time.
            travel_time = self._get_travel_time_between_locations(
                cur_loc, resource.pickup_loc, current_time
            )
            arrive_time = travel_time + current_time

            if arrive_time < earliest:
                best_agent = agent_id
                earliest = arrive_time

        return best_agent if earliest <= resource.expiration_time else None

    def _get_nearest_agent(
        self, resource: Resource, current_time: int
    ) -> Optional[int]:
        """Get the nearest agent for resource from all available agents and occupied agents"""
        available_earliest = float("inf")
        available_best_agent = None
        occupied_earliest = float("inf")
        occupied_best_agent = None

        # Check available agents
        for agent_id in self.available_agent:
            if agent_id not in self.agent_last_location:
                continue

            cur_loc: LocationOnRoad = self.get_current_location(
                self.agent_last_appear_time[agent_id],
                self.agent_last_location[agent_id],
                current_time,
            )

            travel_time = self._get_travel_time_between_locations(
                cur_loc, resource.pickup_loc, current_time
            )
            arrive_time = travel_time + current_time

            if arrive_time < available_earliest:
                available_best_agent = agent_id
                available_earliest = arrive_time

        # Check occupied agents
        for agent_id in self.occupied_agent:
            if agent_id not in self.agent_last_location:
                continue

            cur_loc: LocationOnRoad = self.get_current_location(
                self.agent_last_appear_time[agent_id],
                self.agent_last_location[agent_id],
                current_time,
            )

            assigned_resource = self.resource_assignment.get(agent_id)
            if assigned_resource:
                dropoff_time = self._get_travel_time_between_locations(
                    cur_loc, assigned_resource.dropoff_loc, current_time
                )
                approach_time = self._get_travel_time_between_locations(
                    assigned_resource.dropoff_loc,
                    resource.pickup_loc,
                    current_time + dropoff_time,
                )
                arrive_time = dropoff_time + approach_time + current_time

                if arrive_time < occupied_earliest:
                    occupied_best_agent = agent_id
                    occupied_earliest = arrive_time

        if (
            available_earliest <= occupied_earliest
            and available_earliest <= resource.expiration_time
        ):
            return available_best_agent
        elif (
            available_earliest > occupied_earliest
            and occupied_earliest <= resource.expiration_time
        ):
            self.assignment_for_occupied[occupied_best_agent] = resource
            self.occupied_agent.remove(occupied_best_agent)
            return None
        else:
            return None

    def _get_k_neighbor_regions(self, region: Region, k: int) -> List[Region]:
        k_regions = []
        neighbor_str = self.h3.k_ring(region.hex_addr, k)

        for addr in neighbor_str:
            if addr in self.hex_addr_to_region:
                k_regions.append(self.region_list[self.hex_addr_to_region[addr]])

        return k_regions

    def _sample_a_region(
        self, regions: List[Region], current_time: int, rnd: random.Random
    ) -> Region:
        """choose a region according to probability"""
        size = len(regions)
        weights: list[float] = []
        cumulative_probs: list[float] = []
        cumulative_weight = 0.0

        for region in regions:
            weight = self._get_region_weight(region, current_time)
            weights.append(weight)
            cumulative_weight += weight

        running_sum = 0.0
        for i in range(size):
            running_sum += weights[i]
            cumulative_probs.append(running_sum / cumulative_weight)

        index = self._sample_index(cumulative_probs, rnd)
        return regions[index]

    def _sample_by_distance(
        self,
        candidate_regions: Set[Region],
        current_location: LocationOnRoad,
        speed_factor: float,
        gamma: float,
        rnd: random.Random,
    ) -> Region:
        regions = list(candidate_regions)
        dist_array: list[float] = []
        cumulative_probs: list[float] = []
        sum_dist = 0.0

        for region in regions:
            dest = random.choice(region.intersection_list)
            dist = (
                self.map.travel_time_between(current_location.road.to, dest)
                / speed_factor
                / Configuration.TIME_RESOLUTION
                * len(region.available_agents)
            )
            weighted_dist = math.pow(dist, gamma)
            dist_array.append(weighted_dist)
            sum_dist += weighted_dist

        running_sum = 0.0
        for i in range(len(regions)):
            running_sum += dist_array[i]
            cumulative_probs.append(running_sum / sum_dist)

        index = self._sample_index(cumulative_probs, rnd)
        return regions[index]

    def _get_region_weight(self, region: Region, time: int) -> float:
        time_index = self.temporal_utils.find_time_interval_index(time)
        k = GlobalParameters.TIME_HORIZON // GlobalParameters.TIME_INTERVAL
        weight = 0.0

        for i in range(time_index, time_index + k):
            if i < len(region.resource_quantity):
                weight += math.pow(0.8, i - time_index) * (
                    region.resource_quantity[i]
                    - GlobalParameters.LAMBDA * region.destination_quantity[i]
                )

        return max(weight, 0.0)

    def _sample_index(self, cumulative_probs: List[float], rnd: random.Random) -> int:
        rand_val = rnd.random()
        index = bisect_left(cumulative_probs, rand_val)
        return index if index < len(cumulative_probs) else len(cumulative_probs) - 1

    def _get_cost(self, agent: int, region: Region, time: int) -> int:
        cur_loc = self.get_current_location(
            self.agent_last_appear_time[agent], self.agent_last_location[agent], time
        )
        destination = self._get_destination(region, time)
        travel_time = self._get_travel_time_between_location_intersection(
            cur_loc, destination, time
        )

        time_index = self.temporal_utils.find_time_interval_index(time)
        k = GlobalParameters.TIME_HORIZON // GlobalParameters.TIME_INTERVAL
        resource_num = 0

        for i in range(time_index, time_index + k):
            if i < len(region.resource_quantity):
                resource_num += region.resource_quantity[i]

        return float("inf") if resource_num == 0 else travel_time // resource_num

    def _calculate_regions_capacities(
        self, candidate_regions: Set[Region], num_agents: int, time: int
    ) -> Dict[Region, int]:
        region_capacity: Dict[Region, int] = {}
        sum_weight = 0.0

        for region in candidate_regions:
            weight = self._get_region_weight(region, time)
            sum_weight += weight

        for region in candidate_regions:
            weight = self._get_region_weight(region, time)
            capacity = round(weight / sum_weight * num_agents)
            region_capacity[region] = capacity

        return region_capacity

    def _guide_agent_to_region(self, agent: int, region: Region, time: int) -> None:
        cur_loc = self.get_current_location(
            self.agent_last_appear_time[agent], self.agent_last_location[agent], time
        )
        source_intersection = cur_loc.road.to
        destination_intersection = self._get_destination(region, time)

        if destination_intersection == source_intersection:
            # destination cannot be the source
            # if destination is the source, choose a neighbor to be the destination
            roads_from: list[Road] = list(source_intersection.roads_map_from.values())
            destination_intersection = roads_from[0].to

        shortest_path = self.map.shortest_travel_time_path(
            source_intersection, destination_intersection
        )
        shortest_path.popleft()
        self.agent_routes[agent] = shortest_path
        self.agent_start_search_time[agent] = time

    def _get_destination(self, region: Region, time: int) -> Intersection:
        best_intersection = region.intersection_list[0]
        intersection_agent_num: dict[Intersection, int] = {
            i: 0 for i in region.intersection_list
        }

        for agent in region.available_agents:
            cur_loc: LocationOnRoad = self.get_current_location(
                self.agent_last_appear_time[agent],
                self.agent_last_location[agent],
                time,
            )
            if cur_loc.road.to in intersection_agent_num:
                intersection_agent_num[cur_loc.road.to] += 1

        min_mismatch = float("inf")
        intersection_time_index = self.temporal_utils.get_intersection_temporal_index(
            time
        )
        resource_sum = sum(
            self.intersection_resource_map[i.id][intersection_time_index]
            for i in region.intersection_list
        )

        for intersection in region.intersection_list:
            agent_num = intersection_agent_num.get(intersection, 0)
            resource_num = self.intersection_resource_map[intersection.id][
                intersection_time_index
            ]

            if resource_sum == 0:
                mismatch = float("inf")
            else:
                mismatch = (
                    agent_num / len(region.available_agents)
                    - resource_num / resource_sum
                )

            if mismatch < min_mismatch:
                best_intersection = intersection
                min_mismatch = mismatch

        return best_intersection
