from __future__ import annotations
import heapq
import logging
from collections import deque
from typing import Dict, List, Optional, Tuple, Deque, Union, TYPE_CHECKING
from dataclasses import dataclass
from zoneinfo import ZoneInfo

from timezonefinder import TimezoneFinder

from comset.COMSETsystem.LocationOnRoad import LocationOnRoad
from comset.DataParsing.GeoProjector import GeoProjector
from comset.COMSETsystem.Vertex import Vertex
from comset.COMSETsystem.Link import Link
from comset.COMSETsystem.Road import Road
from comset.COMSETsystem.Intersection import Intersection
from comset.COMSETsystem.Point2D import Point2D

if TYPE_CHECKING:
    from DataParsing.KdTree import KdTree


@dataclass(frozen=True)
class PathTableEntry:
    travel_time: float
    predecessor: int


class CityMap:
    """
    The CityMap represents the map of a city.
    The map is represented as a directed graph of intersections connected by roads.
    (See Intersection and Road class for more details).
    """

    def __init__(
        self,
        intersections: Optional[Dict[int, Intersection]] = None,
        roads: Optional[List[Road]] = None,
        projector: Optional[GeoProjector] = None,
        kd_tree: Optional[KdTree] = None,
    ) -> None:
        """
        Constructor of CityMap
        """
        self.intersections: Dict[int, Intersection] = intersections or {}
        self.roads: List[Road] = roads or []
        self._projector: Optional[GeoProjector] = projector
        self.kd_tree: Optional[KdTree] = kd_tree
        self.immutable_path_table: Tuple[Tuple[PathTableEntry, ...], ...] = tuple()
        self.intersections_by_path_table_index: Dict[int, Intersection] = {}

        if intersections is not None:
            # Setup path_table_index for every intersection
            index = 0
            for intersection in self.intersections.values():
                intersection.path_table_index = index
                self.intersections_by_path_table_index[index] = intersection
                index += 1

    def travel_time_between(
        self,
        source: Union[Intersection, LocationOnRoad],
        destination: Union[Intersection, LocationOnRoad],
    ) -> Union[float, int]:
        """
        Gets the time it takes to move from one intersection to the next
        intersection.

        Warning: This function assumes traversal at the speed limits of the roads; the computed travel time
        may be different than the actual travel time.

        Args:
            source The intersection to depart from
            destination The intersection to arrive at
        Return:
            the time in seconds it takes to go from source to destination
        """
        if isinstance(source, Intersection) and isinstance(destination, Intersection):
            return self._travel_time_between_intersections(source, destination)

        if isinstance(source, LocationOnRoad) and isinstance(
            destination, LocationOnRoad
        ):
            return self._travel_time_between_locations(source, destination)

        raise TypeError("Invalid argument types")

    def _travel_time_between_intersections(
        self, source: Intersection, destination: Intersection
    ) -> float:
        try:
            return self.immutable_path_table[source.path_table_index][
                destination.path_table_index
            ].travel_time
        except AttributeError:
            print("source.path_table_index = ", source.path_table_index)
            print("destination.path_table_index = ", destination.path_table_index)
            print("len(self.immutable_path_table) = ", len(self.immutable_path_table))

    def _travel_time_between_locations(
        self, source: LocationOnRoad, destination: LocationOnRoad
    ) -> int:
        if (
            source.road == destination.road
            and source.get_displacement_on_road(destination) >= 0
        ):
            try:
                travel_time = (
                    source.get_displacement_on_road(destination) / source.road.speed
                )
            except ZeroDivisionError:
                print("source.road.speed = 0")
                exit()
        else:
            end_source = LocationOnRoad(source.road, source.road.length)
            time_to_end = (
                source.get_displacement_on_road(end_source) / source.road.speed
            )
            start_dest = LocationOnRoad(destination.road, 0)
            time_from_start = (
                start_dest.get_displacement_on_road(destination)
                / destination.road.speed
            )
            time_between = self._travel_time_between_intersections(
                source.road.to, destination.road.from_
            )
            travel_time = time_to_end + time_between + time_from_start
        return round(travel_time)

    @property
    def projector(self) -> GeoProjector:
        return self._projector

    def get_nearest_link(self, longitude: float, latitude: float) -> Link:
        x, y = self.projector.from_lat_lon(latitude, longitude)
        return self.kd_tree.nearest(Point2D(x, y))

    def calc_travel_times(self) -> None:
        """
        Compute all-pair shortest travel times using Dijkstra's algorithm.
        """

        # initialize path table
        n = len(self.intersections)
        path_table: List[List[Optional[PathTableEntry]]] = [
            [None] * n for _ in range(n)
        ]

        # creates a queue entry for each intersection
        queue_entries: Dict[Intersection, CityMap.DijkstraQueueEntry] = {
            intersection: CityMap.DijkstraQueueEntry(intersection)
            for intersection in self.intersections.values()
        }

        for source in self.intersections.values():
            # 'reset' every queue entry
            for entry in queue_entries.values():
                entry.cost = float("inf")
                entry.in_queue = True

            # source is set at distance 0
            source_entry = queue_entries[source]
            source_entry.cost = 0.0
            idx = source.path_table_index
            print(f'calc source {idx}')
            path_table[idx][idx] = PathTableEntry(0.0, idx)

            heap = list(queue_entries.values())
            heapq.heapify(heap)

            while heap:
                entry: CityMap.DijkstraQueueEntry = heapq.heappop(heap)
                if not entry.in_queue:
                    continue
                entry.in_queue = False

                for road in entry.intersection.get_roads_from():
                    neighbor_entry = queue_entries[road.to]
                    if not neighbor_entry.in_queue:
                        continue

                    new_cost = entry.cost + road.travel_time
                    if new_cost < neighbor_entry.cost:
                        neighbor_entry.cost = new_cost
                        path_table[source.path_table_index][
                            neighbor_entry.intersection.path_table_index
                        ] = PathTableEntry(
                            new_cost, entry.intersection.path_table_index
                        )
                        heapq.heappush(heap, neighbor_entry)

        # Make the path table unmodifiable
        self._make_path_table_unmodifiable(path_table)

    def _make_path_table_unmodifiable(
        self, path_table: List[List[Optional[PathTableEntry]]]
    ) -> None:
        """Make a path table unmodifiable."""
        # Create the final immutable structure more directly
        # The map() function applies tuple() to each sublist in path_table,
        # and the outer tuple() converts the resulting iterator of tuples into a single tuple of tuples.
        # This can be slightly more memory-efficient and faster than list comprehensions for this specific case.
        self.immutable_path_table = tuple(map(tuple, path_table))

        # Clear the original mutable structure (matching Java behavior)
        # This is done to free up memory, as path_table can be large.
        # It's important that path_table is fully iterated by map() before clearing.
        # Since the outer tuple() consumes the iterator returned by map(), this sequence is safe.
        for row in path_table:  # path_table here is the original list of lists
            row.clear()  # Clears each inner list (which were converted to tuples)
        path_table.clear()  # Clears the outer list itself

    def shortest_travel_time_path(
        self, source: Intersection, destination: Intersection
    ) -> Deque[Intersection]:
        """
        Get the shortest path between a given source and a given destination.

        Args:
            source: the source intersection.
            destination: the destination intersection.

        Returns:
            An ordered list of intersections forming the path.
        """
        path: Deque[Intersection] = deque()
        path.append(destination)
        current: int = destination.path_table_index

        while current != source.path_table_index:
            predecessor_entry = self.immutable_path_table[source.path_table_index][
                current
            ]
            if predecessor_entry is None:
                raise ValueError("No path exists")
            predecessor_index: int = predecessor_entry.predecessor
            predecessor: Intersection = self.intersections_by_path_table_index[
                predecessor_index
            ]
            path.appendleft(predecessor)
            current = predecessor_index

        return path

    @dataclass
    class DijkstraQueueEntry:
        intersection: Intersection
        cost: float = float("inf")
        in_queue: bool = True

        def __lt__(self, other: CityMap.DijkstraQueueEntry) -> bool:
            if self.cost != other.cost:
                return self.cost < other.cost
            return self.intersection.id < other.intersection.id

    def make_copy(self) -> CityMap:
        """return a deep copy of the map"""
        vertices_copy: Dict[int, Vertex] = {}
        intersections_copy: Dict[int, Intersection] = {}

        for orig_intersection in self.intersections.values():
            for road in orig_intersection.get_roads_from():
                links_copy: List[Link] = []
                for link in road.links:
                    # Copy vertices
                    from_vertex = link.from_vertex
                    if from_vertex.id not in vertices_copy:
                        vertices_copy[from_vertex.id] = Vertex(from_vertex)
                    to_vertex = link.to_vertex
                    if to_vertex.id not in vertices_copy:
                        vertices_copy[to_vertex.id] = Vertex(to_vertex)

                    # Create link copy
                    new_link = Link(
                        vertices_copy[from_vertex.id],
                        vertices_copy[to_vertex.id],
                        aLink=link,
                    )
                    vertices_copy[from_vertex.id].links_map_from[
                        vertices_copy[to_vertex.id]
                    ] = new_link
                    vertices_copy[to_vertex.id].links_map_to[
                        vertices_copy[from_vertex.id]
                    ] = new_link
                    links_copy.append(new_link)

                # Create intersections
                from_id = road.from_.id
                if from_id not in intersections_copy:
                    new_intersection = Intersection(road.from_)
                    new_intersection.vertex = vertices_copy[road.from_.vertex.id]
                    intersections_copy[from_id] = new_intersection

                to_id = road.to.id
                if to_id not in intersections_copy:
                    new_intersection = Intersection(road.to)
                    new_intersection.vertex = vertices_copy[road.to.vertex.id]
                    intersections_copy[to_id] = new_intersection

                # Create road copy
                new_road = Road(
                    road,
                    intersections_copy[from_id],
                    intersections_copy[to_id],
                    links_copy,
                )
                for link_copy in links_copy:
                    link_copy.road = new_road

                intersections_copy[from_id].roads_map_from[
                    intersections_copy[to_id]
                ] = new_road
                intersections_copy[to_id].roads_map_to[
                    intersections_copy[from_id]
                ] = new_road

        # Create roads list
        roads_copy: List[Road] = []
        for inter in intersections_copy.values():
            roads_copy.extend(inter.get_roads_from())

        # Create new CityMap
        new_city_map = CityMap()
        new_city_map.intersections = intersections_copy
        new_city_map.roads = roads_copy
        new_city_map.immutable_path_table = self.immutable_path_table
        new_city_map._projector = self._projector
        new_city_map.kd_tree = self.kd_tree
        new_city_map.intersections_by_path_table_index = {
            inter.path_table_index: inter for inter in intersections_copy.values()
        }

        return new_city_map

    def compute_zone_id(self) -> ZoneInfo:
        """
        Compute the time zone ID of the map based on an arbitrary location of the map.
        It is assumed that the entire map falls into a single time zone. In other words,
        the map should not cross more than one time zones.

        Return: the time zone ID of the map
        Raises: ValueError if no time zone is found for the given coordinates
        """
        # Get an arbitrary location of the map
        intersection = next(iter(self.intersections.values()))

        # Disable warning messages
        logging.getLogger().setLevel(logging.CRITICAL)

        # Use timezonefinder to get the timezone name
        tf = TimezoneFinder()
        timezone_str = tf.timezone_at(
            lat=intersection.latitude, lng=intersection.longitude
        )

        if timezone_str is None:
            raise ValueError("No time zone found for the given coordinates")

        return ZoneInfo(timezone_str)
