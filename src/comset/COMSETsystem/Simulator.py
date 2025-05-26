from __future__ import annotations
import heapq
from typing import Dict, List, Optional, Set, TYPE_CHECKING

from tqdm import tqdm

from comset.DataParsing.MapWithData import MapWithData
from comset.COMSETsystem.AgentEvent import AgentEvent
from comset.COMSETsystem.ResourceEvent import ResourceEvent
from comset.COMSETsystem.ScoreInfo import ScoreInfo
from comset.COMSETsystem.LocationOnRoad import LocationOnRoad

if TYPE_CHECKING:
    from COMSETsystem.Configuration import Configuration
    from COMSETsystem.CityMap import CityMap
    from COMSETsystem.Event import Event
    from COMSETsystem.BaseAgent import BaseAgent
    from COMSETsystem.FleetManager import FleetManager
    from COMSETsystem.TrafficPattern import TrafficPattern


class Simulator:
    """
    The Simulator class defines the major steps of the simulation. It is
    responsible for loading the map, creating the necessary number of agents,
    creating a respective AgentEvent for each of them such that they are added
    to the events PriorityQueue. Furthermore, it is also responsible for dealing
    with the arrival of resources, map matching them to the map, and assigning
    them to agents. This produces the score according to the scoring rules.

    The time is simulated by the events having a variable time, this time
    corresponds to when something will be empty and thus needs some
    interaction (triggering). There's an event corresponding to every existent
    Agent and for every resource that hasn't arrived yet. All of this events are
    in a PriorityQueue called events which is ordered by their time in an
    increasing way.
    """

    class PickUp:
        """Helper class to track resource pickups"""

        def __init__(self, resource: ResourceEvent, time: int):
            self.resource = resource
            self.time = time

        def get_resource(self) -> ResourceEvent:
            return self.resource

        def get_time(self) -> int:
            return self.time

    def __init__(self, config: Configuration):
        """
        Constructor of the class Main. This is made such that the type of
        agent/resourceAnalyzer used is not hardcoded and the users can choose
        whichever they want.
        """
        self.configuration: Configuration = config
        self.map: Optional[CityMap] = None

        # A deep copy of map to be passed to agents.
        # This is a way to make map unmodifiable.
        self.map_for_agents: Optional[CityMap] = None
        self.events: List[Event] = []
        self.empty_agents: Set[AgentEvent] = set()
        self.serving_agents: Set[AgentEvent] = set()
        self.simulation_start_time: int = 0
        self.simulation_time: int = 0
        self.simulation_end_time: int = 0
        self.score: Optional[ScoreInfo] = None

        # A list of all the agents in the system. Not really used in COMSET, but maintained for
        # a user's debugging purposes.
        self.agents: List[BaseAgent] = []
        self.fleet_manager: Optional[FleetManager] = None
        self.traffic_pattern: Optional[TrafficPattern] = None
        self.agent_map: Dict[int, AgentEvent] = {}
        self.res_map: Dict[int, ResourceEvent] = {}
        self.configure()

    def configure(self) -> None:
        """
        Configure the simulation system including:

            1. Create a map from the map file and the bounding polygon KML file.
            2. Load the resource data set and map match.
            3. Create the event queue.

        See COMSETsystem.Configuration and Main.java for detailed description of the parameters.
        """
        self.map = self.configuration.map

        # Make a map copy for agents to use so that an agent cannot modify the map used by the simulator
        self.map_for_agents = self.map.make_copy()

        map_wd = MapWithData(
            self.map,
            self.configuration.resource_file,
            self.configuration.agent_placement_seed,
        )

        print("Loading and map-matching resources...")
        self.fleet_manager = self.create_fleet_manager()

        # The simulation end time is the expiration time of the last resource.
        # which is return by createMapWithData
        self.simulation_end_time = map_wd.create_map_with_data(
            self.configuration, self, self.fleet_manager
        )

        self.traffic_pattern = map_wd.get_traffic_pattern(
            self.configuration.traffic_pattern_epoch,
            self.configuration.traffic_pattern_step,
            self.configuration.dynamic_traffic_enabled,
        )
        if self.fleet_manager and self.traffic_pattern:
            self.fleet_manager.traffic_pattern = self.traffic_pattern

        # Deploy agents at random locations of the map.
        print(
            f"Randomly placing {self.configuration.number_of_agents} agents on the map..."
        )
        map_wd.place_agents_randomly(
            self, self.fleet_manager, self.configuration.number_of_agents
        )

        # Initialize the event queue.
        self.events = map_wd.get_events()
        # heapq.heapify(self.events)

        self.mapping_event_id()

    def run(self) -> None:
        """
        This method corresponds to running the simulation. An object of ScoreInfo
        is created in order to keep track of performance in the current
        simulation. Go through every event until the simulation is over.
        """

        print("Running the simulation...")

        self.score = ScoreInfo(self.configuration, self)
        if self.map is None:
            print("Map is null at beginning of run")

        try:
            initial_time = heapq.nsmallest(1, self.events, key=lambda e: e.time)[
                0
            ].time  # TODO: events[0].time
            self.simulation_start_time = self.simulation_time = initial_time
            total_simulation_time = (
                self.simulation_end_time - self.simulation_start_time
            )
            assert total_simulation_time > 0, "total_simulation_time is less than 0"
            print(f"总模拟时间: {total_simulation_time}")

            with tqdm(total=100, desc="Progress", mininterval=1, unit="event") as pbar:
                while self.events:
                    event = heapq.heappop(self.events)
                    assert event is not None, "event is None"
                    next_time = event.time
                    assert next_time >= self.simulation_time, (
                        "event.time is less than simulation_time"
                    )
                    self.simulation_time = next_time

                    # Extend total simulation time for agent which is still delivering resource
                    total_simulation_time = max(
                        total_simulation_time,
                        self.simulation_time - self.simulation_start_time,
                    )

                    # Update progress bar
                    progress = min(
                        (next_time - self.simulation_start_time)
                        / total_simulation_time
                        * 100,
                        100,
                    )
                    pbar.update(progress - pbar.n)

                    if (
                        self.simulation_time <= self.simulation_end_time
                        or len(self.serving_agents) > 0
                    ):
                        try:
                            new_event = event.trigger()
                            if new_event:
                                self.add_event(new_event)
                        except Exception as e:
                            print(f"事件{event}触发失败: {str(e)}")
                            raise e

        except Exception as e:
            import traceback

            traceback.print_exc()
            print(f"Simulation aborted due to error: {str(e)}")

        print("Simulation finished.")

        if self.score:
            self.score.end()

    def has_event(self, event: Event) -> bool:
        """Check if event exists in queue"""
        return event in self.events

    def add_event(self, event: Event) -> None:
        """Add an event to the queue"""
        if event.time < self.simulation_time:
            raise ValueError("Event time in the past")
        heapq.heappush(self.events, event)

    def remove_event(self, event: Event) -> None:
        """Remove an event from the queue"""
        self.events.remove(event)
        heapq.heapify(self.events)

    def mark_agent_empty(self, agent: AgentEvent) -> None:
        """
        Mark an agent as available.

        Args:
            agent: Add this agent to the set of empty agents.
        """
        if agent in self.serving_agents:
            self.serving_agents.remove(agent)
        self.empty_agents.add(agent)

    def mark_agent_serving(self, agent: AgentEvent) -> None:
        """
        Mark an agent as busy.

        Args:
            agent Add this agent to the set of serving agents. A serving has been assigned a resource and is either
                       on its way to pickup or drop off.
        """
        if agent in self.empty_agents:
            self.empty_agents.remove(agent)
        self.serving_agents.add(agent)

    def agent_copy(self, location: LocationOnRoad) -> LocationOnRoad:
        """
        Make an agent copy of locationOnRoad so that an agent cannot modify the attributes of the road.

        Args:
            locationOnRoad the location to make a copy for
        Return:
            an agent copy of the location
        """
        from_inter = self.map_for_agents.intersections[location.road.from_.id]
        to_inter = self.map_for_agents.intersections[location.road.to.id]
        road_copy = from_inter.roads_map_from[to_inter]
        return LocationOnRoad.copy_with_replaced_road(road_copy, location)

    def create_fleet_manager(self) -> FleetManager:
        """Dynamically create FleetManager instance"""
        try:
            return self.configuration.fleet_manager_class(self.map_for_agents)
        except (ImportError, AttributeError) as e:
            raise RuntimeError(f"Failed to create FleetManager: {str(e)}")

    def mapping_event_id(self) -> None:
        """Map event IDs to their respective events"""
        for event in self.events:
            if isinstance(event, AgentEvent):
                self.agent_map[event.id] = event
            elif isinstance(event, ResourceEvent):
                self.res_map[event.id] = event
