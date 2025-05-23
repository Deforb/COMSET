from __future__ import annotations
from typing import List, TypeVar, Callable, Any, Optional, Tuple
from multiprocessing import Pool, cpu_count
from functools import partial
import logging
import traceback

from tqdm import tqdm

T = TypeVar("T")
R = TypeVar("R")


class ParallelProcessor:
    """
    通用并行处理工具类，用于处理计算密集型任务。
    支持多种并行处理模式，包括map、starmap等。
    """

    @staticmethod
    def process(
        items: List[T],
        process_func: Callable[[T], R],
        chunk_size: Optional[int] = None,
        n_jobs: Optional[int] = None,
        ordered: bool = True,
        show_progress: bool = True,
        desc: str = "Processing",
        **kwargs,
    ) -> List[R]:
        """
        Process a list of items in parallel.

        Args:
            items: List of items to process
            process_func: Function to apply to each item
            chunk_size: Number of items per worker
            n_jobs: Number of parallel workers
            ordered: If True, maintain input order in results
            show_progress: Show progress bar
            desc: Progress bar description
            **kwargs: Additional arguments to pass to process_func

        Returns:
            List of processed results
        """
        if not items:
            return []

        n_jobs = n_jobs or cpu_count()
        chunk_size = chunk_size or max(1, len(items) // (n_jobs * 4))

        # 创建偏函数，将额外参数绑定到处理函数
        process_func_with_args = partial(process_func, **kwargs)

        try:
            with Pool(n_jobs) as pool:
                if show_progress:
                    with tqdm(total=len(items), desc=desc) as pbar:
                        results = []
                        map_func = pool.imap if ordered else pool.imap_unordered
                        for result in map_func(
                            process_func_with_args, items, chunksize=chunk_size
                        ):
                            results.append(result)
                            pbar.update(1)
                        return results
                else:
                    return pool.map(process_func_with_args, items, chunksize=chunk_size)
        except Exception as e:
            logging.error(
                f"Parallel processing error: {str(e)}\n{traceback.format_exc()}",
                exc_info=True,
            )
            raise e

    @staticmethod
    def process_star(
        items: List[Tuple[Any, ...]],
        process_func: Callable[..., R],
        chunk_size: Optional[int] = None,
        n_jobs: Optional[int] = None,
        show_progress: bool = True,
        desc: str = "Processing",
    ) -> List[R]:
        """
        并行处理元组列表中的项目（类似 starmap），支持进度条实时更新。

        Args:
            items: 要处理的元组列表
            process_func: 处理函数
            chunk_size: 每个进程处理的数据块大小
            n_jobs: 进程数，默认为CPU核心数
            show_progress: 是否显示进度条
            desc: 进度条描述

        Returns:
            处理结果列表
        """
        if not items:
            return []

        n_jobs = n_jobs or cpu_count()
        chunk_size = chunk_size or max(1, len(items) // (n_jobs * 4))

        try:
            with Pool(n_jobs) as pool:
                if show_progress:
                    with tqdm(total=len(items), desc=desc) as pbar:
                        results = []
                        # 使用 imap_unordered 提升效率，不保证顺序
                        for result in pool.imap_unordered(
                            partial(
                                ParallelProcessor._call_with_unpack, func=process_func
                            ),
                            items,
                            chunksize=chunk_size,
                        ):
                            results.append(result)
                            pbar.update(1)
                            pbar.refresh()  # 强制刷新进度条
                        return results
                else:
                    return pool.starmap(process_func, items, chunksize=chunk_size)
        except Exception as e:
            logging.error(
                f"Parallel processing error: {str(e)}\n{traceback.format_exc()}",
                exc_info=True,
            )
            raise e

    @staticmethod
    def process_batch(
        items: List[T],
        process_func: Callable[[List[T]], List[R]],
        batch_size: int,
        n_jobs: Optional[int] = None,
        desc: str = "Processing",
    ) -> List[R]:
        """
        将数据分批并行处理。

        Args:
            items: 要处理的项目列表
            process_func: 批处理函数
            batch_size: 每批处理的数据量
            n_jobs: 进程数，默认为CPU核心数
            desc: 进度描述

        Returns:
            处理结果列表
        """
        if not items:
            return []

        # 将数据分成批次
        batches = [items[i : i + batch_size] for i in range(0, len(items), batch_size)]

        # 并行处理批次
        results = ParallelProcessor.process(
            batches, process_func, n_jobs=n_jobs, desc=desc
        )

        # 展平结果
        return [item for batch in results for item in batch]

    @staticmethod
    def _call_with_unpack(args: Tuple[Any, ...], func: Callable[..., R]) -> R:
        """
        解包参数并调用处理函数，用于进程池中可序列化调用。
        """
        return func(*args)
