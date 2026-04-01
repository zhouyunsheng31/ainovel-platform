"""
真实小说性能测试 - 100章全链路
P5-3 性能与并发测试
"""
import asyncio
import time
import re
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from openai import AsyncOpenAI


def parse_novel_chapters(file_path: str, max_chapters: int = 100) -> list:
    """解析小说文件，提取章节"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 匹配章节标题：第X章 章节名
    chapter_pattern = r'第(\d+)章\s+([^\n]+)'
    matches = list(re.finditer(chapter_pattern, content))
    
    chapters = []
    for i, match in enumerate(matches[:max_chapters]):
        chapter_num = int(match.group(1))
        chapter_title = match.group(2).strip()
        start_pos = match.end()
        
        # 章节内容到下一章开始或文件结束
        if i + 1 < len(matches):
            end_pos = matches[i + 1].start()
        else:
            end_pos = len(content)
        
        chapter_content = content[start_pos:end_pos].strip()
        
        # 限制每章内容长度（取前3000字）
        if len(chapter_content) > 3000:
            chapter_content = chapter_content[:3000]
        
        chapters.append({
            "index": chapter_num,
            "title": chapter_title,
            "text": chapter_content
        })
    
    return chapters


async def test_100_chapters_full_pipeline():
    """测试100章全链路性能"""
    print("=" * 60)
    print("真实小说性能测试 - 100章全链路")
    print("=" * 60)
    
    # 1. 加载真实小说
    novel_path = "/workspace/novel/青山(1-500章).txt"
    print(f"\n[1/5] 加载小说文件: {novel_path}")
    
    chapters = parse_novel_chapters(novel_path, max_chapters=100)
    print(f"      成功解析 {len(chapters)} 章")
    print(f"      示例: 第{chapters[0]['index']}章《{chapters[0]['title']}》({len(chapters[0]['text'])}字)")
    
    # 2. 初始化LLM客户端
    print("\n[2/5] 初始化LLM客户端")
    client = AsyncOpenAI(
        api_key="sk-ivQlyYxtR5Q9Yiqyfzs5BPzWNqtlLd0sRrjp2KtVaG3Dhv6y",
        base_url="https://coding.st0722.top/v1"
    )
    print("      API: https://coding.st0722.top/v1")
    print("      模型: Qwen3.5-Plus")
    
    # 3. 测试章纲生成（批量并发）
    print(f"\n[3/5] 生成章纲 (100章，并发度10)")
    
    async def generate_chapter_outline(chapter):
        try:
            response = await client.chat.completions.create(
                model="Qwen3.5-Plus",
                messages=[
                    {"role": "system", "content": "你是专业的小说分析师。请为以下章节生成简短章纲，包含：章节名、主要情节、关键人物、情绪变化。用JSON格式返回。"},
                    {"role": "user", "content": f"第{chapter['index']}章《{chapter['title']}》\n\n{chapter['text']}"}
                ],
                temperature=0.7,
                max_tokens=500
            )
            return {
                "index": chapter['index'],
                "title": chapter['title'],
                "status": "COMPLETED",
                "content": response.choices[0].message.content
            }
        except Exception as e:
            return {
                "index": chapter['index'],
                "title": chapter['title'],
                "status": "FAILED",
                "error": str(e)
            }
    
    # 分批处理，每批10章
    batch_size = 10
    all_chapter_outlines = []
    
    start_time = time.time()
    for batch_start in range(0, len(chapters), batch_size):
        batch = chapters[batch_start:batch_start + batch_size]
        batch_num = batch_start // batch_size + 1
        total_batches = (len(chapters) + batch_size - 1) // batch_size
        
        print(f"      处理批次 {batch_num}/{total_batches} (第{batch[0]['index']}-{batch[-1]['index']}章)...")
        
        tasks = [generate_chapter_outline(ch) for ch in batch]
        batch_results = await asyncio.gather(*tasks)
        all_chapter_outlines.extend(batch_results)
        
        success_in_batch = sum(1 for r in batch_results if r['status'] == 'COMPLETED')
        print(f"      批次 {batch_num} 完成: {success_in_batch}/{len(batch)} 成功")
    
    chapter_outline_time = time.time() - start_time
    chapter_success = sum(1 for r in all_chapter_outlines if r['status'] == 'COMPLETED')
    print(f"\n      章纲生成完成: {chapter_success}/100 成功")
    print(f"      总耗时: {chapter_outline_time:.2f}秒")
    print(f"      平均每章: {chapter_outline_time/100:.2f}秒")
    
    # 4. 生成粗纲（每10章合并为一个粗纲）
    print(f"\n[4/5] 生成粗纲 (10个粗纲)")
    
    async def generate_coarse_outline(outline_group, group_index):
        try:
            outline_text = "\n\n".join([
                f"第{o['index']}章《{o['title']}》: {o['content'][:200]}..."
                for o in outline_group if o['status'] == 'COMPLETED'
            ])
            
            response = await client.chat.completions.create(
                model="Qwen3.5-Plus",
                messages=[
                    {"role": "system", "content": "你是专业的小说分析师。请根据以下章节大纲，生成一个粗纲，总结这组章节的主要情节线。用JSON格式返回。"},
                    {"role": "user", "content": outline_text}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            return {
                "index": group_index,
                "status": "COMPLETED",
                "content": response.choices[0].message.content
            }
        except Exception as e:
            return {
                "index": group_index,
                "status": "FAILED",
                "error": str(e)
            }
    
    start_time = time.time()
    coarse_outlines = []
    for i in range(0, len(all_chapter_outlines), 10):
        group = all_chapter_outlines[i:i+10]
        group_index = i // 10 + 1
        print(f"      生成粗纲 {group_index}/10...")
        result = await generate_coarse_outline(group, group_index)
        coarse_outlines.append(result)
    
    coarse_outline_time = time.time() - start_time
    coarse_success = sum(1 for r in coarse_outlines if r['status'] == 'COMPLETED')
    print(f"\n      粗纲生成完成: {coarse_success}/10 成功")
    print(f"      总耗时: {coarse_outline_time:.2f}秒")
    
    # 5. 生成大纲（合并所有粗纲）
    print(f"\n[5/5] 生成大纲和世界纲")
    
    start_time = time.time()
    
    # 大纲
    coarse_text = "\n\n".join([
        f"粗纲{r['index']}: {r['content'][:300]}..."
        for r in coarse_outlines if r['status'] == 'COMPLETED'
    ])
    
    main_outline_response = await client.chat.completions.create(
        model="Qwen3.5-Plus",
        messages=[
            {"role": "system", "content": "你是专业的小说分析师。请根据以下粗纲，生成整本书的大纲，包含主要情节线、人物关系、主题思想。用JSON格式返回。"},
            {"role": "user", "content": coarse_text}
        ],
        temperature=0.7,
        max_tokens=2000
    )
    main_outline = main_outline_response.choices[0].message.content
    
    # 世界纲
    world_outline_response = await client.chat.completions.create(
        model="Qwen3.5-Plus",
        messages=[
            {"role": "system", "content": "你是专业的小说分析师。请根据以下大纲，生成世界纲，包含世界观设定、力量体系、重要势力、核心设定。用JSON格式返回。"},
            {"role": "user", "content": main_outline}
        ],
        temperature=0.7,
        max_tokens=2000
    )
    world_outline = world_outline_response.choices[0].message.content
    
    final_time = time.time() - start_time
    print(f"      大纲和世界纲生成完成")
    print(f"      总耗时: {final_time:.2f}秒")
    
    # 总结
    total_time = chapter_outline_time + coarse_outline_time + final_time
    print("\n" + "=" * 60)
    print("性能测试结果汇总")
    print("=" * 60)
    print(f"小说: 《青山》")
    print(f"章节数: 100章")
    print(f"章纲生成: {chapter_success}/100 成功, 耗时 {chapter_outline_time:.2f}秒")
    print(f"粗纲生成: {coarse_success}/10 成功, 耗时 {coarse_outline_time:.2f}秒")
    print(f"大纲+世界纲: 耗时 {final_time:.2f}秒")
    print(f"总耗时: {total_time:.2f}秒 ({total_time/60:.2f}分钟)")
    print(f"平均每章处理时间: {total_time/100:.2f}秒")
    print("=" * 60)
    
    return {
        "chapter_outlines": all_chapter_outlines,
        "coarse_outlines": coarse_outlines,
        "main_outline": main_outline,
        "world_outline": world_outline,
        "stats": {
            "total_time": total_time,
            "chapter_success_rate": chapter_success / 100,
            "coarse_success_rate": coarse_success / 10
        }
    }


if __name__ == "__main__":
    asyncio.run(test_100_chapters_full_pipeline())
