"""
AI小说拆书系统 - API路由模块
"""
from .books import router as books_router
from .outlines import router as outlines_router
from .tasks import router as tasks_router
from .websocket import router as ws_router

__all__ = ["books_router", "outlines_router", "tasks_router", "ws_router"]
