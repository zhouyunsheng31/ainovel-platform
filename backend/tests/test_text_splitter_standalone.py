"""
AI小说拆书系统 - 文本分割器单元测试
完全独立运行，不依赖langchain等重型库
"""
import re
from dataclasses import dataclass

@dataclass
class ChapterSegment:
    index: int
    text: str
    word_count: int
    start_offset: int
    end_offset: int


class TextSplitter:
    TITLE_PATTERNS = [
        r'^第[一二三四五六七八九十百千万零]*[章回节部卷]\s*.{0,20}$',
        r'^Chapter\s*\d+.*$',
        r'^[一二三四五六七八九十]+[、.．]\s*.{0,30}$',
        r'^\d+[、.．]\s*.{0,30}$',
        r'^第[0-9]+[章回节].*$',
        r'^[（\(][一二三四五六七八九十\d]+[）\)].*$',
    ]
    
    def __init__(self, chapter_size=2000, keep_paragraph_complete=True):
        self.chapter_size = chapter_size
        self.keep_paragraph_complete = keep_paragraph_complete
    
    def remove_titles(self, text):
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            stripped = line.strip()
            is_title = False
            for pattern in self.TITLE_PATTERNS:
                if re.match(pattern, stripped):
                    is_title = True
                    break
            if not is_title:
                cleaned_lines.append(line)
        return '\n'.join(cleaned_lines)
    
    def split_into_chapters(self, text):
        cleaned_text = self.remove_titles(text)
        paragraphs = self._split_paragraphs(cleaned_text)
        chapters = []
        current_chapter = []
        current_word_count = 0
        current_start_offset = 0
        chapter_index = 0
        
        for i, para in enumerate(paragraphs):
            para_word_count = len(para)
            if current_word_count == 0:
                current_chapter.append(para)
                current_word_count += para_word_count
                continue
            if current_word_count + para_word_count <= self.chapter_size * 1.2:
                current_chapter.append(para)
                current_word_count += para_word_count
            else:
                chapter_text = '\n\n'.join(current_chapter)
                chapters.append(ChapterSegment(
                    index=chapter_index,
                    text=chapter_text,
                    word_count=len(chapter_text),
                    start_offset=current_start_offset,
                    end_offset=current_start_offset + len(chapter_text)
                ))
                current_start_offset += len(chapter_text)
                current_chapter = [para]
                current_word_count = para_word_count
                chapter_index += 1
        
        if current_chapter:
            chapter_text = '\n\n'.join(current_chapter)
            if len(chapter_text) < self.chapter_size * 0.3 and chapters:
                last_chapter = chapters[-1]
                merged_text = last_chapter.text + '\n\n' + chapter_text
                chapters[-1] = ChapterSegment(
                    index=last_chapter.index,
                    text=merged_text,
                    word_count=len(merged_text),
                    start_offset=last_chapter.start_offset,
                    end_offset=current_start_offset + len(chapter_text)
                )
            else:
                chapters.append(ChapterSegment(
                    index=chapter_index,
                    text=chapter_text,
                    word_count=len(chapter_text),
                    start_offset=current_start_offset,
                    end_offset=current_start_offset + len(chapter_text)
                ))
        return chapters
    
    def _split_paragraphs(self, text):
        paragraphs = re.split(r'\n\s*\n', text)
        cleaned = []
        for para in paragraphs:
            para = para.strip()
            if para:
                para = re.sub(r'\n+', ' ', para)
                cleaned.append(para)
        return cleaned
    
    def get_split_stats(self, chapters):
        if not chapters:
            return {"total_chapters": 0, "avg_word_count": 0, "min_word_count": 0, "max_word_count": 0}
        word_counts = [c.word_count for c in chapters]
        return {
            "total_chapters": len(chapters),
            "avg_word_count": sum(word_counts) // len(word_counts),
            "min_word_count": min(word_counts),
            "max_word_count": max(word_counts)
        }


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
