"""
书籍相关API路由
POST /api/v1/books/upload - 上传书籍
GET /api/v1/books - 获取书籍列表
GET /api/v1/books/{bookId} - 获取书籍详情
DELETE /api/v1/books/{bookId} - 删除书籍
GET /api/v1/books/{bookId}/tree - 获取纲树结构
GET /api/v1/books/{bookId}/status - 获取处理状态
"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query, Depends, BackgroundTasks
from typing import Optional
import os
import uuid
import hashlib
import aiofiles
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.database import get_session
from ..models.models import Book, ProcessingTask, Outline
from ..models.schemas import (
    BookStatus, ProcessingStage, UploadBookResponse, UploadBookData,
    BookListResponse, BookListData, BookSummary,
    BookDetailResponse, BookDetail,
    DeleteBookResponse, OutlineTreeResponse, OutlineTreeData, OutlineTreeNode,
    BookProcessingStatusResponse, BookProcessingStatusData
)
from ..services.task_processor import task_processor

router = APIRouter(prefix="/api/v1/books", tags=["books"])

# 支持的文件类型
SUPPORTED_FILE_TYPES = {
    ".txt": "TXT",
    ".epub": "EPUB",
    ".doc": "DOC",
    ".docx": "DOCX",
    ".pdf": "PDF"
}

# 文件大小限制 (50MB)
MAX_FILE_SIZE = 50 * 1024 * 1024


async def get_db():
    """数据库会话依赖"""
    async with get_session() as session:
        yield session


@router.post("/upload", response_model=UploadBookResponse)
async def upload_book(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    author: Optional[str] = Form(None),
    force: Optional[str] = Form("false"),
    db: AsyncSession = Depends(get_db),
    background_tasks: BackgroundTasks = None
):
    """
    上传书籍文件
    支持 txt/epub/doc/docx/pdf 格式
    上传后自动启动后台处理流程
    force=true 时跳过重复检测
    """
    # 1. 验证文件类型
    file_ext = os.path.splitext(file.filename or "")[1].lower()
    if file_ext not in SUPPORTED_FILE_TYPES:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "INVALID_FILE_FORMAT",
                "message": f"不支持的文件格式: {file_ext}",
                "details": {"supported_formats": list(SUPPORTED_FILE_TYPES.keys())}
            }
        )
    
    # 2. 读取文件内容
    content = await file.read()
    file_size = len(content)
    
    # 3. 验证文件大小
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail={
                "code": "FILE_TOO_LARGE",
                "message": f"文件超过大小限制: {file_size} > {MAX_FILE_SIZE}",
                "details": {"max_size": MAX_FILE_SIZE}
            }
        )
    
    # 4. 计算文件哈希
    file_hash = hashlib.sha256(content).hexdigest()
    
    # 5. 重复检测（force != "true" 时）
    if force.lower() != "true":
        existing_result = await db.execute(
            select(Book).where(Book.file_hash == file_hash)
        )
        existing_book = existing_result.scalar_one_or_none()
        if existing_book:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "BOOK_ALREADY_EXISTS",
                    "message": f"检测到重复书籍：{existing_book.title}",
                    "details": {
                        "existingBookId": existing_book.book_id,
                        "existingTitle": existing_book.title,
                        "existingOriginalName": existing_book.original_name,
                        "existingStatus": existing_book.status,
                        "fileHash": file_hash
                    }
                }
            )
    
    # 6. 生成ID
    book_id = str(uuid.uuid4())
    task_id = str(uuid.uuid4())
    
    # 7. 提取书名
    original_name = file.filename or "unknown"
    book_title = title or os.path.splitext(original_name)[0]
    
    # 8. 保存文件
    data_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data", "uploads")
    os.makedirs(data_dir, exist_ok=True)
    file_path = os.path.join(data_dir, f"{book_id}{file_ext}")
    
    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)
    
    # 9. 创建数据库记录
    book = Book(
        book_id=book_id,
        title=book_title,
        original_name=original_name,
        file_type=SUPPORTED_FILE_TYPES[file_ext],
        file_path=file_path,
        file_size=file_size,
        file_hash=file_hash,
        status=BookStatus.IDLE.value
    )
    db.add(book)
    
    # 创建处理任务
    task = ProcessingTask(
        task_id=task_id,
        book_id=book_id,
        current_stage="FILE_UPLOAD",
        status="PENDING"
    )
    db.add(task)
    
    await db.commit()
    
    # 10. 启动后台处理任务
    await task_processor.start_processing(book_id, task_id)
    
    return UploadBookResponse(
        data=UploadBookData(
            bookId=book_id,
            taskId=task_id,
            fileName=original_name,
            fileSize=file_size,
            status="UPLOADING",
            message="文件上传成功，正在开始处理..."
        )
    )


@router.get("", response_model=BookListResponse)
async def list_books(
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    sortBy: str = Query("createdAt"),
    sortOrder: str = Query("desc"),
    db: AsyncSession = Depends(get_db)
):
    """获取书籍列表"""
    # 构建查询
    query = select(Book)
    
    if status:
        query = query.where(Book.status == status)
    
    # 排序
    order_column = getattr(Book, sortBy, Book.created_at)
    if sortOrder == "desc":
        query = query.order_by(order_column.desc())
    else:
        query = query.order_by(order_column.asc())
    
    # 分页
    offset = (page - 1) * pageSize
    query = query.offset(offset).limit(pageSize)
    
    result = await db.execute(query)
    books = result.scalars().all()
    
    # 统计总数
    count_query = select(Book)
    if status:
        count_query = count_query.where(Book.status == status)
    count_result = await db.execute(count_query)
    total = len(count_result.scalars().all())
    
    # 构建响应
    book_summaries = []
    for book in books:
        book_summaries.append(BookSummary(
            bookId=book.book_id,
            title=book.title,
            originalName=book.original_name,
            fileType=book.file_type,
            fileSize=book.file_size,
            totalChapters=book.total_chapters or 0,
            status=BookStatus(book.status),
            createdAt=book.created_at.isoformat() + "Z" if book.created_at else "",
            updatedAt=book.updated_at.isoformat() + "Z" if book.updated_at else ""
        ))
    
    return BookListResponse(
        data=BookListData(
            books=book_summaries,
            pagination={
                "page": page,
                "pageSize": pageSize,
                "total": total,
                "totalPages": (total + pageSize - 1) // pageSize
            }
        )
    )


@router.get("/{bookId}", response_model=BookDetailResponse)
async def get_book(bookId: str, db: AsyncSession = Depends(get_db)):
    """获取书籍详情"""
    result = await db.execute(
        select(Book).where(Book.book_id == bookId)
    )
    book = result.scalar_one_or_none()
    
    if not book:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "BOOK_NOT_FOUND",
                "message": f"书籍不存在: {bookId}",
                "details": {}
            }
        )
    
    return BookDetailResponse(
        data=BookDetail(
            bookId=book.book_id,
            title=book.title,
            originalName=book.original_name,
            fileType=book.file_type,
            fileSize=book.file_size,
            totalChapters=book.total_chapters or 0,
            status=BookStatus(book.status),
            createdAt=book.created_at.isoformat() + "Z" if book.created_at else "",
            updatedAt=book.updated_at.isoformat() + "Z" if book.updated_at else "",
            encoding=book.encoding
        )
    )


@router.delete("/{bookId}", response_model=DeleteBookResponse)
async def delete_book(bookId: str, db: AsyncSession = Depends(get_db)):
    """删除书籍"""
    result = await db.execute(
        select(Book).where(Book.book_id == bookId)
    )
    book = result.scalar_one_or_none()
    
    if not book:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "BOOK_NOT_FOUND",
                "message": f"书籍不存在: {bookId}",
                "details": {}
            }
        )
    
    # 删除关联数据（cascade会自动处理）
    await db.delete(book)
    await db.commit()
    
    return DeleteBookResponse(
        data={
            "bookId": bookId,
            "message": "书籍已删除"
        }
    )


@router.get("/{bookId}/tree", response_model=OutlineTreeResponse)
async def get_outline_tree(bookId: str, db: AsyncSession = Depends(get_db)):
    """获取纲树结构"""
    # 验证书籍存在
    book_result = await db.execute(
        select(Book).where(Book.book_id == bookId)
    )
    book = book_result.scalar_one_or_none()
    if not book:
        raise HTTPException(
            status_code=404,
            detail={"code": "BOOK_NOT_FOUND", "message": f"书籍不存在: {bookId}"}
        )
    
    # 查询所有大纲
    outlines_result = await db.execute(
        select(Outline).where(Outline.book_id == bookId).order_by(Outline.outline_type, Outline.outline_index)
    )
    outlines = outlines_result.scalars().all()
    
    # 构建树结构
    # 先找到世界纲（根节点）
    world_outlines = [o for o in outlines if o.outline_type == "WORLD"]
    
    if not world_outlines:
        # 如果还没有世界纲，返回空树
        return OutlineTreeResponse(
            data=OutlineTreeData(
                bookId=bookId,
                tree=OutlineTreeNode(
                    outlineId="",
                    outlineType="WORLD",
                    label="世界纲",
                    status="PENDING",
                    children=[]
                )
            )
        )
    
    world_outline = world_outlines[0]
    
    # 构建节点映射
    node_map = {}
    for o in outlines:
        node_map[o.outline_id] = OutlineTreeNode(
            outlineId=o.outline_id,
            outlineType=o.outline_type,
            outlineIndex=o.outline_index,
            label=_get_outline_label(o),
            summary=o.summary,
            status=o.status,
            chapterRange=[o.chapter_range_start, o.chapter_range_end] if o.chapter_range_start is not None else None,
            children=[]
        )
    
    # 建立父子关系
    root = node_map.get(world_outline.outline_id)
    for o in outlines:
        if o.parent_outline_id and o.parent_outline_id in node_map:
            node_map[o.parent_outline_id].children.append(node_map[o.outline_id])
    
    return OutlineTreeResponse(
        data=OutlineTreeData(
            bookId=bookId,
            tree=root or OutlineTreeNode(
                outlineId="",
                outlineType="WORLD",
                label="世界纲",
                status="PENDING",
                children=[]
            )
        )
    )


@router.get("/{bookId}/status", response_model=BookProcessingStatusResponse)
async def get_book_status(bookId: str, db: AsyncSession = Depends(get_db)):
    """获取书籍处理状态"""
    # 验证书籍存在
    book_result = await db.execute(
        select(Book).where(Book.book_id == bookId)
    )
    book = book_result.scalar_one_or_none()
    if not book:
        raise HTTPException(
            status_code=404,
            detail={"code": "BOOK_NOT_FOUND", "message": f"书籍不存在: {bookId}"}
        )
    
    # 查询任务状态
    task_result = await db.execute(
        select(ProcessingTask).where(ProcessingTask.book_id == bookId)
    )
    task = task_result.scalar_one_or_none()
    
    current_stage = None
    if task and task.current_stage:
        current_stage = ProcessingStage(task.current_stage)
    
    return BookProcessingStatusResponse(
        data=BookProcessingStatusData(
            bookId=bookId,
            status=BookStatus(book.status),
            taskId=task.task_id if task else None,
            currentStage=current_stage,
            stageProgress=task.stage_progress if task and task.stage_progress else {}
        )
    )


def _get_outline_label(outline: Outline) -> str:
    """生成纲标签"""
    type_labels = {
        "WORLD": "世界纲",
        "MAIN": f"大纲 {outline.outline_index or 1}",
        "COARSE": f"粗纲 {outline.outline_index or 1}",
        "CHAPTER": f"章纲 {outline.chapter_index + 1 if outline.chapter_index is not None else outline.outline_index or 1}"
    }
    
    base_label = type_labels.get(outline.outline_type, outline.outline_type)
    
    # 添加章节范围
    if outline.chapter_range_start is not None and outline.chapter_range_end is not None:
        base_label += f" (章节{outline.chapter_range_start + 1}-{outline.chapter_range_end + 1})"
    
    return base_label
