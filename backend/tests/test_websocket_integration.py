"""
WebSocket集成测试
测试WebSocket连接、心跳、消息类型
"""
import pytest

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.api.websocket import handle_client_message, get_timestamp


class TestConnectionManager:
    @pytest.mark.asyncio
    async def test_manager_initial_state(self):
        from app.api.websocket import ConnectionManager
        m = ConnectionManager()
        assert m.active_connections == {}

    @pytest.mark.asyncio
    async def test_manager_connect_and_disconnect(self):
        from app.api.websocket import ConnectionManager
        from unittest.mock import AsyncMock

        m = ConnectionManager()
        ws = AsyncMock()
        ws.accept = AsyncMock()

        await m.connect(ws, "task-001")
        assert "task-001" in m.active_connections
        assert ws in m.active_connections["task-001"]

        m.disconnect(ws, "task-001")
        assert "task-001" not in m.active_connections

    @pytest.mark.asyncio
    async def test_manager_send_to_task(self):
        from app.api.websocket import ConnectionManager
        from unittest.mock import AsyncMock

        m = ConnectionManager()
        ws1 = AsyncMock()
        ws1.send_json = AsyncMock()
        ws2 = AsyncMock()
        ws2.send_json = AsyncMock()

        m.active_connections["task-002"] = {ws1, ws2}
        msg = {"type": "progress", "payload": {"progress": 50}}
        await m.send_to_task("task-002", msg)

        ws1.send_json.assert_called_once_with(msg)
        ws2.send_json.assert_called_once_with(msg)

    @pytest.mark.asyncio
    async def test_manager_send_to_nonexistent_task(self):
        from app.api.websocket import ConnectionManager
        m = ConnectionManager()
        await m.send_to_task("nonexistent", {"type": "test"})

    @pytest.mark.asyncio
    async def test_manager_disconnect_removes_empty_set(self):
        from app.api.websocket import ConnectionManager
        from unittest.mock import AsyncMock

        m = ConnectionManager()
        ws = AsyncMock()
        m.active_connections["task-003"] = {ws}

        m.disconnect(ws, "task-003")
        assert "task-003" not in m.active_connections

    @pytest.mark.asyncio
    async def test_manager_broadcast(self):
        from app.api.websocket import ConnectionManager
        from unittest.mock import AsyncMock

        m = ConnectionManager()
        ws1 = AsyncMock()
        ws1.send_json = AsyncMock()
        ws2 = AsyncMock()
        ws2.send_json = AsyncMock()

        m.active_connections["task-a"] = {ws1}
        m.active_connections["task-b"] = {ws2}

        msg = {"type": "broadcast", "payload": {}}
        await m.broadcast(msg)

        ws1.send_json.assert_called_once_with(msg)
        ws2.send_json.assert_called_once_with(msg)


class TestHandleClientMessage:
    @pytest.mark.asyncio
    async def test_ping_returns_pong(self):
        from unittest.mock import AsyncMock

        ws = AsyncMock()
        ws.send_json = AsyncMock()

        await handle_client_message(ws, "task-001", {"type": "ping"})
        ws.send_json.assert_called_once()
        sent = ws.send_json.call_args[0][0]
        assert sent["type"] == "pong"

    @pytest.mark.asyncio
    async def test_get_status_returns_status_response(self):
        from unittest.mock import AsyncMock

        ws = AsyncMock()
        ws.send_json = AsyncMock()

        await handle_client_message(ws, "task-002", {"type": "get_status"})
        ws.send_json.assert_called_once()
        sent = ws.send_json.call_args[0][0]
        assert sent["type"] == "status_response"
        assert sent["payload"]["taskId"] == "task-002"

    @pytest.mark.asyncio
    async def test_unknown_type_returns_error(self):
        from unittest.mock import AsyncMock

        ws = AsyncMock()
        ws.send_json = AsyncMock()

        await handle_client_message(ws, "task-003", {"type": "custom"})
        ws.send_json.assert_called_once()
        sent = ws.send_json.call_args[0][0]
        assert sent["type"] == "error"
        assert "未知的消息类型" in sent["payload"]["message"]


class TestTimestamp:
    def test_get_timestamp_format(self):
        ts = get_timestamp()
        assert ts.endswith("Z")
        assert "T" in ts


class TestWebSocketHelperFunctions:
    @pytest.mark.asyncio
    async def test_send_progress_update(self):
        from unittest.mock import AsyncMock, patch
        from app.api.websocket import send_progress_update

        mock_manager = AsyncMock()
        with patch("app.api.websocket.manager", mock_manager):
            await send_progress_update("task-1", "CHAPTER_OUTLINE", 50, 10, 5, "处理中")
            mock_manager.send_to_task.assert_called_once()
            msg = mock_manager.send_to_task.call_args[0][1]
            assert msg["type"] == "progress"
            assert msg["payload"]["progress"] == 50
            assert msg["payload"]["stage"] == "CHAPTER_OUTLINE"

    @pytest.mark.asyncio
    async def test_send_outline_update(self):
        from unittest.mock import AsyncMock, patch
        from app.api.websocket import send_outline_update

        mock_manager = AsyncMock()
        with patch("app.api.websocket.manager", mock_manager):
            await send_outline_update("task-1", "outline-1", "CHAPTER", 0, "COMPLETED", "测试概要")
            msg = mock_manager.send_to_task.call_args[0][1]
            assert msg["type"] == "outline_update"
            assert msg["payload"]["outlineId"] == "outline-1"
            assert msg["payload"]["outlineType"] == "CHAPTER"

    @pytest.mark.asyncio
    async def test_send_error_message(self):
        from unittest.mock import AsyncMock, patch
        from app.api.websocket import send_error_message

        mock_manager = AsyncMock()
        with patch("app.api.websocket.manager", mock_manager):
            await send_error_message("task-1", "PROCESSING", 0, "TIMEOUT", "超时", will_retry=True, retry_after=30)
            msg = mock_manager.send_to_task.call_args[0][1]
            assert msg["type"] == "error"
            assert msg["payload"]["errorType"] == "TIMEOUT"
            assert msg["payload"]["willRetry"] is True
            assert msg["payload"]["retryAfter"] == 30

    @pytest.mark.asyncio
    async def test_send_completed_message(self):
        from unittest.mock import AsyncMock, patch
        from app.api.websocket import send_completed_message

        mock_manager = AsyncMock()
        with patch("app.api.websocket.manager", mock_manager):
            await send_completed_message("task-1", "book-1", 20, 120, "world-1")
            msg = mock_manager.send_to_task.call_args[0][1]
            assert msg["type"] == "completed"
            assert msg["payload"]["totalChapters"] == 20
            assert msg["payload"]["worldOutlineId"] == "world-1"
