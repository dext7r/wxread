"""
微信读书自动阅读工具

一个用于微信读书自动阅读的Python工具包，支持：
- 自动阅读时长累积
- 多种推送通知方式
- 灵活的配置管理
- 完善的错误处理和重试机制
"""

__version__ = "2.0.0"
__author__ = "wxread-team"
__description__ = "微信读书自动阅读工具"

from .core.bot import WxReadBot
from .config.manager import ConfigManager
from .notifications.manager import NotificationManager

__all__ = [
    "WxReadBot",
    "ConfigManager", 
    "NotificationManager",
]
