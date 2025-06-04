class TrafficPatternPred:
    """For get the predicted speed factor"""

    def __init__(self, pred_file: str):
        self.speed_factor_pred: list[float] = []
        try:
            with open(pred_file, "r") as file:
                for line in file:
                    self.speed_factor_pred.append(float(line.strip()))
        except Exception as e:
            import traceback

            traceback.print_exc()
            raise e

    def get_speed_factor(self, index: int) -> float:
        return self.speed_factor_pred[index]
