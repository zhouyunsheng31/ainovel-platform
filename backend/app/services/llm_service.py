"""
AI小说拆书系统 - LLM服务
基于 LangChain ChatOpenAI + LangSmith tracing
"""
import os
import re
import json
import asyncio
from typing import Dict, Any, Optional, List
from tenacity import retry, stop_after_attempt, wait_exponential

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from app.config import settings


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
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_input),
        ]
        response = await self.client.ainvoke(messages)
        return response.content if isinstance(response.content, str) else json.dumps(response.content, ensure_ascii=False)

    async def invoke_json(
        self,
        system_prompt: str,
        user_input: str
    ) -> Dict[str, Any]:
        """调用LLM并解析JSON响应。"""
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
            return json.loads(cleaned)
        except json.JSONDecodeError:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                extracted = _remove_trailing_commas(json_match.group())
                return json.loads(extracted)
            raise ValueError(f"Failed to parse JSON response: {response}")

    async def batch_invoke(
        self,
        inputs: List[Dict[str, str]],
        max_concurrency: int = 10
    ) -> List[Dict[str, Any]]:
        """批量并行调用LLM。"""
        semaphore = asyncio.Semaphore(max_concurrency)

        async def invoke_with_semaphore(input_data: Dict):
            async with semaphore:
                return await self.invoke_json(
                    input_data["system_prompt"],
                    input_data["user_input"]
                )

        tasks = [invoke_with_semaphore(inp) for inp in inputs]
        return await asyncio.gather(*tasks, return_exceptions=True)
