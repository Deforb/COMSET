from __future__ import annotations
from typing import Dict, Set, TYPE_CHECKING, Optional, Union

from comset.COMSETsystem.Vertex import Vertex
from comset.COMSETsystem.Point2D import Point2D

if TYPE_CHECKING:
    from Road import Road


class Intersection:
    """
    The Intersection class defines a vertex that connects different streets.
    """

    def __init__(self, param: Union[Vertex, "Intersection"]) -> None:
        if isinstance(param, Vertex):
            # Constructor from Vertex
            vertex: Vertex = param
            self.longitude: float = vertex.longitude
            self.latitude: float = vertex.latitude
            self.id: int = vertex.id
            self.xy: Point2D = vertex.xy
            self.vertex: Vertex = vertex
            self.path_table_index: int = 0
            self.roads_map_to: Dict["Intersection", Road] = {}
            self.roads_map_from: Dict["Intersection", Road] = {}
        elif isinstance(param, Intersection):
            # Copy constructor
            an_intersection = param
            self.longitude: float = an_intersection.longitude
            self.latitude: float = an_intersection.latitude
            self.id: int = an_intersection.id
            self.xy: Point2D = Point2D(an_intersection.xy.x, an_intersection.xy.y)
            self.path_table_index: int = an_intersection.path_table_index
            self.vertex: Optional["Vertex"] = None
            self.roads_map_to: Dict["Intersection", Road] = {}
            self.roads_map_from: Dict["Intersection", Road] = {}
        else:
            raise TypeError("Invalid parameter type for Intersection")

    def is_adjacent(self, i: "Intersection") -> bool:
        """
        Checks if this intersection and the specified intersection are neighbors.
        """
        return i in self.roads_map_from or i in self.roads_map_to

    def road_to(self, i: "Intersection") -> Road:
        """
        Return the road from this intersection to the specified intersection.
        """
        if i in self.roads_map_from:
            return self.roads_map_from[i]
        raise ValueError(f"No road between {self} and {i}")

    def get_roads_from(self) -> Set[Road]:
        """
        Return a set of all the roads going from this intersection.
        """
        return set(self.roads_map_from.values())

    def get_roads_to(self) -> Set[Road]:
        """
        Return a set of all the roads going to this intersection.
        """
        return set(self.roads_map_to.values())

    def get_adjacent_from(self) -> Set["Intersection"]:
        """
        Return a set of intersections that can be directly reached from this intersection.
        """
        return set(self.roads_map_from.keys())

    def get_adjacent_to(self) -> Set["Intersection"]:
        """
        Return a set of intersections that can directly reach this intersection.
        """
        return set(self.roads_map_to.keys())

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Intersection):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    def get_x(self) -> float:
        """
        Return the x-coordinate of this intersection.
        """
        return self.xy.x

    def get_y(self) -> float:
        """
        Return the y-coordinate of this intersection.
        """
        return self.xy.y

    def __str__(self) -> str:
        return f"({self.latitude},{self.longitude})"

    def __lt__(self, other: "Intersection") -> bool:
        return self.id < other.id
