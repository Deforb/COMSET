from __future__ import annotations
from enum import Enum, auto
import logging
from typing import Optional, override, TYPE_CHECKING

from comset.COMSETsystem.Event import Event
from comset.COMSETsystem.FleetManager import ResourceState
from comset.COMSETsystem.Resource import Resource

if TYPE_CHECKING:
    from COMSETsystem.Simulator import Simulator
    from COMSETsystem.FleetManager import FleetManager
    from COMSETsystem.AgentAction import AgentAction
    from COMSETsystem.LocationOnRoad import LocationOnRoad
    from COMSETsystem.AgentEvent import AgentEvent


logger = logging.getLogger(__name__)


class ResourceEvent(Event):
    """
    The ResourceEvent class represents the moment a resource becomes available or expired in
    the simulation. Therefore, there are two cases in which a ResourceEvent object is triggered:

    1. When the resource is introduced to the system and becomes available. In this case, the
    resource is assigned (if there are agents available and within reach) to an agent.
    2. When the resource gets expired.
    """

    class State(Enum):
        AVAILABLE = auto()
        EXPIRED = auto()

    def __init__(
        self,
        pickup_loc: LocationOnRoad,
        dropoff_loc: LocationOnRoad,
        available_time: int,
        static_trip_time: int,
        simulator: Simulator,
        fleet_manager: FleetManager,
        resource_maximum_life_time: int,
    ):
        """
        Constructor for class ResourceEvent.

        :param available_time: time when this agent is introduced to the system
        :param pickup_loc: this resource's location when it becomes available
        :param dropoff_loc: this resource's destination location
        :param simulator: the simulator object
        :param fleet_manager: the fleet manager object
        :param resource_maximum_life_time: time interval that resource waits and expires after that
        """
        super().__init__(available_time, simulator, fleet_manager)
        self.pickup_loc: LocationOnRoad = pickup_loc
        self.dropoff_loc: LocationOnRoad = dropoff_loc
        self.available_time: int = available_time
        self.expiration_time: int = available_time + resource_maximum_life_time
        self.static_trip_time: int = static_trip_time
        self.pickup_time: int = -1
        self.state: ResourceEvent.State = ResourceEvent.State.AVAILABLE
        self.agent_event: Optional[AgentEvent] = None

    @classmethod
    def for_testing(
        cls,
        pickup_loc: LocationOnRoad,
        dropoff_loc: LocationOnRoad,
        available_time: int,
        static_trip_time: int,
        resource_maximum_life_time: int,
    ) -> ResourceEvent:
        """
        Constructor for ResourceEvent that overrides tripTime. Makes it easier to test.

        :param available_time: time when this agent is introduced to the system
        :param pickup_loc: this resource's location when it becomes available
        :param dropoff_loc: this resource's destination location
        :param static_trip_time: the time it takes to go from pickUpLoc to dropoffLoc under static traffic condition
        :param resource_maximum_life_time: time interval that resource waits and expires after that
        """
        instance = cls.__new__(cls)
        super(ResourceEvent, instance).__init__(available_time)
        instance.pickup_loc = pickup_loc
        instance.dropoff_loc = dropoff_loc
        instance.available_time = available_time
        instance.expiration_time = available_time + resource_maximum_life_time
        instance.static_trip_time = static_trip_time
        instance.pickup_time = -1
        instance.state = ResourceEvent.State.AVAILABLE
        instance.agent_event = None
        return instance

    @override
    def trigger(self) -> Optional[Event]:
        """
        Whenever a resource arrives/becomes available an event corresponding to
        it gets triggered. When it triggers it checks for all the active agents
        which agent can get to the resource the fastest. The closest agent is
        saved in the variable bestAgent. If there are no active agents or no
        agent can get in time to the resource, the current resource gets added to
        waitingResources such that once an agent gets available it will check if
        it can get to the resource in time. Furthermore, calculate the score of
        this assignment according to the scoring rules. Also remove the assigned
        agent from the PriorityQueue and from activeAgents.
        """
        logger.info(
            f"******** ResourceEvent id = {self.id} triggered at time {self.time}",
        )
        print(
            f"******** ResourceEvent id = {self.id} triggered at time {self.time}",
        )
        logger.info("Loc = %s,%s", self.pickup_loc, self.dropoff_loc)

        if self.pickup_loc is None:
            print("intersection is null")

        if self.state == ResourceEvent.State.AVAILABLE:
            self._available()
            return self
        else:
            self._expire()
            return None

    def assign_to(self, event: AgentEvent) -> None:
        """Assign this resource event to an agent event."""
        self.agent_event = event

    def copy_resource(self) -> Resource:
        """Create a copy of the resource."""
        agent_id = -1 if self.agent_event is None else self.agent_event.id
        pickup_copy = self.simulator.agent_copy(self.pickup_loc)
        dropoff_copy = self.simulator.agent_copy(self.dropoff_loc)
        return Resource(
            self.id, self.expiration_time, agent_id, pickup_copy, dropoff_copy
        )

    def pickup(self, pickup_time: int) -> None:
        """Record pickup time and remove event from simulator."""
        self.pickup_time = pickup_time
        self.simulator.remove_event(self)

    def is_picked_up(self) -> bool:
        """Check if the resource has been picked up."""
        return self.pickup_time > 0

    def drop_off(self, drop_off_time: int) -> None:
        """Record completed trip in simulator score."""
        static_trip_time = self.simulator.map.travel_time_between(
            self.pickup_loc, self.dropoff_loc
        )
        self.simulator.score.record_completed_trip(
            drop_off_time, self.pickup_time, static_trip_time
        )

    def _available(self) -> None:
        """Handle resource becoming available."""
        self.simulator.score.total_resources += 1

        action = self.fleet_manager.on_resource_availability_change(
            self.copy_resource(),
            ResourceState.AVAILABLE,
            self.simulator.agent_copy(self.pickup_loc),
            self.time,
        )
        self._process_agent_action(action)
        self.time = self.expiration_time
        self.state = ResourceEvent.State.EXPIRED

    def _expire(self) -> None:
        """Handle resource expiration."""
        assert not self.is_picked_up(), "Resource expiring after having been picked up"

        action = self.fleet_manager.on_resource_availability_change(
            self.copy_resource(),
            ResourceState.EXPIRED,
            self.simulator.agent_copy(self.pickup_loc),
            self.time,
        )
        self._process_agent_action(action)
        if self.agent_event is not None:
            # We're assigned but hasn't been picked up, so the trip is being aborted.
            self.agent_event.abort_resource()
            self.simulator.score.record_abortion()

        self.simulator.score.record_expiration()
        logger.info("Expired.")

    def _process_agent_action(self, agent_action: Optional[AgentAction]) -> None:
        """Process agent assignment action from fleet manager."""
        if agent_action is None:
            return

        agent_event = self.simulator.agent_map.get(agent_action.agent_id)
        resource_event = self.simulator.res_map.get(agent_action.res_id)

        if agent_event and resource_event and not agent_event.has_res_pickup():
            agent_event.assign_to(resource_event, self.time)
            resource_event.assign_to(agent_event)
