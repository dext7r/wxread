"""
推送管理器

统一管理所有推送服务，提供：
- 推送器工厂
- 统一推送接口
- 推送器选择和切换
- 推送状态管理
"""

from typing import Dict, Any, Optional, Type
from enum import Enum

from .pushers.base import BasePusher
from .pushers.pushplus import PushPlusPusher
from .pushers.telegram import TelegramPusher
from .pushers.wxpusher import WxPusherPusher
from ..utils.exceptions import PushError, ConfigError
from ..utils.logger import LoggerMixin


class PushMethod(Enum):
    """推送方式枚举"""
    PUSHPLUS = "pushplus"
    TELEGRAM = "telegram"
    WXPUSHER = "wxpusher"


class NotificationManager(LoggerMixin):
    """推送管理器"""
    
    # 推送器映射
    PUSHER_MAP: Dict[str, Type[BasePusher]] = {
        PushMethod.PUSHPLUS.value: PushPlusPusher,
        PushMethod.TELEGRAM.value: TelegramPusher,
        PushMethod.WXPUSHER.value: WxPusherPusher,
    }
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化推送管理器
        
        Args:
            config: 推送配置
        """
        self.config = config
        self.method = config.get('method')
        self.pusher: Optional[BasePusher] = None
        
        if self.method:
            self._initialize_pusher()
    
    def _initialize_pusher(self):
        """初始化推送器"""
        if not self.method:
            return
        
        if self.method not in self.PUSHER_MAP:
            raise ConfigError(
                f"不支持的推送方式: {self.method}，"
                f"支持的方式: {list(self.PUSHER_MAP.keys())}"
            )
        
        pusher_class = self.PUSHER_MAP[self.method]
        
        try:
            self.pusher = pusher_class(self.config)
            self.logger.info(f"推送器 {self.method} 初始化成功")
        except Exception as e:
            error_msg = f"推送器 {self.method} 初始化失败: {e}"
            self.logger.error(error_msg)
            raise ConfigError(error_msg)
    
    def send(self, content: str, title: Optional[str] = None) -> bool:
        """
        发送推送消息
        
        Args:
            content: 消息内容
            title: 消息标题（可选）
            
        Returns:
            bool: 发送是否成功
            
        Raises:
            PushError: 推送失败
        """
        if not self.is_enabled():
            self.logger.info("推送未启用，跳过发送")
            return True
        
        if not self.pusher:
            raise PushError("推送器未初始化")
        
        try:
            return self.pusher.send(content, title)
        except Exception as e:
            error_msg = f"推送发送失败: {e}"
            self.logger.error(error_msg)
            raise PushError(error_msg, push_method=self.method)
    
    def is_enabled(self) -> bool:
        """检查推送是否启用"""
        return bool(self.method and self.pusher)
    
    def validate_config(self) -> bool:
        """验证推送配置"""
        if not self.method:
            return True  # 推送未启用，配置有效
        
        if not self.pusher:
            self.logger.error("推送器未初始化")
            return False
        
        return self.pusher.validate_config()
    
    def get_pusher_info(self) -> Dict[str, Any]:
        """获取推送器信息"""
        if not self.pusher:
            return {"enabled": False}
        
        return {
            "enabled": True,
            "method": self.method,
            "pusher_class": self.pusher.__class__.__name__,
            "required_config": self.pusher.get_required_config_keys(),
            "config_valid": self.pusher.validate_config()
        }
    
    def test_push(self) -> bool:
        """测试推送功能"""
        if not self.is_enabled():
            self.logger.info("推送未启用，无法测试")
            return False
        
        try:
            test_content = "这是一条测试消息，用于验证推送功能是否正常工作。"
            test_title = "微信读书推送测试"
            
            result = self.send(test_content, test_title)
            
            if result:
                self.logger.info("推送测试成功")
            else:
                self.logger.error("推送测试失败")
            
            return result
            
        except Exception as e:
            self.logger.error(f"推送测试异常: {e}")
            return False
    
    @classmethod
    def get_supported_methods(cls) -> list:
        """获取支持的推送方式列表"""
        return list(cls.PUSHER_MAP.keys())
    
    @classmethod
    def create_from_config(cls, config: Dict[str, Any]) -> 'NotificationManager':
        """
        从配置创建推送管理器
        
        Args:
            config: 完整配置字典
            
        Returns:
            NotificationManager: 推送管理器实例
        """
        push_config = {}
        method = config.get('PUSH_METHOD')
        
        if method:
            push_config['method'] = method
            
            if method == PushMethod.PUSHPLUS.value:
                push_config['token'] = config.get('PUSHPLUS_TOKEN')
            elif method == PushMethod.TELEGRAM.value:
                push_config['bot_token'] = config.get('TELEGRAM_BOT_TOKEN')
                push_config['chat_id'] = config.get('TELEGRAM_CHAT_ID')
                push_config['http_proxy'] = config.get('http_proxy')
                push_config['https_proxy'] = config.get('https_proxy')
            elif method == PushMethod.WXPUSHER.value:
                push_config['spt'] = config.get('WXPUSHER_SPT')
        
        return cls(push_config)
    
    def __str__(self) -> str:
        """字符串表示"""
        if self.is_enabled():
            return f"NotificationManager(method={self.method}, enabled=True)"
        else:
            return "NotificationManager(enabled=False)"
