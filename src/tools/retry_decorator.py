import functools
import logging
from typing import Callable, Any

from tenacity import retry, stop_after_attempt,retry_if_exception_type, before_sleep_log, wait_exponential

logger = logging.getLogger(__name__)

# 定义需要的异常重试
network_exceptions = (
    ConnectionError,
    TimeoutError,
    OSError,
)

def tool_retry(
        attempts:int = 3,
        min_wait:int = 1.0,
        max_wait:int = 10.0,
        fallback:Callable = None,
):
    """
    工具调用重试装饰器
    :param attempts: 最大重试次数
    :param min_wait: 指数退避最小等待秒数
    :param max_wait: 指数退避最大等待秒数
    :param fallback: 所有重试都失败后的降级函数，后备方案，防止程序崩溃
    """
    def decorator(func: Callable[..., Any]) :
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # 使用 tenacity 进行重试
            retry_func = retry(
                stop=stop_after_attempt(attempts), # 尝试多少次后停止
                wait=wait_exponential(multiplier=1,min=min_wait,max=max_wait), # 每次尝试的等待时间
                retry=retry_if_exception_type(network_exceptions), # 什么错误会进行重试
                reraise=True,
                before_sleep=before_sleep_log(logger, logging.WARNING),# 每次调用失败都记录日志
            )(func)

            try:
                return retry_func(*args, **kwargs)
            except Exception as e:
                logger.error(f"工具[{func.__name__}] 重试 {attempts} 次后 仍然失败：{e}")
                # 进行函数降级
                if fallback:
                    logger.info(f"执行函数降级：{fallback.__name__}")
                    return fallback(*args, **kwargs)
                return "服务器繁忙，重试 {attempts} 次后 仍然失败，请稍后再试。"
        return wrapper
    return decorator