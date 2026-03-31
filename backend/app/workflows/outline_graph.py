"""
AI小说拆书系统 - LangGraph 工作流骨架
最小可运行：章纲 -> 粗纲 -> 大纲 -> 世界纲
"""
from typing import TypedDict, List, Dict, Any, Optional, Callable, Awaitable, Protocol, runtime_checkable
from langgraph.graph import StateGraph, END


ProgressCallback = Optional[Callable[[str, int, int], Awaitable[None]]]


@runtime_checkable
class OutlineServiceProtocol(Protocol):
    async def generate_chapter_outlines(
        self, chapters: List[Dict[str, Any]], progress_callback: object = None
    ) -> List[Dict[str, Any]]: ...
    async def generate_coarse_outlines(
        self, chapter_outlines: List[Dict[str, Any]], group_size: int = 10, progress_callback: object = None
    ) -> List[Dict[str, Any]]: ...
    async def generate_main_outlines(
        self, coarse_outlines: List[Dict[str, Any]], group_size: int = 10, progress_callback: object = None
    ) -> List[Dict[str, Any]]: ...
    async def generate_world_outline(
        self, main_outlines: List[Dict[str, Any]], progress_callback: object = None
    ) -> Dict[str, Any]: ...


class OutlineGraphState(TypedDict, total=False):
    chapters: List[Dict[str, Any]]
    chapter_outlines: List[Dict[str, Any]]
    coarse_outlines: List[Dict[str, Any]]
    main_outlines: List[Dict[str, Any]]
    world_outline: Dict[str, Any]
    errors: List[Dict[str, Any]]
    progress_callback: ProgressCallback


class OutlineGraphWorkflow:
    """基于 LangGraph 的四层纲工作流。"""

    def __init__(self, outline_service: OutlineServiceProtocol):
        self.outline_service = outline_service
        self.graph = self._build().compile()

    def _build(self) -> StateGraph:
        graph = StateGraph(OutlineGraphState)
        graph.add_node("chapter_outline_step", self._chapter_outline_node)
        graph.add_node("coarse_outline_step", self._coarse_outline_node)
        graph.add_node("main_outline_step", self._main_outline_node)
        graph.add_node("world_outline_step", self._world_outline_node)

        graph.set_entry_point("chapter_outline_step")
        graph.add_edge("chapter_outline_step", "coarse_outline_step")
        graph.add_edge("coarse_outline_step", "main_outline_step")
        graph.add_edge("main_outline_step", "world_outline_step")
        graph.add_edge("world_outline_step", END)

        return graph

    async def _chapter_outline_node(self, state: OutlineGraphState) -> Dict[str, Any]:
        callback = state.get("progress_callback")
        chapters = state.get("chapters", [])
        result = await self.outline_service.generate_chapter_outlines(
            chapters,
            progress_callback=lambda c, t: callback("CHAPTER_OUTLINE", c, t) if callback else None
        )
        errors = [
            {"stage": "CHAPTER_OUTLINE", "index": item["index"], "error": item.get("error", "Unknown error")}
            for item in result if item.get("status") == "FAILED"
        ]
        return {"chapter_outlines": result, "errors": state.get("errors", []) + errors}

    async def _coarse_outline_node(self, state: OutlineGraphState) -> Dict[str, Any]:
        callback = state.get("progress_callback")
        result = await self.outline_service.generate_coarse_outlines(
            state.get("chapter_outlines", []),
            progress_callback=lambda c, t: callback("COARSE_OUTLINE", c, t) if callback else None
        )
        errors = [
            {"stage": "COARSE_OUTLINE", "index": item["index"], "error": item.get("error", "Unknown error")}
            for item in result if item.get("status") == "FAILED"
        ]
        return {"coarse_outlines": result, "errors": state.get("errors", []) + errors}

    async def _main_outline_node(self, state: OutlineGraphState) -> Dict[str, Any]:
        callback = state.get("progress_callback")
        result = await self.outline_service.generate_main_outlines(
            state.get("coarse_outlines", []),
            progress_callback=lambda c, t: callback("MAIN_OUTLINE", c, t) if callback else None
        )
        errors = [
            {"stage": "MAIN_OUTLINE", "index": item["index"], "error": item.get("error", "Unknown error")}
            for item in result if item.get("status") == "FAILED"
        ]
        return {"main_outlines": result, "errors": state.get("errors", []) + errors}

    async def _world_outline_node(self, state: OutlineGraphState) -> Dict[str, Any]:
        callback = state.get("progress_callback")
        result = await self.outline_service.generate_world_outline(
            state.get("main_outlines", []),
            progress_callback=lambda c, t: callback("WORLD_OUTLINE", c, t) if callback else None
        )
        errors = []
        if result.get("status") == "FAILED":
            errors.append({"stage": "WORLD_OUTLINE", "error": result.get("error", "Unknown error")})
        return {"world_outline": result, "errors": state.get("errors", []) + errors}

    async def run(
        self,
        chapters: List[Dict[str, Any]],
        progress_callback: ProgressCallback = None
    ) -> Dict[str, Any]:
        initial_state: OutlineGraphState = {
            "chapters": chapters,
            "chapter_outlines": [],
            "coarse_outlines": [],
            "main_outlines": [],
            "world_outline": {},
            "errors": [],
            "progress_callback": progress_callback,
        }
        return await self.graph.ainvoke(initial_state)
