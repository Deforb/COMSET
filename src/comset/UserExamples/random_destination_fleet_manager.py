from __future__ import annotations
from collections import deque
from random import Random
from typing import Optional, Set, Dict, Deque, TYPE_CHECKING, override

from comset.COMSETsystem.FleetManager import FleetManager, ResourceState
from comset.COMSETsystem.AgentAction import AgentAction
from comset.COMSETsystem.LocationOnRoad import LocationOnRoad

if TYPE_CHECKING:
    from COMSETsystem.CityMap import CityMap
    from COMSETsystem.Resource import Resource
    from COMSETsystem.Intersection import Intersection


class RandomDestinationFleetManager(FleetManager):
    """
    A fleet manager that assigns agents to resources based on proximity and plans random cruising routes.
    """

    def __init__(self, city_map: CityMap) -> None:
        super().__init__(city_map)
        self.agent_last_appear_time: Dict[int, int] = {}
        self.agent_last_location: Dict[int, LocationOnRoad] = {}
        self.resource_assignment: Dict[int, Resource] = {}
        self.waiting_resources: Dict[int, Resource] = {}  # key: resource.id
        self.available_agent: Set[int] = set()
        self.agent_rnd: Dict[int, Random] = {}
        self.agent_routes: Dict[int, Deque[Intersection]] = {}

    @override
    def on_agent_introduced(
        self, agent_id: int, current_loc: LocationOnRoad, time: int
    ) -> None:
        """
        Notifies the fleet manager that a new agent has been introduced.

        Args:
            agent_id: Unique identifier for the agent.
            current_loc: The agent's current location.
            time: Current simulation time.
        """
        self.agent_last_appear_time[agent_id] = time
        self.agent_last_location[agent_id] = current_loc
        self.available_agent.add(agent_id)

    @override
    def on_resource_availability_change(
        self,
        resource: Resource,
        state: ResourceState,
        current_loc: LocationOnRoad,
        time: int,
    ) -> AgentAction:
        """
        Handles changes in resource availability and assigns agents accordingly.

        Args:
            resource: The resource whose state has changed.
            state: New state of the resource.
            current_loc: Current location of the resource.
            time: Current simulation time.

        Returns:
            AgentAction indicating the action to be taken.
        """
        action = AgentAction.do_nothing()

        if state == ResourceState.AVAILABLE:
            assigned_agent = self.get_nearest_available_agent(resource, time)
            if assigned_agent is not None:
                self.resource_assignment[assigned_agent] = resource
                self.agent_routes[assigned_agent] = deque()
                self.available_agent.discard(assigned_agent)
                action = AgentAction.assign_to(assigned_agent, resource.id)
            else:
                self.waiting_resources[resource.id] = resource
        elif state == ResourceState.DROPPED_OFF:
            best_resource = None
            earliest_arrival = float("inf")
            for res in sorted(self.waiting_resources.values(), key=lambda r: r.id):
                travel_time = self.map.travel_time_between(current_loc, res.pickup_loc)
                arrive_time = time + travel_time
                if (
                    arrive_time <= res.expiration_time
                    and arrive_time < earliest_arrival
                ):
                    earliest_arrival = arrive_time
                    best_resource = res

            if best_resource:
                del self.waiting_resources[best_resource.id]
                action = AgentAction.assign_to(
                    resource.assigned_agent_id, best_resource.id
                )
            else:
                self.available_agent.add(resource.assigned_agent_id)
                action = AgentAction.do_nothing()
            self.resource_assignment[resource.assigned_agent_id] = best_resource
            self.agent_last_location[resource.assigned_agent_id] = current_loc
            self.agent_last_appear_time[resource.assigned_agent_id] = time
        elif state == ResourceState.EXPIRED:
            if resource.id in self.waiting_resources:
                del self.waiting_resources[resource.id]
            if resource.assigned_agent_id != -1:
                self.agent_routes[resource.assigned_agent_id] = deque()
                self.available_agent.add(resource.assigned_agent_id)
                if resource.assigned_agent_id in self.resource_assignment:
                    del self.resource_assignment[resource.assigned_agent_id]
        elif state == ResourceState.PICKED_UP:
            self.agent_routes[resource.assigned_agent_id] = deque()

        return action

    @override
    def on_reach_intersection(
        self, agent_id: int, time: int, current_loc: LocationOnRoad
    ) -> Intersection:
        """
        Plans cruising route for an agent reaching an intersection.

        Args:
            agent_id: Unique identifier for the agent.
            time: Current simulation time.
            current_loc: Agent's current location.

        Returns:
            Next target intersection.
        """
        if agent_id == 240902 and time == 1464800008:
            print("here")

        self.agent_last_appear_time[agent_id] = time
        route = self.agent_routes.get(agent_id, deque())

        if not route:
            route = self.plan_route(agent_id, current_loc)
            self.agent_routes[agent_id] = route

        next_intersection = route.popleft()
        next_road = current_loc.road.to.road_to(next_intersection)
        new_location = LocationOnRoad.create_from_road_start(next_road)
        self.agent_last_location[agent_id] = new_location
        return next_intersection

    @override
    def on_reach_intersection_with_resource(
        self, agent_id: int, time: int, current_loc: LocationOnRoad, resource: Resource
    ) -> Intersection:
        """
        Plans route for an agent carrying a resource.

        Args:
            agent_id: Unique identifier for the agent.
            time: Current simulation time.
            current_loc: Agent's current location.
            resource: Resource being carried.

        Returns:
            Next target intersection.
        """
        self.agent_last_appear_time[agent_id] = time
        route = self.agent_routes.get(agent_id, deque())

        if not route:
            route = self.plan_route_to_target(resource.pickup_loc, resource.dropoff_Loc)
            self.agent_routes[agent_id] = route

        next_intersection = route.popleft()
        next_road = current_loc.road.to.road_to(next_intersection)
        new_location = LocationOnRoad.create_from_road_start(next_road)
        self.agent_last_location[agent_id] = new_location
        return next_intersection

    def get_nearest_available_agent(
        self, resource: Resource, current_time: int
    ) -> Optional[int]:
        """
        Finds the nearest available agent to a resource.

        Args:
            resource: Target resource.
            current_time: Current simulation time.

        Returns:
            ID of the nearest agent or None if none available.
        """
        earliest_arrival = float("inf")
        best_agent = None

        for agent_id in sorted(self.available_agent):
            if agent_id not in self.agent_last_location:
                continue

            last_time = self.agent_last_appear_time[agent_id]
            last_loc = self.agent_last_location[agent_id]
            cur_loc = self.get_current_location(last_time, last_loc, current_time)
            travel_time = self.map.travel_time_between(cur_loc, resource.pickup_loc)
            arrive_time = current_time + travel_time

            if arrive_time < earliest_arrival:
                earliest_arrival = arrive_time
                best_agent = agent_id

        return best_agent if earliest_arrival <= resource.expiration_time else None

    def plan_route(
        self, agent_id: int, current_location: LocationOnRoad
    ) -> Deque[Intersection]:
        """
        Plans route for an agent, either to assigned resource or random destination.

        Args:
            agent_id: Unique identifier for the agent.
            current_location: Agent's current location.

        Returns:
            Planned route as a deque of intersections.
        """
        if assigned_res := self.resource_assignment.get(agent_id):
            source = current_location.road.to
            dest = assigned_res.pickup_loc.road.from_
            path = self.map.shortest_travel_time_path(source, dest)
            if path:
                path.popleft()
            return path
        else:
            return self.get_random_route(agent_id, current_location)

    def plan_route_to_target(
        self, source_loc: LocationOnRoad, dest_loc: LocationOnRoad
    ) -> Deque[Intersection]:
        """
        Plans route between two locations.

        Args:
            source_loc: Starting location.
            dest_loc: Target location.

        Returns:
            Planned route as a deque of intersections.
        """
        source = source_loc.road.to
        dest = dest_loc.road.from_
        path = self.map.shortest_travel_time_path(source, dest)
        if path:
            path.popleft()
        return path

    def get_random_route(
        self, agent_id: int, current_location: LocationOnRoad
    ) -> Deque[Intersection]:
        """
        Generates a random cruising route for an agent.

        Args:
            agent_id: Unique identifier for the agent.
            current_location: Agent's current location.

        Returns:
            Randomly generated route.
        """
        rnd = self.agent_rnd.get(agent_id)
        if not rnd:
            rnd = Random(agent_id)
            self.agent_rnd[agent_id] = rnd

        source = current_location.road.to
        intersections = list(self.map.intersections.values())
        dest = rnd.choice(intersections)

        if dest == source:
            roads = list(source.roads_map_from.values())
            if roads:
                dest = roads[0].to
            else:
                return deque()

        path = self.map.shortest_travel_time_path(source, dest)
        if path:
            path.popleft()
        return path
