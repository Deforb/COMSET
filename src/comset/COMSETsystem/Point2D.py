from dataclasses import dataclass
import math


@dataclass
class Point2D:
    """
    二维坐标点类，用于表示地图上的点
    """

    x: float
    y: float

    def distance(self, other: "Point2D") -> float:
        """
        计算两点之间的欧式距离

        参数:
            other: 另一个Point2D对象

        返回:
            两点之间的距离
        """
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)
