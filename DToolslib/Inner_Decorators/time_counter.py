
from typing import Any, Callable
import time
import wrapt
import sys


@wrapt.decorator
def time_counter(func, instance, args, kwargs) -> Callable[..., tuple[Any, float]]:
    """
    用于计算函数的执行时间. 

    参数:
    - func: 的函数

    返回值:
    包装后的函数, 返回函数的执行结果和执行时间的元组
    """
    start = time.perf_counter()
    result = func(*args, **kwargs)
    end = time.perf_counter()
    sys.stdout.write(f'[\x1B[36m{func.__module__}\x1B[0m] - [\x1B[36m{func.__qualname__}\x1B[0m]-[\x1B[32mrunTime\x1B[0m]:\t \x1B[31m{(end - start)*1000} ms\x1B[0m\n')
    return result
