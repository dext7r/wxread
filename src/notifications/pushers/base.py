"""
推送器基类

定义了所有推送器的通用接口和基础功能：
- 统一的推送接口
- 重试机制
- 错误处理
- 日志记录
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import time
import random

from ...utils.logger import LoggerMixin
from ...utils.exceptions import PushError
from ...utils.retry import retry_with_backoff


class BasePusher(ABC, LoggerMixin):
    """推送器基类"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化推送器
        
        Args:
            config: 推送器配置
        """
        self.config = config
        self.name = self.__class__.__name__.replace('Pusher', '').lower()
    
    @abstractmethod
    def _send_message(self, content: str, title: Optional[str] = None) -> bool:
        """
        发送消息的具体实现
        
        Args:
            content: 消息内容
            title: 消息标题（可选）
            
        Returns:
            bool: 发送是否成功
            
        Raises:
            PushError: 推送失败
        """
        pass
    
    @retry_with_backoff(
        max_attempts=3,
        base_delay=1.0,
        max_delay=60.0,
        exceptions=(PushError,)
    )
    def send(self, content: str, title: Optional[str] = None) -> bool:
        """
        发送消息（带重试）
        
        Args:
            content: 消息内容
            title: 消息标题（可选）
            
        Returns:
            bool: 发送是否成功
        """
        try:
            self.logger.info(f"开始使用 {self.name} 发送推送消息")
            result = self._send_message(content, title)
            
            if result:
                self.logger.info(f"{self.name} 推送发送成功")
            else:
                self.logger.warning(f"{self.name} 推送发送失败")
            
            return result
            
        except Exception as e:
            error_msg = f"{self.name} 推送发送异常: {e}"
            self.logger.error(error_msg)
            raise PushError(error_msg, push_method=self.name)
    
    def validate_config(self) -> bool:
        """
        验证配置是否有效
        
        Returns:
            bool: 配置是否有效
        """
        return True
    
    def get_required_config_keys(self) -> list:
        """
        获取必需的配置键列表
        
        Returns:
            list: 必需的配置键
        """
        return []
    
    def _add_random_delay(self, min_seconds: float = 0.5, max_seconds: float = 2.0):
        """
        添加随机延迟，避免频率限制
        
        Args:
            min_seconds: 最小延迟秒数
            max_seconds: 最大延迟秒数
        """
        delay = random.uniform(min_seconds, max_seconds)
        time.sleep(delay)
    
    def __str__(self) -> str:
        """字符串表示"""
        return f"{self.__class__.__name__}(name={self.name})"
