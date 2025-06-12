"""
配置验证器

提供配置项的验证功能，确保配置的正确性和完整性：
- 类型验证
- 必填项检查
- 值范围验证
- 依赖关系验证
"""

import re
from typing import Any, Dict, List, Optional, Union, Callable
from urllib.parse import urlparse

from ..utils.exceptions import ConfigError, ValidationError
from ..utils.logger import get_logger


logger = get_logger(__name__)


class ConfigValidator:
    """配置验证器"""
    
    def __init__(self):
        self.validation_rules = {
            # 基础配置
            'READ_NUM': self._validate_read_num,
            'PUSH_METHOD': self._validate_push_method,
            
            # 推送配置
            'PUSHPLUS_TOKEN': self._validate_token,
            'TELEGRAM_BOT_TOKEN': self._validate_telegram_bot_token,
            'TELEGRAM_CHAT_ID': self._validate_telegram_chat_id,
            'WXPUSHER_SPT': self._validate_token,
            
            # 网络配置
            'http_proxy': self._validate_proxy_url,
            'https_proxy': self._validate_proxy_url,
            
            # 微信读书配置
            'WXREAD_CURL_BASH': self._validate_curl_bash,
        }
    
    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证完整配置
        
        Args:
            config: 配置字典
            
        Returns:
            Dict[str, Any]: 验证后的配置
            
        Raises:
            ConfigError: 配置验证失败
        """
        validated_config = {}
        errors = []
        
        # 验证各个配置项
        for key, value in config.items():
            try:
                if key in self.validation_rules:
                    validated_value = self.validation_rules[key](value)
                    validated_config[key] = validated_value
                else:
                    validated_config[key] = value
            except ValidationError as e:
                errors.append(f"{key}: {e.message}")
        
        # 验证依赖关系
        dependency_errors = self._validate_dependencies(validated_config)
        errors.extend(dependency_errors)
        
        if errors:
            raise ConfigError(
                f"配置验证失败: {'; '.join(errors)}",
                details={'errors': errors}
            )
        
        logger.info("配置验证通过")
        return validated_config
    
    def _validate_read_num(self, value: Any) -> int:
        """验证阅读次数"""
        if value is None:
            return 40  # 默认值
        
        try:
            num = int(value)
            if num <= 0:
                raise ValidationError("阅读次数必须大于0")
            if num > 1000:
                raise ValidationError("阅读次数不能超过1000")
            return num
        except (ValueError, TypeError):
            raise ValidationError("阅读次数必须是有效的整数")
    
    def _validate_push_method(self, value: Any) -> Optional[str]:
        """验证推送方式"""
        if not value or value == "":
            return None
        
        valid_methods = ['pushplus', 'telegram', 'wxpusher']
        if value not in valid_methods:
            raise ValidationError(
                f"推送方式必须是以下之一: {', '.join(valid_methods)}"
            )
        return value
    
    def _validate_token(self, value: Any) -> Optional[str]:
        """验证通用token"""
        if not value or value == "":
            return None
        
        if not isinstance(value, str):
            raise ValidationError("Token必须是字符串")
        
        if len(value.strip()) < 10:
            raise ValidationError("Token长度不能少于10个字符")
        
        return value.strip()
    
    def _validate_telegram_bot_token(self, value: Any) -> Optional[str]:
        """验证Telegram机器人token"""
        if not value or value == "":
            return None
        
        # Telegram bot token格式: 数字:字母数字字符
        pattern = r'^\d+:[A-Za-z0-9_-]+$'
        if not re.match(pattern, str(value)):
            raise ValidationError(
                "Telegram Bot Token格式不正确，应为: 数字:字母数字字符"
            )
        
        return str(value)
    
    def _validate_telegram_chat_id(self, value: Any) -> Optional[str]:
        """验证Telegram聊天ID"""
        if not value or value == "":
            return None
        
        # 可以是数字或@开头的用户名
        str_value = str(value)
        if str_value.startswith('@'):
            if len(str_value) < 2:
                raise ValidationError("Telegram用户名不能为空")
        else:
            try:
                int(str_value)
            except ValueError:
                raise ValidationError(
                    "Telegram Chat ID必须是数字或@开头的用户名"
                )
        
        return str_value
    
    def _validate_proxy_url(self, value: Any) -> Optional[str]:
        """验证代理URL"""
        if not value or value == "":
            return None
        
        try:
            parsed = urlparse(str(value))
            if not parsed.scheme or not parsed.netloc:
                raise ValidationError("代理URL格式不正确")
            
            if parsed.scheme not in ['http', 'https', 'socks4', 'socks5']:
                raise ValidationError(
                    "代理协议必须是http、https、socks4或socks5"
                )
            
            return str(value)
        except Exception:
            raise ValidationError("代理URL格式不正确")
    
    def _validate_curl_bash(self, value: Any) -> Optional[str]:
        """验证curl bash命令"""
        if not value or value == "":
            return None
        
        str_value = str(value)
        if not str_value.startswith('curl'):
            raise ValidationError("CURL_BASH必须以'curl'开头")
        
        # 检查是否包含必要的URL
        if 'weread.qq.com/web/book/read' not in str_value:
            raise ValidationError(
                "CURL_BASH必须包含微信读书的read接口URL"
            )
        
        return str_value
    
    def _validate_dependencies(self, config: Dict[str, Any]) -> List[str]:
        """验证配置项之间的依赖关系"""
        errors = []
        
        push_method = config.get('PUSH_METHOD')
        if push_method:
            # 检查推送方式对应的token是否存在
            if push_method == 'pushplus':
                if not config.get('PUSHPLUS_TOKEN'):
                    errors.append("使用pushplus推送时必须提供PUSHPLUS_TOKEN")
            
            elif push_method == 'telegram':
                if not config.get('TELEGRAM_BOT_TOKEN'):
                    errors.append("使用telegram推送时必须提供TELEGRAM_BOT_TOKEN")
                if not config.get('TELEGRAM_CHAT_ID'):
                    errors.append("使用telegram推送时必须提供TELEGRAM_CHAT_ID")
            
            elif push_method == 'wxpusher':
                if not config.get('WXPUSHER_SPT'):
                    errors.append("使用wxpusher推送时必须提供WXPUSHER_SPT")
        
        return errors
