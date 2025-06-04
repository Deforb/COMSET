from comset.COMSETsystem.LocationOnRoad import LocationOnRoad


class Resource:
    """
    This class is a copy of the information for a Resource that is useful to the Fleet Manager. It's a copy so that
    the Fleet Manager cannot change the original Resource's attributes.
    """

    def __init__(
        self,
        id: int,
        expiration_time: int,
        assigned_agent_id: int,
        pickup_loc: LocationOnRoad,
        dropoff_Loc: LocationOnRoad,
    ):
        self.id = id
        self.expiration_time = expiration_time
        self.assigned_agent_id = assigned_agent_id
        self.pickup_loc = pickup_loc
        self.dropoff_loc = dropoff_Loc
