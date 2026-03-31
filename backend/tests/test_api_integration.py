"""
API集成测试
测试所有API端点的功能：上传、任务状态、纲树、错误日志等关键路径
"""
import pytest
import pytest_asyncio
import asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from main import app
from app.models.database import init_db


@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="module")
async def client():
    await init_db()
    with patch("app.api.books.task_processor") as mock_tp:
        mock_tp.start_processing = AsyncMock()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac


def _make_txt_content(size: int = 100) -> bytes:
    paragraph = "这是一段测试文本，用于模拟小说内容。" * 10
    full = paragraph.encode("utf-8")
    return full[:size] if size < len(full) else full


class TestHealthEndpoints:
    @pytest.mark.asyncio
    async def test_root(self, client):
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "message" in data
        assert "version" in data

    @pytest.mark.asyncio
    async def test_health(self, client):
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "service" in data


class TestUploadBook:
    @pytest.mark.asyncio
    async def test_upload_txt_file(self, client):
        files = {"file": ("test.txt", _make_txt_content(), "text/plain")}
        data = {"title": "测试上传TXT"}
        response = await client.post("/api/v1/books/upload", files=files, data=data)
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True
        assert "bookId" in result["data"]
        assert "taskId" in result["data"]
        assert result["data"]["fileName"] == "test.txt"
        assert result["data"]["status"] == "UPLOADING"

    @pytest.mark.asyncio
    async def test_upload_with_title_and_author(self, client):
        files = {"file": ("novel.txt", _make_txt_content(), "text/plain")}
        data = {"title": "自定义书名", "author": "测试作者"}
        response = await client.post("/api/v1/books/upload", files=files, data=data)
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True
        assert result["data"]["fileName"] == "novel.txt"

    @pytest.mark.asyncio
    async def test_upload_without_title_uses_filename(self, client):
        files = {"file": ("我的小说.txt", _make_txt_content(), "text/plain")}
        response = await client.post("/api/v1/books/upload", files=files)
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_upload_invalid_format(self, client):
        files = {"file": ("test.xyz", b"Invalid content", "application/octet-stream")}
        response = await client.post("/api/v1/books/upload", files=files)
        assert response.status_code == 400
        detail = response.json()
        assert "INVALID_FILE_FORMAT" in str(detail)

    @pytest.mark.asyncio
    async def test_upload_invalid_format_exe(self, client):
        files = {"file": ("malware.exe", b"MZ\x90\x00", "application/octet-stream")}
        response = await client.post("/api/v1/books/upload", files=files)
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_upload_oversized_file(self, client):
        big_content = b"x" * (50 * 1024 * 1024 + 1)
        files = {"file": ("big.txt", big_content, "text/plain")}
        response = await client.post("/api/v1/books/upload", files=files)
        assert response.status_code == 413
        detail = response.json()
        assert "FILE_TOO_LARGE" in str(detail)


class TestBooksList:
    @pytest.mark.asyncio
    async def test_list_books_default(self, client):
        response = await client.get("/api/v1/books")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "books" in data["data"]
        assert "pagination" in data["data"]
        pagination = data["data"]["pagination"]
        assert "page" in pagination
        assert "pageSize" in pagination
        assert "total" in pagination
        assert "totalPages" in pagination

    @pytest.mark.asyncio
    async def test_list_books_with_status_filter(self, client):
        response = await client.get("/api/v1/books?status=COMPLETED")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_list_books_pagination(self, client):
        response = await client.get("/api/v1/books?page=1&pageSize=5")
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["pagination"]["page"] == 1
        assert data["data"]["pagination"]["pageSize"] == 5

    @pytest.mark.asyncio
    async def test_list_books_sorting(self, client):
        response = await client.get("/api/v1/books?sortBy=title&sortOrder=asc")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_list_books_response_schema(self, client):
        response = await client.get("/api/v1/books")
        data = response.json()
        assert "success" in data
        assert "timestamp" in data
        books = data["data"]["books"]
        if books:
            book = books[0]
            required_fields = ["bookId", "title", "originalName", "fileType",
                               "fileSize", "totalChapters", "status", "createdAt", "updatedAt"]
            for field in required_fields:
                assert field in book, f"Missing field: {field}"


class TestBookDetail:
    @pytest.mark.asyncio
    async def test_get_book_detail(self, client):
        list_resp = await client.get("/api/v1/books")
        books = list_resp.json()["data"]["books"]
        if not books:
            pytest.skip("No books available")
        book_id = books[0]["bookId"]
        response = await client.get(f"/api/v1/books/{book_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        detail = data["data"]
        assert detail["bookId"] == book_id
        assert "title" in detail
        assert "originalName" in detail
        assert "fileType" in detail
        assert "fileSize" in detail
        assert "totalChapters" in detail
        assert "status" in detail
        assert "encoding" in detail
        assert "createdAt" in detail
        assert "updatedAt" in detail

    @pytest.mark.asyncio
    async def test_get_book_not_found(self, client):
        response = await client.get("/api/v1/books/non-existent-id")
        assert response.status_code == 404
        detail = response.json()
        assert "BOOK_NOT_FOUND" in str(detail)


class TestBookDelete:
    @pytest.mark.asyncio
    async def test_delete_book(self, client):
        files = {"file": ("to_delete.txt", _make_txt_content(), "text/plain")}
        upload_resp = await client.post("/api/v1/books/upload", files=files)
        assert upload_resp.status_code == 200
        book_id = upload_resp.json()["data"]["bookId"]

        delete_resp = await client.delete(f"/api/v1/books/{book_id}")
        assert delete_resp.status_code == 200
        data = delete_resp.json()
        assert data["success"] is True
        assert data["data"]["bookId"] == book_id

        verify_resp = await client.get(f"/api/v1/books/{book_id}")
        assert verify_resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_book_not_found(self, client):
        response = await client.delete("/api/v1/books/non-existent-id")
        assert response.status_code == 404
        detail = response.json()
        assert "BOOK_NOT_FOUND" in str(detail)


class TestOutlineTree:
    @pytest.mark.asyncio
    async def test_get_outline_tree_for_book(self, client):
        list_resp = await client.get("/api/v1/books")
        books = list_resp.json()["data"]["books"]
        if not books:
            pytest.skip("No books available")
        book_id = books[0]["bookId"]
        response = await client.get(f"/api/v1/books/{book_id}/tree")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "tree" in data["data"]
        assert data["data"]["bookId"] == book_id
        tree = data["data"]["tree"]
        assert "outlineId" in tree
        assert "outlineType" in tree
        assert "label" in tree
        assert "status" in tree
        assert "children" in tree

    @pytest.mark.asyncio
    async def test_get_outline_tree_book_not_found(self, client):
        response = await client.get("/api/v1/books/non-existent-id/tree")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_outline_tree_empty_structure(self, client):
        files = {"file": ("empty_tree.txt", _make_txt_content(), "text/plain")}
        upload_resp = await client.post("/api/v1/books/upload", files=files)
        book_id = upload_resp.json()["data"]["bookId"]

        tree_resp = await client.get(f"/api/v1/books/{book_id}/tree")
        assert tree_resp.status_code == 200
        data = tree_resp.json()
        tree = data["data"]["tree"]
        assert tree["outlineType"] == "WORLD"
        assert tree["status"] == "PENDING"
        assert tree["children"] == []


class TestBookStatus:
    @pytest.mark.asyncio
    async def test_get_book_status(self, client):
        files = {"file": ("status_check.txt", _make_txt_content(), "text/plain")}
        upload_resp = await client.post("/api/v1/books/upload", files=files)
        book_id = upload_resp.json()["data"]["bookId"]

        status_resp = await client.get(f"/api/v1/books/{book_id}/status")
        assert status_resp.status_code == 200
        data = status_resp.json()
        assert data["success"] is True
        status_data = data["data"]
        assert status_data["bookId"] == book_id
        assert "status" in status_data
        assert "taskId" in status_data

    @pytest.mark.asyncio
    async def test_get_book_status_not_found(self, client):
        response = await client.get("/api/v1/books/non-existent-id/status")
        assert response.status_code == 404


class TestTaskStatus:
    @pytest.mark.asyncio
    async def test_get_task_status_from_upload(self, client):
        files = {"file": ("task_test.txt", _make_txt_content(), "text/plain")}
        upload_resp = await client.post("/api/v1/books/upload", files=files)
        task_id = upload_resp.json()["data"]["taskId"]

        response = await client.get(f"/api/v1/tasks/{task_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        task_data = data["data"]
        assert task_data["taskId"] == task_id
        assert "bookId" in task_data
        assert "status" in task_data
        assert "currentStage" in task_data
        assert "stageProgress" in task_data
        assert "totalChapters" in task_data
        assert "completedChapters" in task_data
        assert "errorCount" in task_data
        assert "startTime" in task_data
        progress = task_data["stageProgress"]
        assert "FILE_UPLOAD" in progress
        assert "TEXT_PREPROCESS" in progress
        assert "CHAPTER_OUTLINE" in progress
        assert "COARSE_OUTLINE" in progress
        assert "MAIN_OUTLINE" in progress
        assert "WORLD_OUTLINE" in progress

    @pytest.mark.asyncio
    async def test_get_task_not_found(self, client):
        response = await client.get("/api/v1/tasks/non-existent-id")
        assert response.status_code == 404
        detail = response.json()
        assert "TASK_NOT_FOUND" in str(detail)


class TestTaskErrors:
    @pytest.mark.asyncio
    async def test_get_task_errors_not_found(self, client):
        response = await client.get("/api/v1/tasks/non-existent-id/errors")
        assert response.status_code == 404
        detail = response.json()
        assert "TASK_NOT_FOUND" in str(detail)

    @pytest.mark.asyncio
    async def test_get_task_errors_from_valid_task(self, client):
        files = {"file": ("errors_test.txt", _make_txt_content(), "text/plain")}
        upload_resp = await client.post("/api/v1/books/upload", files=files)
        task_id = upload_resp.json()["data"]["taskId"]

        response = await client.get(f"/api/v1/tasks/{task_id}/errors")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        error_data = data["data"]
        assert error_data["taskId"] == task_id
        assert "totalErrors" in error_data
        assert "errors" in error_data
        assert isinstance(error_data["errors"], list)

    @pytest.mark.asyncio
    async def test_get_task_errors_pagination(self, client):
        files = {"file": ("errors_page.txt", _make_txt_content(), "text/plain")}
        upload_resp = await client.post("/api/v1/books/upload", files=files)
        task_id = upload_resp.json()["data"]["taskId"]

        response = await client.get(f"/api/v1/tasks/{task_id}/errors?page=1&pageSize=10")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestOutlinesAPI:
    @pytest.mark.asyncio
    async def test_get_outline_not_found(self, client):
        response = await client.get("/api/v1/outlines/non-existent-id")
        assert response.status_code == 404
        detail = response.json()
        assert "OUTLINE_NOT_FOUND" in str(detail)

    @pytest.mark.asyncio
    async def test_copy_outline_not_found(self, client):
        response = await client.post("/api/v1/outlines/non-existent-id/copy")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_copy_outline_text_format(self, client):
        files = {"file": ("copy_test.txt", _make_txt_content(), "text/plain")}
        upload_resp = await client.post("/api/v1/books/upload", files=files)
        book_id = upload_resp.json()["data"]["bookId"]

        tree_resp = await client.get(f"/api/v1/books/{book_id}/tree")
        tree = tree_resp.json()["data"]["tree"]
        if tree["outlineId"]:
            copy_resp = await client.post(
                f"/api/v1/outlines/{tree['outlineId']}/copy?format=text"
            )
            assert copy_resp.status_code == 200
            data = copy_resp.json()
            assert data["success"] is True
            assert "copyContent" in data["data"]
            assert data["data"]["copyFormat"] == "text"

    @pytest.mark.asyncio
    async def test_copy_outline_json_format(self, client):
        files = {"file": ("copy_json_test.txt", _make_txt_content(), "text/plain")}
        upload_resp = await client.post("/api/v1/books/upload", files=files)
        book_id = upload_resp.json()["data"]["bookId"]

        tree_resp = await client.get(f"/api/v1/books/{book_id}/tree")
        tree = tree_resp.json()["data"]["tree"]
        if tree["outlineId"]:
            copy_resp = await client.post(
                f"/api/v1/outlines/{tree['outlineId']}/copy?format=json"
            )
            assert copy_resp.status_code == 200
            data = copy_resp.json()
            assert data["data"]["copyFormat"] == "json"

    @pytest.mark.asyncio
    async def test_copy_outline_markdown_format(self, client):
        files = {"file": ("copy_md_test.txt", _make_txt_content(), "text/plain")}
        upload_resp = await client.post("/api/v1/books/upload", files=files)
        book_id = upload_resp.json()["data"]["bookId"]

        tree_resp = await client.get(f"/api/v1/books/{book_id}/tree")
        tree = tree_resp.json()["data"]["tree"]
        if tree["outlineId"]:
            copy_resp = await client.post(
                f"/api/v1/outlines/{tree['outlineId']}/copy?format=markdown"
            )
            assert copy_resp.status_code == 200
            data = copy_resp.json()
            assert data["data"]["copyFormat"] == "markdown"


class TestResponseConsistency:
    @pytest.mark.asyncio
    async def test_api_responses_have_consistent_structure(self, client):
        response = await client.get("/api/v1/books")
        data = response.json()
        assert "success" in data
        assert "timestamp" in data
        assert "data" in data

    @pytest.mark.asyncio
    async def test_error_responses_have_detail(self, client):
        error_endpoints = [
            ("/api/v1/books/non-existent-id", 404),
            ("/api/v1/tasks/non-existent-id", 404),
            ("/api/v1/tasks/non-existent-id/errors", 404),
            ("/api/v1/outlines/non-existent-id", 404),
        ]
        for endpoint, expected_status in error_endpoints:
            response = await client.get(endpoint)
            assert response.status_code == expected_status, (
                f"{endpoint} expected {expected_status}, got {response.status_code}"
            )
            data = response.json()
            assert "detail" in data or "error" in data, (
                f"{endpoint} error response missing detail/error field"
            )

    @pytest.mark.asyncio
    async def test_upload_error_response_structure(self, client):
        files = {"file": ("test.xyz", b"bad", "application/octet-stream")}
        response = await client.post("/api/v1/books/upload", files=files)
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        detail = data["detail"]
        assert "code" in detail
        assert "message" in detail
