from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from COMSETsystem.Intersection import Intersection
    from COMSETsystem.Link import Link


class Road:
    """
	The Road class defines a directed road segment between two intersections.\\
	A road may consist of one or more links wherein each each link is a\\
	directed straight line connecting two vertices.
	"""

    # 道路的起始交叉口（上游）
    from_: Intersection = None
    # 道路的结束交叉口（下游）
    to: Intersection = None
    # 道路长度（米）
    length: float = 0.0
    # 道路行驶时间（秒）
    travel_time: float = 0.0
    # 平均速度（米/秒）
    speed: float = 0.0
    # 唯一ID
    id: int = 0

    # ID计数器，用于生成唯一ID
    maxId = 0

    # 构成道路的链接列表
    links: List[Link] = []

    def __init__(
        self,
        original: Optional[Road] = None,
        from_intersection: Optional[Intersection] = None,
        to_intersection: Optional[Intersection] = None,
        links: Optional[List[Link]] = None,
    ) -> None:
        if original is None:
            # 构造一个"空"道路对象
            self.id = Road.maxId
            Road.maxId += 1
            self.length = 0
            self.travel_time = 0
            self.links = []
        else:
            # 创建道路的副本
            self.id = original.id
            self.from_ = from_intersection
            self.to = to_intersection
            self.links = links
            self.speed = original.speed
            self.length = original.length
            self.travel_time = original.travel_time

    def add_link(self, link: Link) -> None:
        """
        Add a link to the road and accumulate travel time as a road can consists of
        multiple links. This code assume links are added in order, otherwise the beginTime
        for the link will not be correct.
        """
        self.links.append(link)
        link.road = self
        link.begin_time = self.travel_time
        self.length += link.length
        self.travel_time += link.travel_time

    def set_speed(self):
        self.speed = self.length / self.travel_time

    def __lt__(self, other: Road):
        return self.id < other.id

    def __eq__(self, road: Road) -> bool:
        return road.from_ == self.from_ and road.to == self.to

    def __str__(self) -> str:
        return f"{self.from_},{self.to},{self.length},{self.travel_time},{self.speed}"

    def __hash__(self) -> int:
        return hash(self.id)
