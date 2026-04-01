"""
AI小说拆书系统 - 纲生成服务
协调LLM调用生成四层纲结构
"""
import traceback
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
from app.services.error_codes import ErrorCodes
from app.services.logging import logger


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
        logger.info("开始生成章纲", extra={
            "chapter_count": len(chapters)
        })
        
        inputs = [
            {
                "system_prompt": CHAPTER_OUTLINE_SYSTEM,
                "user_input": CHAPTER_OUTLINE_USER_TEMPLATE.format(
                    chapter_content=ch["text"]
                )
            }
            for ch in chapters
        ]
        
        try:
            # 并行调用
            results = await self.llm.batch_invoke(
                inputs,
                max_concurrency=10  # 最大并发数
            )
            
            # 处理结果
            chapter_outlines = []
            success_count = 0
            error_count = 0
            
            for i, result in enumerate(results):
                if isinstance(result, Exception) or (isinstance(result, dict) and "error" in result):
                    error_message = str(result) if isinstance(result, Exception) else result.get("error", "未知错误")
                    chapter_outlines.append({
                        "index": i,
                        "error": error_message,
                        "status": "FAILED"
                    })
                    error_count += 1
                    logger.error("章纲生成失败", extra={
                        "chapter_index": i,
                        "error_message": error_message
                    })
                else:
                    chapter_outlines.append({
                        "index": i,
                        "content": result,
                        "summary": result.get("summary", ""),
                        "status": "COMPLETED"
                    })
                    success_count += 1
                
                if progress_callback:
                    await progress_callback(i + 1, len(chapters))
            
            logger.info("章纲生成完成", extra={
                "chapter_count": len(chapters),
                "success_count": success_count,
                "error_count": error_count
            })
            
            return chapter_outlines
        except Exception as e:
            error_code = ErrorCodes.CHAPTER_OUTLINE_ERROR
            error_message = f"章纲生成失败: {str(e)}"
            logger.error("章纲生成过程出错", extra={
                "error_code": error_code,
                "error_message": error_message,
                "stack_trace": traceback.format_exc()
            })
            # 返回失败结果
            return [{
                "index": i,
                "error": error_message,
                "status": "FAILED"
            } for i in range(len(chapters))]
    
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
        logger.info("开始生成粗纲", extra={
            "chapter_outline_count": len(chapter_outlines),
            "group_size": group_size
        })
        
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
        
        logger.info("粗纲分组完成", extra={
            "group_count": len(groups)
        })
        
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
        
        try:
            results = await self.llm.batch_invoke(inputs, max_concurrency=5)
            
            coarse_outlines = []
            success_count = 0
            error_count = 0
            
            for i, result in enumerate(results):
                start_idx = i * group_size
                end_idx = min(start_idx + group_size, len(chapter_outlines))
                
                if isinstance(result, Exception) or (isinstance(result, dict) and "error" in result):
                    error_message = str(result) if isinstance(result, Exception) else result.get("error", "未知错误")
                    coarse_outlines.append({
                        "index": i,
                        "chapter_range": [start_idx, end_idx - 1],
                        "source_indices": list(range(start_idx, end_idx)),
                        "error": error_message,
                        "status": "FAILED"
                    })
                    error_count += 1
                    logger.error("粗纲生成失败", extra={
                        "coarse_index": i,
                        "chapter_range": [start_idx, end_idx - 1],
                        "error_message": error_message
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
                    success_count += 1
                
                if progress_callback:
                    await progress_callback(i + 1, len(groups))
            
            logger.info("粗纲生成完成", extra={
                "group_count": len(groups),
                "success_count": success_count,
                "error_count": error_count
            })
            
            return coarse_outlines
        except Exception as e:
            error_code = ErrorCodes.COARSE_OUTLINE_ERROR
            error_message = f"粗纲生成失败: {str(e)}"
            logger.error("粗纲生成过程出错", extra={
                "error_code": error_code,
                "error_message": error_message,
                "stack_trace": traceback.format_exc()
            })
            # 返回失败结果
            return [{
                "index": i,
                "chapter_range": [i * group_size, min((i + 1) * group_size, len(chapter_outlines)) - 1],
                "source_indices": list(range(i * group_size, min((i + 1) * group_size, len(chapter_outlines)) - 1)),
                "error": error_message,
                "status": "FAILED"
            } for i in range(len(groups))]
    
    async def generate_main_outlines(
        self,
        coarse_outlines: List[Dict[str, Any]],
        group_size: int = 10,
        progress_callback=None
    ) -> List[Dict[str, Any]]:
        """
        生成大纲（每10份粗纲生成1份大纲）
        """
        logger.info("开始生成大纲", extra={
            "coarse_outline_count": len(coarse_outlines),
            "group_size": group_size
        })
        
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
        
        logger.info("大纲分组完成", extra={
            "group_count": len(groups)
        })
        
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
        
        try:
            results = await self.llm.batch_invoke(inputs, max_concurrency=5)
            
            main_outlines = []
            success_count = 0
            error_count = 0
            
            for i, result in enumerate(results):
                start_idx = i * group_size
                end_idx = min(start_idx + group_size, len(coarse_outlines))
                
                if isinstance(result, Exception) or (isinstance(result, dict) and "error" in result):
                    error_message = str(result) if isinstance(result, Exception) else result.get("error", "未知错误")
                    main_outlines.append({
                        "index": i,
                        "source_indices": list(range(start_idx, end_idx)),
                        "error": error_message,
                        "status": "FAILED"
                    })
                    error_count += 1
                    logger.error("大纲生成失败", extra={
                        "main_index": i,
                        "source_indices": list(range(start_idx, end_idx)),
                        "error_message": error_message
                    })
                else:
                    main_outlines.append({
                        "index": i,
                        "source_indices": list(range(start_idx, end_idx)),
                        "content": result,
                        "summary": result.get("summary", ""),
                        "status": "COMPLETED"
                    })
                    success_count += 1
                
                if progress_callback:
                    await progress_callback(i + 1, len(groups))
            
            logger.info("大纲生成完成", extra={
                "group_count": len(groups),
                "success_count": success_count,
                "error_count": error_count
            })
            
            return main_outlines
        except Exception as e:
            error_code = ErrorCodes.MAIN_OUTLINE_ERROR
            error_message = f"大纲生成失败: {str(e)}"
            logger.error("大纲生成过程出错", extra={
                "error_code": error_code,
                "error_message": error_message,
                "stack_trace": traceback.format_exc()
            })
            # 返回失败结果
            return [{
                "index": i,
                "source_indices": list(range(i * group_size, min((i + 1) * group_size, len(coarse_outlines)) - 1)),
                "error": error_message,
                "status": "FAILED"
            } for i in range(len(groups))]
    
    async def generate_world_outline(
        self,
        main_outlines: List[Dict[str, Any]],
        progress_callback=None
    ) -> Dict[str, Any]:
        """
        生成世界纲（所有大纲生成1份世界纲）
        """
        completed_count = sum(1 for mo in main_outlines if mo.get("status") == "COMPLETED")
        logger.info("开始生成世界纲", extra={
            "main_outline_count": len(main_outlines),
            "completed_count": completed_count
        })
        
        summaries = [
            mo.get("summary", "") if isinstance(mo.get("content"), dict)
            else mo.get("content", {}).get("summary", "")
            for mo in main_outlines
            if mo.get("status") == "COMPLETED"
        ]
        
        if not summaries:
            error_code = ErrorCodes.WORLD_OUTLINE_ERROR
            error_message = "没有可用的大纲生成世界纲"
            logger.error("世界纲生成失败", extra={
                "error_code": error_code,
                "error_message": error_message
            })
            return {
                "content": {},
                "error": error_message,
                "status": "FAILED"
            }
        
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
            
            logger.info("世界纲生成成功", extra={
                "summary_count": len(summaries)
            })
            
            return {
                "content": result,
                "summary": result.get("summary", ""),
                "source_indices": list(range(len(main_outlines))),
                "status": "COMPLETED"
            }
        except Exception as e:
            error_code = ErrorCodes.WORLD_OUTLINE_ERROR
            error_message = f"世界纲生成失败: {str(e)}"
            logger.error("世界纲生成过程出错", extra={
                "error_code": error_code,
                "error_message": error_message,
                "stack_trace": traceback.format_exc()
            })
            return {
                "content": {},
                "error": error_message,
                "status": "FAILED"
            }

