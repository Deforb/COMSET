"""
Profiling the code with cProfile
"""

import cProfile
import pstats


def collect():
    from main import main

    profiler = cProfile.Profile()
    profiler.enable()

    main()

    profiler.disable()
    stats = pstats.Stats(profiler).sort_stats("cumulative")
    # stats.print_stats()
    stats.dump_stats("profile_results.prof")


def display():
    import pstats
    from pstats import SortKey

    # 加载 .prof 文件
    p = pstats.Stats("profile_results.prof")

    # 清理文件名，使其更易读
    p.strip_dirs()

    p.sort_stats(SortKey.TIME).print_stats(20)


if __name__ == "__main__":
    collect()
    display()
