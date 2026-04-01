"""
AI小说拆书系统 - 日志工具
"""
import logging
import json
from typing import Dict, Any, Optional
from datetime import datetime, timezone


class StructuredLogger:
    """结构化日志记录器"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # 确保只有一个处理器
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def _format_message(self, message: str, extra: Optional[Dict[str, Any]] = None) -> str:
        """格式化消息为结构化JSON"""
        log_data = {
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": self.logger.level
        }
        
        if extra:
            log_data.update(extra)
        
        return json.dumps(log_data, ensure_ascii=False)
    
    def info(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """记录信息级日志"""
        self.logger.info(self._format_message(message, extra))
    
    def warning(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """记录警告级日志"""
        self.logger.warning(self._format_message(message, extra))
    
    def error(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """记录错误级日志"""
        self.logger.error(self._format_message(message, extra))
    
    def critical(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """记录严重错误级日志"""
        self.logger.critical(self._format_message(message, extra))
    
    def debug(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """记录调试级日志"""
        self.logger.debug(self._format_message(message, extra))


# 全局日志器实例
logger = StructuredLogger("ai-novel-system")
