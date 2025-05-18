from __future__ import annotations
from typing import Dict, Optional, Set, Union, TYPE_CHECKING

from comset.COMSETsystem.Point2D import Point2D
from comset.COMSETsystem.Link import Link

if TYPE_CHECKING:
    from Intersection import Intersection


class Vertex:
    """
    A Vertex object corresponds to a "node" element in an OSM JSON map.
    """

    def __init__(
        self,
        *args: Union[float, Vertex],  # 接受坐标值或另一个Vertex对象
    ) -> None:
        """
        构造方法，支持两种初始化方式：
        1. 用坐标值初始化：Vertex(longitude, latitude, x, y, id)
        2. 用另一个Vertex对象复制：Vertex(other_vertex)
        """
        if len(args) == 1 and isinstance(args[0], Vertex):
            # 复制构造：Vertex(other_vertex)
            other: Vertex = args[0]
            self.longitude: float = other.longitude
            self.latitude: float = other.latitude
            self.id: int = other.id
            self.xy = Point2D(other.get_x(), other.get_y())
        elif len(args) == 5:
            # 常规构造：Vertex(longitude, latitude, x, y, id)
            self.longitude = args[0]
            self.latitude = args[1]
            self.id = args[4]
            self.xy = Point2D(args[2], args[3])
        else:
            raise TypeError(
                "Invalid arguments. Use either: "
                "Vertex(longitude, latitude, x, y, id) or "
                "Vertex(other_vertex)"
            )

        self.intersection: Optional[Intersection] = None
        self.links_map_to: Dict[Vertex, "Link"] = {}
        self.links_map_from: Dict[Vertex, "Link"] = {}

    def add_edge(self, other: "Vertex", distance: float, speed: float) -> None:
        """
        Adds an edge (link) from this vertex to a specified vertex
        with a specified distance and speed limit.

        Args:
            other: The vertex the link goes to
            distance: The distance of the link (generally just the distance
                     between the two vertices
            speed: The speed limit on the link between the vertices
        """
        if self.id == other.id:
            return
        link = Link(self, other, distance, speed)
        self.links_map_from[other] = link
        other.links_map_to[self] = link

    def remove_edge(self, other: "Vertex") -> None:
        """
        Removes the edge (link) between this vertex and the specified vertex

        Args:
            other: The vertex that the removed link goes to
        Raises:
            ValueError: if there is no link between this vertex and the specified vertex
        """
        if other in self.links_map_from:
            del self.links_map_from[other]
            del other.links_map_to[self]
            return
        raise ValueError("Trying to remove link that doesn't exist.")

    def cut_vertex(self) -> None:
        """
        Removes this vertex and reconnects all the neighbors such that the
        graph remains the same minus this vertex.
        """
        for from_link in self.links_map_from.values():
            for to_link in self.links_map_to.values():
                to_link.from_vertex.add_edge(
                    from_link.to_vertex,
                    from_link.length + to_link.length,
                    min(from_link.speed, to_link.speed),
                )
        self.sever_vertex()

    def sever_vertex(self) -> None:
        """
        Removes this vertex by cutting all the incoming and outgoing links.
        """
        while self.links_map_from:
            other = next(iter(self.links_map_from.keys()))
            self.remove_edge(other)

        while self.links_map_to:
            other = next(iter(self.links_map_to.keys()))
            other.remove_edge(self)

    def is_adjacent(self, other: "Vertex") -> bool:
        """
        Checks if this vertex and the specified vertex are neighbors,
        i.e. if there is a link from this to the other or from the other to this.

        Args:
            other: The vertex to check
        Returns:
            True if there is a link between this and other, False otherwise.
        """
        return (other in self.links_map_from) or (other in self.links_map_to)

    def to(self, other: "Vertex") -> "Link":
        """
        Return the link from this vertex to the specified vertex.

        Args:
            other: The vertex that the link goes to
        Returns:
            The link between this and the other vertex
        Raises:
            ValueError: if there is no link between this and the other
        """
        if other in self.links_map_from:
            return self.links_map_from[other]
        raise ValueError("no link between this and other")

    def get_links_from(self) -> Set["Link"]:
        """
        Return a set of all the links going from this vertex to some other vertex.

        Returns:
            a set of links from this vertex to other vertices.
        """
        return set(self.links_map_from.values())

    def get_links_to(self) -> Set["Link"]:
        """
        Return a set of all the links going from some vertex to this vertex.

        Returns:
            a set of links going to this vertex.
        """
        return set(self.links_map_to.values())

    def get_adjacent_from(self) -> Set["Vertex"]:
        """
        Return a set of Vertices that you can directly go to from this vertex,
        i.e. there exists a link from this vertex to every vertex in the returned set

        Returns:
            a set of vertices that you can go to from this vertex
        """
        return set(self.links_map_from.keys())

    def get_adjacent_to(self) -> Set["Vertex"]:
        """
        Return a set of Vertices from which you can directly go to this vertex,
        i.e. there exists a link from every vertex in the returned set to this vertex

        Returns:
            a set of vertices from which you can directly go to this vertex
        """
        return set(self.links_map_to.keys())

    def __eq__(self, other: object) -> bool:
        """
        Checks if the given vertex is the same as this vertex

        Args:
            other: The given vertex to check
        Returns:
            True if the given vertex is the same as this vertex
        """
        if not isinstance(other, Vertex):
            return False
        return other.id == self.id

    def distance_to(self, other: "Vertex") -> float:
        """
        returns the Euclidean distance from this vertex to the specified vertex

        Args:
            other: specified vertex
        Returns:
            distance between this vertex and specified vertex
        """
        return self.xy.distance(other.xy)

    def get_x(self) -> float:
        """
        returns the x-coordinate of this vertex
        Returns:
            x-coordinate
        """
        return self.xy.x

    def get_y(self) -> float:
        """
        returns the y-coordinate of this vertex
        Returns:
            y-coordinate
        """
        return self.xy.y

    def __str__(self) -> str:
        """
        returns the longitude and latitude as a string
        Returns:
            string of longitude and latitude
        """
        return f"({self.latitude},{self.longitude})"

    def __lt__(self, other: "Vertex") -> bool:
        """
        Compare vertices based on their id for ordering
        """
        return self.id < other.id

    def __hash__(self) -> int:
        return hash(self.id)
