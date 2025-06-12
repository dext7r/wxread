"""
加密和哈希工具

提供微信读书接口所需的加密和哈希功能：
- 数据编码
- 哈希计算
- 签名生成
- 随机数生成
"""

import hashlib
import random
import time
import urllib.parse
from typing import Dict, Any, Union

from ..utils.logger import get_logger


logger = get_logger(__name__)


class CryptoUtils:
    """加密工具类"""
    
    # 微信读书加密密钥（从原代码中提取）
    ENCRYPTION_KEY = "3c5c8717f3daf09iop3423zafeqoi"
    
    @staticmethod
    def encode_data(data: Dict[str, Any]) -> str:
        """
        对数据进行URL编码
        
        Args:
            data: 要编码的数据字典
            
        Returns:
            str: 编码后的字符串
        """
        try:
            # 按键名排序并进行URL编码
            encoded_pairs = []
            for key in sorted(data.keys()):
                value = str(data[key])
                encoded_value = urllib.parse.quote(value, safe='')
                encoded_pairs.append(f"{key}={encoded_value}")
            
            result = '&'.join(encoded_pairs)
            logger.debug(f"数据编码完成，长度: {len(result)}")
            return result
            
        except Exception as e:
            logger.error(f"数据编码失败: {e}")
            raise
    
    @staticmethod
    def calculate_hash(input_string: str) -> str:
        """
        计算自定义哈希值（基于原始算法）
        
        Args:
            input_string: 输入字符串
            
        Returns:
            str: 哈希值
        """
        try:
            # 原始哈希算法的Python实现
            _7032f5 = 0x15051505
            _cc1055 = _7032f5
            length = len(input_string)
            _19094e = length - 1
            
            while _19094e > 0:
                char_code = ord(input_string[_19094e])
                shift_amount = (length - _19094e) % 30
                _7032f5 = 0x7fffffff & (_7032f5 ^ char_code << shift_amount)
                
                if _19094e > 0:
                    char_code_prev = ord(input_string[_19094e - 1])
                    shift_amount_prev = _19094e % 30
                    _cc1055 = 0x7fffffff & (_cc1055 ^ char_code_prev << shift_amount_prev)
                
                _19094e -= 2
            
            result = hex(_7032f5 + _cc1055)[2:].lower()
            logger.debug(f"哈希计算完成: {result}")
            return result
            
        except Exception as e:
            logger.error(f"哈希计算失败: {e}")
            raise
    
    @staticmethod
    def generate_signature(timestamp: int, random_num: int) -> str:
        """
        生成签名
        
        Args:
            timestamp: 时间戳（毫秒）
            random_num: 随机数
            
        Returns:
            str: SHA256签名
        """
        try:
            # 组合签名字符串
            sign_string = f"{timestamp}{random_num}{CryptoUtils.ENCRYPTION_KEY}"
            
            # 计算SHA256哈希
            signature = hashlib.sha256(sign_string.encode()).hexdigest()
            
            logger.debug(f"签名生成完成，长度: {len(signature)}")
            return signature
            
        except Exception as e:
            logger.error(f"签名生成失败: {e}")
            raise
    
    @staticmethod
    def generate_random_number(min_val: int = 0, max_val: int = 1000) -> int:
        """
        生成随机数
        
        Args:
            min_val: 最小值
            max_val: 最大值
            
        Returns:
            int: 随机数
        """
        return random.randint(min_val, max_val)
    
    @staticmethod
    def generate_timestamp() -> tuple:
        """
        生成时间戳
        
        Returns:
            tuple: (秒级时间戳, 毫秒级时间戳)
        """
        current_time = int(time.time())
        timestamp_ms = int(current_time * 1000) + CryptoUtils.generate_random_number(0, 1000)
        
        return current_time, timestamp_ms
    
    @staticmethod
    def create_request_data(
        base_data: Dict[str, Any],
        book_id: str,
        chapter_id: str,
        last_time: int
    ) -> Dict[str, Any]:
        """
        创建请求数据
        
        Args:
            base_data: 基础数据模板
            book_id: 书籍ID
            chapter_id: 章节ID
            last_time: 上次请求时间
            
        Returns:
            Dict[str, Any]: 完整的请求数据
        """
        try:
            # 复制基础数据
            data = base_data.copy()
            
            # 移除旧的签名
            data.pop('s', None)
            
            # 设置书籍和章节
            data['b'] = book_id
            data['c'] = chapter_id
            
            # 生成时间戳
            current_time, timestamp_ms = CryptoUtils.generate_timestamp()
            data['ct'] = current_time
            data['ts'] = timestamp_ms
            data['rt'] = current_time - last_time
            
            # 生成随机数
            data['rn'] = CryptoUtils.generate_random_number()
            
            # 生成签名
            data['sg'] = CryptoUtils.generate_signature(timestamp_ms, data['rn'])
            
            # 计算最终哈希
            encoded_data = CryptoUtils.encode_data(data)
            data['s'] = CryptoUtils.calculate_hash(encoded_data)
            
            logger.debug("请求数据创建完成")
            return data
            
        except Exception as e:
            logger.error(f"请求数据创建失败: {e}")
            raise
    
    @staticmethod
    def validate_response(response_data: Dict[str, Any]) -> bool:
        """
        验证响应数据
        
        Args:
            response_data: 响应数据
            
        Returns:
            bool: 验证是否通过
        """
        try:
            # 检查基本字段
            if 'succ' not in response_data:
                logger.warning("响应缺少succ字段")
                return False
            
            if response_data.get('succ') != 1:
                logger.warning(f"响应succ字段值异常: {response_data.get('succ')}")
                return False
            
            # 检查synckey字段（可选）
            if 'synckey' in response_data:
                logger.debug("响应包含synckey字段")
            else:
                logger.debug("响应不包含synckey字段")
            
            return True
            
        except Exception as e:
            logger.error(f"响应验证失败: {e}")
            return False
