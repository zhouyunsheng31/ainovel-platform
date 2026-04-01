"""
完整工作流测试 - 生成四层纲并保存到数据库
P5-3 性能与并发测试补充
"""
import asyncio
import time
import re
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.config import settings
from app.models.database import init_db, get_session
from app.models.models import Book
from app.services.llm_service import LLMService
from app.services.outline_service import OutlineService
from app.services.text_splitter import TextSplitter
from app.workflows.outline_graph import OutlineGraphWorkflow
from sqlalchemy.ext.asyncio import AsyncSession


def parse_novel_chapters(file_path: str, max_chapters: int = 20) -> list:
    """解析小说文件，提取章节"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    chapter_pattern = r'第(\d+)章\s+([^\n]+)'
    matches = list(re.finditer(chapter_pattern, content))
    
    chapters = []
    for i, match in enumerate(matches[:max_chapters]):
        chapter_num = int(match.group(1))
        chapter_title = match.group(2).strip()
        start_pos = match.end()
        
        if i + 1 < len(matches):
            end_pos = matches[i + 1].start()
        else:
            end_pos = len(content)
        
        chapter_content = content[start_pos:end_pos].strip()
        if len(chapter_content) > 3000:
            chapter_content = chapter_content[:3000]
        
        chapters.append({
            "index": chapter_num,
            "text": chapter_content,
            "title": chapter_title
        })
    
    return chapters


async def test_full_workflow_with_chapter_count():
    """测试完整工作流，生成4层纲并保存到数据库"""
    print("=" * 80)
    print("完整四层纲工作流测试")
    print("=" * 80)
    
    # 1. 初始化数据库
    print("\n[1/6] 初始化数据库...")
    await init_db()
    
    # 2. 加载小说
    novel_path = "/workspace/novel/青山(1-500章).txt"
    print(f"\n[2/6] 加载小说: {novel_path}")
    
    chapters = parse_novel_chapters(novel_path, max_chapters=20)  # 先用20章测试
    print(f"      解析了 {len(chapters)} 章")
    print(f"      第1章: {chapters[0]['title']} ({len(chapters[0]['text'])}字)")
    
    # 3. 初始化服务
    print("\n[3/6] 初始化服务...")
    llm_service = LLMService()
    outline_service = OutlineService(llm_service=llm_service)
    workflow = OutlineGraphWorkflow(outline_service=outline_service)
    
    # 4. 运行工作流
    print(f"\n[4/6] 运行四层纲工作流 ({len(chapters)}章)...")
    
    progress_updates = []
    def progress_callback(stage, current, total):
        progress_updates.append((stage, current, total))
        print(f"      进度: {stage} - {current}/{total}")
    
    start_time = time.time()
    result = await workflow.run(chapters, progress_callback=progress_callback)
    total_time = time.time() - start_time
    
    # 5. 输出结果
    print("\n[5/6] 工作流结果:")
    print(f"      总耗时: {total_time:.2f}秒 ({total_time/60:.2f}分钟)")
    print(f"      章纲数: {len(result['chapter_outlines'])}")
    print(f"      粗纲数: {len(result['coarse_outlines'])}")
    print(f"      大纲数: {len(result['main_outlines'])}")
    print(f"      世界纲: {'成功' if result['world_outline']['status'] == 'COMPLETED' else '失败'}")
    print(f"      错误数: {len(result.get('errors', []))}")
    
    # 6. 统计各层纲成功率
    print("\n[6/6] 各层纲成功率:")
    
    chapter_success = sum(1 for o in result['chapter_outlines'] if o['status'] == 'COMPLETED')
    print(f"      章纲: {chapter_success}/{len(result['chapter_outlines'])} 成功")
    
    coarse_success = sum(1 for o in result['coarse_outlines'] if o['status'] == 'COMPLETED')
    print(f"      粗纲: {coarse_success}/{len(result['coarse_outlines'])} 成功")
    
    main_success = sum(1 for o in result['main_outlines'] if o['status'] == 'COMPLETED')
    print(f"      大纲: {main_success}/{len(result['main_outlines'])} 成功")
    
    print(f"      世界纲: {1 if result['world_outline']['status'] == 'COMPLETED' else 0}/1 成功")
    
    # 总结
    print("\n" + "=" * 80)
    print("完整工作流测试完成")
    print("=" * 80)
    print(f"小说: 《青山》({len(chapters)}章)")
    print(f"总耗时: {total_time:.2f}秒")
    print(f"成功率: 章纲{chapter_success}/{len(chapters)}, 粗纲{coarse_success}/{len(result['coarse_outlines'])}, 大纲{main_success}/{len(result['main_outlines'])}")
    print("=" * 80)
    
    return result


if __name__ == "__main__":
    asyncio.run(test_full_workflow_with_chapter_count())
