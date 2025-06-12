"""
微信读书自动阅读机器人

核心业务逻辑类，负责：
- 自动阅读流程控制
- Cookie管理和刷新
- 错误处理和恢复
- 阅读进度跟踪
"""

import time
import random
from typing import Dict, Any, List, Optional

from .crypto import CryptoUtils
from .request_manager import RequestManager
from ..config.manager import ConfigManager
from ..notifications.manager import NotificationManager
from ..utils.logger import LoggerMixin
from ..utils.exceptions import WxReadError, AuthError, NetworkError


class WxReadBot(LoggerMixin):
    """微信读书自动阅读机器人"""
    
    def __init__(self, config_manager: ConfigManager):
        """
        初始化机器人
        
        Args:
            config_manager: 配置管理器
        """
        self.config = config_manager
        self.notification = NotificationManager.create_from_config(
            config_manager.get_all()
        )
        
        # 请求管理器
        self.request_manager = RequestManager(
            config_manager.get_request_config()
        )
        
        # 阅读配置
        self.read_num = config_manager.get('READ_NUM', 40)
        
        # 初始化数据
        self._initialize_data()
        
        self.logger.info("微信读书机器人初始化完成")
    
    def _initialize_data(self):
        """初始化数据"""
        # 从配置中获取curl bash命令并解析
        curl_bash = self.config.get('WXREAD_CURL_BASH')
        if curl_bash:
            self.headers, self.cookies = self._parse_curl_bash(curl_bash)
        else:
            # 使用默认配置（兼容旧版本）
            self.headers = self._get_default_headers()
            self.cookies = self._get_default_cookies()
        
        # 基础数据模板
        self.base_data = {
            "appId": "wb182564874603h266381671",
            "b": "ce032b305a9bc1ce0b0dd2a",
            "c": "7f632b502707f6ffaa6bf2e",
            "ci": 27,
            "co": 389,
            "sm": "19聚会《三体》网友的聚会地点是一处僻静",
            "pr": 74,
            "rt": 15,
            "ps": "4ee326507a65a465g015fae",
            "pc": "aab32e207a65a466g010615",
        }
        
        # 书籍和章节列表
        self.book_ids = [
            "36d322f07186022636daa5e", "6f932ec05dd9eb6f96f14b9",
            "43f3229071984b9343f04a4", "d7732ea0813ab7d58g0184b8",
            "3d03298058a9443d052d409", "4fc328a0729350754fc56d4",
            "a743220058a92aa746632c0", "140329d0716ce81f140468e",
            "1d9321c0718ff5e11d9afe8", "ff132750727dc0f6ff1f7b5",
            "e8532a40719c4eb7e851cbe", "9b13257072562b5c9b1c8d6"
        ]
        
        self.chapter_ids = [
            "ecc32f3013eccbc87e4b62e", "a87322c014a87ff679a21ea",
            "e4d32d5015e4da3b7fbb1fa", "16732dc0161679091c5aeb1",
            "8f132430178f14e45fce0f7", "c9f326d018c9f0f895fb5e4",
            "45c322601945c48cce2e120", "d3d322001ad3d9446802347",
            "65132ca01b6512bd43d90e3", "c20321001cc20ad4d76f5ae",
            "c51323901dc51ce410c121b", "aab325601eaab3238922e53",
            "9bf32f301f9bf31c7ff0a60", "c7432af0210c74d97b01b1c",
            "70e32fb021170efdf2eca12", "6f4322302126f4922f45dec"
        ]
    
    def _parse_curl_bash(self, curl_bash: str) -> tuple:
        """
        解析curl bash命令
        
        Args:
            curl_bash: curl bash命令
            
        Returns:
            tuple: (headers, cookies)
        """
        # 这里应该实现curl bash解析逻辑
        # 为了简化，暂时返回默认值
        return self._get_default_headers(), self._get_default_cookies()
    
    def _get_default_headers(self) -> Dict[str, str]:
        """获取默认请求头"""
        return {
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'content-type': 'application/json',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
        }
    
    def _get_default_cookies(self) -> Dict[str, str]:
        """获取默认Cookie"""
        return {
            'RK': 'oxEY1bTnXf',
            'ptcz': '53e3b35a9486dd63c4d06430b05aa169402117fc407dc5cc9329b41e59f62e2b',
            'pac_uid': '0_e63870bcecc18',
            'iip': '0',
        }
    
    def refresh_cookie(self) -> bool:
        """
        刷新Cookie
        
        Returns:
            bool: 刷新是否成功
        """
        try:
            self.logger.info("开始刷新Cookie")
            
            new_skey = self.request_manager.renew_cookie(
                self.headers, self.cookies
            )
            
            if new_skey:
                self.cookies['wr_skey'] = new_skey
                self.logger.info(f"Cookie刷新成功，新密钥: {new_skey}")
                return True
            else:
                error_msg = "无法获取新密钥，可能是配置有误"
                self.logger.error(error_msg)
                self._send_error_notification(error_msg)
                return False
                
        except Exception as e:
            error_msg = f"Cookie刷新失败: {e}"
            self.logger.error(error_msg)
            self._send_error_notification(error_msg)
            return False
    
    def fix_synckey(self) -> bool:
        """
        修复synckey
        
        Returns:
            bool: 修复是否成功
        """
        try:
            self.logger.info("尝试修复synckey")
            return self.request_manager.fix_synckey(
                self.headers, self.cookies
            )
        except Exception as e:
            self.logger.error(f"synckey修复失败: {e}")
            return False
    
    def read_once(self, book_id: str, chapter_id: str, last_time: int) -> tuple:
        """
        执行一次阅读
        
        Args:
            book_id: 书籍ID
            chapter_id: 章节ID
            last_time: 上次阅读时间
            
        Returns:
            tuple: (是否成功, 当前时间, 错误信息)
        """
        try:
            # 创建请求数据
            request_data = CryptoUtils.create_request_data(
                self.base_data, book_id, chapter_id, last_time
            )
            
            # 发送请求
            response = self.request_manager.read_book(
                request_data, self.headers, self.cookies
            )
            
            # 验证响应
            if CryptoUtils.validate_response(response):
                current_time = request_data['ct']
                
                if 'synckey' in response:
                    return True, current_time, None
                else:
                    # 尝试修复synckey
                    self.logger.warning("响应缺少synckey，尝试修复")
                    self.fix_synckey()
                    return False, last_time, "缺少synckey"
            else:
                # Cookie可能过期，尝试刷新
                self.logger.warning("响应验证失败，尝试刷新Cookie")
                if self.refresh_cookie():
                    return False, last_time, "Cookie已刷新"
                else:
                    return False, last_time, "Cookie刷新失败"
                    
        except Exception as e:
            error_msg = f"阅读请求失败: {e}"
            self.logger.error(error_msg)
            return False, last_time, error_msg
    
    def start_reading(self) -> Dict[str, Any]:
        """
        开始自动阅读
        
        Returns:
            Dict[str, Any]: 阅读结果
        """
        self.logger.info(f"开始自动阅读，目标次数: {self.read_num}")
        
        # 初始化Cookie
        if not self.refresh_cookie():
            raise AuthError("初始Cookie刷新失败")
        
        # 阅读统计
        success_count = 0
        last_time = int(time.time()) - 30
        
        for attempt in range(1, self.read_num + 1):
            self.logger.info(f"第 {attempt} 次阅读尝试")
            
            # 随机选择书籍和章节
            book_id = random.choice(self.book_ids)
            chapter_id = random.choice(self.chapter_ids)
            
            # 执行阅读
            success, current_time, error = self.read_once(
                book_id, chapter_id, last_time
            )
            
            if success:
                success_count += 1
                last_time = current_time
                reading_minutes = success_count * 0.5
                
                self.logger.info(f"阅读成功，累计时长: {reading_minutes} 分钟")
                
                # 等待30秒
                time.sleep(30)
            else:
                self.logger.warning(f"阅读失败: {error}")
                # 失败时等待较短时间
                time.sleep(5)
        
        # 计算结果
        total_minutes = success_count * 0.5
        result = {
            'success_count': success_count,
            'total_attempts': self.read_num,
            'reading_minutes': total_minutes,
            'success_rate': success_count / self.read_num * 100
        }
        
        self.logger.info(f"阅读完成，成功 {success_count}/{self.read_num} 次，累计 {total_minutes} 分钟")
        
        # 发送完成通知
        self._send_completion_notification(result)
        
        return result
    
    def _send_completion_notification(self, result: Dict[str, Any]):
        """发送完成通知"""
        if self.notification.is_enabled():
            content = (
                f"🎉 微信读书自动阅读完成！\n"
                f"⏱️ 阅读时长：{result['reading_minutes']} 分钟\n"
                f"📊 成功率：{result['success_rate']:.1f}%\n"
                f"✅ 成功次数：{result['success_count']}/{result['total_attempts']}"
            )
            
            try:
                self.notification.send(content, "微信读书完成通知")
            except Exception as e:
                self.logger.error(f"发送完成通知失败: {e}")
    
    def _send_error_notification(self, error_msg: str):
        """发送错误通知"""
        if self.notification.is_enabled():
            content = f"❌ 微信读书自动阅读出现错误：\n{error_msg}"
            
            try:
                self.notification.send(content, "微信读书错误通知")
            except Exception as e:
                self.logger.error(f"发送错误通知失败: {e}")
    
    def close(self):
        """关闭机器人"""
        if self.request_manager:
            self.request_manager.close()
        self.logger.info("微信读书机器人已关闭")
