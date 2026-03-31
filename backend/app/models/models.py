"""
AI小说拆书系统 - ORM数据模型
严格按照架构设计文档实现
"""
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from .database import Base


class ProcessingStatus(enum.Enum):
    """处理状态枚举"""
    IDLE = "IDLE"
    UPLOADING = "UPLOADING"
    PREPROCESSING = "PREPROCESSING"
    EXTRACTING = "EXTRACTING"  # 章纲提取
    GENERATING = "GENERATING"   # 粗纲生成
    OUTLINING = "OUTLINING"    # 大纲生成
    WORLDING = "WORLDING"      # 世界纲生成
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"


class OutlineType(enum.Enum):
    """纲类型枚举"""
    CHAPTER = "CHAPTER"  # 章纲
    COARSE = "COARSE"    # 粗纲
    MAIN = "MAIN"       # 大纲
    WORLD = "WORLD"     # 世界纲


class OutlineStatus(enum.Enum):
    """纲状态枚举"""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


def generate_uuid() -> str:
    """生成UUID字符串"""
    return str(uuid.uuid4())


class Book(Base):
    """书籍表"""
    __tablename__ = "books"
    
    book_id = Column(String(36), primary_key=True, default=generate_uuid)
    title = Column(String(255), nullable=False)
    original_name = Column(String(255), nullable=False)
    file_type = Column(String(10), nullable=False)  # TXT/EPUB/DOC/DOCX/PDF
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    encoding = Column(String(20))  # UTF-8/GBK/GB2312
    total_chapters = Column(Integer, default=0)
    status = Column(String(20), default="IDLE")  # ProcessingStatus
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    chapters = relationship("Chapter", back_populates="book", cascade="all, delete-orphan")
    task = relationship("ProcessingTask", back_populates="book", uselist=False, cascade="all, delete-orphan")
    outlines = relationship("Outline", back_populates="book", cascade="all, delete-orphan")


class ProcessingTask(Base):
    """处理任务表"""
    __tablename__ = "processing_tasks"
    
    task_id = Column(String(36), primary_key=True, default=generate_uuid)
    book_id = Column(String(36), ForeignKey("books.book_id"), nullable=False)
    current_stage = Column(String(30), default="FILE_UPLOAD")
    stage_progress = Column(JSON, default=dict)  # {"UPLOADING": 100, "EXTRACTING": 45, ...}
    total_chapters = Column(Integer, default=0)
    completed_chapters = Column(Integer, default=0)
    status = Column(String(20), default="PENDING")  # PENDING/RUNNING/COMPLETED/FAILED
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关系
    book = relationship("Book", back_populates="task")
    errors = relationship("ErrorLog", back_populates="task", cascade="all, delete-orphan")


class Chapter(Base):
    """章节表"""
    __tablename__ = "chapters"
    
    chapter_id = Column(String(36), primary_key=True, default=generate_uuid)
    book_id = Column(String(36), ForeignKey("books.book_id"), nullable=False)
    chapter_index = Column(Integer, nullable=False)  # 0-based
    original_text = Column(Text, nullable=False)
    word_count = Column(Integer, nullable=False)
    start_offset = Column(Integer, nullable=False)
    end_offset = Column(Integer, nullable=False)
    status = Column(String(20), default="PENDING")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关系
    book = relationship("Book", back_populates="chapters")


class Outline(Base):
    """纲表 - 存储四层纲结构"""
    __tablename__ = "outlines"
    
    outline_id = Column(String(36), primary_key=True, default=generate_uuid)
    book_id = Column(String(36), ForeignKey("books.book_id"), nullable=False)
    outline_type = Column(String(10), nullable=False)  # OutlineType
    outline_index = Column(Integer)  # 类型内的序号
    chapter_index = Column(Integer)  # 仅章纲用：对应章节序号
    chapter_range_start = Column(Integer)  # 仅粗纲用
    chapter_range_end = Column(Integer)  # 仅粗纲用
    content_json = Column(JSON)  # 结构化内容
    summary = Column(Text)  # 概括（传递给上层）
    llm_response = Column(Text)  # LLM原始响应
    source_outline_ids = Column(JSON)  # 来源纲ID列表
    parent_outline_id = Column(String(36), ForeignKey("outlines.outline_id"))
    status = Column(String(20), default="PENDING")
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关系
    book = relationship("Book", back_populates="outlines")
    children = relationship("Outline", back_populates="parent", cascade="all")
    parent = relationship("Outline", back_populates="children", remote_side=[outline_id])


class ErrorLog(Base):
    """错误日志表"""
    __tablename__ = "errors_log"
    
    error_id = Column(String(36), primary_key=True, default=generate_uuid)
    task_id = Column(String(36), ForeignKey("processing_tasks.task_id"), nullable=False)
    book_id = Column(String(36), ForeignKey("books.book_id"), nullable=False)
    stage = Column(String(30), nullable=False)
    chapter_index = Column(Integer)
    error_type = Column(String(50), nullable=False)
    error_message = Column(Text, nullable=False)
    stack_trace = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # 关系
    task = relationship("ProcessingTask", back_populates="errors")
