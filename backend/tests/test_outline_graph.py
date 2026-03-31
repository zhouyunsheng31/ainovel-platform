import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.workflows.outline_graph import OutlineGraphWorkflow


class FakeOutlineService:
    async def generate_chapter_outlines(self, chapters, progress_callback=None):
        if progress_callback:
            result = progress_callback(len(chapters), len(chapters))
            if result is not None:
                await result
        return [
            {"index": i, "content": {"summary": f"章纲{i+1}"}, "summary": f"章纲{i+1}", "status": "COMPLETED"}
            for i, _ in enumerate(chapters)
        ]

    async def generate_coarse_outlines(self, chapter_outlines, group_size=10, progress_callback=None):
        if progress_callback:
            result = progress_callback(1, 1)
            if result is not None:
                await result
        return [
            {"index": 0, "content": {"summary": "粗纲1"}, "summary": "粗纲1", "status": "COMPLETED"}
        ]

    async def generate_main_outlines(self, coarse_outlines, group_size=10, progress_callback=None):
        if progress_callback:
            result = progress_callback(1, 1)
            if result is not None:
                await result
        return [
            {"index": 0, "content": {"summary": "大纲1"}, "summary": "大纲1", "status": "COMPLETED"}
        ]

    async def generate_world_outline(self, main_outlines, progress_callback=None):
        if progress_callback:
            result = progress_callback(1, 1)
            if result is not None:
                await result
        return {"content": {"summary": "世界纲"}, "summary": "世界纲", "status": "COMPLETED"}


class FailingChapterOutlineService(FakeOutlineService):
    async def generate_chapter_outlines(self, chapters, progress_callback=None):
        if progress_callback:
            result = progress_callback(len(chapters), len(chapters))
            if result is not None:
                await result
        return [
            {"index": i, "content": {}, "summary": "", "status": "FAILED", "error": f"章纲{i+1}生成失败"}
            for i, _ in enumerate(chapters)
        ]


class FailingCoarseOutlineService(FakeOutlineService):
    async def generate_coarse_outlines(self, chapter_outlines, group_size=10, progress_callback=None):
        if progress_callback:
            result = progress_callback(1, 1)
            if result is not None:
                await result
        return [
            {"index": 0, "content": {}, "summary": "", "status": "FAILED", "error": "粗纲生成失败"}
        ]


class FailingMainOutlineService(FakeOutlineService):
    async def generate_main_outlines(self, coarse_outlines, group_size=10, progress_callback=None):
        if progress_callback:
            result = progress_callback(1, 1)
            if result is not None:
                await result
        return [
            {"index": 0, "content": {}, "summary": "", "status": "FAILED", "error": "大纲生成失败"}
        ]


class FailingWorldOutlineService(FakeOutlineService):
    async def generate_world_outline(self, main_outlines, progress_callback=None):
        if progress_callback:
            result = progress_callback(1, 1)
            if result is not None:
                await result
        return {"content": {}, "summary": "", "status": "FAILED", "error": "世界纲生成失败"}


class MultiFailService(FakeOutlineService):
    async def generate_chapter_outlines(self, chapters, progress_callback=None):
        if progress_callback:
            result = progress_callback(len(chapters), len(chapters))
            if result is not None:
                await result
        return [
            {"index": 0, "content": {"summary": "章纲1"}, "summary": "章纲1", "status": "COMPLETED"},
            {"index": 1, "content": {}, "summary": "", "status": "FAILED", "error": "章纲2失败"},
        ]

    async def generate_coarse_outlines(self, chapter_outlines, group_size=10, progress_callback=None):
        if progress_callback:
            result = progress_callback(1, 1)
            if result is not None:
                await result
        return [
            {"index": 0, "content": {}, "summary": "", "status": "FAILED", "error": "粗纲失败"}
        ]


@pytest.fixture
def sample_chapters():
    return [{"index": 0, "text": "a"}, {"index": 1, "text": "b"}]


class TestOutlineGraphHappyPath:
    @pytest.mark.asyncio
    async def test_full_workflow_produces_correct_structure(self, sample_chapters):
        workflow = OutlineGraphWorkflow(outline_service=FakeOutlineService())
        result = await workflow.run(chapters=sample_chapters)

        assert len(result["chapter_outlines"]) == 2
        assert len(result["coarse_outlines"]) == 1
        assert len(result["main_outlines"]) == 1
        assert result["world_outline"]["summary"] == "世界纲"
        assert result["errors"] == []

    @pytest.mark.asyncio
    async def test_chapter_outlines_content(self, sample_chapters):
        workflow = OutlineGraphWorkflow(outline_service=FakeOutlineService())
        result = await workflow.run(chapters=sample_chapters)

        assert result["chapter_outlines"][0]["index"] == 0
        assert result["chapter_outlines"][0]["status"] == "COMPLETED"
        assert result["chapter_outlines"][1]["index"] == 1
        assert result["chapter_outlines"][1]["status"] == "COMPLETED"

    @pytest.mark.asyncio
    async def test_coarse_outlines_content(self, sample_chapters):
        workflow = OutlineGraphWorkflow(outline_service=FakeOutlineService())
        result = await workflow.run(chapters=sample_chapters)

        assert result["coarse_outlines"][0]["index"] == 0
        assert result["coarse_outlines"][0]["status"] == "COMPLETED"

    @pytest.mark.asyncio
    async def test_main_outlines_content(self, sample_chapters):
        workflow = OutlineGraphWorkflow(outline_service=FakeOutlineService())
        result = await workflow.run(chapters=sample_chapters)

        assert result["main_outlines"][0]["index"] == 0
        assert result["main_outlines"][0]["status"] == "COMPLETED"

    @pytest.mark.asyncio
    async def test_world_outline_content(self, sample_chapters):
        workflow = OutlineGraphWorkflow(outline_service=FakeOutlineService())
        result = await workflow.run(chapters=sample_chapters)

        assert result["world_outline"]["status"] == "COMPLETED"
        assert "世界纲" in result["world_outline"]["summary"]


class TestOutlineGraphProgressCallback:
    @pytest.mark.asyncio
    async def test_progress_callback_receives_all_stages(self, sample_chapters):
        calls = []

        async def progress(stage, current, total):
            calls.append((stage, current, total))

        workflow = OutlineGraphWorkflow(outline_service=FakeOutlineService())
        await workflow.run(chapters=sample_chapters, progress_callback=progress)

        stages = [item[0] for item in calls]
        assert stages == [
            "CHAPTER_OUTLINE",
            "COARSE_OUTLINE",
            "MAIN_OUTLINE",
            "WORLD_OUTLINE",
        ]

    @pytest.mark.asyncio
    async def test_progress_callback_with_current_and_total(self, sample_chapters):
        calls = []

        async def progress(stage, current, total):
            calls.append((stage, current, total))

        workflow = OutlineGraphWorkflow(outline_service=FakeOutlineService())
        await workflow.run(chapters=sample_chapters, progress_callback=progress)

        chapter_calls = [c for c in calls if c[0] == "CHAPTER_OUTLINE"]
        assert len(chapter_calls) == 1
        assert chapter_calls[0][1] == 2
        assert chapter_calls[0][2] == 2

    @pytest.mark.asyncio
    async def test_no_progress_callback_does_not_crash(self, sample_chapters):
        workflow = OutlineGraphWorkflow(outline_service=FakeOutlineService())
        result = await workflow.run(chapters=sample_chapters, progress_callback=None)

        assert len(result["chapter_outlines"]) == 2
        assert result["errors"] == []


class TestOutlineGraphFailures:
    @pytest.mark.asyncio
    async def test_chapter_outline_failure(self, sample_chapters):
        workflow = OutlineGraphWorkflow(outline_service=FailingChapterOutlineService())
        result = await workflow.run(chapters=sample_chapters)

        assert len(result["chapter_outlines"]) == 2
        assert all(co["status"] == "FAILED" for co in result["chapter_outlines"])
        assert len(result["errors"]) == 2
        assert result["errors"][0]["stage"] == "CHAPTER_OUTLINE"
        assert result["errors"][0]["index"] == 0
        assert "章纲" in result["errors"][0]["error"]

    @pytest.mark.asyncio
    async def test_coarse_outline_failure(self, sample_chapters):
        workflow = OutlineGraphWorkflow(outline_service=FailingCoarseOutlineService())
        result = await workflow.run(chapters=sample_chapters)

        assert len(result["chapter_outlines"]) == 2
        assert result["chapter_outlines"][0]["status"] == "COMPLETED"
        assert len(result["coarse_outlines"]) == 1
        assert result["coarse_outlines"][0]["status"] == "FAILED"
        assert len(result["errors"]) == 1
        assert result["errors"][0]["stage"] == "COARSE_OUTLINE"

    @pytest.mark.asyncio
    async def test_main_outline_failure(self, sample_chapters):
        workflow = OutlineGraphWorkflow(outline_service=FailingMainOutlineService())
        result = await workflow.run(chapters=sample_chapters)

        assert len(result["chapter_outlines"]) == 2
        assert len(result["coarse_outlines"]) == 1
        assert len(result["main_outlines"]) == 1
        assert result["main_outlines"][0]["status"] == "FAILED"
        assert len(result["errors"]) == 1
        assert result["errors"][0]["stage"] == "MAIN_OUTLINE"

    @pytest.mark.asyncio
    async def test_world_outline_failure(self, sample_chapters):
        workflow = OutlineGraphWorkflow(outline_service=FailingWorldOutlineService())
        result = await workflow.run(chapters=sample_chapters)

        assert len(result["chapter_outlines"]) == 2
        assert len(result["coarse_outlines"]) == 1
        assert len(result["main_outlines"]) == 1
        assert result["world_outline"]["status"] == "FAILED"
        assert len(result["errors"]) == 1
        assert result["errors"][0]["stage"] == "WORLD_OUTLINE"

    @pytest.mark.asyncio
    async def test_multiple_stage_failures_accumulate(self, sample_chapters):
        workflow = OutlineGraphWorkflow(outline_service=MultiFailService())
        result = await workflow.run(chapters=sample_chapters)

        assert len(result["errors"]) == 2
        stages = [e["stage"] for e in result["errors"]]
        assert "CHAPTER_OUTLINE" in stages
        assert "COARSE_OUTLINE" in stages


class TestOutlineGraphEdgeCases:
    @pytest.mark.asyncio
    async def test_empty_chapters(self):
        workflow = OutlineGraphWorkflow(outline_service=FakeOutlineService())
        result = await workflow.run(chapters=[])

        assert result["chapter_outlines"] == []
        assert result["errors"] == []

    @pytest.mark.asyncio
    async def test_single_chapter(self):
        workflow = OutlineGraphWorkflow(outline_service=FakeOutlineService())
        result = await workflow.run(chapters=[{"index": 0, "text": "only chapter"}])

        assert len(result["chapter_outlines"]) == 1
        assert result["chapter_outlines"][0]["index"] == 0
        assert result["errors"] == []
