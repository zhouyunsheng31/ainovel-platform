"""
AI小说拆书系统 - Pydantic数据模型（API请求/响应）
严格遵循OpenAPI规范
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ================================
# 枚举定义
# ================================

class BookStatus(str, Enum):
    """书籍状态"""
    IDLE = "IDLE"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"


class ProcessingStage(str, Enum):
    """处理阶段"""
    FILE_UPLOAD = "FILE_UPLOAD"
    TEXT_PREPROCESS = "TEXT_PREPROCESS"
    CHAPTER_OUTLINE = "CHAPTER_OUTLINE"
    COARSE_OUTLINE = "COARSE_OUTLINE"
    MAIN_OUTLINE = "MAIN_OUTLINE"
    WORLD_OUTLINE = "WORLD_OUTLINE"


class TaskStatusEnum(str, Enum):
    """任务状态"""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class OutlineTypeEnum(str, Enum):
    """纲类型"""
    CHAPTER = "CHAPTER"
    COARSE = "COARSE"
    MAIN = "MAIN"
    WORLD = "WORLD"


class OutlineStatusEnum(str, Enum):
    """纲状态"""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


# ================================
# API响应基类
# ================================

class APIResponse(BaseModel):
    """通用API响应包装"""
    success: bool = True
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


class ErrorResponse(APIResponse):
    """错误响应"""
    success: bool = False
    data: Optional[Dict[str, Any]] = None
    error: Dict[str, Any]


# ================================
# 书籍相关模型
# ================================

class BookCreate(BaseModel):
    """创建书籍请求"""
    title: Optional[str] = None
    author: Optional[str] = None


class BookSummary(BaseModel):
    """书籍列表项"""
    bookId: str
    title: str
    originalName: str
    fileType: str
    fileSize: int
    totalChapters: int = 0
    status: BookStatus
    createdAt: str
    updatedAt: str


class BookDetail(BookSummary):
    """书籍详情"""
    encoding: Optional[str] = None


class UploadBookData(BaseModel):
    """上传响应数据"""
    bookId: str
    taskId: str
    fileName: str
    fileSize: int
    status: str = "UPLOADING"
    message: str


class UploadBookResponse(APIResponse):
    """上传响应"""
    data: UploadBookData


class BookListData(BaseModel):
    """书籍列表数据"""
    books: List[BookSummary]
    pagination: Dict[str, int]


class BookListResponse(APIResponse):
    """书籍列表响应"""
    data: BookListData


class BookDetailResponse(APIResponse):
    """书籍详情响应"""
    data: BookDetail


class DeleteBookResponse(APIResponse):
    """删除书籍响应"""
    data: Dict[str, str]


# ================================
# 纲相关模型
# ================================

class OutlineTreeNode(BaseModel):
    """纲树节点"""
    outlineId: str
    outlineType: OutlineTypeEnum
    outlineIndex: Optional[int] = None
    label: str
    summary: Optional[str] = None
    status: OutlineStatusEnum = OutlineStatusEnum.PENDING
    chapterRange: Optional[List[int]] = None
    childCount: int = 0
    children: List["OutlineTreeNode"] = []


class OutlineTreeData(BaseModel):
    """纲树数据"""
    bookId: str
    tree: OutlineTreeNode


class OutlineTreeResponse(APIResponse):
    """纲树响应"""
    data: OutlineTreeData


class ChapterOutlineContent(BaseModel):
    """章纲内容"""
    generalStyle: Optional[str] = None
    globalVisualRhythm: Optional[str] = None
    settingsTemplate: Optional[Dict[str, Any]] = None
    plotStyleIntegration: Optional[Dict[str, Any]] = None
    summary: str


class GenericOutlineContent(BaseModel):
    """通用纲内容"""
    summary: str
    beatAnalysis: Optional[Dict[str, Any]] = None  # 起承转合
    plotRhythm: Optional[str] = None  # 剧情节奏
    plotAnalysis: Optional[str] = None  # 剧情分析
    metadata: Optional[Dict[str, Any]] = None


class OutlineDetailData(BaseModel):
    """纲详情数据"""
    outlineId: str
    bookId: str
    outlineType: OutlineTypeEnum
    chapterIndex: Optional[int] = None
    status: OutlineStatusEnum
    content: Dict[str, Any]
    summary: str
    createdAt: str


class OutlineDetailResponse(APIResponse):
    """纲详情响应"""
    data: OutlineDetailData


class CopyOutlineData(BaseModel):
    """复制纲响应数据"""
    outlineId: str
    outlineType: OutlineTypeEnum
    copyContent: str
    copyFormat: str = "text"


class CopyOutlineResponse(APIResponse):
    """复制纲响应"""
    data: CopyOutlineData


# ================================
# 任务相关模型
# ================================

class StageProgress(BaseModel):
    """阶段进度"""
    FILE_UPLOAD: int = 0
    TEXT_PREPROCESS: int = 0
    CHAPTER_OUTLINE: int = 0
    COARSE_OUTLINE: int = 0
    MAIN_OUTLINE: int = 0
    WORLD_OUTLINE: int = 0


class TaskStatusData(BaseModel):
    """任务状态数据"""
    taskId: str
    bookId: str
    status: TaskStatusEnum
    currentStage: ProcessingStage
    stageProgress: StageProgress
    totalChapters: int = 0
    completedChapters: int = 0
    errorCount: int = 0
    startTime: str
    endTime: Optional[str] = None
    estimatedTimeRemaining: Optional[int] = None


class TaskStatusResponse(APIResponse):
    """任务状态响应"""
    data: TaskStatusData


class TaskErrorItem(BaseModel):
    """任务错误项"""
    errorId: str
    stage: ProcessingStage
    chapterIndex: Optional[int] = None
    errorType: str
    errorMessage: str
    timestamp: str


class TaskErrorsData(BaseModel):
    """任务错误数据"""
    taskId: str
    totalErrors: int
    errors: List[TaskErrorItem]


class TaskErrorsResponse(APIResponse):
    """任务错误响应"""
    data: TaskErrorsData


class BookProcessingStatusData(BaseModel):
    """书籍维度处理状态数据"""
    bookId: str
    status: BookStatus
    taskId: Optional[str] = None
    currentStage: Optional[ProcessingStage] = None
    stageProgress: Dict[str, int] = {}


class BookProcessingStatusResponse(APIResponse):
    """书籍维度处理状态响应"""
    data: BookProcessingStatusData


# ================================
# WebSocket消息模型
# ================================

class WebSocketProgressPayload(BaseModel):
    """进度推送消息"""
    taskId: str
    stage: ProcessingStage
    progress: int
    total: int
    completed: int
    message: str


class WebSocketOutlineUpdatePayload(BaseModel):
    """纲更新消息"""
    outlineId: str
    outlineType: OutlineTypeEnum
    chapterIndex: Optional[int] = None
    status: OutlineStatusEnum
    summary: str


class WebSocketErrorPayload(BaseModel):
    """错误消息"""
    taskId: str
    stage: ProcessingStage
    chapterIndex: Optional[int] = None
    errorType: str
    errorMessage: str
    willRetry: bool
    retryAfter: Optional[int] = None


class WebSocketCompletedPayload(BaseModel):
    """完成消息"""
    taskId: str
    bookId: str
    status: str = "COMPLETED"
    totalChapters: int
    totalTime: int  # 秒
    worldOutlineId: str
