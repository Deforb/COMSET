from enum import Enum
from typing import Optional, TYPE_CHECKING

from comset.COMSETsystem.CityMap import CityMap
from comset.COMSETsystem.LocationOnRoad import LocationOnRoad
from comset.COMSETsystem.Resource import Resource
from comset.COMSETsystem.AgentAction import AgentAction
from comset.COMSETsystem.Intersection import Intersection

if TYPE_CHECKING:
    from TrafficPattern import TrafficPattern


class ResourceState(Enum):
    AVAILABLE = 1
    PICKED_UP = 2
    DROPPED_OFF = 3
    EXPIRED = 4


class FleetManager:
    """
    Abstract base class for fleet management in the COMSET system.
    """

    def __init__(self, map: CityMap) -> None:
        """
        Initialize the FleetManager with a city map.

        Args:
            map: The CityMap instance representing the city layout.
        """
        self.map = map
        self.traffic_pattern: Optional[TrafficPattern] = None

    def on_agent_introduced(
        self, agent_id: int, current_loc: LocationOnRoad, time: int
    ) -> None:
        """
        Called when a new agent is introduced to the system.

        Args:
            agent_id: Unique identifier for the agent.
            current_loc: The agent's current location on the road.
            time: The current simulation time.
        """
        raise NotImplementedError

    def on_resource_availability_change(
        self,
        resource: Resource,
        state: ResourceState,
        current_loc: LocationOnRoad,
        time: int,
    ) -> AgentAction:
        """
        Called when a resource's availability state changes.

        Args:
            resource: The resource whose state changed.
            state: The new state of the resource.
            current_loc: Current location of the agent (if applicable).
            time: The current simulation time.

        Returns:
            An AgentAction indicating what action the agent should take.
        """
        raise NotImplementedError

    def on_reach_intersection(
        self, agent_id: int, time: int, current_loc: LocationOnRoad
    ) -> Intersection:
        """
        Called when an agent reaches an intersection without a resource.

        Args:
            agent_id: Unique identifier for the agent.
            time: The current simulation time.
            current_loc: The agent's current location on the road.

        Returns:
            The next intersection the agent should move to.
        """
        raise NotImplementedError

    def on_reach_intersection_with_resource(
        self, agent_id: int, time: int, current_loc: LocationOnRoad, resource: Resource
    ) -> Intersection:
        """
        Called when an agent reaches an intersection while carrying a resource.

        Args:
            agent_id: Unique identifier for the agent.
            time: The current simulation time.
            current_loc: The agent's current location on the road.
            resource: The resource being carried by the agent.

        Returns:
            The next intersection the agent should move to.
        """
        raise NotImplementedError

    def get_current_location(
        self, last_appear_time: int, last_location: LocationOnRoad, current_time: int
    ) -> LocationOnRoad:
        """
        Calculate the current location of an agent based on movement over time.

        Args:
            last_appear_time: Time when the agent was last seen.
            last_location: Location where the agent was last seen.
            current_time: Current simulation time.

        Returns:
            The agent's current location on the road.
        """
        elapsed_time = current_time - last_appear_time
        return self.traffic_pattern.travel_road_for_time(
            last_appear_time, last_location, elapsed_time
        )
