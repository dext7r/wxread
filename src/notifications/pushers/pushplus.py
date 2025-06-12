"""
PushPlus推送器

实现PushPlus推送服务的具体功能
"""

import json
import requests
from typing import Dict, Any, Optional

from .base import BasePusher
from ...utils.exceptions import PushError


class PushPlusPusher(BasePusher):
    """PushPlus推送器"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_url = "https://www.pushplus.plus/send"
        self.token = config.get('token')
        
        if not self.token:
            raise PushError("PushPlus token未配置", push_method=self.name)
    
    def _send_message(self, content: str, title: Optional[str] = None) -> bool:
        """发送PushPlus消息"""
        if not title:
            title = "微信读书推送"
        
        payload = {
            "token": self.token,
            "title": title,
            "content": content,
            "template": "html"  # 支持HTML格式
        }
        
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'WxRead-Bot/2.0'
        }
        
        try:
            response = requests.post(
                self.api_url,
                data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
                headers=headers,
                timeout=30
            )
            
            response.raise_for_status()
            result = response.json()
            
            # 检查PushPlus API返回结果
            if result.get('code') == 200:
                self.logger.info(f"PushPlus推送成功: {result.get('msg', '')}")
                return True
            else:
                error_msg = result.get('msg', '未知错误')
                self.logger.error(f"PushPlus推送失败: {error_msg}")
                raise PushError(f"PushPlus API错误: {error_msg}", push_method=self.name)
                
        except requests.exceptions.RequestException as e:
            error_msg = f"PushPlus网络请求失败: {e}"
            self.logger.error(error_msg)
            raise PushError(error_msg, push_method=self.name)
        except json.JSONDecodeError as e:
            error_msg = f"PushPlus响应解析失败: {e}"
            self.logger.error(error_msg)
            raise PushError(error_msg, push_method=self.name)
    
    def validate_config(self) -> bool:
        """验证PushPlus配置"""
        if not self.token:
            self.logger.error("PushPlus token未配置")
            return False
        
        if len(self.token.strip()) < 10:
            self.logger.error("PushPlus token长度不足")
            return False
        
        return True
    
    def get_required_config_keys(self) -> list:
        """获取必需的配置键"""
        return ['token']
