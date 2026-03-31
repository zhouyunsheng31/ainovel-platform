"""
AI小说拆书系统 - FastAPI主入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn

from app.api import books_router, outlines_router, tasks_router, ws_router
from app.models.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化数据库
    await init_db()
    yield
    # 关闭时清理资源


app = FastAPI(
    title="AI小说拆书系统",
    description="基于LangChain的四层纲生成系统",
    version="1.0.0",
    lifespan=lifespan
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(books_router)
app.include_router(outlines_router)
app.include_router(tasks_router)
app.include_router(ws_router)


@app.get("/")
async def root():
    """根路径健康检查"""
    return {
        "success": True,
        "message": "AI小说拆书系统API运行中",
        "version": "1.0.0"
    }


@app.get("/health")
async def health():
    """健康检查端点"""
    return {
        "status": "healthy",
        "service": "ai-novel-backend"
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
