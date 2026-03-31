"""
纲相关API路由
GET /api/v1/outlines/{outlineId} - 获取纲详情
POST /api/v1/outlines/{outlineId}/copy - 复制纲内容
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any
import json

from ..models.database import get_session
from ..models.models import Outline
from ..models.schemas import (
    OutlineTypeEnum, OutlineStatusEnum,
    OutlineDetailResponse, OutlineDetailData,
    CopyOutlineResponse, CopyOutlineData
)

router = APIRouter(prefix="/api/v1/outlines", tags=["outlines"])


async def get_db():
    """数据库会话依赖"""
    async with get_session() as session:
        yield session


@router.get("/{outlineId}", response_model=OutlineDetailResponse)
async def get_outline(outlineId: str, db: AsyncSession = Depends(get_db)):
    """获取纲详情"""
    result = await db.execute(
        select(Outline).where(Outline.outline_id == outlineId)
    )
    outline = result.scalar_one_or_none()
    
    if not outline:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "OUTLINE_NOT_FOUND",
                "message": f"纲不存在: {outlineId}",
                "details": {}
            }
        )
    
    content = outline.content_json if outline.content_json else {}
    if isinstance(content, str):
        try:
            content = json.loads(content)
        except (json.JSONDecodeError, TypeError):
            content = {}
    
    return OutlineDetailResponse(
        data=OutlineDetailData(
            outlineId=outline.outline_id,
            bookId=outline.book_id,
            outlineType=OutlineTypeEnum(outline.outline_type),
            chapterIndex=outline.chapter_index,
            status=OutlineStatusEnum(outline.status),
            content=content,
            summary=outline.summary or "",
            createdAt=outline.created_at.isoformat() + "Z" if outline.created_at else ""
        )
    )


@router.post("/{outlineId}/copy", response_model=CopyOutlineResponse)
async def copy_outline(
    outlineId: str,
    format: str = "text",
    db: AsyncSession = Depends(get_db)
):
    """复制纲内容"""
    result = await db.execute(
        select(Outline).where(Outline.outline_id == outlineId)
    )
    outline = result.scalar_one_or_none()
    
    if not outline:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "OUTLINE_NOT_FOUND",
                "message": f"纲不存在: {outlineId}",
                "details": {}
            }
        )
    
    copy_content = _format_outline_content(outline, format)
    
    return CopyOutlineResponse(
        data=CopyOutlineData(
            outlineId=outlineId,
            outlineType=OutlineTypeEnum(outline.outline_type),
            copyContent=copy_content,
            copyFormat=format
        )
    )


def _format_outline_content(outline: Outline, format: str) -> str:
    """格式化纲内容用于复制"""
    type_labels = {
        "CHAPTER": "章纲",
        "COARSE": "粗纲",
        "MAIN": "大纲",
        "WORLD": "世界纲"
    }
    type_label = type_labels.get(outline.outline_type, outline.outline_type)
    
    if outline.outline_type == "CHAPTER":
        index_info = f" {outline.chapter_index + 1}" if outline.chapter_index is not None else ""
        label = f"【{type_label}{index_info}】"
    elif outline.chapter_range_start is not None:
        label = f"【{type_label} (章节{outline.chapter_range_start + 1}-{outline.chapter_range_end + 1})】"
    else:
        label = f"【{type_label}】"
    
    if format == "json":
        return json.dumps({
            "type": outline.outline_type,
            "index": outline.chapter_index,
            "range": [outline.chapter_range_start, outline.chapter_range_end] if outline.chapter_range_start is not None else None,
            "summary": outline.summary,
            "content": outline.content_json
        }, ensure_ascii=False, indent=2)
    
    elif format == "markdown":
        lines = [f"# {label}", "", f"**概括**: {outline.summary or '无'}", ""]
        content = outline.content_json if outline.content_json else {}
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except (json.JSONDecodeError, TypeError):
                content = {}
        if content:
            lines.append("## 详细内容\n")
            lines.append(_dict_to_markdown(content, 2))
        return "\n".join(lines)
    
    else:
        lines = [label, "", f"概括：{outline.summary or '无'}", ""]
        content = outline.content_json if outline.content_json else {}
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except (json.JSONDecodeError, TypeError):
                content = {}
        if content:
            lines.append("详细内容：")
            lines.append(_dict_to_text(content, indent=1))
        return "\n".join(lines)


def _dict_to_markdown(d: Dict[str, Any], level: int = 1) -> str:
    """将字典转换为Markdown格式"""
    lines = []
    prefix = "#" * level
    for key, value in d.items():
        if isinstance(value, dict):
            lines.append(f"{prefix} {key}\n")
            lines.append(_dict_to_markdown(value, level + 1))
        elif isinstance(value, list):
            lines.append(f"{prefix} {key}:\n")
            for item in value:
                if isinstance(item, dict):
                    lines.append(_dict_to_markdown(item, level + 1))
                else:
                    lines.append(f"- {item}\n")
        else:
            lines.append(f"**{key}**: {value}")
    return "\n".join(lines)


def _dict_to_text(d: Dict[str, Any], indent: int = 0) -> str:
    """将字典转换为纯文本格式"""
    lines = []
    prefix = "  " * indent
    for key, value in d.items():
        if isinstance(value, dict):
            lines.append(f"{prefix}{key}:")
            lines.append(_dict_to_text(value, indent + 1))
        elif isinstance(value, list):
            lines.append(f"{prefix}{key}:")
            for item in value:
                if isinstance(item, dict):
                    lines.append(_dict_to_text(item, indent + 1))
                else:
                    lines.append(f"{prefix}  - {item}")
        else:
            lines.append(f"{prefix}{key}: {value}")
    return "\n".join(lines)
