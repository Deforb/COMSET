from __future__ import annotations
from typing import Optional, ClassVar, TYPE_CHECKING

if TYPE_CHECKING:
    from comset.COMSETsystem.Point2D import Point2D
    from comset.COMSETsystem.Vertex import Vertex
    from comset.COMSETsystem.Road import Road


class Link:
    """
    The Link class defines a directed link segment between two vertices.
    """

    max_id: ClassVar[int] = 0  # ID counter for unique ids

    def __init__(
        self,
        from_vertex: Vertex,
        to_vertex: Vertex,
        length: Optional[float] = 0,
        speed: Optional[float] = 0,
        aLink: Optional[Link] = None,
    ) -> None:
        """
        Constructor for Link. Sets the beginning and end vertex,
        the speed limit on the link, the length (distance) of the link and
        (based on the speed limit and distance) the time it takes to traverse
        the link.

        Args:
            from_vertex: The start vertex
            to_vertex: The end vertex
            length: The length of the link in meters
            speed: The speed limit on the link in meters per second
            aLink: An existing link

        Two modes:
            1. New link: Link(from_vertex, to_vertex, length, speed)
            2. Copy from existing: Link(existing_link, from_vertex, to_vertex)
        """

        if aLink is not None:
            # Copy constructor mode
            self.id = aLink.id
            self.from_vertex = from_vertex
            self.to_vertex = to_vertex
            self.length = aLink.length
            self.speed = aLink.speed
            self.travel_time = aLink.travel_time
            self.begin_time = aLink.begin_time
            self.road = None
            self.min_x = aLink.min_x
            self.min_y = aLink.min_y
            self.max_x = aLink.max_x
            self.max_y = aLink.max_y

        else:
            # Regular constructor mode
            self.id = Link.max_id
            Link.max_id += 1
            self.from_vertex = from_vertex
            self.to_vertex = to_vertex
            self.length: float = length
            self.speed: float = speed
            self.travel_time: float = length / speed
            self.road: Optional[Road] = None

            from_x = from_vertex.xy.x
            from_y = from_vertex.xy.y
            to_x = to_vertex.xy.x
            to_y = to_vertex.xy.y
            self.min_x = min(from_x, to_x)
            self.min_y = min(from_y, to_y)
            self.max_x = max(from_x, to_x)
            self.max_y = max(from_y, to_y)

    def __lt__(self, other: Link) -> bool:
        return self.id < other.id

    def __eq__(self, other: Link) -> bool:
        return (
            self.from_vertex == other.from_vertex and self.to_vertex == other.to_vertex
        )

    def __str__(self) -> str:
        return (
            f"{self.from_vertex},{self.to_vertex},"
            f"{self.length},{self.travel_time},{self.speed}"
        )

    def __hash__(self) -> int:
        return hash(self.id)

    def distance_sq(self, p: Point2D) -> float:
        """
        Calculate squared distance between a point and this link segment.

        Args:
            p: Query point

        Returns:
            Squared distance to the nearest point on the link segment
        """
        x1 = self.from_vertex.xy.x
        y1 = self.from_vertex.xy.y
        x2 = self.to_vertex.xy.x
        y2 = self.to_vertex.xy.y
        x = p.x
        y = p.y
        length_sq = (x1 - x2) ** 2 + (y1 - y2) ** 2

        if length_sq == 0.0:
            return self._distance_sq_point(x1, y1, x, y)
        else:
            t = ((x - x1) * (x2 - x1) + (y - y1) * (y2 - y1)) / length_sq
            if t < 0.0:
                return self._distance_sq_point(x1, y1, x, y)
            elif t > 1.0:
                return self._distance_sq_point(x2, y2, x, y)
            else:
                proj_x = x1 + t * (x2 - x1)
                proj_y = y1 + t * (y2 - y1)
                return self._distance_sq_point(proj_x, proj_y, x, y)

    def _distance_sq_point(self, x1: float, y1: float, x2: float, y2: float) -> float:
        return (x1 - x2) ** 2 + (y1 - y2) ** 2
