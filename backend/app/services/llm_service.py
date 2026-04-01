"""
AI小说拆书系统 - LLM服务
基于 LangChain ChatOpenAI + LangSmith tracing
"""
import os
import re
import json
import asyncio
import traceback
from typing import Dict, Any, Optional, List, Callable, Awaitable
from tenacity import retry, stop_after_attempt, wait_exponential

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from app.config import settings
from app.services.error_codes import ErrorCodes
from app.services.logging import logger


class LLMService:
    """LLM调用服务 - 使用LangChain标准模型接口"""

    def __init__(
        self,
        base_url: str = None,
        api_key: str = None,
        model_name: str = None,
        temperature: float = None,
        max_tokens: int = None
    ):
        self.base_url = base_url or settings.api_base_url
        self.api_key = api_key or settings.api_key
        self.model_name = model_name or settings.model_name
        self.temperature = temperature if temperature is not None else settings.temperature
        self.max_tokens = max_tokens or settings.max_tokens
        self.timeout = settings.llm_timeout

        self._configure_langsmith()
        self.client = ChatOpenAI(
            model=self.model_name,
            api_key=self.api_key,
            base_url=self.base_url,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            timeout=self.timeout,
        )

    def _configure_langsmith(self) -> None:
        """按配置启用 LangSmith tracing。"""
        if settings.langsmith_api_key:
            os.environ["LANGCHAIN_TRACING_V2"] = "true"
            os.environ["LANGSMITH_TRACING"] = "true"
            os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
            os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    async def invoke(
        self,
        system_prompt: str,
        user_input: str,
        response_format: Optional[Dict] = None
    ) -> str:
        """
        调用LLM。
        response_format 目前仅用于兼容旧接口，真正的 JSON 约束通过 prompt + invoke_json 完成。
        """
        logger.info("开始调用LLM", extra={
            "model_name": self.model_name,
            "prompt_length": len(system_prompt) + len(user_input),
            "response_format": response_format
        })
        
        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_input),
            ]
            response = await self.client.ainvoke(messages)
            result = response.content if isinstance(response.content, str) else json.dumps(response.content, ensure_ascii=False)
            
            logger.info("LLM调用成功", extra={
                "model_name": self.model_name,
                "response_length": len(result)
            })
            
            return result
        except Exception as e:
            error_code = ErrorCodes.LLM_API_ERROR
            error_message = f"LLM调用失败: {str(e)}"
            logger.error("LLM调用失败", extra={
                "model_name": self.model_name,
                "error_code": error_code,
                "error_message": error_message,
                "stack_trace": traceback.format_exc()
            })
            raise

    async def invoke_json(
        self,
        system_prompt: str,
        user_input: str
    ) -> Dict[str, Any]:
        """调用LLM并解析JSON响应。"""
        logger.info("开始调用LLM并解析JSON", extra={
            "model_name": self.model_name,
            "prompt_length": len(system_prompt) + len(user_input)
        })
        
        enhanced_prompt = f"{system_prompt}\n\n请只返回有效 JSON 对象，不要使用 Markdown 代码块，不要补充解释。"
        response = await self.invoke(enhanced_prompt, user_input)

        def _remove_trailing_commas(text: str) -> str:
            text = re.sub(r',\s*([}\]])', r'\1', text)
            return text

        try:
            cleaned = response.strip()
            if cleaned.startswith("```"):
                cleaned = re.sub(r"^```json\s*|^```\s*|```$", "", cleaned, flags=re.IGNORECASE | re.MULTILINE).strip()
            cleaned = _remove_trailing_commas(cleaned)
            result = json.loads(cleaned)
            
            logger.info("JSON解析成功", extra={
                "model_name": self.model_name,
                "response_length": len(response)
            })
            
            return result
        except json.JSONDecodeError:
            error_code = ErrorCodes.LLM_JSON_PARSE_ERROR
            error_message = f"JSON解析失败: {response[:200]}..."
            logger.error("JSON解析失败", extra={
                "model_name": self.model_name,
                "error_code": error_code,
                "error_message": error_message
            })
            
            # 尝试提取JSON部分
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                try:
                    extracted = _remove_trailing_commas(json_match.group())
                    result = json.loads(extracted)
                    logger.info("尝试提取JSON成功", extra={
                        "model_name": self.model_name
                    })
                    return result
                except json.JSONDecodeError:
                    error_message = f"提取JSON后仍然解析失败: {extracted[:200]}..."
                    logger.error("提取JSON后仍然解析失败", extra={
                        "model_name": self.model_name,
                        "error_code": error_code,
                        "error_message": error_message
                    })
                    raise ValueError(error_message)
            
            raise ValueError(error_message)

    async def batch_invoke(
        self,
        inputs: List[Dict[str, str]],
        max_concurrency: int = 10,
        on_item_complete: Optional[Callable[[int, Any], Awaitable[None]]] = None
    ) -> List[Dict[str, Any]]:
        """
        批量并行调用LLM。
        on_item_complete: 每完成一项时回调 (index, result)
        """
        logger.info("开始批量调用LLM", extra={
            "model_name": self.model_name,
            "batch_size": len(inputs),
            "max_concurrency": max_concurrency
        })
        
        semaphore = asyncio.Semaphore(max_concurrency)
        results: List[Any] = [None] * len(inputs)

        async def invoke_with_semaphore(input_data: Dict, index: int):
            async with semaphore:
                try:
                    logger.info(f"批量调用LLM - 开始处理第{index}项", extra={
                        "model_name": self.model_name,
                        "batch_index": index
                    })
                    result = await self.invoke_json(
                        input_data["system_prompt"],
                        input_data["user_input"]
                    )
                    logger.info(f"批量调用LLM - 第{index}项处理成功", extra={
                        "model_name": self.model_name,
                        "batch_index": index
                    })
                    results[index] = result
                    if on_item_complete:
                        await on_item_complete(index, result)
                    return result
                except Exception as e:
                    error_code = ErrorCodes.LLM_API_ERROR
                    error_message = f"批量调用LLM失败: {str(e)}"
                    logger.error(f"批量调用LLM - 第{index}项处理失败", extra={
                        "model_name": self.model_name,
                        "batch_index": index,
                        "error_code": error_code,
                        "error_message": error_message,
                        "stack_trace": traceback.format_exc()
                    })
                    err_result = {"error": error_message, "error_code": error_code}
                    results[index] = err_result
                    if on_item_complete:
                        await on_item_complete(index, err_result)
                    return err_result

        tasks = [invoke_with_semaphore(inp, i) for i, inp in enumerate(inputs)]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # 统计成功和失败的数量
        success_count = sum(1 for r in results if not isinstance(r, Exception) and "error" not in r)
        error_count = len(results) - success_count
        
        logger.info("批量调用LLM完成", extra={
            "model_name": self.model_name,
            "batch_size": len(inputs),
            "success_count": success_count,
            "error_count": error_count
        })
        
        return results
