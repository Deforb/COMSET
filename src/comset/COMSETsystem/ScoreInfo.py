from __future__ import annotations
from dataclasses import dataclass
from typing import List, TYPE_CHECKING
import math
import time

if TYPE_CHECKING:
    from Configuration import Configuration
    from Simulator import Simulator


@dataclass
class IntervalCheckRecord:
    time: int
    interval: int
    expected_interval: int


class ScoreInfo:
    def __init__(self, configuration: Configuration, simulator: Simulator) -> None:
        # Configuration and simulator references
        self.configuration = configuration
        self.simulator = simulator

        # Total accumulated times
        self.total_resource_trip_time: int = 0
        self.total_resource_wait_time: int = 0
        self.total_agent_search_time: int = 0
        self.total_agent_cruise_time: int = 0
        self.total_agent_approach_time: int = 0

        # Counters
        self.expired_resources: int = 0
        self.total_resources: int = 0
        self.total_assignments: int = 0
        self.total_searches: int = 0
        self.total_abortions: int = 0

        # Data structures
        self.approach_time_check_records: List[IntervalCheckRecord] = []
        self.completed_trip_time: List[IntervalCheckRecord] = []

        # Timing and memory tracking
        self.start_time: int = int(time.time() * 1_000_000_000)  # in nanoseconds
        self.allocated_memory: int = 0

        # String builder for performance report
        self.sb: List[str] = []

    def accumulate_resource_wait_time(self, wait_time: int) -> None:
        self.total_resource_wait_time += wait_time

    def record_approach_time(
        self,
        current_time: int,
        start_search_time: int,
        assign_time: int,
        available_time: int,
        static_approach_time: int,
    ) -> None:
        self.total_agent_search_time += current_time - start_search_time
        self.total_searches += 1
        self.accumulate_resource_wait_time(current_time - available_time)
        self.total_agent_cruise_time += assign_time - start_search_time

        approach_time = current_time - assign_time
        self.total_agent_approach_time += approach_time
        self.approach_time_check_records.append(
            IntervalCheckRecord(assign_time, approach_time, static_approach_time)
        )

    def record_expiration(self) -> None:
        self.expired_resources += 1
        self.accumulate_resource_wait_time(
            self.configuration.resource_maximum_life_time
        )

    def record_abortion(self) -> None:
        self.total_abortions += 1

    def beginning(self) -> None:
        """
        Initializes and gets the max memory, allocated memory and free
        memory. All of these are added to the Performance Report which is
        saved in the StringBuilder. Furthermore also takes the time, such
        that later on we can compare to the time when the simulation is over.
        The allocated memory is also used to compare to the allocated memory
        by the end of the simulation.
        """
        self.sb.clear()
        self.sb.append("Performance Report:\n")
        self.sb.append("free memory: N/A\n")
        self.sb.append("allocated memory: N/A\n")
        self.sb.append("max memory: N/A\n")
        self.sb.append("total free memory: N/A\n")

        print("".join(self.sb))

    def end(self) -> None:
        """
        Calculate the time the simulation took by taking the time right now
        and comparing to the time when the simulation started. Add the total
        time to the report and the score as well.

        Furthermore, calculate the allocated memory by the participant's implementation by comparing the
        previous allocated memory with the current allocated memory.
        Print the Performance Report.
        """
        self.sb.clear()
        end_time = int(time.time() * 1_000_000_000)
        total_time = (end_time - self.start_time) // 1_000_000_000  # in seconds
        print(f"\nrunning time: {total_time} seconds")
        print("\n***Simulation environment***")
        print(f"JSON map file: {self.configuration.map_json_file}")
        print(f"Resource dataset file: {self.configuration.resource_file}")
        print(
            f"Bounding polygon KML file: {self.configuration.bounding_polygon_kml_file}"
        )
        print(f"Number of agents: {self.configuration.number_of_agents}")
        print(f"Number of resources: {self.total_resources}")
        print(
            f"Resource Maximum Life Time: {self.configuration.resource_maximum_life_time} seconds"
        )
        print(f"Fleet Manager class: {self.configuration.agent_class_name}")
        print(f"Time resolution: {self.configuration.TIME_RESOLUTION}")
        print(f"Simulation Start Time: {self.simulator.simulation_start_time}")
        print(f"Simulation End Time: {self.simulator.simulation_end_time}")
        print(f"Final Simulation Time: {self.simulator.simulation_time}")

        print("\n***Statistics***")

        if self.total_resources == 0:
            self.sb.append("No resources.\n")
        else:
            # Collect the "search" time for the agents that are empty at the end of the simulation.
            # These agents are in search status and therefore the amount of time they spend on
            # searching until the end of the simulation should be counted toward the total search time.
            # FIXME: Move this loop into the simulator and just add the time to totalAgentSearchTime and increment
            # totalSearches.  This will allow us to make emptyAgents private.
            total_remain_time = 0
            for agent_event in self.simulator.empty_agents:
                total_remain_time += (
                    self.simulator.simulation_end_time - agent_event.start_search_time
                )

            avg_search_time = self.configuration.to_seconds(
                self.total_agent_search_time + total_remain_time
            ) // (self.total_assignments + len(self.simulator.empty_agents))

            avg_resource_wait_time = (
                self.configuration.to_seconds(self.total_resource_wait_time)
                // self.total_resources
            )

            expiration_percentage = (
                self.expired_resources * 100
            ) // self.total_resources

            avg_cruise_time = (
                self.configuration.to_seconds(self.total_agent_cruise_time)
                // self.total_assignments
            )

            avg_approach_time = (
                self.configuration.to_seconds(self.total_agent_approach_time)
                // self.total_assignments
            )

            avg_trip_time = (
                self.configuration.to_seconds(self.total_resource_trip_time)
                // self.total_assignments
            )

            self.sb.append(f"average agent search time: {avg_search_time} seconds\n")
            self.sb.append(
                f"average resource wait time: {avg_resource_wait_time} seconds\n"
            )
            self.sb.append(
                f"resource expiration percentage: {expiration_percentage}%\n"
            )
            self.sb.append(f"average agent cruise time: {avg_cruise_time} seconds\n")
            self.sb.append(
                f"average agent approach time: {avg_approach_time} seconds\n"
            )
            self.sb.append(f"average resource trip time: {avg_trip_time} seconds\n")
            self.sb.append(f"total number of assignments: {self.total_assignments}\n")
            self.sb.append(f"total number of abortions: {self.total_abortions}\n")
            self.sb.append(f"total number of searches: {self.total_searches}\n")

        print("".join(self.sb))

        # TODO: Add configuration to control these checks.
        print("********** Completed Trips time checks")
        self.check_and_print_interval_records(self.completed_trip_time)

        print("********** Approach time checks")
        self.check_and_print_interval_records(self.approach_time_check_records)

    def check_and_print_interval_records(
        self,
        check_records: List[IntervalCheckRecord],
        print_limit: int = 10,
        threshold: float = 0.06,
    ) -> None:
        print("time, simulated_ratio, expected_ratio, difference")
        l2 = 0.0
        below_threshold_count = 0

        for check_record in check_records:
            ratio = self._compute_ratio(check_record)
            # FIXME: store speed_factor in IntervalCheckRecord and we can get rid of this dependence on simulator and
            # trafficPattern
            reference_ratio = self.simulator.traffic_pattern.get_speed_factor(
                check_record.time
            )
            diff = ratio - reference_ratio
            if abs(diff) > threshold or math.isnan(diff):
                if print_limit > 0:
                    print(f"{check_record.time}, {ratio}, {reference_ratio}, {diff}")
                print_limit -= 1
                below_threshold_count += 1
            l2 += ratio**2

        print(f"Threshold = {threshold}; Count = {below_threshold_count}")
        count = len(self.completed_trip_time)
        if count > 0:
            print(f"Ratios RMS = {math.sqrt(l2 / count)}; Count = {count}")
        else:
            print("Ratios RMS = N/A; Count = 0")

    def _compute_ratio(self, check_record: IntervalCheckRecord) -> float:
        # Take care of the special case of a match in which both interval and expected_interval are zeroes.
        # Think of this case as taking the limit as we approach 0/0. We assume that the default
        # speedfactor applies.
        # FIXME: store speedfactor in IntervalCheckRecord and we can get rid of this dependence on simulator and
        # trafficPattern
        if check_record.interval == 0 and check_record.expected_interval == 0:
            return self.simulator.traffic_pattern.get_speed_factor(check_record.time)
        else:
            return check_record.expected_interval / check_record.interval

    def record_completed_trip(
        self, drop_off_time: int, pickup_time: int, static_trip_time: int
    ) -> None:
        trip_time = drop_off_time - pickup_time
        self.total_resource_trip_time += trip_time
        self.total_assignments += 1
        self.completed_trip_time.append(
            IntervalCheckRecord(pickup_time, trip_time, static_trip_time)
        )
