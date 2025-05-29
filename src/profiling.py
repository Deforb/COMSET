"""
A performance profiling tool module using cProfile.

This module provides two main functionalities:
1. collect(): Run the program and collect performance profiling data
2. display(): Display the profiling results

Key Features:
- Performance profiling using cProfile
- Save profiling results to .prof file
- Visualize performance data
- Support sorting by cumulative time and display top 20 time-consuming functions

Usage Example:
    # Collect performance data
    collect()
    
    # Display analysis results
    display()

Notes:
- Running collect() will execute main() function and generate profile_results.prof file
- display() will show the top 20 time-consuming functions sorted by execution time
- Analysis results include call counts, total time, and time per call for each function
"""

from pstats import Stats, SortKey


def collect():
    import cProfile
    from main import main

    profiler = cProfile.Profile()
    profiler.enable()

    main()

    profiler.disable()
    stats = Stats(profiler).sort_stats("cumulative")
    # stats.print_stats()
    stats.dump_stats("profile_results.prof")


def display():
    # 加载 .prof 文件
    p = Stats("profile_results.prof")

    # 清理文件名，使其更易读
    p.strip_dirs()

    p.sort_stats(SortKey.TIME).print_stats(20)


if __name__ == "__main__":
    collect()
    # display()
