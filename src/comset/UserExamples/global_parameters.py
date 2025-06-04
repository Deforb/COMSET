from datetime import datetime


class GlobalParameters:
    """
    The default parameters shared with the whole program
    """

    TIME_INTERVAL = 5
    TIME_HORIZON = 20
    NUM_OF_TIME_INTERVALS_PER_DAY = 288
    NUM_OF_INTERSECTION_TIME_INTERVAL_PER_DAY = 48
    CRUISING_THRESHOLD = 600
    K = 6  # the size of neighbor layers
    N = 5  # the size of candidate regions
    GAMMA = -1.5
    LAMBDA = 0.8
    REGION_FILE = "model/regions.txt"
    TRAFFIC_PATTERN_PRED_FILE = "model/trafficPatternItem_pred_1_6.txt"
    PICKUP_PRED_FILE = "model/pickup_pred_1_6.txt"
    DROPOFF_PRED_FILE = "model/dropoff_pred_1_6.txt"
    INTERSECTION_RESOURCE_FILE = "model/intersectionPickup_1_6_pred.txt"
    TEMPORAL_START_DATETIME = datetime(2016, 1, 1, 0, 0, 0)
    TEMPORAL_END_DATETIME = datetime(2016, 7, 1, 0, 0, 0)
