"""
AI小说拆书系统 - 性能与并发测试
P5-3 性能与并发测试
"""
import asyncio
import time
import pytest
from typing import List, Dict, Any

# 直接导入模块，避免循环导入
import app.services.llm_service
import app.services.outline_service
import app.services.text_splitter

LLMService = app.services.llm_service.LLMService
OutlineService = app.services.outline_service.OutlineService
TextSplitter = app.services.text_splitter.TextSplitter


class TestPerformance:
    """性能与并发测试类"""

    @pytest.fixture
    def llm_service(self):
        """LLM服务实例"""
        return LLMService()

    @pytest.fixture
    def outline_service(self, llm_service):
        """大纲服务实例"""
        return OutlineService(llm_service=llm_service)

    @pytest.fixture
    def text_splitter(self):
        """文本分割器实例"""
        return TextSplitter()

    async def _load_test_novel(self, file_name: str, max_chapters: int = 10) -> List[str]:
        """加载测试小说文本并分割成章节"""
        file_path = f"/workspace/novel/{file_name}"
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 简单分割成章节（按换行符）
            chapters = []
            current_chapter = []
            for line in content.split('\n'):
                if line.strip():
                    current_chapter.append(line)
                elif current_chapter:
                    chapters.append('\n'.join(current_chapter))
                    current_chapter = []
                    if len(chapters) >= max_chapters:
                        break
            
            if current_chapter and len(chapters) < max_chapters:
                chapters.append('\n'.join(current_chapter))
            
            return chapters[:max_chapters]
        except Exception as e:
            pytest.skip(f"Failed to load test novel: {e}")
            return []

    @pytest.mark.performance
    async def test_single_chapter_processing_time(self, outline_service, text_splitter):
        """测试单章节处理时间"""
        # 加载测试章节
        chapters = await self._load_test_novel("青山(1-500章).txt", max_chapters=1)
        if not chapters:
            pytest.skip("No test chapters available")
        
        chapter_content = chapters[0][:2000]  # 取前2000字
        
        # 测试章纲提取时间
        start_time = time.time()
        chapter_outline = await outline_service.generate_chapter_outline(chapter_content, chapter_index=1)
        end_time = time.time()
        processing_time = end_time - start_time
        
        print(f"Single chapter outline generation time: {processing_time:.2f} seconds")
        assert processing_time < 30, f"Processing time too long: {processing_time:.2f} seconds"

    @pytest.mark.performance
    async def test_batch_chapter_processing(self, outline_service, text_splitter):
        """测试批量章节处理性能"""
        # 加载测试章节
        chapters = await self._load_test_novel("青山(1-500章).txt", max_chapters=5)
        if not chapters:
            pytest.skip("No test chapters available")
        
        # 准备章节内容（每章取前1000字）
        chapter_contents = [chapter[:1000] for chapter in chapters]
        
        # 测试批量处理时间
        start_time = time.time()
        chapter_outlines = await outline_service.generate_chapter_outlines(chapter_contents)
        end_time = time.time()
        total_time = end_time - start_time
        avg_time_per_chapter = total_time / len(chapter_contents)
        
        print(f"Batch chapter outline generation time: {total_time:.2f} seconds")
        print(f"Average time per chapter: {avg_time_per_chapter:.2f} seconds")
        assert total_time < 120, f"Total processing time too long: {total_time:.2f} seconds"
        assert avg_time_per_chapter < 30, f"Average processing time per chapter too long: {avg_time_per_chapter:.2f} seconds"

    @pytest.mark.performance
    async def test_full_pipeline_performance(self, outline_service, text_splitter):
        """测试完整流水线性能"""
        # 加载测试章节
        chapters = await self._load_test_novel("青山(1-500章).txt", max_chapters=3)
        if not chapters:
            pytest.skip("No test chapters available")
        
        # 准备章节内容（每章取前1000字）
        chapter_contents = [chapter[:1000] for chapter in chapters]
        
        # 测试完整流水线时间
        start_time = time.time()
        
        # 1. 生成章纲
        chapter_outlines = await outline_service.generate_chapter_outlines(chapter_contents)
        
        # 2. 生成粗纲
        coarse_outlines = await outline_service.generate_coarse_outline(chapter_outlines)
        
        # 3. 生成大纲
        main_outline = await outline_service.generate_main_outline(coarse_outlines)
        
        # 4. 生成世界纲
        world_outline = await outline_service.generate_world_outline(main_outline, chapter_outlines)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        print(f"Full pipeline processing time: {total_time:.2f} seconds")
        assert total_time < 180, f"Full pipeline processing time too long: {total_time:.2f} seconds"

    @pytest.mark.performance
    async def test_concurrency_stability(self, outline_service, text_splitter):
        """测试并发稳定性"""
        # 加载测试章节
        chapters = await self._load_test_novel("青山(1-500章).txt", max_chapters=8)
        if not chapters:
            pytest.skip("No test chapters available")
        
        # 准备章节内容（每章取前800字）
        chapter_contents = [chapter[:800] for chapter in chapters]
        
        # 测试并发处理
        start_time = time.time()
        
        # 使用LLM服务的batch_invoke方法进行并发测试
        llm_service = outline_service.llm_service
        inputs = [
            {
                "system_prompt": "你是一个专业的小说分析师，请为以下章节生成章纲。",
                "user_input": content
            }
            for content in chapter_contents
        ]
        
        results = await llm_service.batch_invoke(inputs, max_concurrency=5)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # 统计成功和失败的数量
        success_count = sum(1 for r in results if not isinstance(r, Exception))
        failure_count = len(results) - success_count
        
        print(f"Concurrency test results: {success_count} success, {failure_count} failure")
        print(f"Total concurrency test time: {total_time:.2f} seconds")
        
        # 失败率应低于20%
        failure_rate = failure_count / len(results)
        assert failure_rate < 0.2, f"Failure rate too high: {failure_rate:.2f}"
        assert total_time < 150, f"Concurrency test time too long: {total_time:.2f} seconds"


if __name__ == "__main__":
    import asyncio
    asyncio.run(TestPerformance().test_single_chapter_processing_time())
