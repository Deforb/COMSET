class TimestampAbstract:
    """
    Record data type that represents a state of an agent(or resource) in system.
    A state is defined by the latitude, longitude at which the agent was situated at a specific time.
    Used to parse datasets. Each agent in a dataset has many timestamps.

    A timestamp consists of a latitude, longitude, whether the agent was available and the time.
    """

    def __init__(self, pickup_lat: float, pickup_lon: float, time: int) -> None:
        """
        Initialize a TimestampAbstract instance.

        :param pickup_lat: latitude at which resource appears
        :param pickup_lon: longitude at which agent appears
        :param time: time at which the agent/resource was at (lon, lat) position on map
        """
        self._pickup_lat = pickup_lat
        self._pickup_lon = pickup_lon
        self._time = time

    @property
    def pickup_lat(self) -> float:
        """
        Returns the pickup latitude.

        :return: this instance's pickup latitude.
        """
        return self._pickup_lat

    @property
    def pickup_lon(self) -> float:
        """
        Returns the pickup longitude.

        :return: this instance's pickup longitude.
        """
        return self._pickup_lon

    @property
    def time(self) -> int:
        """
        Returns the time.

        :return: this instance's time.
        """
        return self._time
