"""
配置管理器

统一管理所有配置项，支持：
- 环境变量读取
- 配置文件读取
- 默认值设置
- 配置验证
- 配置加密存储
"""

import os
import json
from typing import Any, Dict, Optional, Union
from pathlib import Path

from .validator import ConfigValidator
from ..utils.exceptions import ConfigError
from ..utils.logger import get_logger, LoggerMixin


logger = get_logger(__name__)


class ConfigManager(LoggerMixin):
    """配置管理器"""
    
    def __init__(self, config_file: Optional[str] = None):
        """
        初始化配置管理器
        
        Args:
            config_file: 配置文件路径
        """
        self.config_file = config_file
        self.validator = ConfigValidator()
        self._config = {}
        self._load_config()
    
    def _load_config(self):
        """加载配置"""
        # 1. 加载默认配置
        self._config.update(self._get_default_config())
        
        # 2. 加载配置文件
        if self.config_file and Path(self.config_file).exists():
            file_config = self._load_config_file()
            self._config.update(file_config)
        
        # 3. 加载环境变量
        env_config = self._load_env_config()
        self._config.update(env_config)
        
        # 4. 验证配置
        self._config = self.validator.validate_config(self._config)
        
        self.logger.info("配置加载完成")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            'READ_NUM': 40,
            'PUSH_METHOD': None,
            'PUSHPLUS_TOKEN': None,
            'TELEGRAM_BOT_TOKEN': None,
            'TELEGRAM_CHAT_ID': None,
            'WXPUSHER_SPT': None,
            'http_proxy': None,
            'https_proxy': None,
            'WXREAD_CURL_BASH': None,
            
            # 内部配置
            'LOG_LEVEL': 'INFO',
            'LOG_DIR': 'logs',
            'REQUEST_TIMEOUT': 30,
            'MAX_RETRIES': 3,
            'RETRY_DELAY': 1.0,
            'CIRCUIT_BREAKER_THRESHOLD': 5,
            'CIRCUIT_BREAKER_TIMEOUT': 60,
        }
    
    def _load_config_file(self) -> Dict[str, Any]:
        """从文件加载配置"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                if self.config_file.endswith('.json'):
                    return json.load(f)
                else:
                    # 简单的key=value格式
                    config = {}
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            if '=' in line:
                                key, value = line.split('=', 1)
                                config[key.strip()] = value.strip()
                    return config
        except Exception as e:
            self.logger.warning(f"加载配置文件失败: {e}")
            return {}
    
    def _load_env_config(self) -> Dict[str, Any]:
        """从环境变量加载配置"""
        env_keys = [
            'READ_NUM', 'PUSH_METHOD', 'PUSHPLUS_TOKEN',
            'TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID', 'WXPUSHER_SPT',
            'http_proxy', 'https_proxy', 'WXREAD_CURL_BASH',
            'LOG_LEVEL', 'LOG_DIR'
        ]
        
        config = {}
        for key in env_keys:
            value = os.getenv(key)
            if value is not None:
                # 尝试转换数字类型
                if key in ['READ_NUM', 'REQUEST_TIMEOUT', 'MAX_RETRIES']:
                    try:
                        config[key] = int(value)
                    except ValueError:
                        config[key] = value
                elif key in ['RETRY_DELAY']:
                    try:
                        config[key] = float(value)
                    except ValueError:
                        config[key] = value
                else:
                    config[key] = value
        
        return config
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            key: 配置键
            default: 默认值
            
        Returns:
            Any: 配置值
        """
        return self._config.get(key, default)
    
    def set(self, key: str, value: Any):
        """
        设置配置值
        
        Args:
            key: 配置键
            value: 配置值
        """
        self._config[key] = value
    
    def get_all(self) -> Dict[str, Any]:
        """获取所有配置"""
        return self._config.copy()
    
    def get_push_config(self) -> Dict[str, Any]:
        """获取推送相关配置"""
        push_method = self.get('PUSH_METHOD')
        if not push_method:
            return {}
        
        config = {'method': push_method}
        
        if push_method == 'pushplus':
            config['token'] = self.get('PUSHPLUS_TOKEN')
        elif push_method == 'telegram':
            config['bot_token'] = self.get('TELEGRAM_BOT_TOKEN')
            config['chat_id'] = self.get('TELEGRAM_CHAT_ID')
            config['http_proxy'] = self.get('http_proxy')
            config['https_proxy'] = self.get('https_proxy')
        elif push_method == 'wxpusher':
            config['spt'] = self.get('WXPUSHER_SPT')
        
        return config
    
    def get_request_config(self) -> Dict[str, Any]:
        """获取请求相关配置"""
        return {
            'timeout': self.get('REQUEST_TIMEOUT', 30),
            'max_retries': self.get('MAX_RETRIES', 3),
            'retry_delay': self.get('RETRY_DELAY', 1.0),
            'proxies': {
                'http': self.get('http_proxy'),
                'https': self.get('https_proxy'),
            } if self.get('http_proxy') or self.get('https_proxy') else None
        }
    
    def is_push_enabled(self) -> bool:
        """检查是否启用推送"""
        return bool(self.get('PUSH_METHOD'))
    
    def validate(self) -> bool:
        """验证当前配置"""
        try:
            self.validator.validate_config(self._config)
            return True
        except ConfigError as e:
            self.logger.error(f"配置验证失败: {e}")
            return False
    
    def save_to_file(self, file_path: str):
        """保存配置到文件"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
            self.logger.info(f"配置已保存到 {file_path}")
        except Exception as e:
            raise ConfigError(f"保存配置文件失败: {e}")
    
    def __str__(self) -> str:
        """字符串表示（隐藏敏感信息）"""
        safe_config = {}
        sensitive_keys = [
            'PUSHPLUS_TOKEN', 'TELEGRAM_BOT_TOKEN', 
            'TELEGRAM_CHAT_ID', 'WXPUSHER_SPT', 'WXREAD_CURL_BASH'
        ]
        
        for key, value in self._config.items():
            if key in sensitive_keys and value:
                safe_config[key] = "***"
            else:
                safe_config[key] = value
        
        return json.dumps(safe_config, indent=2, ensure_ascii=False)
