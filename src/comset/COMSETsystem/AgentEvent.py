from __future__ import annotations
import logging
from enum import Enum
from typing import Optional, TYPE_CHECKING, override

from comset.COMSETsystem.AgentAction import AgentAction
from comset.COMSETsystem.Event import Event
from comset.COMSETsystem.LocationOnRoad import LocationOnRoad
from comset.COMSETsystem.FleetManager import ResourceState

if TYPE_CHECKING:
    from Simulator import Simulator
    from FleetManager import FleetManager
    from ResourceEvent import ResourceEvent


logger = logging.getLogger(__name__)


class AgentEvent(Event):
    """
    The AgentEvent class represents a moment an agent is going to perform an
    action in the simulation, such as becoming empty and picking up a
    resource, or driving to some other Intersection.

    An AgentEvent is triggered in either of the following cases:

    1. The agent reaches an intersection.
    2. The agent drops off a resource.

    In the case that the agent reaches an intersection, the AgentEvent invokes agent.next_intersection()
    to let the agent determine which of the neighboring intersections to go to. The AgentEvent is triggered
    again when the agent reaches the next intersection, and so on. This is how the agent's search route
    is executed. The searching ends when the agent is assigned to a resource, in which case the AgentEvent
    is set to be triggered at the time when the agent drops off the resource to its destination.

    In the case that the agent drops off a resource, the AgentEvent checks if there are waiting resources. If so,
    the AgentEvent assigns the agent to the closest waiting resource if the travel time from the agent's current location
    to the resource is smaller than the resource's remaining life time. Otherwise the AgentEvent moves the agent to
    the end intersection of the current road.
    """

    class State(Enum):
        INITIAL = 1
        INTERSECTION_REACHED = 2
        PICKING_UP = 3
        DROPPING_OFF = 4

    def __init__(
        self,
        loc: LocationOnRoad,
        started_search: int,
        simulator: Simulator,
        fleet_manager: FleetManager,
    ) -> None:
        """
        Constructor for class AgentEvent.

        :param loc: this agent's location when it becomes empty.
        """
        super().__init__(started_search, simulator, fleet_manager)
        self.loc: LocationOnRoad = loc
        self.is_pickup: bool = False
        self.state: AgentEvent.State = AgentEvent.State.INITIAL
        self.start_search_time: int = started_search
        self.assigned_resource: Optional[ResourceEvent] = None
        self.assign_time: int = 0
        self.assign_location: Optional[LocationOnRoad] = None
        self.last_appear_time: int = started_search
        self.last_appear_location: LocationOnRoad = loc

    @override
    def trigger(self) -> AgentEvent:
        logger.info(f"******** AgentEvent id = {self.id} triggered at time {self.time}")
        logger.info(f"Loc = {self.loc}")

        match self.state:
            case AgentEvent.State.INITIAL:
                self._navigate_to_nearest_intersection()
            case AgentEvent.State.INTERSECTION_REACHED:
                self._navigate()
            case AgentEvent.State.PICKING_UP:
                if self.assigned_resource is None:
                    self._move_to_end_intersection()
                else:
                    self._pickup()
            case AgentEvent.State.DROPPING_OFF:
                self._drop_off()

        return self

    def has_res_pickup(self) -> bool:
        return self.is_pickup

    def assign_to(self, resource_event: ResourceEvent, assign_time: int) -> None:
        elapsed_time = assign_time - self.last_appear_time
        current_location = self.simulator.traffic_pattern.travel_road_for_time(
            self.last_appear_time, self.last_appear_location, elapsed_time
        )
        self.assign_location = current_location
        self.assign_time = assign_time
        self._assign_resource(resource_event)

        if self._is_on_same_road(
            self.loc, self.assigned_resource.pickup_loc
        ) and current_location.upstream_to(self.assigned_resource.pickup_loc):
            next_event_time = (
                assign_time
                + self.simulator.traffic_pattern.road_forward_travel_time(
                    assign_time, current_location, self.assigned_resource.pickup_loc
                )
            )
            self.simulator.remove_event(self)
            self._update(
                next_event_time,
                self.assigned_resource.pickup_loc,
                AgentEvent.State.PICKING_UP,
                assign_time,
                current_location,
            )
            self.simulator.add_event(self)

    def abort_resource(self) -> None:
        # Since we were on the event queue, we need to remove ourselves before rescheduling ourselves.
        self.simulator.remove_event(self)
        self._unassign_resource()
        self.is_pickup = False
        if self.state == AgentEvent.State.PICKING_UP:
            self._move_to_end_intersection()
        self.simulator.add_event(self)

    def _navigate(self) -> None:
        assert self.loc.at_end_intersection(), "Agent not at an intersection."

        if self._is_arriving_pickup_loc():
            travel_time = self.fleet_manager.traffic_pattern.road_travel_time_from_start_intersection(
                self.time, self.assigned_resource.pickup_loc
            )
            next_event_time = self.time + travel_time
            self._update(
                next_event_time,
                self.assigned_resource.pickup_loc,
                AgentEvent.State.PICKING_UP,
                self.time,
                self.loc,
            )
            return

        if self._is_arriving_drop_off_loc():
            travel_time = self.fleet_manager.traffic_pattern.road_travel_time_from_start_intersection(
                self.time, self.assigned_resource.dropoff_loc
            )
            next_event_time = self.time + travel_time
            self._update(
                next_event_time,
                self.assigned_resource.dropoff_loc,
                AgentEvent.State.DROPPING_OFF,
                self.time,
                self.loc,
            )
            return

        if self.is_pickup and self.assigned_resource is not None:
            next_intersection = self.fleet_manager.on_reach_intersection_with_resource(
                self.id,
                self.time,
                self.simulator.agent_copy(self.loc),
                self.assigned_resource.copy_resource(),
            )
        else:
            next_intersection = self.fleet_manager.on_reach_intersection(
                self.id, self.time, self.simulator.agent_copy(self.loc)
            )

        if next_intersection is None:
            raise Exception("FleetManager did not return a next location")
        if not self.loc.road.to.is_adjacent(next_intersection):
            raise Exception("move not made to an adjacent location")

        # set location and time of the next trigger
        next_road = self.loc.road.to.road_to(next_intersection)
        next_location = LocationOnRoad.create_from_road_end(next_road)
        travel_time = (
            self.fleet_manager.traffic_pattern.road_travel_time_from_start_intersection(
                self.time, next_location
            )
        )
        self._update(
            self.time + travel_time,
            next_location,
            AgentEvent.State.INTERSECTION_REACHED,
            self.time,
            LocationOnRoad.create_from_road_start(next_road),
        )

        logger.info(f"Move to {next_road.to}")
        logger.info(f"Next trigger time = {self.time}")

    def _navigate_to_nearest_intersection(self) -> None:
        self.start_search_time = self.time
        self.fleet_manager.on_agent_introduced(
            self.id, self.simulator.agent_copy(self.loc), self.time
        )
        self._move_to_end_intersection()

    def _is_arriving_pickup_loc(self) -> bool:
        return (
            not self.is_pickup
            and self.assigned_resource is not None
            and self.assigned_resource.pickup_loc.road.from_ == self.loc.road.to
        )

    def _is_arriving_drop_off_loc(self) -> bool:
        return (
            self.is_pickup
            and self.assigned_resource is not None
            and self.assigned_resource.dropoff_loc.road.from_ == self.loc.road.to
        )

    def _pickup(self) -> None:
        """The handler of a pickup event."""
        logger.info(f"Pickup at {self.loc}")

        self.is_pickup = True
        static_approach_time = self.simulator.map.travel_time_between(
            self.assign_location, self.loc
        )

        self.simulator.score.record_approach_time(
            self.time,
            self.start_search_time,
            self.assign_time,
            self.assigned_resource.available_time,
            static_approach_time,
        )

        self.assigned_resource.pickup(self.time)
        action = self.fleet_manager.on_resource_availability_change(
            self.assigned_resource.copy_resource(),
            ResourceState.PICKED_UP,
            self.simulator.agent_copy(self.loc),
            self.time,
        )

        if self._is_valid_assignment_action(action):
            resource_event = self.simulator.res_map.get(action.res_id)
            agent_event = self.simulator.agent_map.get(action.agent_id)
            agent_event.assign_to(resource_event, self.time)
            resource_event.assign_to(agent_event)

        if self._is_on_same_road(
            self.assigned_resource.dropoff_loc, self.loc
        ) and self.loc.upstream_to(self.assigned_resource.dropoff_loc):
            travel_time = self.fleet_manager.traffic_pattern.road_forward_travel_time(
                self.time, self.loc, self.assigned_resource.dropoff_loc
            )
            next_event_time = self.time + travel_time
            self._update(
                next_event_time,
                self.assigned_resource.dropoff_loc,
                AgentEvent.State.DROPPING_OFF,
                self.time,
                self.loc,
            )
        else:
            self._move_to_end_intersection()

    def _drop_off(self) -> None:
        """The handler of a drop-off event."""
        self.start_search_time = self.time
        logger.info(f"Dropoff at {self.loc}")
        self.is_pickup = False
        self.assigned_resource.drop_off(self.time)

        action = self.fleet_manager.on_resource_availability_change(
            self.assigned_resource.copy_resource(),
            ResourceState.DROPPED_OFF,
            self.simulator.agent_copy(self.loc),
            self.time,
        )

        # 先清理当前资源
        self._unassign_resource()

        if not self._is_valid_assignment_action(action):
            self._move_to_end_intersection()
            return

        resource_event = self.simulator.res_map.get(action.res_id)
        if action.agent_id == self.id:
            self._assign_resource(resource_event)
            self.assigned_resource.assign_to(self)
            self.assign_time = self.time
            self.assign_location = self.loc

            if self._is_on_same_road(
                self.loc, self.assigned_resource.pickup_loc
            ) and self.loc.upstream_to(self.assigned_resource.pickup_loc):
                # Reach resource pickup location before reach the end intersection
                travel_time = (
                    self.fleet_manager.traffic_pattern.road_forward_travel_time(
                        self.time, self.loc, self.assigned_resource.pickup_loc
                    )
                )
                next_event_time = self.time + travel_time
                self._update(
                    next_event_time,
                    self.assigned_resource.pickup_loc,
                    AgentEvent.State.PICKING_UP,
                    self.time,
                    self.loc,
                )
            else:
                self._move_to_end_intersection()
        else:
            agent_event = self.simulator.agent_map.get(action.agent_id)
            agent_event.assign_to(resource_event, self.time)
            resource_event.assign_to(agent_event)
            self._move_to_end_intersection()

    def _move_to_end_intersection(self) -> None:
        travel_time = (
            self.fleet_manager.traffic_pattern.road_travel_time_to_end_intersection(
                self.time, self.loc
            )
        )
        next_event_time = self.time + travel_time
        next_loc = LocationOnRoad.create_from_road_end(self.loc.road)
        self._update(
            next_event_time,
            next_loc,
            AgentEvent.State.INTERSECTION_REACHED,
            self.time,
            self.loc,
        )

    def _update(
        self,
        time: int,
        loc: LocationOnRoad,
        state: State,
        last_appear_time: int,
        last_appear_location: LocationOnRoad,
    ) -> None:
        assert (
            time >= self.simulator.simulation_time
        ), "trying to update event to the past time"
        self.time = time
        self.loc = loc
        self.state = state
        self.last_appear_time = last_appear_time
        self.last_appear_location = last_appear_location

    def _is_valid_assignment_action(self, agent_action: Optional[AgentAction]) -> bool:
        if agent_action is None:
            return False

        agent_event = self.simulator.agent_map.get(agent_action.agent_id)
        res_event = self.simulator.res_map.get(agent_action.res_id)

        return (
            agent_event is not None
            and res_event is not None
            and not agent_event.has_res_pickup()
            and agent_action.get_type() == AgentAction.Type.ASSIGN
        )

    def _is_on_same_road(self, loc1: LocationOnRoad, loc2: LocationOnRoad) -> bool:
        return loc1.road == loc2.road

    def _assign_resource(self, resource_event: ResourceEvent) -> None:
        assert self.assigned_resource is None
        self.assigned_resource = resource_event
        self.simulator.mark_agent_serving(self)

    def _unassign_resource(self) -> None:
        assert self.assigned_resource is not None
        self.assigned_resource = None
        self.simulator.mark_agent_empty(self)
