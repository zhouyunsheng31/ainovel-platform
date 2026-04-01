"""
AI小说拆书系统 - 任务处理服务
负责后台处理流程的启动和管理
"""
import asyncio
from typing import Optional
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import async_session_factory
from app.models.models import Book, ProcessingTask, Outline, ErrorLog, Chapter
from app.models.schemas import BookStatus
from app.services.file_processor import FileProcessor
from app.services.text_splitter import TextSplitter
from app.services.outline_service import OutlineService
from app.workflows.outline_graph import OutlineGraphWorkflow
from app.api.websocket import (
    send_progress_update,
    send_error_message, send_completed_message
)


class TaskProcessor:
    """后台任务处理器"""
    
    def __init__(self):
        self.file_processor = FileProcessor()
        self.text_splitter = TextSplitter()
        self.outline_service = OutlineService()
        self.workflow = OutlineGraphWorkflow(self.outline_service)
    
    async def start_processing(self, book_id: str, task_id: str):
        """
        启动后台处理流程
        在后台运行完整的处理流程
        """
        # 创建后台任务
        asyncio.create_task(self._process_book(book_id, task_id))
    
    async def _process_book(self, book_id: str, task_id: str):
        """
        完整的书籍处理流程
        """
        async with async_session_factory() as db:
            try:
                # 更新任务状态
                await self._update_task_status(db, task_id, "PROCESSING", "FILE_UPLOAD", 0)
                await self._update_book_status(db, book_id, BookStatus.PROCESSING.value)
                
                # 1. 获取书籍信息
                book = await self._get_book(db, book_id)
                if not book:
                    await self._log_error(db, task_id, book_id, "FILE_UPLOAD", None, "BOOK_NOT_FOUND", "书籍不存在")
                    return
                
                # 2. 文本预处理阶段
                await self._update_task_status(db, task_id, "PROCESSING", "TEXT_PREPROCESS", 0)
                
                # 提取文本
                text, encoding = await self.file_processor.extract_text(
                    book.file_path, book.file_type
                )
                
                # 更新编码
                book.encoding = encoding
                await db.commit()
                
                # 分割章节
                chapters = self.text_splitter.split_into_chapters(text)
                book.total_chapters = len(chapters)
                await db.commit()
                
                # 保存章节数据
                for chapter in chapters:
                    db_chapter = Chapter(
                        chapter_id=f"{book_id}_{chapter.index}",
                        book_id=book_id,
                        chapter_index=chapter.index,
                        original_text=chapter.text,
                        word_count=chapter.word_count,
                        start_offset=chapter.start_offset,
                        end_offset=chapter.end_offset
                    )
                    db.add(db_chapter)
                await db.commit()
                
                await self._update_task_status(db, task_id, "PROCESSING", "TEXT_PREPROCESS", 100, 
                                               total_chapters=len(chapters))
                
                # 发送WebSocket进度
                await send_progress_update(
                    task_id, "TEXT_PREPROCESS", 100, 1, 1,
                    f"文本预处理完成，共{len(chapters)}章"
                )
                
                # 3. 章纲提取阶段
                await self._update_task_status(db, task_id, "PROCESSING", "CHAPTER_OUTLINE", 0)
                
                chapter_data = [{"index": c.index, "text": c.text} for c in chapters]
                
                # 运行LangGraph工作流
                result = await self.workflow.run(
                    chapters=chapter_data,
                    progress_callback=lambda stage, current, total: self._workflow_progress_callback(
                        task_id, stage, current, total
                    )
                )
                
                # 4. 保存结果
                await self._save_outlines(db, book_id, result)
                
                # 5. 完成
                await self._update_task_status(db, task_id, "COMPLETED", "WORLD_OUTLINE", 100)
                await self._update_book_status(db, book_id, BookStatus.COMPLETED.value)
                
                # 发送完成消息
                await send_completed_message(
                    task_id, book_id, len(chapters), 0,
                    result.get("world_outline", {}).get("outline_id", "")
                )
                
            except Exception as e:
                # 记录错误
                error_msg = str(e)
                import traceback
                traceback.print_exc()
                await self._log_error(db, task_id, book_id, "PROCESSING", None, "PROCESSING_ERROR", error_msg)
                await self._update_task_status(db, task_id, "FAILED", "PROCESSING", 0)
                await self._update_book_status(db, book_id, BookStatus.FAILED.value)
                
                # 发送错误消息
                await send_error_message(task_id, "PROCESSING", 0, "PROCESSING_ERROR", error_msg)
    
    async def _workflow_progress_callback(self, task_id: str, stage: str, current: int, total: int):
        """工作流进度回调"""
        progress = int((current / total) * 100) if total > 0 else 0
        
        await send_progress_update(
            task_id, stage, progress, total, current,
            f"{stage}: {current}/{total}"
        )
        
        # 更新数据库中的进度
        async with async_session_factory() as db:
            await self._update_stage_progress(db, task_id, stage, progress)
    
    async def _update_task_status(
        self, db: AsyncSession, task_id: str, status: str, 
        current_stage: str, progress: int, **kwargs
    ):
        """更新任务状态"""
        result = await db.execute(
            select(ProcessingTask).where(ProcessingTask.task_id == task_id)
        )
        task = result.scalar_one_or_none()
        
        if task:
            task.status = status
            task.current_stage = current_stage
            
            if status == "PROCESSING" and not task.start_time:
                task.start_time = datetime.utcnow()
            elif status in ["COMPLETED", "FAILED"]:
                task.end_time = datetime.utcnow()
            
            if "total_chapters" in kwargs:
                task.total_chapters = kwargs["total_chapters"]
            
            # 更新阶段进度
            if not task.stage_progress:
                task.stage_progress = {}
            task.stage_progress[current_stage] = progress
            
            await db.commit()
    
    async def _update_stage_progress(self, db: AsyncSession, task_id: str, stage: str, progress: int):
        """更新阶段进度"""
        result = await db.execute(
            select(ProcessingTask).where(ProcessingTask.task_id == task_id)
        )
        task = result.scalar_one_or_none()
        
        if task:
            if not task.stage_progress:
                task.stage_progress = {}
            task.stage_progress[stage] = progress
            await db.commit()
    
    async def _update_book_status(self, db: AsyncSession, book_id: str, status: str):
        """更新书籍状态"""
        result = await db.execute(
            select(Book).where(Book.book_id == book_id)
        )
        book = result.scalar_one_or_none()
        
        if book:
            book.status = status
            await db.commit()
    
    async def _get_book(self, db: AsyncSession, book_id: str) -> Optional[Book]:
        """获取书籍"""
        result = await db.execute(
            select(Book).where(Book.book_id == book_id)
        )
        return result.scalar_one_or_none()
    
    async def _log_error(
        self, db: AsyncSession, task_id: str, book_id: str, stage: str, 
        chapter_index: Optional[int], error_type: str, error_message: str
    ):
        """记录错误"""
        error = ErrorLog(
            task_id=task_id,
            book_id=book_id,
            stage=stage,
            chapter_index=chapter_index,
            error_type=error_type,
            error_message=error_message
        )
        db.add(error)
        await db.commit()
    
    async def _save_outlines(self, db: AsyncSession, book_id: str, result: dict):
        """保存生成的纲结构，建立父子层级关系"""
        chapter_ids = {}
        coarse_ids = {}
        main_ids = []
        world_id = None

        # 1. 先保存世界纲（根节点）
        wo = result.get("world_outline", {})
        if wo.get("status") == "COMPLETED":
            wid = f"world_{book_id}"
            outline = Outline(
                outline_id=wid,
                book_id=book_id,
                outline_type="WORLD",
                outline_index=0,
                content_json=wo.get("content", {}),
                summary=wo.get("summary", ""),
                status="COMPLETED"
            )
            db.add(outline)
            world_id = wid
            await db.flush()

        # 2. 保存章纲
        for co in result.get("chapter_outlines", []):
            if co.get("status") == "COMPLETED":
                oid = f"chapter_{book_id}_{co['index']}"
                outline = Outline(
                    outline_id=oid,
                    book_id=book_id,
                    outline_type="CHAPTER",
                    outline_index=co["index"],
                    chapter_index=co["index"],
                    content_json=co.get("content", {}),
                    summary=co.get("summary", ""),
                    status="COMPLETED"
                )
                db.add(outline)
                chapter_ids[co["index"]] = oid

        await db.flush()

        # 3. 保存大纲（父节点是世界纲）
        for mo in result.get("main_outlines", []):
            if mo.get("status") == "COMPLETED":
                oid = f"main_{book_id}_{mo['index']}"
                outline = Outline(
                    outline_id=oid,
                    book_id=book_id,
                    outline_type="MAIN",
                    outline_index=mo["index"],
                    content_json=mo.get("content", {}),
                    summary=mo.get("summary", ""),
                    parent_outline_id=world_id,
                    status="COMPLETED"
                )
                db.add(outline)
                main_ids.append(oid)

        await db.flush()

        # 4. 保存粗纲（父节点是大纲）
        for co in result.get("coarse_outlines", []):
            if co.get("status") == "COMPLETED":
                oid = f"coarse_{book_id}_{co['index']}"
                range_start = co.get("chapter_range", [0, 0])[0]
                range_end = co.get("chapter_range", [0, 0])[1]
                source_ids = [
                    chapter_ids[i] for i in range(range_start, range_end + 1)
                    if i in chapter_ids
                ]
                parent_id = main_ids[0] if main_ids else None
                outline = Outline(
                    outline_id=oid,
                    book_id=book_id,
                    outline_type="COARSE",
                    outline_index=co["index"],
                    chapter_range_start=range_start,
                    chapter_range_end=range_end,
                    content_json=co.get("content", {}),
                    summary=co.get("summary", ""),
                    source_outline_ids=source_ids,
                    parent_outline_id=parent_id,
                    status="COMPLETED"
                )
                db.add(outline)
                coarse_ids[co["index"]] = oid

        await db.flush()

        # 5. 更新章纲的父节点（关联到粗纲）
        for coarse_idx, coarse_id in coarse_ids.items():
            coarse_outline = result.get("coarse_outlines", [])
            for co in coarse_outline:
                if co.get("index") == coarse_idx and co.get("status") == "COMPLETED":
                    range_start = co.get("chapter_range", [0, 0])[0]
                    range_end = co.get("chapter_range", [0, 0])[1]
                    for ch_idx in range(range_start, range_end + 1):
                        if ch_idx in chapter_ids:
                            ch_result = await db.execute(
                                select(Outline).where(Outline.outline_id == chapter_ids[ch_idx])
                            )
                            ch_obj = ch_result.scalar_one_or_none()
                            if ch_obj:
                                ch_obj.parent_outline_id = coarse_id
                    break

        await db.commit()


# 全局任务处理器实例
task_processor = TaskProcessor()
