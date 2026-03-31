"""
AI小说拆书系统 - 配置模块
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """应用配置"""
    
    # API配置
    api_base_url: str = "https://api.n1n.ai/v1"
    api_key: str = "<YOUR_API_KEY>"
    model_name: str = "gpt-5.4-nano"
    
    # LLM参数
    temperature: float = 0.7
    max_tokens: int = 4096
    llm_timeout: int = 60
    
    # 数据库
    database_url: str = "sqlite+aiosqlite:///./data/novel_platform.db"
    
    # 文件存储
    upload_dir: str = "./data/uploads"
    max_file_size: int = 50 * 1024 * 1024  # 50MB
    
    # 分章配置
    chapter_size: int = 2000  # 每章字数
    keep_paragraph_complete: bool = True  # 保持段落完整
    
    # LangSmith追踪（可选）
    langsmith_api_key: Optional[str] = None
    langsmith_project: str = "novel-platform"
    
    # 服务器配置
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True
    
    # 并发配置
    max_concurrent_llm_calls: int = 10  # 最大并行LLM调用数
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# 全局配置实例
settings = Settings()
