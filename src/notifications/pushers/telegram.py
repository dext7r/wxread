"""
Telegram推送器

实现Telegram Bot推送服务的具体功能
"""

import requests
from typing import Dict, Any, Optional

from .base import BasePusher
from ...utils.exceptions import PushError


class TelegramPusher(BasePusher):
    """Telegram推送器"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.bot_token = config.get('bot_token')
        self.chat_id = config.get('chat_id')
        self.http_proxy = config.get('http_proxy')
        self.https_proxy = config.get('https_proxy')
        
        if not self.bot_token:
            raise PushError("Telegram bot token未配置", push_method=self.name)
        if not self.chat_id:
            raise PushError("Telegram chat ID未配置", push_method=self.name)
        
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        
        # 设置代理
        self.proxies = {}
        if self.http_proxy:
            self.proxies['http'] = self.http_proxy
        if self.https_proxy:
            self.proxies['https'] = self.https_proxy
    
    def _send_message(self, content: str, title: Optional[str] = None) -> bool:
        """发送Telegram消息"""
        # 组合标题和内容
        if title:
            message = f"*{title}*\n\n{content}"
        else:
            message = content
        
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "Markdown",  # 支持Markdown格式
            "disable_web_page_preview": True
        }
        
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'WxRead-Bot/2.0'
        }
        
        # 首先尝试使用代理
        if self.proxies:
            try:
                return self._send_with_proxy(payload, headers)
            except Exception as e:
                self.logger.warning(f"代理发送失败，尝试直连: {e}")
        
        # 直连发送
        return self._send_direct(payload, headers)
    
    def _send_with_proxy(self, payload: dict, headers: dict) -> bool:
        """使用代理发送"""
        response = requests.post(
            self.api_url,
            json=payload,
            headers=headers,
            proxies=self.proxies,
            timeout=30
        )
        
        return self._handle_response(response, "代理")
    
    def _send_direct(self, payload: dict, headers: dict) -> bool:
        """直连发送"""
        try:
            response = requests.post(
                self.api_url,
                json=payload,
                headers=headers,
                timeout=30
            )
            
            return self._handle_response(response, "直连")
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Telegram直连发送失败: {e}"
            self.logger.error(error_msg)
            raise PushError(error_msg, push_method=self.name)
    
    def _handle_response(self, response: requests.Response, method: str) -> bool:
        """处理响应"""
        try:
            response.raise_for_status()
            result = response.json()
            
            if result.get('ok'):
                self.logger.info(f"Telegram {method}推送成功")
                return True
            else:
                error_msg = result.get('description', '未知错误')
                self.logger.error(f"Telegram {method}推送失败: {error_msg}")
                raise PushError(f"Telegram API错误: {error_msg}", push_method=self.name)
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Telegram {method}网络请求失败: {e}"
            self.logger.error(error_msg)
            raise PushError(error_msg, push_method=self.name)
        except ValueError as e:
            error_msg = f"Telegram {method}响应解析失败: {e}"
            self.logger.error(error_msg)
            raise PushError(error_msg, push_method=self.name)
    
    def validate_config(self) -> bool:
        """验证Telegram配置"""
        if not self.bot_token:
            self.logger.error("Telegram bot token未配置")
            return False
        
        if not self.chat_id:
            self.logger.error("Telegram chat ID未配置")
            return False
        
        # 验证bot token格式
        if ':' not in self.bot_token:
            self.logger.error("Telegram bot token格式不正确")
            return False
        
        return True
    
    def get_required_config_keys(self) -> list:
        """获取必需的配置键"""
        return ['bot_token', 'chat_id']
