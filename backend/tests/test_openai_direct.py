"""
直接使用OpenAI客户端测试LLM API
P5-3 性能与并发测试
"""
import asyncio
import time
import os
from openai import AsyncOpenAI


async def test_openai_api():
    """直接测试OpenAI API"""
    print("开始测试OpenAI API...")
    
    # 配置客户端
    client = AsyncOpenAI(
        api_key="sk-ivQlyYxtR5Q9Yiqyfzs5BPzWNqtlLd0sRrjp2KtVaG3Dhv6y",
        base_url="https://coding.st0722.top/v1"
    )
    
    # 测试单个调用
    print("\n测试单个API调用...")
    start_time = time.time()
    
    try:
        response = await client.chat.completions.create(
            model="Qwen3.5-Plus",
            messages=[
                {"role": "system", "content": "你是一个专业的小说分析师，请为以下章节生成章纲。"},
                {"role": "user", "content": "第一章 觉醒\n清晨的阳光透过窗帘缝隙洒进房间，林阳从梦中醒来。他揉了揉眼睛，发现自己躺在一个陌生的房间里。"}
            ],
            temperature=0.7,
            max_tokens=4096
        )
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        print(f"API调用时间: {processing_time:.2f}秒")
        print(f"响应类型: {type(response)}")
        print(f"响应: {response}")
        
        if hasattr(response, 'choices') and len(response.choices) > 0:
            content = response.choices[0].message.content
            print(f"生成的章纲: {content[:100]}...")
        
        print("单个API调用测试成功！")
        
    except Exception as e:
        end_time = time.time()
        processing_time = end_time - start_time
        print(f"API调用失败: {e}")
        print(f"耗时: {processing_time:.2f}秒")
    
    # 测试批量调用
    print("\n测试批量API调用...")
    start_time = time.time()
    
    async def call_api(i):
        try:
            response = await client.chat.completions.create(
                model="Qwen3.5-Plus",
                messages=[
                    {"role": "system", "content": "你是一个专业的小说分析师，请为以下章节生成章纲。"},
                    {"role": "user", "content": f"第{i}章 测试章节\n这是第{i}章的内容，用于测试LLM性能。"}
                ],
                temperature=0.7,
                max_tokens=1024
            )
            return response
        except Exception as e:
            return e
    
    tasks = [call_api(i) for i in range(1, 4)]
    results = await asyncio.gather(*tasks)
    
    end_time = time.time()
    total_time = end_time - start_time
    
    success_count = sum(1 for r in results if not isinstance(r, Exception))
    failure_count = len(results) - success_count
    
    print(f"批量调用时间: {total_time:.2f}秒")
    print(f"成功: {success_count}, 失败: {failure_count}")
    
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"调用 {i+1} 失败: {result}")
        else:
            print(f"调用 {i+1} 成功")
    
    print("批量API调用测试完成！")


async def main():
    """运行所有测试"""
    await test_openai_api()
    print("\n所有测试完成！")


if __name__ == "__main__":
    asyncio.run(main())
