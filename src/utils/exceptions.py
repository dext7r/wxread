"""
自定义异常类

定义了微信读书工具中使用的所有自定义异常类型，
提供更精确的错误分类和处理。
"""

from typing import Optional, Dict, Any


class WxReadError(Exception):
    """微信读书工具基础异常类"""
    
    def __init__(
        self, 
        message: str, 
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
    
    def __str__(self) -> str:
        if self.error_code:
            return f"[{self.error_code}] {self.message}"
        return self.message


class ConfigError(WxReadError):
    """配置相关异常"""
    
    def __init__(self, message: str, config_key: Optional[str] = None, **kwargs):
        super().__init__(message, error_code="CONFIG_ERROR", **kwargs)
        self.config_key = config_key


class NetworkError(WxReadError):
    """网络请求相关异常"""
    
    def __init__(
        self, 
        message: str, 
        status_code: Optional[int] = None,
        url: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, error_code="NETWORK_ERROR", **kwargs)
        self.status_code = status_code
        self.url = url


class AuthError(WxReadError):
    """认证相关异常"""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(message, error_code="AUTH_ERROR", **kwargs)


class PushError(WxReadError):
    """推送通知相关异常"""
    
    def __init__(
        self, 
        message: str, 
        push_method: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, error_code="PUSH_ERROR", **kwargs)
        self.push_method = push_method


class ValidationError(WxReadError):
    """数据验证相关异常"""
    
    def __init__(
        self, 
        message: str, 
        field_name: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, error_code="VALIDATION_ERROR", **kwargs)
        self.field_name = field_name


class RateLimitError(WxReadError):
    """频率限制异常"""
    
    def __init__(
        self, 
        message: str, 
        retry_after: Optional[int] = None,
        **kwargs
    ):
        super().__init__(message, error_code="RATE_LIMIT_ERROR", **kwargs)
        self.retry_after = retry_after


class CircuitBreakerError(WxReadError):
    """熔断器异常"""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(message, error_code="CIRCUIT_BREAKER_ERROR", **kwargs)
