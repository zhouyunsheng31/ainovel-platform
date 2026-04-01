"""
直接测试LLM服务性能
P5-3 性能与并发测试
"""
import asyncio
import time
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 直接导入必要的模块，避免循环导入
from pydantic_settings import BaseSettings, SettingsConfigDict
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
import json
import re
from tenacity import retry, stop_after_attempt, wait_exponential


class Settings(BaseSettings):
    """临时配置类"""
    api_base_url: str = "https://coding.st0722.top"
    api_key: str = "sk-ivQlyYxtR5Q9Yiqyfzs5BPzWNqtlLd0sRrjp2KtVaG3Dhv6y"
    model_name: str = "Qwen3.5-Plus"
    temperature: float = 0.7
    max_tokens: int = 4096
    llm_timeout: int = 60


class SimpleLLMService:
    """简化版LLM服务"""
    
    def __init__(self):
        self.settings = Settings()
        self.client = ChatOpenAI(
            model=self.settings.model_name,
            api_key=self.settings.api_key,
            base_url=self.settings.api_base_url,
            temperature=self.settings.temperature,
            max_tokens=self.settings.max_tokens,
            timeout=self.settings.llm_timeout,
        )
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    async def invoke(self, system_prompt: str, user_input: str) -> str:
        """调用LLM"""
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_input),
        ]
        print(f"发送请求到LLM...")
        print(f"系统提示: {system_prompt[:50]}...")
        print(f"用户输入: {user_input[:50]}...")
        try:
            response = await self.client.ainvoke(messages)
            print(f"响应类型: {type(response)}")
            print(f"响应内容: {response}")
            if hasattr(response, 'content'):
                return response.content if isinstance(response.content, str) else json.dumps(response.content, ensure_ascii=False)
            else:
                return str(response)
        except Exception as e:
            print(f"调用错误: {e}")
            raise
    
    async def batch_invoke(self, inputs: list, max_concurrency: int = 3):
        """批量调用LLM"""
        async def invoke_one(input_data):
            return await self.invoke(input_data["system_prompt"], input_data["user_input"])
        
        tasks = [invoke_one(inp) for inp in inputs]
        return await asyncio.gather(*tasks, return_exceptions=True)


async def test_single_llm_call():
    """测试单个LLM调用性能"""
    print("测试单个LLM调用性能...")
    llm = SimpleLLMService()
    
    system_prompt = "你是一个专业的小说分析师，请为以下章节生成章纲。"
    user_input = """第一章 觉醒
    清晨的阳光透过窗帘缝隙洒进房间，林阳从梦中醒来。他揉了揉眼睛，发现自己躺在一个陌生的房间里。
    """
    
    start_time = time.time()
    try:
        response = await llm.invoke(system_prompt, user_input)
        end_time = time.time()
        processing_time = end_time - start_time
        print(f"单个LLM调用时间: {processing_time:.2f}秒")
        print(f"响应长度: {len(response)}字符")
        print("测试成功！")
    except Exception as e:
        end_time = time.time()
        processing_time = end_time - start_time
        print(f"测试失败: {e}")
        print(f"耗时: {processing_time:.2f}秒")


async def test_batch_llm_calls():
    """测试批量LLM调用性能"""
    print("\n测试批量LLM调用性能...")
    llm = SimpleLLMService()
    
    inputs = [
        {
            "system_prompt": "你是一个专业的小说分析师，请为以下章节生成章纲。",
            "user_input": f"第{i}章 测试章节\n    这是第{i}章的内容，用于测试LLM性能。" 
        }
        for i in range(1, 4)
    ]
    
    start_time = time.time()
    try:
        results = await llm.batch_invoke(inputs, max_concurrency=3)
        end_time = time.time()
        total_time = end_time - start_time
        
        success_count = sum(1 for r in results if not isinstance(r, Exception))
        failure_count = len(results) - success_count
        
        print(f"批量调用时间: {total_time:.2f}秒")
        print(f"成功: {success_count}, 失败: {failure_count}")
        print("测试成功！")
    except Exception as e:
        end_time = time.time()
        total_time = end_time - start_time
        print(f"测试失败: {e}")
        print(f"耗时: {total_time:.2f}秒")


async def main():
    """运行所有测试"""
    print("开始LLM性能测试...")
    print(f"LLM配置: 模型={Settings().model_name}, API={Settings().api_base_url}")
    
    await test_single_llm_call()
    await test_batch_llm_calls()
    
    print("\nLLM性能测试完成！")


if __name__ == "__main__":
    asyncio.run(main())
