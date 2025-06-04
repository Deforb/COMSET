from src.comset.COMSETsystem.Intersection import Intersection
from src.comset.COMSETsystem.Resource import Resource


class Region:
    """A region is a hexagon divided by H3 library"""

    def __init__(self, hex_addr: str):
        self.hex_addr = hex_addr  # The index of region
        self.intersection_list: list[Intersection] = []
        self.available_agents: set[int] = set()
        self.waiting_resources: set[Resource] = set()
        self.resource_quantity: list[int] = []  # Predicted resource quantity
        self.destination_quantity: list[int] = []  # Predicted dropoff points
