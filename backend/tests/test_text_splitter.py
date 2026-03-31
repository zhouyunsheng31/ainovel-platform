"""
AI小说拆书系统 - 文本分割器单元测试
独立运行，不依赖langchain等重型库
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.services.text_splitter import TextSplitter, ChapterSegment


def test_remove_titles():
    """测试标题删除功能"""
    splitter = TextSplitter()
    
    text = """第一章 开始

这是正文内容。

第二章 继续

更多内容。"""
    
    result = splitter.remove_titles(text)
    
    assert "第一章" not in result
    assert "第二章" not in result
    assert "这是正文内容" in result
    assert "更多内容" in result
    print("test_remove_titles passed")


def test_split_into_chapters():
    """测试章节分割功能"""
    splitter = TextSplitter(chapter_size=100)
    
    paragraphs = []
    for i in range(20):
        paragraphs.append(f"这是第{i+1}段内容，包含一些文字来测试分割功能。" * 3)
    
    text = "\n\n".join(paragraphs)
    chapters = splitter.split_into_chapters(text)
    
    assert len(chapters) > 0
    for ch in chapters:
        assert isinstance(ch, ChapterSegment)
        assert ch.text
        assert ch.word_count > 0
    print("test_split_into_chapters passed")


def test_paragraph_integrity():
    """测试段落完整性"""
    splitter = TextSplitter(chapter_size=50)
    
    text = "这是第一段内容。\n\n这是第二段内容。\n\n这是第三段内容。"
    chapters = splitter.split_into_chapters(text)
    
    for ch in chapters:
        assert "内容。" in ch.text or "内容" in ch.text
        assert not ch.text.endswith("这是")  
        assert not ch.text.startswith("段内容")
    print("test_paragraph_integrity passed")


def test_get_split_stats():
    """测试分割统计功能"""
    splitter = TextSplitter()
    
    chapters = [
        ChapterSegment(index=0, text="a" * 100, word_count=100, start_offset=0, end_offset=100),
        ChapterSegment(index=1, text="b" * 200, word_count=200, start_offset=100, end_offset=300),
        ChapterSegment(index=2, text="c" * 150, word_count=150, start_offset=300, end_offset=450),
    ]
    
    stats = splitter.get_split_stats(chapters)
    
    assert stats["total_chapters"] == 3
    assert stats["avg_word_count"] == 150
    assert stats["min_word_count"] == 100
    assert stats["max_word_count"] == 200
    print("test_get_split_stats passed")


if __name__ == "__main__":
    test_remove_titles()
    test_split_into_chapters()
    test_paragraph_integrity()
    test_get_split_stats()
    print("\nAll tests passed!")
