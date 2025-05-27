from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional, TypeVar, TYPE_CHECKING, override

if TYPE_CHECKING:
    from COMSETsystem.Simulator import Simulator
    from COMSETsystem.FleetManager import FleetManager
    # from COMSETsystem.AgentEvent import AgentEvent

# For type hinting the return type of trigger()
EventType = TypeVar("EventType", bound="Event")


class Event(ABC):
    """
    The Event class represents an event which is something that is happening in
    the simulation. In this case we have agent events and resource events which
    will be described in their respective class. An event most importantly has
    time. This is when this event will happen, and thus triggered.
    """

    _max_id = 0

    def __init__(
        self,
        time: int,
        simulator: Optional[Simulator] = None,
        fleet_manager: Optional[FleetManager] = None,
    ) -> None:
        """
        Constructor for class Event

        Args:
            time: core to this class, indicates when this event will trigger.
            simulator: a reference to simulator
            fleet_manager: a reference to fleet manager
        """
        self._id = Event._max_id
        Event._max_id += 1
        self._time = time
        self.simulator = simulator
        self.fleet_manager = fleet_manager

    @abstractmethod
    def trigger(self) -> Optional[EventType]:
        """
        Function called when the Event needs to be executed.

        Returns:
            new Event if needed.
        """
        pass

    @property
    def id(self) -> int:
        return self._id

    @id.setter
    def id(self, value: int) -> None:
        self._id = value

    def __lt__(self, other: "Event") -> bool:
        """
        To be used by the PriorityQueue to order the Events

        Args:
            other: the event being compared to this one

        Returns:
            bool: whether this event should be processed before the other
        """
        if self.time != other.time:
            return self.time < other.time
        elif self.__class__ == other.__class__:  # tie on time; if same type compare id
            if self.id != other.id:
                return self.id < other.id
            else:
                assert False, "Duplicate event exception"
        else:
            # if not same type, agent should be processed first
            return self.__class__.__name__ == "AgentEvent"

    @property
    def time(self) -> int:
        return self._time

    @time.setter
    def time(self, value: int) -> None:
        """
        Set the time of the event.
        Note: Should never change the time when the event is on the simulator queue!
        """
        # TODO: it costs too much time to check this every time,
        # temporally delete it and plan refactor to heapdict.
        # if hasattr(self, "simulator") and self.simulator is not None:
        #     assert not self.simulator.has_event(self)
        self._time = value

    @override
    def __str__(self) -> str:
        return f"{self.__class__.__name__} {self.id} at time {self.time}"
