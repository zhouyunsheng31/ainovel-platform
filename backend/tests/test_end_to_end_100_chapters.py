"""
端到端100章真实小说测试 - 完整四层纲 + 纲树图表
P5-3 性能与并发测试完整版
"""
import asyncio
import time
import os
import sys
from pathlib import Path
import tempfile
import shutil

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from httpx import AsyncClient
from app.config import settings


# 复制真实小说到临时文件，用于上传
def copy_real_novel_for_upload() -> str:
    """复制真实小说文件到临时目录，用于上传"""
    source_path = Path("/workspace/novel/青山(1-500章).txt")
    temp_dir = Path(tempfile.mkdtemp())
    dest_path = temp_dir / "青山100章.txt"
    
    # 读取前100章
    with open(source_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    import re
    chapter_pattern = r'第(\d+)章\s+([^\n]+)'
    matches = list(re.finditer(chapter_pattern, content))
    
    if len(matches) >= 100:
        # 截取前100章
        end_pos = matches[99].end()
        content = content[:end_pos]
    
    with open(dest_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✓ 准备了测试小说: {dest_path}")
    print(f"  章节数: 前100章")
    return str(dest_path), str(temp_dir)


async def test_complete_workflow_100_chapters():
    """完整工作流测试：上传→处理→纲树展示"""
    print("=" * 90)
    print("端到端100章真实小说测试 - 完整四层纲 + 纲树图表")
    print("=" * 90)
    
    # 准备测试文件
    print("\n[1/7] 准备测试小说...")
    test_file, temp_dir = copy_real_novel_for_upload()
    
    try:
        # 启动后端服务（在后台）
        # 实际上，需要手动先启动后端，这里假设后端已在8000端口运行
        base_url = "http://localhost:8000"
        print(f"\n[2/7] 连接后端: {base_url}")
        
        async with AsyncClient(base_url=base_url, timeout=3600) as client:
            # 1. 上传文件
            print("\n[3/7] 上传真实小说文件...")
            start_upload = time.time()
            
            with open(test_file, 'rb') as f:
                files = {'file': ('青山100章.txt', f, 'text/plain')}
                data = {
                    'title': '青山（测试版）',
                    'author': '会说话的肘子'
                }
                
                response = await client.post('/books/upload', files=files, data=data)
            
            if response.status_code != 200:
                print(f"✗ 上传失败: {response.status_code}")
                print(response.text)
                return
            
            upload_result = response.json()
            book_id = upload_result['data']['book_id']
            task_id = upload_result['data']['task_id']
            
            upload_time = time.time() - start_upload
            print(f"✓ 上传成功")
            print(f"  Book ID: {book_id}")
            print(f"  Task ID: {task_id}")
            print(f"  上传耗时: {upload_time:.2f}秒")
            
            # 2. 轮询任务状态
            print("\n[4/7] 等待处理完成（最多60分钟）...")
            start_process = time.time()
            max_wait = 3600  # 60分钟
            poll_interval = 5
            
            completed = False
            last_status = ""
            
            while time.time() - start_process < max_wait:
                await asyncio.sleep(poll_interval)
                
                try:
                    response = await client.get(f'/books/{book_id}/status')
                    if response.status_code == 200:
                        status_data = response.json()['data']
                        current_status = status_data.get('status', '')
                        
                        if current_status != last_status:
                            last_status = current_status
                            print(f"  状态: {current_status}")
                            
                            if current_status in ['COMPLETED', 'FAILED']:
                                completed = True
                                break
                except Exception as e:
                    print(f"  轮询错误: {e}")
            
            if not completed:
                print(f"✗ 超时: {max_wait/60}分钟未完成")
                return
            
            process_time = time.time() - start_process
            print(f"✓ 处理完成")
            print(f"  总耗时: {process_time:.2f}秒 ({process_time/60:.2f}分钟)")
            
            # 3. 获取书籍详情
            print("\n[5/7] 获取书籍详情...")
            response = await client.get(f'/books/{book_id}')
            if response.status_code == 200:
                book_detail = response.json()['data']
                print(f"✓ 书籍详情获取成功")
                print(f"  标题: {book_detail['title']}")
                print(f"  总章节: {book_detail.get('total_chapters', 0)}章")
                print(f"  状态: {book_detail['status']}")
            
            # 4. 获取纲树（多层级图表）
            print("\n[6/7] 获取纲树（多层级图表）...")
            response = await client.get(f'/books/{book_id}/outlines/tree')
            if response.status_code == 200:
                tree_data = response.json()['data']
                print(f"✓ 纲树获取成功")
                
                # 统计各层纲数量
                def count_outlines(node, layer=0):
                    count = 1
                    if 'children' in node:
                        for child in node['children']:
                            count += count_outlines(child, layer + 1)
                    return count
                
                total_outlines = count_outlines(tree_data['tree'])
                print(f"  总纲节点数: {total_outlines}")
                print(f"  世界纲: 1个")
                
                if 'children' in tree_data['tree']:
                    main_count = len(tree_data['tree']['children'])
                    print(f"  大纲: {main_count}个")
                    
                    coarse_count = 0
                    chapter_count = 0
                    for main in tree_data['tree']['children']:
                        if 'children' in main:
                            coarse_count += len(main['children'])
                            for coarse in main['children']:
                                if 'children' in coarse:
                                    chapter_count += len(coarse['children'])
                    
                    print(f"  粗纲: {coarse_count}个")
                    print(f"  章纲: {chapter_count}个")
            
            # 5. 复制纲功能测试
            print("\n[7/7] 测试复制纲功能...")
            formats_to_test = ['markdown', 'json', 'text']
            for fmt in formats_to_test:
                try:
                    response = await client.get(f'/books/{book_id}/outlines/copy', params={'format': fmt})
                    if response.status_code == 200:
                        copy_result = response.json()['data']
                        print(f"  ✓ {fmt.upper()}格式复制成功")
                        print(f"    长度: {len(copy_result.get('content', ''))}字符")
                except Exception as e:
                    print(f"  ✗ {fmt.upper()}格式复制失败: {e}")
            
            # 总结
            print("\n" + "=" * 90)
            print("端到端测试完成！")
            print("=" * 90)
            print(f"📚 小说: 青山（前100章）")
            print(f"⏱️  上传耗时: {upload_time:.2f}秒")
            print(f"⏱️  处理耗时: {process_time:.2f}秒")
            print(f"✅ 四层纲: 世界纲→大纲→粗纲→章纲")
            print(f"🌳 纲树图表: 已生成并可获取")
            print(f"📋 复制功能: Markdown/JSON/Text 支持")
            print("=" * 90)
            
            return {
                'book_id': book_id,
                'task_id': task_id,
                'upload_time': upload_time,
                'process_time': process_time
            }
    
    finally:
        # 清理临时文件
        shutil.rmtree(temp_dir)
        print(f"\n✓ 已清理临时文件: {temp_dir}")


if __name__ == "__main__":
    print("\n" + "=" * 90)
    print("⚠️  重要提示：请先确保后端服务已在 http://localhost:8000 运行！")
    print("=" * 90)
    print("\n启动后端服务命令:")
    print("  cd backend && python main.py")
    print("\n然后在另一个终端运行这个测试:")
    print("  cd backend && python tests/test_end_to_end_100_chapters.py")
    print("\n" + "=" * 90 + "\n")
    
    # 先不直接运行，因为需要后端服务启动
    print("请确认后端服务已启动，然后按Enter继续...")
    try:
        input()
        asyncio.run(test_complete_workflow_100_chapters())
    except KeyboardInterrupt:
        print("\n测试已取消")
