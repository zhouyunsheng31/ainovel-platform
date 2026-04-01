"""
AI小说拆书系统 - 性能与并发测试（简化版）
P5-3 性能与并发测试
"""
import asyncio
import time
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 直接从文件导入，避免循环导入
from app.services.llm_service import LLMService


async def test_single_llm_call():
    """测试单个LLM调用性能"""
    print("测试单个LLM调用性能...")
    llm_service = LLMService()
    
    system_prompt = "你是一个专业的小说分析师，请为以下章节生成章纲。"
    user_input = """第一章 觉醒
    清晨的阳光透过窗帘缝隙洒进房间，林阳从梦中醒来。他揉了揉眼睛，发现自己躺在一个陌生的房间里。
    """
    
    start_time = time.time()
    try:
        response = await llm_service.invoke(system_prompt, user_input)
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
    llm_service = LLMService()
    
    inputs = [
        {
            "system_prompt": "你是一个专业的小说分析师，请为以下章节生成章纲。",
            "user_input": f"第{i}章 测试章节\n    这是第{i}章的内容，用于测试LLM性能。" 
        }
        for i in range(1, 4)
    ]
    
    start_time = time.time()
    try:
        results = await llm_service.batch_invoke(inputs, max_concurrency=3)
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


async def test_json_invoke():
    """测试JSON格式调用性能"""
    print("\n测试JSON格式调用性能...")
    llm_service = LLMService()
    
    system_prompt = "你是一个专业的小说分析师，请为以下章节生成章纲。返回JSON格式，包含title和content字段。"
    user_input = """第一章 觉醒
    清晨的阳光透过窗帘缝隙洒进房间，林阳从梦中醒来。他揉了揉眼睛，发现自己躺在一个陌生的房间里。
    """
    
    start_time = time.time()
    try:
        response = await llm_service.invoke_json(system_prompt, user_input)
        end_time = time.time()
        processing_time = end_time - start_time
        print(f"JSON调用时间: {processing_time:.2f}秒")
        print(f"响应类型: {type(response)}")
        print(f"响应内容: {response}")
        print("测试成功！")
    except Exception as e:
        end_time = time.time()
        processing_time = end_time - start_time
        print(f"测试失败: {e}")
        print(f"耗时: {processing_time:.2f}秒")


async def main():
    """运行所有性能测试"""
    print("开始性能测试...")
    print(f"LLM配置: {LLMService().__dict__}")
    
    await test_single_llm_call()
    await test_batch_llm_calls()
    await test_json_invoke()
    
    print("\n性能测试完成！")


if __name__ == "__main__":
    asyncio.run(main())
