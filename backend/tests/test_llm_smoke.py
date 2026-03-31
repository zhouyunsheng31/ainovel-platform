import importlib.util
import os
import sys

import pytest

_backend = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, _backend)


def _load_module_from_file(name, filepath):
    spec = importlib.util.spec_from_file_location(name, filepath)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_llm_mod = _load_module_from_file(
    "app.services.llm_service",
    os.path.join(_backend, "app", "services", "llm_service.py"),
)
_outline_mod = _load_module_from_file(
    "app.services.outline_service",
    os.path.join(_backend, "app", "services", "outline_service.py"),
)
_workflow_mod = _load_module_from_file(
    "app.workflows.outline_graph",
    os.path.join(_backend, "app", "workflows", "outline_graph.py"),
)
_prompts_mod = _load_module_from_file(
    "app.prompts.outlines",
    os.path.join(_backend, "app", "prompts", "outlines.py"),
)
LLMService = _llm_mod.LLMService
OutlineService = _outline_mod.OutlineService
OutlineGraphWorkflow = _workflow_mod.OutlineGraphWorkflow
CHAPTER_OUTLINE_SYSTEM = _prompts_mod.CHAPTER_OUTLINE_SYSTEM
CHAPTER_OUTLINE_USER_TEMPLATE = _prompts_mod.CHAPTER_OUTLINE_USER_TEMPLATE

SHORT_TEXT = (
    "长安城的清晨总是被钟鼓楼的报晓声唤醒。天刚蒙蒙亮，东市的商户们便已支起了摊位，"
    "叫卖声此起彼伏。沈惊鸿站在城墙上，望着脚下这座繁华的帝都，眼中却只有无尽的疲惫。"
    "三年前的那个夜晚，改变了她的一生。她从将门之女沦为逃犯，从人人敬仰的沈将军之女"
    "变成了江湖上令人闻风丧胆的暗影杀手。"
)

SAMPLE_CHAPTERS = [
    {"index": 0, "text": SHORT_TEXT},
    {"index": 1, "text": (
        "江南的梅雨季节总是让人心生倦意。柳如是撑着油纸伞走在青石板路上，"
        "雨水顺着伞沿滴落，在地上溅起细小的水花。她刚从师父的药庐出来，"
        "怀中揣着那本泛黄的医书。师父说这本书记载着失传已久的回春术，"
        "能起死回生，但代价是施术者折损十年阳寿。"
    )},
    {"index": 2, "text": (
        "大漠孤烟直，长河落日圆。萧远站在鸣沙山顶，目送最后一缕夕阳沉入地平线。"
        "身后是绵延千里的商队，驼铃声在风中叮当作响。他是这支西域商队的护卫首领，"
        "身手不凡，却有一个不为人知的秘密——他是前朝遗孤，身上流着亡国的血脉。"
    )},
]


@pytest.fixture(scope="module")
def llm_service():
    return LLMService()


@pytest.fixture(scope="module")
def outline_service(llm_service):
    return OutlineService(llm_service=llm_service)


@pytest.mark.llm
@pytest.mark.asyncio
class TestLLMInvokeJson:
    async def test_llm_invoke_json_returns_valid_json(self, llm_service):
        user_input = CHAPTER_OUTLINE_USER_TEMPLATE.format(
            chapter_content=SHORT_TEXT
        )
        result = await llm_service.invoke_json(
            CHAPTER_OUTLINE_SYSTEM, user_input
        )
        assert isinstance(result, dict), f"invoke_json 应返回 dict，实际为 {type(result)}"
        assert len(result) > 0, "返回的 dict 不应为空"


@pytest.mark.llm
@pytest.mark.asyncio
class TestChapterOutlineRealGeneration:
    async def test_chapter_outline_real_generation(self, outline_service):
        results = await outline_service.generate_chapter_outlines(
            SAMPLE_CHAPTERS
        )
        assert isinstance(results, list), "应返回 list"
        assert len(results) == 3, f"应返回 3 项，实际 {len(results)}"
        for item in results:
            assert item.get("status") == "COMPLETED", (
                f"章纲 {item.get('index')} 未成功: {item.get('error')}"
            )
            assert "index" in item
            assert "content" in item


@pytest.mark.llm
@pytest.mark.asyncio
class TestFullPipelineMicroSmoke:
    async def test_full_pipeline_micro_smoke(self, outline_service):
        async def _noop(stage, current, total):
            pass

        workflow = OutlineGraphWorkflow(outline_service=outline_service)
        result = await workflow.run(SAMPLE_CHAPTERS, progress_callback=_noop)

        assert "chapter_outlines" in result
        assert "coarse_outlines" in result
        assert "main_outlines" in result
        assert "world_outline" in result

        chapter_outlines = result["chapter_outlines"]
        assert len(chapter_outlines) == 3
        for co in chapter_outlines:
            assert co.get("status") == "COMPLETED", (
                f"章纲 {co.get('index')} 失败: {co.get('error')}"
            )

        coarse_outlines = result["coarse_outlines"]
        assert len(coarse_outlines) >= 1
        for co in coarse_outlines:
            assert co.get("status") == "COMPLETED", (
                f"粗纲 {co.get('index')} 失败: {co.get('error')}"
            )

        main_outlines = result["main_outlines"]
        assert len(main_outlines) >= 1
        for mo in main_outlines:
            assert mo.get("status") == "COMPLETED", (
                f"大纲 {mo.get('index')} 失败: {mo.get('error')}"
            )

        world_outline = result["world_outline"]
        assert world_outline.get("status") == "COMPLETED", (
            f"世界纲失败: {world_outline.get('error')}"
        )
        assert isinstance(world_outline.get("content"), dict)

        assert result.get("errors") == [] or len(result.get("errors", [])) == 0, (
            f"不应有错误，实际: {result['errors']}"
        )
