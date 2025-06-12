"""
HTTP请求管理器

提供统一的HTTP请求管理功能：
- 连接池管理
- 请求重试
- 超时控制
- 错误处理
- Cookie管理
"""

import json
import time
from typing import Dict, Any, Optional, Union
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ..utils.logger import LoggerMixin
from ..utils.exceptions import NetworkError, AuthError
from ..utils.retry import retry_with_backoff, CircuitBreaker


class RequestManager(LoggerMixin):
    """HTTP请求管理器"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化请求管理器
        
        Args:
            config: 请求配置
        """
        self.config = config
        self.timeout = config.get('timeout', 30)
        self.max_retries = config.get('max_retries', 3)
        self.retry_delay = config.get('retry_delay', 1.0)
        self.proxies = config.get('proxies')
        
        # 创建会话
        self.session = self._create_session()
        
        # 熔断器
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60,
            expected_exception=NetworkError
        )
        
        # 微信读书相关URL
        self.urls = {
            'read': 'https://weread.qq.com/web/book/read',
            'renew': 'https://weread.qq.com/web/login/renewal',
            'fix_synckey': 'https://weread.qq.com/web/book/chapterInfos'
        }
    
    def _create_session(self) -> requests.Session:
        """创建HTTP会话"""
        session = requests.Session()
        
        # 配置重试策略
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST"]
        )
        
        # 配置适配器
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,
            pool_maxsize=20
        )
        
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # 设置代理
        if self.proxies:
            session.proxies.update(self.proxies)
        
        self.logger.info("HTTP会话创建完成")
        return session
    
    @retry_with_backoff(
        max_attempts=3,
        base_delay=1.0,
        exceptions=(NetworkError,)
    )
    def post_json(
        self,
        url: str,
        data: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
        cookies: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        发送JSON POST请求
        
        Args:
            url: 请求URL
            data: 请求数据
            headers: 请求头
            cookies: Cookie
            
        Returns:
            Dict[str, Any]: 响应数据
            
        Raises:
            NetworkError: 网络请求失败
        """
        try:
            # 准备请求参数
            request_headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            if headers:
                request_headers.update(headers)
            
            # 序列化数据
            json_data = json.dumps(data, separators=(',', ':'), ensure_ascii=False)
            
            self.logger.debug(f"发送POST请求: {url}")
            
            # 发送请求
            response = self.session.post(
                url,
                data=json_data.encode('utf-8'),
                headers=request_headers,
                cookies=cookies,
                timeout=self.timeout
            )
            
            # 检查响应状态
            response.raise_for_status()
            
            # 解析响应
            try:
                result = response.json()
                self.logger.debug(f"请求成功，响应长度: {len(response.text)}")
                return result
            except json.JSONDecodeError as e:
                raise NetworkError(f"响应JSON解析失败: {e}", url=url)
        
        except requests.exceptions.Timeout:
            raise NetworkError(f"请求超时: {url}", url=url)
        except requests.exceptions.ConnectionError as e:
            raise NetworkError(f"连接错误: {e}", url=url)
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response else None
            raise NetworkError(f"HTTP错误: {e}", status_code=status_code, url=url)
        except Exception as e:
            raise NetworkError(f"请求异常: {e}", url=url)
    
    def read_book(
        self,
        data: Dict[str, Any],
        headers: Dict[str, str],
        cookies: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        发送阅读请求
        
        Args:
            data: 阅读数据
            headers: 请求头
            cookies: Cookie
            
        Returns:
            Dict[str, Any]: 响应数据
        """
        return self.circuit_breaker._call_with_circuit_breaker(
            self.post_json,
            self.urls['read'],
            data,
            headers,
            cookies
        )
    
    def renew_cookie(
        self,
        headers: Dict[str, str],
        cookies: Dict[str, str]
    ) -> Optional[str]:
        """
        刷新Cookie
        
        Args:
            headers: 请求头
            cookies: Cookie
            
        Returns:
            Optional[str]: 新的wr_skey值
        """
        try:
            cookie_data = {"rq": "%2Fweb%2Fbook%2Fread"}
            
            response = self.session.post(
                self.urls['renew'],
                data=json.dumps(cookie_data, separators=(',', ':')),
                headers=headers,
                cookies=cookies,
                timeout=self.timeout
            )
            
            response.raise_for_status()
            
            # 从响应头中提取新的wr_skey
            set_cookie_header = response.headers.get('Set-Cookie', '')
            for cookie in set_cookie_header.split(';'):
                if "wr_skey" in cookie:
                    new_skey = cookie.split('=')[-1][:8]
                    self.logger.info(f"Cookie刷新成功，新密钥: {new_skey}")
                    return new_skey
            
            self.logger.warning("未找到新的wr_skey")
            return None
            
        except Exception as e:
            self.logger.error(f"Cookie刷新失败: {e}")
            raise NetworkError(f"Cookie刷新失败: {e}")
    
    def fix_synckey(
        self,
        headers: Dict[str, str],
        cookies: Dict[str, str],
        book_ids: list = None
    ) -> bool:
        """
        修复synckey
        
        Args:
            headers: 请求头
            cookies: Cookie
            book_ids: 书籍ID列表
            
        Returns:
            bool: 修复是否成功
        """
        try:
            if not book_ids:
                book_ids = ["3300060341"]  # 默认书籍ID
            
            data = {"bookIds": book_ids}
            
            response = self.session.post(
                self.urls['fix_synckey'],
                data=json.dumps(data, separators=(',', ':')),
                headers=headers,
                cookies=cookies,
                timeout=self.timeout
            )
            
            response.raise_for_status()
            self.logger.info("synckey修复请求发送成功")
            return True
            
        except Exception as e:
            self.logger.error(f"synckey修复失败: {e}")
            return False
    
    def close(self):
        """关闭会话"""
        if self.session:
            self.session.close()
            self.logger.info("HTTP会话已关闭")
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()
