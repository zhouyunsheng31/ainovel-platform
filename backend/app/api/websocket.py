"""
WebSocket实时推送路由
WS /api/v1/ws/{taskId} - 实时进度推送
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, Set
import json
import asyncio
from datetime import datetime, timezone

router = APIRouter(tags=["websocket"])


class ConnectionManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, task_id: str):
        """接受新连接"""
        await websocket.accept()
        if task_id not in self.active_connections:
            self.active_connections[task_id] = set()
        self.active_connections[task_id].add(websocket)
    
    def disconnect(self, websocket: WebSocket, task_id: str):
        """断开连接"""
        if task_id in self.active_connections:
            self.active_connections[task_id].discard(websocket)
            if not self.active_connections[task_id]:
                del self.active_connections[task_id]
    
    async def send_to_task(self, task_id: str, message: dict):
        """向指定任务的所有连接发送消息"""
        if task_id in self.active_connections:
            disconnected = set()
            for connection in self.active_connections[task_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    disconnected.add(connection)
            for conn in disconnected:
                self.active_connections[task_id].discard(conn)
    
    async def broadcast(self, message: dict):
        """向所有连接广播消息"""
        for task_id in list(self.active_connections.keys()):
            await self.send_to_task(task_id, message)


manager = ConnectionManager()


def get_timestamp() -> str:
    """获取ISO格式时间戳"""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@router.websocket("/api/v1/ws/{taskId}")
async def websocket_endpoint(websocket: WebSocket, taskId: str):
    """
    WebSocket实时进度推送
    消息类型：progress/outline_update/error/completed
    """
    await manager.connect(websocket, taskId)
    
    try:
        await websocket.send_json({
            "type": "connected",
            "payload": {"taskId": taskId, "message": "WebSocket连接成功"},
            "timestamp": get_timestamp()
        })
        
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                try:
                    message = json.loads(data)
                    await handle_client_message(websocket, taskId, message)
                except json.JSONDecodeError:
                    await websocket.send_json({
                        "type": "error",
                        "payload": {"message": "无效的JSON消息"},
                        "timestamp": get_timestamp()
                    })
            except asyncio.TimeoutError:
                await websocket.send_json({
                    "type": "heartbeat",
                    "payload": {},
                    "timestamp": get_timestamp()
                })
                
    except WebSocketDisconnect:
        manager.disconnect(websocket, taskId)
    except Exception as e:
        try:
            await websocket.send_json({
                "type": "error",
                "payload": {"errorType": "WEBSOCKET_ERROR", "errorMessage": str(e)},
                "timestamp": get_timestamp()
            })
        except Exception:
            pass
        manager.disconnect(websocket, taskId)


async def handle_client_message(websocket: WebSocket, task_id: str, message: dict):
    """处理客户端消息"""
    msg_type = message.get("type", "unknown")
    
    if msg_type == "ping":
        await websocket.send_json({"type": "pong", "payload": {}, "timestamp": get_timestamp()})
    elif msg_type == "get_status":
        await websocket.send_json({
            "type": "status_response",
            "payload": {"taskId": task_id, "message": "请使用HTTP API查询详细状态"},
            "timestamp": get_timestamp()
        })
    else:
        await websocket.send_json({
            "type": "error",
            "payload": {"message": f"未知的消息类型: {msg_type}"},
            "timestamp": get_timestamp()
        })


# ================================
# 进度推送辅助函数（供服务层调用）
# ================================

async def send_progress_update(task_id: str, stage: str, progress: int, total: int, completed: int, message: str):
    """发送进度更新消息"""
    await manager.send_to_task(task_id, {
        "type": "progress",
        "payload": {
            "taskId": task_id, "stage": stage, "progress": progress,
            "total": total, "completed": completed, "message": message
        },
        "timestamp": get_timestamp()
    })


async def send_outline_update(task_id: str, outline_id: str, outline_type: str, chapter_index: int, status: str, summary: str):
    """发送纲更新消息"""
    await manager.send_to_task(task_id, {
        "type": "outline_update",
        "payload": {
            "outlineId": outline_id, "outlineType": outline_type,
            "chapterIndex": chapter_index, "status": status, "summary": summary
        },
        "timestamp": get_timestamp()
    })


async def send_error_message(task_id: str, stage: str, chapter_index: int, error_type: str, error_message: str, will_retry: bool = False, retry_after: int = None):
    """发送错误消息"""
    await manager.send_to_task(task_id, {
        "type": "error",
        "payload": {
            "taskId": task_id, "stage": stage, "chapterIndex": chapter_index,
            "errorType": error_type, "errorMessage": error_message,
            "willRetry": will_retry, "retryAfter": retry_after
        },
        "timestamp": get_timestamp()
    })


async def send_completed_message(task_id: str, book_id: str, total_chapters: int, total_time: int, world_outline_id: str):
    """发送完成消息"""
    await manager.send_to_task(task_id, {
        "type": "completed",
        "payload": {
            "taskId": task_id, "bookId": book_id, "status": "COMPLETED",
            "totalChapters": total_chapters, "totalTime": total_time,
            "worldOutlineId": world_outline_id
        },
        "timestamp": get_timestamp()
    })
