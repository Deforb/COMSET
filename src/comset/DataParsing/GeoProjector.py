import math


class GeoProjector:
    """
    The GeoProjector class projects a lat,lon location to a point in 2D space. Suitable for a
    small geographic area (e.g., a city) which can be considered flat.
    """

    EARTH_RADIUS: float = 6370000.0  # Earth radius in meters

    ref_lat: float
    ref_lon: float
    meters_per_lat_degree: float
    meters_per_lon_degree: float

    def __init__(self, ref_lat: float, ref_lon: float) -> None:
        """
        Constructor of class. The parameters specify a reference location which can be any location
        in the considered geographic area.

        Args:
            ref_lat: Latitude of a local position
            ref_lon: Longitude of a local position
        """
        self.ref_lat = ref_lat
        self.ref_lon = ref_lon

        # Calculate meters per degree for latitude and longitude at the reference point
        self.meters_per_lat_degree = GeoProjector.distance_great_circle(
            ref_lat, ref_lon, ref_lat + 1.0, ref_lon
        )
        self.meters_per_lon_degree = GeoProjector.distance_great_circle(
            ref_lat, ref_lon, ref_lat, ref_lon + 1.0
        )

    def from_lat_lon(self, lat: float, lon: float) -> list[float]:
        """
        Project a lat, lon location to 2D space.

        Args:
            lat: Latitude
            lon: Longitude

        Returns:
            Projected 2D point as [x, y] in meters
        """
        x = (lon - self.ref_lon) * self.meters_per_lon_degree
        y = (lat - self.ref_lat) * self.meters_per_lat_degree
        return [x, y]

    def to_lat_lon(self, x: float, y: float) -> list[float]:
        """
        Project a 2D point back to geographic coordinates.

        Args:
            x: X coordinate in meters
            y: Y coordinate in meters

        Returns:
            Original geographic coordinates as [lat, lon]
        """
        lon = self.ref_lon + (x / self.meters_per_lon_degree)
        lat = self.ref_lat + (y / self.meters_per_lat_degree)
        return [lat, lon]

    @staticmethod
    def distance_great_circle(
        lat1: float, lon1: float, lat2: float, lon2: float
    ) -> float:
        """
        Compute great-circle distance between two locations on earth modeled as a sphere.

        Args:
            lat1: Latitude of the first location
            lon1: Longitude of the first location
            lat2: Latitude of the second location
            lon2: Longitude of the second location

        Returns:
            Great-circle distance in meters
        """
        rad_lat1 = math.radians(lat1)
        rad_lon1 = math.radians(lon1)
        rad_lat2 = math.radians(lat2)
        rad_lon2 = math.radians(lon2)

        q1 = (
            math.cos(rad_lat1)
            * math.cos(rad_lon1)
            * math.cos(rad_lat2)
            * math.cos(rad_lon2)
        )
        q2 = (
            math.cos(rad_lat1)
            * math.sin(rad_lon1)
            * math.cos(rad_lat2)
            * math.sin(rad_lon2)
        )
        q3 = math.sin(rad_lat1) * math.sin(rad_lat2)
        q = q1 + q2 + q3

        # Clamp q to avoid numerical errors in acos
        if q > 1.0:
            q = 1.0
        elif q < -1.0:
            q = -1.0

        return math.acos(q) * GeoProjector.EARTH_RADIUS
