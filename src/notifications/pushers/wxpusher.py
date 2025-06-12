"""
WxPusher推送器

实现WxPusher推送服务的具体功能
"""

import requests
from typing import Dict, Any, Optional
from urllib.parse import quote

from .base import BasePusher
from ...utils.exceptions import PushError


class WxPusherPusher(BasePusher):
    """WxPusher推送器"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.spt = config.get('spt')
        
        if not self.spt:
            raise PushError("WxPusher SPT未配置", push_method=self.name)
        
        # WxPusher极简API URL
        self.api_url_template = "https://wxpusher.zjiecode.com/api/send/message/{}/{}"
    
    def _send_message(self, content: str, title: Optional[str] = None) -> bool:
        """发送WxPusher消息"""
        # 组合标题和内容
        if title:
            message = f"{title}\n\n{content}"
        else:
            message = content
        
        # URL编码消息内容
        encoded_message = quote(message, safe='')
        
        # 构建请求URL
        api_url = self.api_url_template.format(self.spt, encoded_message)
        
        headers = {
            'User-Agent': 'WxRead-Bot/2.0'
        }
        
        try:
            response = requests.get(
                api_url,
                headers=headers,
                timeout=30
            )
            
            response.raise_for_status()
            
            # WxPusher极简API通常返回简单的文本响应
            response_text = response.text.strip()
            
            # 检查响应内容
            if 'success' in response_text.lower() or response.status_code == 200:
                self.logger.info(f"WxPusher推送成功: {response_text}")
                return True
            else:
                self.logger.error(f"WxPusher推送失败: {response_text}")
                raise PushError(f"WxPusher API错误: {response_text}", push_method=self.name)
                
        except requests.exceptions.RequestException as e:
            error_msg = f"WxPusher网络请求失败: {e}"
            self.logger.error(error_msg)
            raise PushError(error_msg, push_method=self.name)
    
    def validate_config(self) -> bool:
        """验证WxPusher配置"""
        if not self.spt:
            self.logger.error("WxPusher SPT未配置")
            return False
        
        if len(self.spt.strip()) < 10:
            self.logger.error("WxPusher SPT长度不足")
            return False
        
        return True
    
    def get_required_config_keys(self) -> list:
        """获取必需的配置键"""
        return ['spt']
