"""
AI小说拆书系统 - 文本分割服务
按照2000字/章标准分割，保持段落完整
"""
import re
from typing import List
from dataclasses import dataclass

from app.config import settings


@dataclass
class ChapterSegment:
    """章节分割结果"""
    index: int           # 章节序号（0-based）
    text: str             # 章节文本
    word_count: int      # 字数
    start_offset: int    # 在原文中的起始位置
    end_offset: int      # 在原文中的结束位置


class TextSplitter:
    """文本分割服务 - 智能分章"""
    
    # 标题模式（需要删除）
    TITLE_PATTERNS = [
        r'^第[一二三四五六七八九十百千万零]*[章回节部卷]\s*.{0,20}$',  # 中文章节
        r'^Chapter\s*\d+.*$',  # 英文章节
        r'^[一二三四五六七八九十]+[、.．]\s*.{0,30}$',  # 中文章节编号
        r'^\d+[、.．]\s*.{0,30}$',  # 数字编号
        r'^第[0-9]+[章回节].*$',  # 数字章节
        r'^[（\(][一二三四五六七八九十\d]+[）\)].*$',  # 括号编号
    ]
    
    def __init__(self, chapter_size: int = None, keep_paragraph_complete: bool = None):
        self.chapter_size = chapter_size or settings.chapter_size
        self.keep_paragraph_complete = keep_paragraph_complete if keep_paragraph_complete is not None else settings.keep_paragraph_complete
    
    def remove_titles(self, text: str) -> str:
        """
        删除所有标题行
        包括：第X章、Chapter X、数字编号等
        """
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
    
    def split_into_chapters(self, text: str) -> List[ChapterSegment]:
        """
        将文本分割成约2000字的章节
        
        分割策略：
        1. 按2000字初步定位分割点
        2. 向后查找最近的段落边界
        3. 确保不切断句子和段落
        """
        # 先删除标题
        cleaned_text = self.remove_titles(text)
        
        # 按段落分割
        paragraphs = self._split_paragraphs(cleaned_text)
        
        chapters = []
        current_chapter = []
        current_word_count = 0
        current_start_offset = 0
        chapter_index = 0
        
        for i, para in enumerate(paragraphs):
            para_word_count = len(para)
            
            # 如果当前章节为空，直接加入（避免空章节）
            if current_word_count == 0:
                current_chapter.append(para)
                current_word_count += para_word_count
                continue
            
            # 如果加入此段落不超过限制，加入
            if current_word_count + para_word_count <= self.chapter_size * 1.2:  # 允许20%溢出
                current_chapter.append(para)
                current_word_count += para_word_count
            else:
                # 保存当前章节
                chapter_text = '\n\n'.join(current_chapter)
                chapters.append(ChapterSegment(
                    index=chapter_index,
                    text=chapter_text,
                    word_count=len(chapter_text),
                    start_offset=current_start_offset,
                    end_offset=current_start_offset + len(chapter_text)
                ))
                
                # 开始新章节
                current_start_offset += len(chapter_text)
                current_chapter = [para]
                current_word_count = para_word_count
                chapter_index += 1
        
        # 保存最后一个章节
        if current_chapter:
            chapter_text = '\n\n'.join(current_chapter)
            # 如果最后一个章节太短，合并到上一章节
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
    
    def _split_paragraphs(self, text: str) -> List[str]:
        """
        将文本按段落分割
        段落定义：连续的空白行分隔的文本块
        """
        # 使用正则分割段落
        paragraphs = re.split(r'\n\s*\n', text)
        
        # 清理每个段落
        cleaned = []
        for para in paragraphs:
            para = para.strip()
            if para:
                # 将段落内的单个换行符替换为空格（合并同行）
                para = re.sub(r'\n+', ' ', para)
                cleaned.append(para)
        
        return cleaned
    
    def get_split_stats(self, chapters: List[ChapterSegment]) -> dict:
        """获取分割统计信息"""
        if not chapters:
            return {
                "total_chapters": 0,
                "avg_word_count": 0,
                "min_word_count": 0,
                "max_word_count": 0
            }
        
        word_counts = [c.word_count for c in chapters]
        return {
            "total_chapters": len(chapters),
            "avg_word_count": sum(word_counts) // len(word_counts),
            "min_word_count": min(word_counts),
            "max_word_count": max(word_counts)
        }
