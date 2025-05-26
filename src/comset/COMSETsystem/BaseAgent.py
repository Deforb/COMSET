from abc import ABC, abstractmethod

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from comset.COMSETsystem.CityMap import CityMap
    from comset.COMSETsystem.LocationOnRoad import LocationOnRoad
    from comset.COMSETsystem.Intersection import Intersection


class BaseAgent(ABC):
    """
    The BaseAgent class is the class the participants should extend in order to create an Agent that will be used in
    Simulator to run the simulation. The participants should extend the BaseAgent class to implement their agent search
    strategies.
    """

    def __init__(self, agent_id: int, map: CityMap):
        self.id: int = agent_id
        self.map: CityMap = map

    @abstractmethod
    def plan_search_route(
        self, current_location: LocationOnRoad, current_time: int
    ) -> None:
        """
        This is a callback method called when the agent drops off a resource or when the previous route is finished.
        The agent uses this method to plan a route which defines what is the intersection to return for each of
        the subsequent nextIntersection calls.
        See UserExamples.AgentRandomDestination and UserExamples.AgentRandomWalk for two examples how planSearchRoute works.
        This method must be overridden in every Agent implementation.
        """
        pass

    @abstractmethod
    def next_intersection(
        self, current_location: LocationOnRoad, current_time: int
    ) -> Intersection:
        """
        This method must be overridden in every Agent implementation in order to return an Intersection that the
        Simulator can use to move the Agent.
        This method is a callback method which is called when the agent reaches an intersection. The agent decides which
        of the neighboring intersections to go to. The Simulator will move the agent to the returned intersection and then
        call this method again, and so on. This is how a planned route is executed by the Simulator.

        Args:
            current_location: The agent's location at the time when the method is called
            current_time: The time at which the method is invoked
        Returns:
            Intersection that the Agent is going to move to
        """
        pass

    @abstractmethod
    def assigned_to(
        self,
        current_location: LocationOnRoad,
        current_time: int,
        resource_id: int,
        resource_pickup_location: LocationOnRoad,
        resource_dropoff_location: LocationOnRoad,
    ) -> None:
        """
        This method is to inform the agent that it is assigned to a resource. No action is necessary from the agent. The agent
        will be automatically moved to the destination of the resource. The method is provided in case that the agent wants to use
        the assignment information to assist its future routing strategy.
        This method must be overridden in every Agent implementation.

        Args:
            current_location: The agent's location at the time when the method is called
            current_time: The time at which the assignment occurs
            resource_id: The id of the resource to which the agent is assigned
            resource_pickup_location: The pickup location of the resource to which the agent is assigned
            resource_dropoff_location: The dropoff location of the resource to which the agent is assigned
        """
        pass
