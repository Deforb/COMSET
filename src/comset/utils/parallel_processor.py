from __future__ import annotations
from typing import List, TypeVar, Callable, Any, Optional, Tuple
from multiprocessing import Pool, cpu_count
from functools import partial
import logging
from tqdm import tqdm

T = TypeVar('T')
R = TypeVar('R')

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
        use_imap: bool = False,
        desc: str = "Processing",
        **kwargs
    ) -> List[R]:
        """
        并行处理列表中的项目。
        
        Args:
            items: 要处理的项目列表
            process_func: 处理函数
            chunk_size: 每个进程处理的数据块大小
            n_jobs: 进程数，默认为CPU核心数
            use_imap: 是否使用imap（按顺序返回结果）
            desc: 进度描述
            **kwargs: 传递给处理函数的额外参数
            
        Returns:
            处理结果列表
        """
        if not items:
            return []
            
        n_jobs = n_jobs or cpu_count()
        chunk_size = chunk_size or max(1, len(items) // (n_jobs * 4))
        
        # 创建偏函数，将额外参数绑定到处理函数
        process_func_with_args = partial(process_func, **kwargs)
        
        try:
            with Pool(processes=n_jobs) as pool:
                if use_imap:
                    results = []
                    with tqdm(total=len(items), desc=desc) as pbar:
                        for result in pool.imap(process_func_with_args, items, chunksize=chunk_size):
                            results.append(result)
                            pbar.update(1)
                    return results
                else:
                    return pool.map(process_func_with_args, items, chunksize=chunk_size)
        except Exception as e:
            logging.error(f"并行处理出错: {str(e)}")
            raise
            
    @staticmethod
    def process_star(
        items: List[Tuple],
        process_func: Callable,
        chunk_size: Optional[int] = None,
        n_jobs: Optional[int] = None,
        desc: str = "Processing"
    ) -> List[Any]:
        """
        并行处理元组列表中的项目（类似starmap）。
        
        Args:
            items: 要处理的元组列表
            process_func: 处理函数
            chunk_size: 每个进程处理的数据块大小
            n_jobs: 进程数，默认为CPU核心数
            desc: 进度描述
            
        Returns:
            处理结果列表
        """
        if not items:
            return []
            
        n_jobs = n_jobs or cpu_count()
        chunk_size = chunk_size or max(1, len(items) // (n_jobs * 4))
        
        try:
            with Pool(processes=n_jobs) as pool:
                results = []
                with tqdm(total=len(items), desc=desc) as pbar:
                    # 使用 imap 和 starmap 的组合来实现进度更新
                    for i in range(0, len(items), chunk_size):
                        chunk = items[i:i + chunk_size]
                        chunk_results = pool.starmap(process_func, chunk)
                        results.extend(chunk_results)
                        pbar.update(len(chunk))
                return results
        except Exception as e:
            logging.error(f"并行处理出错: {str(e)}")
            raise
            
    @staticmethod
    def process_batch(
        items: List[T],
        process_func: Callable[[List[T]], List[R]],
        batch_size: int,
        n_jobs: Optional[int] = None,
        desc: str = "Processing"
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
        batches = [items[i:i + batch_size] for i in range(0, len(items), batch_size)]
        
        # 并行处理批次
        results = ParallelProcessor.process(
            batches,
            process_func,
            n_jobs=n_jobs,
            desc=desc
        )
        
        # 展平结果
        return [item for batch in results for item in batch] 