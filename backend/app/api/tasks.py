"""
任务相关API路由
GET /api/v1/tasks/{taskId} - 获取任务状态
GET /api/v1/tasks/{taskId}/errors - 获取任务错误日志
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from ..models.database import get_session
from ..models.models import ProcessingTask, ErrorLog
from ..models.schemas import (
    TaskStatusEnum, ProcessingStage, StageProgress,
    TaskStatusResponse, TaskStatusData,
    TaskErrorsResponse, TaskErrorsData, TaskErrorItem
)

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])


async def get_db():
    """数据库会话依赖"""
    async with get_session() as session:
        yield session


@router.get("/{taskId}", response_model=TaskStatusResponse)
async def get_task_status(taskId: str, db: AsyncSession = Depends(get_db)):
    """获取任务状态"""
    result = await db.execute(
        select(ProcessingTask).where(ProcessingTask.task_id == taskId)
    )
    task = result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "TASK_NOT_FOUND",
                "message": f"任务不存在: {taskId}",
                "details": {}
            }
        )
    
    stage_progress = task.stage_progress or {}
    
    return TaskStatusResponse(
        data=TaskStatusData(
            taskId=task.task_id,
            bookId=task.book_id,
            status=TaskStatusEnum(task.status),
            currentStage=ProcessingStage(task.current_stage),
            stageProgress=StageProgress(**{
                "FILE_UPLOAD": stage_progress.get("FILE_UPLOAD", 0),
                "TEXT_PREPROCESS": stage_progress.get("TEXT_PREPROCESS", 0),
                "CHAPTER_OUTLINE": stage_progress.get("CHAPTER_OUTLINE", 0),
                "COARSE_OUTLINE": stage_progress.get("COARSE_OUTLINE", 0),
                "MAIN_OUTLINE": stage_progress.get("MAIN_OUTLINE", 0),
                "WORLD_OUTLINE": stage_progress.get("WORLD_OUTLINE", 0)
            }),
            totalChapters=task.total_chapters or 0,
            completedChapters=task.completed_chapters or 0,
            errorCount=0,
            startTime=task.start_time.isoformat() + "Z" if task.start_time else "",
            endTime=task.end_time.isoformat() + "Z" if task.end_time else None,
            estimatedTimeRemaining=_estimate_time_remaining(task)
        )
    )


@router.get("/{taskId}/errors", response_model=TaskErrorsResponse)
async def get_task_errors(
    taskId: str,
    page: int = 1,
    pageSize: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """获取任务错误日志"""
    task_result = await db.execute(
        select(ProcessingTask).where(ProcessingTask.task_id == taskId)
    )
    task = task_result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "TASK_NOT_FOUND",
                "message": f"任务不存在: {taskId}",
                "details": {}
            }
        )
    
    offset = (page - 1) * pageSize
    errors_result = await db.execute(
        select(ErrorLog)
        .where(ErrorLog.task_id == taskId)
        .order_by(ErrorLog.timestamp.desc())
        .offset(offset)
        .limit(pageSize)
    )
    errors = errors_result.scalars().all()
    
    count_result = await db.execute(
        select(ErrorLog).where(ErrorLog.task_id == taskId)
    )
    total_errors = len(count_result.scalars().all())
    
    error_items = []
    for error in errors:
        error_items.append(TaskErrorItem(
            errorId=error.error_id,
            stage=ProcessingStage(error.stage),
            chapterIndex=error.chapter_index,
            errorType=error.error_type,
            errorMessage=error.error_message,
            timestamp=error.timestamp.isoformat() + "Z" if error.timestamp else ""
        ))
    
    return TaskErrorsResponse(
        data=TaskErrorsData(
            taskId=taskId,
            totalErrors=total_errors,
            errors=error_items
        )
    )


def _estimate_time_remaining(task: ProcessingTask) -> int:
    """估算剩余时间（秒）"""
    if not task.start_time or task.total_chapters == 0:
        return None
    
    stage_progress = task.stage_progress or {}
    
    weights = {
        "FILE_UPLOAD": 0.05,
        "TEXT_PREPROCESS": 0.10,
        "CHAPTER_OUTLINE": 0.40,
        "COARSE_OUTLINE": 0.25,
        "MAIN_OUTLINE": 0.15,
        "WORLD_OUTLINE": 0.05
    }
    
    total_progress = sum(
        stage_progress.get(stage, 0) / 100 * weight
        for stage, weight in weights.items()
    )
    
    if total_progress == 0:
        return None
    
    elapsed = (datetime.now(timezone.utc) - task.start_time).total_seconds()
    estimated_total = elapsed / total_progress
    remaining = estimated_total - elapsed
    
    return max(0, int(remaining))
