"""
重试机制和熔断器

提供智能的重试机制和熔断器模式，用于处理网络请求失败等场景：
- 指数退避重试
- 熔断器模式
- 自定义重试条件
"""

import time
import random
import functools
from typing import Callable, Optional, Tuple, Type, Union, List
from enum import Enum
from datetime import datetime, timedelta

from .logger import get_logger
from .exceptions import CircuitBreakerError, RateLimitError


logger = get_logger(__name__)


class CircuitState(Enum):
    """熔断器状态"""
    CLOSED = "closed"      # 关闭状态，正常工作
    OPEN = "open"          # 开启状态，拒绝请求
    HALF_OPEN = "half_open"  # 半开状态，尝试恢复


def retry_with_backoff(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable] = None
):
    """
    指数退避重试装饰器
    
    Args:
        max_attempts: 最大重试次数
        base_delay: 基础延迟时间（秒）
        max_delay: 最大延迟时间（秒）
        backoff_factor: 退避因子
        jitter: 是否添加随机抖动
        exceptions: 需要重试的异常类型
        on_retry: 重试时的回调函数
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_attempts - 1:
                        logger.error(f"函数 {func.__name__} 重试 {max_attempts} 次后仍然失败")
                        raise
                    
                    # 计算延迟时间
                    delay = min(base_delay * (backoff_factor ** attempt), max_delay)
                    if jitter:
                        delay *= (0.5 + random.random() * 0.5)  # 添加50%的随机抖动
                    
                    logger.warning(
                        f"函数 {func.__name__} 第 {attempt + 1} 次执行失败: {e}, "
                        f"{delay:.2f}秒后重试"
                    )
                    
                    # 调用重试回调
                    if on_retry:
                        on_retry(attempt + 1, e, delay)
                    
                    time.sleep(delay)
                except Exception as e:
                    # 不在重试范围内的异常直接抛出
                    logger.error(f"函数 {func.__name__} 遇到不可重试的异常: {e}")
                    raise
            
            # 理论上不会到达这里
            raise last_exception
        
        return wrapper
    return decorator


class CircuitBreaker:
    """
    熔断器实现
    
    当失败次数超过阈值时，熔断器会开启，拒绝后续请求。
    经过一段时间后，熔断器会进入半开状态，尝试恢复服务。
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: Type[Exception] = Exception
    ):
        """
        初始化熔断器
        
        Args:
            failure_threshold: 失败阈值
            recovery_timeout: 恢复超时时间（秒）
            expected_exception: 预期的异常类型
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
        
        self.logger = get_logger(f"{__name__}.CircuitBreaker")
    
    def __call__(self, func):
        """装饰器调用"""
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return self._call_with_circuit_breaker(func, *args, **kwargs)
        return wrapper
    
    def _call_with_circuit_breaker(self, func, *args, **kwargs):
        """通过熔断器调用函数"""
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                self.logger.info("熔断器进入半开状态，尝试恢复")
            else:
                raise CircuitBreakerError(
                    f"熔断器开启中，拒绝调用 {func.__name__}"
                )
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise
    
    def _should_attempt_reset(self) -> bool:
        """判断是否应该尝试重置熔断器"""
        if self.last_failure_time is None:
            return True
        
        return (
            datetime.now() - self.last_failure_time
        ).total_seconds() >= self.recovery_timeout
    
    def _on_success(self):
        """成功时的处理"""
        if self.state == CircuitState.HALF_OPEN:
            self.logger.info("熔断器恢复正常，关闭熔断器")
        
        self.failure_count = 0
        self.state = CircuitState.CLOSED
    
    def _on_failure(self):
        """失败时的处理"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            self.logger.warning(
                f"失败次数达到阈值 {self.failure_threshold}，开启熔断器"
            )
    
    def reset(self):
        """手动重置熔断器"""
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
        self.logger.info("手动重置熔断器")
    
    @property
    def is_open(self) -> bool:
        """熔断器是否开启"""
        return self.state == CircuitState.OPEN
