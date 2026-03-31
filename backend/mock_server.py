"""
AI小说拆书系统 - Mock Server
基于 OpenAPI 规范的 Mock 服务，用于前端独立开发
"""
import uuid
from datetime import datetime
from typing import Dict, Any
from fastapi import FastAPI, UploadFile, File, Form, Query, Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

app = FastAPI(
    title="AI小说拆书系统 Mock Server",
    description="基于 OpenAPI 规范的 Mock 服务",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MOCK_BOOKS: Dict[str, Dict[str, Any]] = {}
MOCK_TASKS: Dict[str, Dict[str, Any]] = {}
MOCK_OUTLINES: Dict[str, Dict[str, Any]] = {}


def _timestamp() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _success(data: Any) -> Dict[str, Any]:
    return {"success": True, "data": data, "error": None, "timestamp": _timestamp()}


def _error(code: str, message: str, details: Dict = None) -> Dict[str, Any]:
    return {
        "success": False,
        "data": None,
        "error": {"code": code, "message": message, "details": details or {}},
        "timestamp": _timestamp(),
    }


@app.get("/")
async def root():
    return {"message": "Mock Server Running", "version": "1.0.0"}


@app.post("/api/v1/books/upload")
async def upload_book(
    file: UploadFile = File(...),
    title: str = Form(None),
    author: str = Form(None),
):
    file_ext = file.filename.split(".")[-1].lower() if file.filename else ""
    if file_ext not in ["txt", "epub", "doc", "docx", "pdf"]:
        return JSONResponse(status_code=400, content=_error("INVALID_FILE_FORMAT", f"不支持的文件格式: .{file_ext}"))

    book_id = str(uuid.uuid4())
    task_id = str(uuid.uuid4())

    MOCK_BOOKS[book_id] = {
        "bookId": book_id,
        "title": title or file.filename.rsplit(".", 1)[0],
        "originalName": file.filename,
        "fileType": file_ext.upper(),
        "fileSize": 1024000,
        "totalChapters": 20,
        "status": "PROCESSING",
        "createdAt": _timestamp(),
        "updatedAt": _timestamp(),
    }

    MOCK_TASKS[task_id] = {
        "taskId": task_id,
        "bookId": book_id,
        "status": "RUNNING",
        "currentStage": "TEXT_PREPROCESS",
        "stageProgress": {
            "FILE_UPLOAD": 100,
            "TEXT_PREPROCESS": 50,
            "CHAPTER_OUTLINE": 0,
            "COARSE_OUTLINE": 0,
            "MAIN_OUTLINE": 0,
            "WORLD_OUTLINE": 0,
        },
        "totalChapters": 20,
        "completedChapters": 0,
        "errorCount": 0,
        "startTime": _timestamp(),
    }

    return _success({
        "bookId": book_id,
        "taskId": task_id,
        "fileName": file.filename,
        "fileSize": 1024000,
        "status": "UPLOADING",
        "message": "文件上传成功，正在开始处理...",
    })


@app.get("/api/v1/books")
async def list_books(
    status: str = Query(None),
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    sortBy: str = Query("createdAt"),
    sortOrder: str = Query("desc"),
):
    books = list(MOCK_BOOKS.values())
    if status:
        books = [b for b in books if b["status"] == status]

    if sortBy == "createdAt":
        books.sort(key=lambda x: x["createdAt"], reverse=(sortOrder == "desc"))
    elif sortBy == "title":
        books.sort(key=lambda x: x["title"], reverse=(sortOrder == "desc"))

    total = len(books)
    start = (page - 1) * pageSize
    end = start + pageSize

    return _success({
        "books": books[start:end],
        "pagination": {
            "page": page,
            "pageSize": pageSize,
            "total": total,
            "totalPages": (total + pageSize - 1) // pageSize,
        },
    })


@app.get("/api/v1/books/{bookId}")
async def get_book(bookId: str = Path(...)):
    if bookId not in MOCK_BOOKS:
        return JSONResponse(status_code=404, content=_error("BOOK_NOT_FOUND", "书籍不存在"))

    book = MOCK_BOOKS[bookId].copy()
    book["encoding"] = "UTF-8"
    return _success(book)


@app.delete("/api/v1/books/{bookId}")
async def delete_book(bookId: str = Path(...)):
    if bookId not in MOCK_BOOKS:
        return JSONResponse(status_code=404, content=_error("BOOK_NOT_FOUND", "书籍不存在"))

    del MOCK_BOOKS[bookId]
    return _success({"bookId": bookId, "message": "书籍已删除"})


@app.get("/api/v1/books/{bookId}/tree")
async def get_outline_tree(bookId: str = Path(...)):
    if bookId not in MOCK_BOOKS:
        return JSONResponse(status_code=404, content=_error("BOOK_NOT_FOUND", "书籍不存在"))

    world_id = f"outline_world_{bookId}"
    main_id = f"outline_main_{bookId}_1"
    coarse_id = f"outline_coarse_{bookId}_1"
    chapter_id = f"outline_chapter_{bookId}_1"

    tree = {
        "outlineId": world_id,
        "outlineType": "WORLD",
        "label": "世界纲",
        "summary": "这是一个宏大的修仙世界，讲述了主角从凡人到仙人的成长历程...",
        "status": "COMPLETED",
        "childCount": 1,
        "children": [
            {
                "outlineId": main_id,
                "outlineType": "MAIN",
                "outlineIndex": 1,
                "label": "大纲 1 (章节1-20)",
                "summary": "第一部分讲述主角的觉醒与初步成长...",
                "status": "COMPLETED",
                "chapterRange": [1, 20],
                "childCount": 2,
                "children": [
                    {
                        "outlineId": coarse_id,
                        "outlineType": "COARSE",
                        "outlineIndex": 1,
                        "label": "粗纲 1 (章节1-10)",
                        "summary": "前十章讲述主角的出身和初入修仙界...",
                        "status": "COMPLETED",
                        "chapterRange": [1, 10],
                        "childCount": 1,
                        "children": [
                            {
                                "outlineId": chapter_id,
                                "outlineType": "CHAPTER",
                                "outlineIndex": 1,
                                "label": "章纲 1",
                                "summary": "第一章介绍主角林风的背景和日常...",
                                "status": "COMPLETED",
                                "childCount": 0,
                                "children": [],
                            }
                        ],
                    }
                ],
            }
        ],
    }

    return _success({"bookId": bookId, "tree": tree})


@app.get("/api/v1/books/{bookId}/status")
async def get_book_status(bookId: str = Path(...)):
    if bookId not in MOCK_BOOKS:
        return JSONResponse(status_code=404, content=_error("BOOK_NOT_FOUND", "书籍不存在"))

    book = MOCK_BOOKS[bookId]
    task = next((t for t in MOCK_TASKS.values() if t["bookId"] == bookId), None)

    if not task:
        return _success({
            "bookId": bookId,
            "status": book["status"],
            "currentStage": None,
            "progress": 100 if book["status"] == "COMPLETED" else 0,
        })

    return _success({
        "bookId": bookId,
        "status": book["status"],
        "currentStage": task["currentStage"],
        "progress": sum(task["stageProgress"].values()) // 6,
        "taskId": task["taskId"],
    })


@app.get("/api/v1/outlines/{outlineId}")
async def get_outline_detail(outlineId: str = Path(...)):
    outline_type = "CHAPTER"
    if "world" in outlineId:
        outline_type = "WORLD"
    elif "main" in outlineId:
        outline_type = "MAIN"
    elif "coarse" in outlineId:
        outline_type = "COARSE"

    return _success({
        "outlineId": outlineId,
        "bookId": "mock_book_id",
        "outlineType": outline_type,
        "chapterIndex": 1 if outline_type == "CHAPTER" else None,
        "status": "COMPLETED",
        "content": {
            "generalStyle": "本章节采用第三人称视角叙述，语言风格质朴自然...",
            "globalVisualRhythm": "节奏先缓后急，开篇平铺直叙，中段逐渐加快...",
            "settingsTemplate": {
                "characters": ["主角：林风", "配角：村长李伯"],
                "locations": ["青石村", "后山"],
                "items": ["祖传玉佩"],
            },
            "plotStyleIntegration": {
                "plotElements": {
                    "mainPlot": "主角林风在村中过着平凡生活",
                    "conflict": "突然出现的神秘人打破平静",
                    "climax": "玉佩觉醒，主角获得神秘力量",
                },
                "styleAnalysis": "文风质朴中带有神秘感...",
            },
            "summary": "本章主要介绍主角林风的背景，他在青石村过着平凡的生活...",
        },
        "summary": "本章主要介绍主角林风的背景...",
        "createdAt": _timestamp(),
    })


@app.post("/api/v1/outlines/{outlineId}/copy")
async def copy_outline(
    outlineId: str = Path(...),
    format: str = Query("text"),
):
    outline_type = "CHAPTER"
    if "world" in outlineId:
        outline_type = "WORLD"
    elif "main" in outlineId:
        outline_type = "MAIN"
    elif "coarse" in outlineId:
        outline_type = "COARSE"

    content = f"【{outline_type}纲】\n\n概括：这是一个示例纲内容...\n\n详细内容：本章节采用第三人称视角叙述..."

    return _success({
        "outlineId": outlineId,
        "outlineType": outline_type,
        "copyContent": content,
        "copyFormat": format,
    })


@app.get("/api/v1/tasks/{taskId}")
async def get_task_status(taskId: str = Path(...)):
    if taskId not in MOCK_TASKS:
        return JSONResponse(status_code=404, content=_error("TASK_NOT_FOUND", "任务不存在"))

    return _success(MOCK_TASKS[taskId])


@app.get("/api/v1/tasks/{taskId}/errors")
async def get_task_errors(
    taskId: str = Path(...),
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
):
    if taskId not in MOCK_TASKS:
        return JSONResponse(status_code=404, content=_error("TASK_NOT_FOUND", "任务不存在"))

    return _success({
        "taskId": taskId,
        "totalErrors": 0,
        "errors": [],
    })


if __name__ == "__main__":
    print("=" * 50)
    print("AI小说拆书系统 Mock Server")
    print("地址: http://localhost:3001")
    print("API文档: http://localhost:3001/docs")
    print("=" * 50)
    uvicorn.run(app, host="0.0.0.0", port=3001)
