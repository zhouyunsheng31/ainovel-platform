"""
AI小说拆书系统 - 任务处理服务
负责后台处理流程的启动和管理
"""
import asyncio
import traceback
from typing import Optional
from datetime import datetime, timezone

from sqlalchemy import select, update
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
from app.services.error_codes import ErrorCodes, ErrorMessages
from app.services.logging import logger


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
                # 记录任务开始
                logger.info("开始处理书籍", extra={
                    "task_id": task_id,
                    "book_id": book_id,
                    "stage": "START"
                })
                
                # 更新任务状态
                await self._update_task_status(db, task_id, "PROCESSING", "FILE_UPLOAD", 0)
                await self._update_book_status(db, book_id, BookStatus.PROCESSING.value)
                
                # 1. 获取书籍信息
                book = await self._get_book(db, book_id)
                if not book:
                    error_code = ErrorCodes.BOOK_NOT_FOUND
                    error_message = ErrorMessages.get_message(error_code)
                    logger.error("书籍不存在", extra={
                        "task_id": task_id,
                        "book_id": book_id,
                        "error_code": error_code,
                        "stage": "FILE_UPLOAD"
                    })
                    await self._log_error(db, task_id, book_id, "FILE_UPLOAD", None, error_code, error_message)
                    await send_error_message(task_id, "FILE_UPLOAD", 0, error_code, error_message)
                    return
                
                # 2. 文本预处理阶段
                await self._update_task_status(db, task_id, "PROCESSING", "TEXT_PREPROCESS", 0)
                logger.info("开始文本预处理", extra={
                    "task_id": task_id,
                    "book_id": book_id,
                    "stage": "TEXT_PREPROCESS"
                })
                
                try:
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
                    
                    logger.info("文本预处理完成", extra={
                        "task_id": task_id,
                        "book_id": book_id,
                        "stage": "TEXT_PREPROCESS",
                        "total_chapters": len(chapters)
                    })
                    
                except Exception as e:
                    error_code = ErrorCodes.TEXT_PARSE_ERROR
                    error_message = f"文本预处理失败: {str(e)}"
                    logger.error("文本预处理失败", extra={
                        "task_id": task_id,
                        "book_id": book_id,
                        "error_code": error_code,
                        "error_message": error_message,
                        "stage": "TEXT_PREPROCESS",
                        "stack_trace": traceback.format_exc()
                    })
                    await self._log_error(db, task_id, book_id, "TEXT_PREPROCESS", None, error_code, error_message)
                    await self._update_task_status(db, task_id, "FAILED", "TEXT_PREPROCESS", 0)
                    await self._update_book_status(db, book_id, BookStatus.FAILED.value)
                    await send_error_message(task_id, "TEXT_PREPROCESS", 0, error_code, error_message)
                    return
                
                # 3. 章纲提取阶段（逐章保存）
                await self._update_task_status(db, task_id, "PROCESSING", "CHAPTER_OUTLINE", 0)
                logger.info("开始章纲提取（逐章保存模式）", extra={
                    "task_id": task_id,
                    "book_id": book_id,
                    "stage": "CHAPTER_OUTLINE"
                })
                
                chapter_data = [{"index": c.index, "text": c.text} for c in chapters]
                
                try:
                    saved_chapter_outlines = []

                    async def _on_chapter_saved(chapter_index: int, chapter_result: dict):
                        outline_id = f"chapter_{book_id}_{chapter_index}"
                        status = chapter_result.get("status", "FAILED")
                        outline = Outline(
                            outline_id=outline_id,
                            book_id=book_id,
                            outline_type="CHAPTER",
                            outline_index=chapter_index,
                            chapter_index=chapter_index,
                            content_json=chapter_result.get("content", {}),
                            summary=chapter_result.get("summary", ""),
                            status=status,
                            error_message=chapter_result.get("error") if status == "FAILED" else None
                        )
                        async with async_session_factory() as save_db:
                            existing = await save_db.execute(
                                select(Outline).where(Outline.outline_id == outline_id)
                            )
                            if not existing.scalar_one_or_none():
                                save_db.add(outline)
                                await save_db.commit()
                        saved_chapter_outlines.append(chapter_result)

                    chapter_outlines = await self.outline_service.generate_chapter_outlines(
                        chapter_data,
                        progress_callback=lambda current, total: self._workflow_progress_callback(
                            task_id, "CHAPTER_OUTLINE", current, total
                        ),
                        on_chapter_complete=_on_chapter_saved
                    )

                    logger.info("章纲提取完成", extra={
                        "task_id": task_id,
                        "book_id": book_id,
                        "saved_count": len(saved_chapter_outlines),
                        "total_count": len(chapter_data)
                    })
                except Exception as e:
                    error_code = ErrorCodes.WORKFLOW_ERROR
                    error_message = f"章纲提取失败: {str(e)}"
                    logger.error("章纲提取失败", extra={
                        "task_id": task_id,
                        "book_id": book_id,
                        "error_code": error_code,
                        "error_message": error_message,
                        "stage": "CHAPTER_OUTLINE",
                        "stack_trace": traceback.format_exc()
                    })
                    await self._log_error(db, task_id, book_id, "CHAPTER_OUTLINE", None, error_code, error_message)
                    await self._update_task_status(db, task_id, "FAILED", "CHAPTER_OUTLINE", 0)
                    await self._update_book_status(db, book_id, BookStatus.FAILED.value)
                    await send_error_message(task_id, "CHAPTER_OUTLINE", 0, error_code, error_message)
                    return

                # 4. 粗纲生成阶段（逐阶段保存）
                await self._update_task_status(db, task_id, "PROCESSING", "COARSE_OUTLINE", 0)
                try:
                    coarse_outlines = await self.outline_service.generate_coarse_outlines(
                        chapter_outlines,
                        progress_callback=lambda current, total: self._workflow_progress_callback(
                            task_id, "COARSE_OUTLINE", current, total
                        )
                    )
                    await self._save_coarse_outlines(db, book_id, coarse_outlines)
                    logger.info("粗纲生成完成", extra={
                        "task_id": task_id,
                        "book_id": book_id,
                        "coarse_count": len(coarse_outlines)
                    })
                except Exception as e:
                    error_code = ErrorCodes.WORKFLOW_ERROR
                    error_message = f"粗纲生成失败: {str(e)}"
                    logger.error("粗纲生成失败", extra={
                        "task_id": task_id,
                        "book_id": book_id,
                        "error_code": error_code,
                        "error_message": error_message,
                        "stack_trace": traceback.format_exc()
                    })
                    await self._log_error(db, task_id, book_id, "COARSE_OUTLINE", None, error_code, error_message)
                    await self._update_task_status(db, task_id, "FAILED", "COARSE_OUTLINE", 0)
                    await self._update_book_status(db, book_id, BookStatus.FAILED.value)
                    await send_error_message(task_id, "COARSE_OUTLINE", 0, error_code, error_message)
                    return

                # 5. 大纲生成阶段（逐阶段保存）
                await self._update_task_status(db, task_id, "PROCESSING", "MAIN_OUTLINE", 0)
                try:
                    main_outlines = await self.outline_service.generate_main_outlines(
                        coarse_outlines,
                        progress_callback=lambda current, total: self._workflow_progress_callback(
                            task_id, "MAIN_OUTLINE", current, total
                        )
                    )
                    await self._save_main_outlines(db, book_id, main_outlines)
                    logger.info("大纲生成完成", extra={
                        "task_id": task_id,
                        "book_id": book_id,
                        "main_count": len(main_outlines)
                    })
                except Exception as e:
                    error_code = ErrorCodes.WORKFLOW_ERROR
                    error_message = f"大纲生成失败: {str(e)}"
                    logger.error("大纲生成失败", extra={
                        "task_id": task_id,
                        "book_id": book_id,
                        "error_code": error_code,
                        "error_message": error_message,
                        "stack_trace": traceback.format_exc()
                    })
                    await self._log_error(db, task_id, book_id, "MAIN_OUTLINE", None, error_code, error_message)
                    await self._update_task_status(db, task_id, "FAILED", "MAIN_OUTLINE", 0)
                    await self._update_book_status(db, book_id, BookStatus.FAILED.value)
                    await send_error_message(task_id, "MAIN_OUTLINE", 0, error_code, error_message)
                    return

                # 6. 世界纲生成阶段
                await self._update_task_status(db, task_id, "PROCESSING", "WORLD_OUTLINE", 0)
                try:
                    world_outline = await self.outline_service.generate_world_outline(
                        main_outlines,
                        progress_callback=lambda current, total: self._workflow_progress_callback(
                            task_id, "WORLD_OUTLINE", current, total
                        )
                    )
                    await self._save_world_outline(db, book_id, world_outline)
                    logger.info("世界纲生成完成", extra={
                        "task_id": task_id,
                        "book_id": book_id
                    })
                except Exception as e:
                    error_code = ErrorCodes.WORKFLOW_ERROR
                    error_message = f"世界纲生成失败: {str(e)}"
                    logger.error("世界纲生成失败", extra={
                        "task_id": task_id,
                        "book_id": book_id,
                        "error_code": error_code,
                        "error_message": error_message,
                        "stack_trace": traceback.format_exc()
                    })
                    await self._log_error(db, task_id, book_id, "WORLD_OUTLINE", None, error_code, error_message)
                    await self._update_task_status(db, task_id, "FAILED", "WORLD_OUTLINE", 0)
                    await self._update_book_status(db, book_id, BookStatus.FAILED.value)
                    await send_error_message(task_id, "WORLD_OUTLINE", 0, error_code, error_message)
                    return

                # 7. 补全层级关系
                try:
                    await self._link_outline_hierarchy(db, book_id, chapter_outlines, coarse_outlines, main_outlines)
                except Exception as e:
                    logger.warning("层级关系补全失败（不影响已保存数据）", extra={
                        "task_id": task_id,
                        "book_id": book_id,
                        "error_message": str(e)
                    })

                # 8. 完成
                await self._update_task_status(db, task_id, "COMPLETED", "WORLD_OUTLINE", 100)
                await self._update_book_status(db, book_id, BookStatus.COMPLETED.value)
                
                await send_completed_message(
                    task_id, book_id, len(chapters), 0,
                    f"world_{book_id}"
                )
                
                logger.info("任务完成", extra={
                    "task_id": task_id,
                    "book_id": book_id,
                    "stage": "COMPLETED",
                    "total_chapters": len(chapters)
                })
                
            except Exception as e:
                # 记录错误
                error_msg = str(e)
                error_code = ErrorCodes.SYSTEM_ERROR
                logger.error("任务处理失败", extra={
                    "task_id": task_id,
                    "book_id": book_id,
                    "error_code": error_code,
                    "error_message": error_msg,
                    "stage": "PROCESSING",
                    "stack_trace": traceback.format_exc()
                })
                await self._log_error(db, task_id, book_id, "PROCESSING", None, error_code, error_msg)
                await self._update_task_status(db, task_id, "FAILED", "PROCESSING", 0)
                await self._update_book_status(db, book_id, BookStatus.FAILED.value)
                
                # 发送错误消息
                await send_error_message(task_id, "PROCESSING", 0, error_code, error_msg)
    
    async def _workflow_progress_callback(self, task_id: str, stage: str, current: int, total: int):
        """工作流进度回调"""
        progress = int((current / total) * 100) if total > 0 else 0
        
        # 记录进度日志
        logger.info("工作流进度更新", extra={
            "task_id": task_id,
            "stage": stage,
            "progress": progress,
            "current": current,
            "total": total
        })
        
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
                task.start_time = datetime.now(timezone.utc)
            elif status in ["COMPLETED", "FAILED"]:
                task.end_time = datetime.now(timezone.utc)
            
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
    
    async def _save_coarse_outlines(self, db: AsyncSession, book_id: str, coarse_outlines: list):
        """保存粗纲到数据库"""
        for co in coarse_outlines:
            if co.get("status") == "COMPLETED":
                oid = f"coarse_{book_id}_{co['index']}"
                range_start = co.get("chapter_range", [0, 0])[0]
                range_end = co.get("chapter_range", [0, 0])[1]
                existing = await db.execute(
                    select(Outline).where(Outline.outline_id == oid)
                )
                if existing.scalar_one_or_none():
                    continue
                source_ids = [
                    f"chapter_{book_id}_{i}" for i in range(range_start, range_end + 1)
                ]
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
                    status="COMPLETED"
                )
                db.add(outline)
        await db.commit()

    async def _save_main_outlines(self, db: AsyncSession, book_id: str, main_outlines: list):
        """保存大纲到数据库"""
        for mo in main_outlines:
            if mo.get("status") == "COMPLETED":
                oid = f"main_{book_id}_{mo['index']}"
                existing = await db.execute(
                    select(Outline).where(Outline.outline_id == oid)
                )
                if existing.scalar_one_or_none():
                    continue
                source_ids = [
                    f"coarse_{book_id}_{ci}" for ci in mo.get("source_indices", [])
                ]
                outline = Outline(
                    outline_id=oid,
                    book_id=book_id,
                    outline_type="MAIN",
                    outline_index=mo["index"],
                    content_json=mo.get("content", {}),
                    summary=mo.get("summary", ""),
                    source_outline_ids=source_ids,
                    status="COMPLETED"
                )
                db.add(outline)
        await db.commit()

    async def _save_world_outline(self, db: AsyncSession, book_id: str, world_outline: dict):
        """保存世界纲到数据库"""
        if world_outline.get("status") == "COMPLETED":
            wid = f"world_{book_id}"
            existing = await db.execute(
                select(Outline).where(Outline.outline_id == wid)
            )
            if not existing.scalar_one_or_none():
                outline = Outline(
                    outline_id=wid,
                    book_id=book_id,
                    outline_type="WORLD",
                    outline_index=0,
                    content_json=world_outline.get("content", {}),
                    summary=world_outline.get("summary", ""),
                    status="COMPLETED"
                )
                db.add(outline)
                await db.commit()

    async def _link_outline_hierarchy(self, db: AsyncSession, book_id: str,
                                       chapter_outlines: list, coarse_outlines: list,
                                       main_outlines: list):
        """补全层级关系：世界纲←大纲←粗纲←章纲"""
        world_id = f"world_{book_id}"

        for mo in main_outlines:
            if mo.get("status") == "COMPLETED":
                oid = f"main_{book_id}_{mo['index']}"
                await db.execute(
                    update(Outline).where(Outline.outline_id == oid)
                    .values(parent_outline_id=world_id)
                )
        await db.flush()

        main_id_by_coarse_index = {}
        for mo in main_outlines:
            if mo.get("status") == "COMPLETED":
                for ci in mo.get("source_indices", []):
                    main_id_by_coarse_index[ci] = f"main_{book_id}_{mo['index']}"

        for co in coarse_outlines:
            if co.get("status") == "COMPLETED":
                oid = f"coarse_{book_id}_{co['index']}"
                parent_id = main_id_by_coarse_index.get(co["index"])
                await db.execute(
                    update(Outline).where(Outline.outline_id == oid)
                    .values(parent_outline_id=parent_id)
                )
        await db.flush()

        coarse_ids = {}
        for co in coarse_outlines:
            if co.get("status") == "COMPLETED":
                coarse_ids[co["index"]] = f"coarse_{book_id}_{co['index']}"

        for co in coarse_outlines:
            if co.get("status") == "COMPLETED":
                rs = co.get("chapter_range", [0, 0])[0]
                re_ = co.get("chapter_range", [0, 0])[1]
                parent_coarse_id = coarse_ids.get(co["index"])
                for ch_idx in range(rs, re_ + 1):
                    ch_oid = f"chapter_{book_id}_{ch_idx}"
                    await db.execute(
                        update(Outline).where(Outline.outline_id == ch_oid)
                        .values(parent_outline_id=parent_coarse_id)
                    )
        await db.commit()

    async def _save_outlines(self, db: AsyncSession, book_id: str, result: dict):
        """保存生成的纲结构，建立父子层级关系（自顶向下：世界纲→主纲→粗纲→章纲）"""
        chapter_ids = {}
        coarse_ids = {}
        main_id_by_index = {}
        main_id_by_coarse_index = {}
        world_id = None

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
                main_id_by_index[mo["index"]] = oid
                for ci in mo.get("source_indices", []):
                    main_id_by_coarse_index[ci] = oid

        await db.flush()

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

        for co in result.get("coarse_outlines", []):
            if co.get("status") == "COMPLETED":
                oid = f"coarse_{book_id}_{co['index']}"
                range_start = co.get("chapter_range", [0, 0])[0]
                range_end = co.get("chapter_range", [0, 0])[1]
                source_ids = [
                    chapter_ids[i] for i in range(range_start, range_end + 1)
                    if i in chapter_ids
                ]
                parent_id = main_id_by_coarse_index.get(co["index"])
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

        for ch_idx, ch_oid in chapter_ids.items():
            parent_coarse_id = None
            for co in result.get("coarse_outlines", []):
                if co.get("status") == "COMPLETED":
                    rs = co.get("chapter_range", [0, 0])[0]
                    re_ = co.get("chapter_range", [0, 0])[1]
                    if rs <= ch_idx <= re_:
                        parent_coarse_id = coarse_ids.get(co["index"])
                        break
            await db.execute(
                update(Outline)
                .where(Outline.outline_id == ch_oid)
                .values(parent_outline_id=parent_coarse_id)
            )

        await db.commit()


# 全局任务处理器实例
task_processor = TaskProcessor()
