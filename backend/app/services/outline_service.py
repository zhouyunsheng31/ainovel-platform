"""
AI小说拆书系统 - 纲生成服务
协调LLM调用生成四层纲结构
"""
from typing import List, Dict, Any

from app.services.llm_service import LLMService
from app.prompts.outlines import (
    CHAPTER_OUTLINE_SYSTEM,
    CHAPTER_OUTLINE_USER_TEMPLATE,
    COARSE_OUTLINE_SYSTEM,
    COARSE_OUTLINE_USER_TEMPLATE,
    MAIN_OUTLINE_SYSTEM,
    MAIN_OUTLINE_USER_TEMPLATE,
    WORLD_OUTLINE_SYSTEM,
    WORLD_OUTLINE_USER_TEMPLATE
)


class OutlineService:
    """纲生成服务 - 四层纲提取"""
    
    def __init__(self, llm_service: LLMService = None):
        self.llm = llm_service or LLMService()
    
    async def generate_chapter_outlines(
        self,
        chapters: List[Dict[str, Any]],
        progress_callback=None
    ) -> List[Dict[str, Any]]:
        """
        并行生成所有章纲
        
        Args:
            chapters: 章节列表 [{"index": 0, "text": "..."}, ...]
            progress_callback: 进度回调函数
        
        Returns:
            章纲结果列表
        """
        inputs = [
            {
                "system_prompt": CHAPTER_OUTLINE_SYSTEM,
                "user_input": CHAPTER_OUTLINE_USER_TEMPLATE.format(
                    chapter_content=ch["text"]
                )
            }
            for ch in chapters
        ]
        
        # 并行调用
        results = await self.llm.batch_invoke(
            inputs,
            max_concurrency=10  # 最大并发数
        )
        
        # 处理结果
        chapter_outlines = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                chapter_outlines.append({
                    "index": i,
                    "error": str(result),
                    "status": "FAILED"
                })
            else:
                chapter_outlines.append({
                    "index": i,
                    "content": result,
                    "summary": result.get("summary", ""),
                    "status": "COMPLETED"
                })
            
            if progress_callback:
                await progress_callback(i + 1, len(chapters))
        
        return chapter_outlines
    
    async def generate_coarse_outlines(
        self,
        chapter_outlines: List[Dict[str, Any]],
        group_size: int = 10,
        progress_callback=None
    ) -> List[Dict[str, Any]]:
        """
        生成粗纲（每10份章纲生成1份粗纲）
        
        Args:
            chapter_outlines: 章纲列表
            group_size: 分组大小，默认10
            progress_callback: 进度回调
        
        Returns:
            粗纲结果列表
        """
        # 提取章纲概括
        summaries = [
            co.get("summary", "") if isinstance(co.get("content"), dict) 
            else co.get("content", {}).get("summary", "")
            for co in chapter_outlines
        ]
        
        # 分组
        groups = []
        for i in range(0, len(summaries), group_size):
            groups.append(summaries[i:i + group_size])
        
        # 为每组生成粗纲
        inputs = []
        for i, group in enumerate(groups):
            group_text = "\n\n".join([
                f"【章纲{j+1}】{s}" 
                for j, s in enumerate(group)
            ])
            inputs.append({
                "system_prompt": COARSE_OUTLINE_SYSTEM,
                "user_input": COARSE_OUTLINE_USER_TEMPLATE.format(summaries=group_text)
            })
        
        results = await self.llm.batch_invoke(inputs, max_concurrency=5)
        
        coarse_outlines = []
        for i, result in enumerate(results):
            start_idx = i * group_size
            end_idx = min(start_idx + group_size, len(chapter_outlines))
            
            if isinstance(result, Exception):
                coarse_outlines.append({
                    "index": i,
                    "chapter_range": [start_idx, end_idx - 1],
                    "source_indices": list(range(start_idx, end_idx)),
                    "error": str(result),
                    "status": "FAILED"
                })
            else:
                coarse_outlines.append({
                    "index": i,
                    "chapter_range": [start_idx, end_idx - 1],
                    "source_indices": list(range(start_idx, end_idx)),
                    "content": result,
                    "summary": result.get("summary", ""),
                    "status": "COMPLETED"
                })
            
            if progress_callback:
                await progress_callback(i + 1, len(groups))
        
        return coarse_outlines
    
    async def generate_main_outlines(
        self,
        coarse_outlines: List[Dict[str, Any]],
        group_size: int = 10,
        progress_callback=None
    ) -> List[Dict[str, Any]]:
        """
        生成大纲（每10份粗纲生成1份大纲）
        """
        # 提取粗纲概括
        summaries = [
            co.get("summary", "") if isinstance(co.get("content"), dict)
            else co.get("content", {}).get("summary", "")
            for co in coarse_outlines
        ]
        
        # 分组
        groups = []
        for i in range(0, len(summaries), group_size):
            groups.append(summaries[i:i + group_size])
        
        inputs = []
        for i, group in enumerate(groups):
            group_text = "\n\n".join([
                f"【粗纲{j+1}】{s}"
                for j, s in enumerate(group)
            ])
            inputs.append({
                "system_prompt": MAIN_OUTLINE_SYSTEM,
                "user_input": MAIN_OUTLINE_USER_TEMPLATE.format(summaries=group_text)
            })
        
        results = await self.llm.batch_invoke(inputs, max_concurrency=5)
        
        main_outlines = []
        for i, result in enumerate(results):
            start_idx = i * group_size
            end_idx = min(start_idx + group_size, len(coarse_outlines))
            
            if isinstance(result, Exception):
                main_outlines.append({
                    "index": i,
                    "source_indices": list(range(start_idx, end_idx)),
                    "error": str(result),
                    "status": "FAILED"
                })
            else:
                main_outlines.append({
                    "index": i,
                    "source_indices": list(range(start_idx, end_idx)),
                    "content": result,
                    "summary": result.get("summary", ""),
                    "status": "COMPLETED"
                })
            
            if progress_callback:
                await progress_callback(i + 1, len(groups))
        
        return main_outlines
    
    async def generate_world_outline(
        self,
        main_outlines: List[Dict[str, Any]],
        progress_callback=None
    ) -> Dict[str, Any]:
        """
        生成世界纲（所有大纲生成1份世界纲）
        """
        summaries = [
            mo.get("summary", "") if isinstance(mo.get("content"), dict)
            else mo.get("content", {}).get("summary", "")
            for mo in main_outlines
            if mo.get("status") == "COMPLETED"
        ]
        
        summaries_text = "\n\n".join([
            f"【大纲{i+1}】{s}"
            for i, s in enumerate(summaries)
        ])
        
        try:
            result = await self.llm.invoke_json(
                WORLD_OUTLINE_SYSTEM,
                WORLD_OUTLINE_USER_TEMPLATE.format(summaries=summaries_text)
            )
            
            if progress_callback:
                await progress_callback(1, 1)
            
            return {
                "content": result,
                "summary": result.get("summary", ""),
                "source_indices": list(range(len(main_outlines))),
                "status": "COMPLETED"
            }
        except Exception as e:
            return {
                "content": {},
                "error": str(e),
                "status": "FAILED"
            }

