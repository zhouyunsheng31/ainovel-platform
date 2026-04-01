"""
AI小说拆书系统 - 错误码定义
"""


class ErrorCodes:
    """统一错误码定义"""
    
    # 系统级错误
    SYSTEM_ERROR = "SYSTEM_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    NETWORK_ERROR = "NETWORK_ERROR"
    
    # 文件处理错误
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    FILE_READ_ERROR = "FILE_READ_ERROR"
    FILE_TYPE_NOT_SUPPORTED = "FILE_TYPE_NOT_SUPPORTED"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    
    # 书籍相关错误
    BOOK_NOT_FOUND = "BOOK_NOT_FOUND"
    BOOK_ALREADY_EXISTS = "BOOK_ALREADY_EXISTS"
    BOOK_PROCESSING = "BOOK_PROCESSING"
    
    # 任务相关错误
    TASK_NOT_FOUND = "TASK_NOT_FOUND"
    TASK_ALREADY_RUNNING = "TASK_ALREADY_RUNNING"
    TASK_FAILED = "TASK_FAILED"
    
    # 文本处理错误
    TEXT_PARSE_ERROR = "TEXT_PARSE_ERROR"
    CHAPTER_SPLIT_ERROR = "CHAPTER_SPLIT_ERROR"
    
    # LLM相关错误
    LLM_API_ERROR = "LLM_API_ERROR"
    LLM_TIMEOUT = "LLM_TIMEOUT"
    LLM_JSON_PARSE_ERROR = "LLM_JSON_PARSE_ERROR"
    LLM_RATE_LIMIT = "LLM_RATE_LIMIT"
    
    # 大纲生成错误
    OUTLINE_GENERATION_ERROR = "OUTLINE_GENERATION_ERROR"
    CHAPTER_OUTLINE_ERROR = "CHAPTER_OUTLINE_ERROR"
    COARSE_OUTLINE_ERROR = "COARSE_OUTLINE_ERROR"
    MAIN_OUTLINE_ERROR = "MAIN_OUTLINE_ERROR"
    WORLD_OUTLINE_ERROR = "WORLD_OUTLINE_ERROR"
    
    # 工作流错误
    WORKFLOW_ERROR = "WORKFLOW_ERROR"
    WORKFLOW_TIMEOUT = "WORKFLOW_TIMEOUT"
    
    # WebSocket错误
    WS_CONNECTION_ERROR = "WS_CONNECTION_ERROR"
    WS_MESSAGE_ERROR = "WS_MESSAGE_ERROR"


class ErrorMessages:
    """错误消息映射"""
    
    ERROR_MAPPING = {
        # 系统级错误
        ErrorCodes.SYSTEM_ERROR: "系统内部错误",
        ErrorCodes.DATABASE_ERROR: "数据库操作错误",
        ErrorCodes.NETWORK_ERROR: "网络连接错误",
        
        # 文件处理错误
        ErrorCodes.FILE_NOT_FOUND: "文件不存在",
        ErrorCodes.FILE_READ_ERROR: "文件读取失败",
        ErrorCodes.FILE_TYPE_NOT_SUPPORTED: "不支持的文件类型",
        ErrorCodes.FILE_TOO_LARGE: "文件大小超出限制",
        
        # 书籍相关错误
        ErrorCodes.BOOK_NOT_FOUND: "书籍不存在",
        ErrorCodes.BOOK_ALREADY_EXISTS: "书籍已存在",
        ErrorCodes.BOOK_PROCESSING: "书籍正在处理中",
        
        # 任务相关错误
        ErrorCodes.TASK_NOT_FOUND: "任务不存在",
        ErrorCodes.TASK_ALREADY_RUNNING: "任务已在运行",
        ErrorCodes.TASK_FAILED: "任务执行失败",
        
        # 文本处理错误
        ErrorCodes.TEXT_PARSE_ERROR: "文本解析错误",
        ErrorCodes.CHAPTER_SPLIT_ERROR: "章节分割错误",
        
        # LLM相关错误
        ErrorCodes.LLM_API_ERROR: "LLM API调用错误",
        ErrorCodes.LLM_TIMEOUT: "LLM调用超时",
        ErrorCodes.LLM_JSON_PARSE_ERROR: "LLM返回JSON解析错误",
        ErrorCodes.LLM_RATE_LIMIT: "LLM API速率限制",
        
        # 大纲生成错误
        ErrorCodes.OUTLINE_GENERATION_ERROR: "大纲生成错误",
        ErrorCodes.CHAPTER_OUTLINE_ERROR: "章纲生成错误",
        ErrorCodes.COARSE_OUTLINE_ERROR: "粗纲生成错误",
        ErrorCodes.MAIN_OUTLINE_ERROR: "大纲生成错误",
        ErrorCodes.WORLD_OUTLINE_ERROR: "世界纲生成错误",
        
        # 工作流错误
        ErrorCodes.WORKFLOW_ERROR: "工作流执行错误",
        ErrorCodes.WORKFLOW_TIMEOUT: "工作流执行超时",
        
        # WebSocket错误
        ErrorCodes.WS_CONNECTION_ERROR: "WebSocket连接错误",
        ErrorCodes.WS_MESSAGE_ERROR: "WebSocket消息处理错误",
    }
    
    @classmethod
    def get_message(cls, error_code: str) -> str:
        """获取错误消息"""
        return cls.ERROR_MAPPING.get(error_code, "未知错误")
