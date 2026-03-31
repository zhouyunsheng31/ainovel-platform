import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.workflows.outline_graph import OutlineGraphWorkflow


NOVEL_OPENINGS = [
    "长安城的清晨总是被钟鼓楼的报晓声唤醒。天刚蒙蒙亮，东市的商户们便已支起了摊位，叫卖声此起彼伏。沈惊鸿站在城墙上，望着脚下这座繁华的帝都，眼中却只有无尽的疲惫。三年前的那个夜晚，改变了她的一生。她从将门之女沦为逃犯，从人人敬仰的沈将军之女变成了江湖上令人闻风丧胆的暗影杀手。",
    "江南的梅雨季节总是让人心生倦意。柳如是撑着油纸伞走在青石板路上，雨水顺着伞沿滴落，在地上溅起细小的水花。她刚从师父的药庐出来，怀中揣着那本泛黄的医书。师父说这本书记载着失传已久的回春术，能起死回生，但代价是施术者折损十年阳寿。",
    "大漠孤烟直，长河落日圆。萧远站在鸣沙山顶，目送最后一缕夕阳沉入地平线。身后是绵延千里的商队，驼铃声在风中叮当作响。他是这支西域商队的护卫首领，身手不凡，却有一个不为人知的秘密——他是前朝遗孤，身上流着亡国的血脉。",
    "苏州城的绣坊里，沈婉儿正在绣架前飞针走线。她的苏绣技艺已臻化境，一针一线皆可传神。然而此刻她绣的却不是寻常的花鸟鱼虫，而是一幅隐藏着惊天秘密的舆图。父亲临终前告诉她，这幅舆图指向一个被遗忘了两百年的宝藏，而宝藏中藏着一本能改变天下格局的兵书。",
    "洛阳城的夜色被万家灯火点亮。叶知秋坐在酒楼二层，一边品着陈年女儿红，一边观察着楼下的行人。他表面是个游手好闲的纨绔子弟，实际上是大内密探，奉命追查一桩涉及朝廷命官的走私大案。案情的线索指向了一个令所有人都意想不到的方向。",
    "金陵城的秦淮河上，画舫灯火通明，丝竹声声。苏沐晴站在船头，一袭白衣胜雪，手中的玉笛吹奏着一曲哀婉的《梅花三弄》。她本是名门闺秀，却因家族获罪而沦落风尘。但她从未放弃寻找洗刷家族冤屈的证据，哪怕这意味着要深入虎穴。",
    "蜀中的剑门关上，寒风凛冽。赵无极握着手中的长枪，目光如炬地注视着关外的茫茫群山。北方游牧民族的大军压境，而他手下只有三千守军。朝廷的援军遥遥无期，粮草也只够支撑半月。他知道这将是一场九死一生的守城战，但他绝不会退缩。",
    "杭州西湖的断桥边，白素贞静静地望着湖面上的倒影。千年修行让她拥有了通天的法力，却无法让她忘记那个在雨中为她撑伞的书生。人间有情，妖亦有情。她甘愿放弃千年道行，只为与他共度一生。然而天条森严，人妖殊途，命运似乎早已注定了一场悲剧。",
    "汴京城的御书房内，年轻的皇帝赵祯正在批阅奏折。烛火摇曳间，他看到了一份令他震惊的密报——他最信任的太傅竟然暗中勾结外敌，企图颠覆朝廷。这份密报来自一个神秘的情报网，而掌控这个情报网的人，竟然是他以为早已死去多年的亲兄长。",
    "洞庭湖畔的岳阳楼上，范仲淹提笔写下千古名句。然而在他身后，一场暗流涌动的朝堂争斗正在酝酿。改革派与保守派的对决已到了水火不容的地步，而他作为改革的核心人物，即将面临一生中最大的政治危机。友人劝他明哲保身，他却选择了以天下为己任。",
    "大理国苍山脚下，段誉正跟随一位白衣老者学习六脉神剑。他本是大理世子，却无心权位，一心向往江湖自由。然而命运弄人，他的身世之谜远比他想象的复杂。他的生母并非现任王妃，而是一位来自中原的神秘女子，这个秘密牵涉到两国之间的一段恩怨。",
    "太原城的演武场上，杨家将的后人们正在进行日常操练。杨延昭手持长枪，一招一式虎虎生风。自杨老令公战死沙场后，杨家的重担便落在了他肩上。辽军再次集结于雁门关外，这一次他必须守住这道防线，不仅是为了大宋，更是为了杨家满门的忠烈之名。",
    "广州港的码头上，一艘来自波斯的大船刚刚靠岸。船上的商人们带来了异域的香料、宝石和一种前所未见的黑色火药。年轻的商人林远图敏锐地意识到这种火药的军事价值，他决定冒险将其献给朝廷。然而这条从广州到汴京的路上，布满了觊觎此物的各路势力。",
    "成都府的锦江边，杜甫草堂的茅屋在秋风中瑟瑟发抖。诗人提笔写下新诗，却不知他的诗稿即将被一位神秘的江湖人士带走。这位江湖人士并非贪图诗稿的价值，而是诗中暗藏着前朝遗留下来的藏宝图。一场围绕着诗人草堂的明争暗斗悄然展开。",
    "雁门关外的草原上，萧峰孤身一人策马狂奔。身后是契丹追兵，前方是宋辽边境。他既是契丹人又是汉人养大的矛盾身份让他两边都无法归属。杏子林中的真相揭开后，他失去了丐帮帮主之位，也失去了所有信任。但真正的考验还在后面，一个关乎两国和平的秘密正在等他去揭开。",
    "景德镇御窑厂内，老窑工郑三正在烧制一批皇家贡瓷。窑火连烧三天三夜，温度的控制需要极其精准。他祖上三代都是御窑工匠，掌握着一种失传的釉色配方。然而这个秘密引来了一场杀身之祸，有人不惜纵火烧毁整个窑厂来夺取这个配方。",
    "武当山紫霄宫中，张三丰正在给弟子们传授太极拳理。他已年过百岁，须发皆白，但精神矍铄。忽然一道黑影掠过院墙，留下一封挑战书。挑战者是西域魔教教主，号称天下无敌。这一战不仅关乎武当的声誉，更牵涉到一本失传的《九阳真经》的下落。",
    "北京城紫禁城内，于谦站在午门之外，手捧奏折等待觐见。土木堡之变的消息刚刚传来，皇帝被瓦剌俘虏，朝野震动。有大臣主张南迁避祸，但他知道一旦南迁，大明半壁江山将不复存在。他必须说服太后和群臣坚守北京，哪怕这意味着要拥立新君。",
    "敦煌莫高窟的洞窟中，一位无名画师正在绘制壁画。他已在这沙漠中的石窟里度过了十年光阴，将毕生心血倾注于这些佛像和飞天之上。然而他不知道的是，他绘制的一幅看似普通的经变图中，隐藏着通往藏经洞的地图。千年之后，这个秘密将引发一场国际性的文化争夺战。",
    "扬州城的瘦西湖畔，杜牧故地重游。十年一觉扬州梦，赢得青楼薄幸名。他此番前来并非为了怀旧，而是奉命调查一桩与盐商有关的贪腐大案。两淮盐税是大唐财政的重要支柱，但近年来盐税收入锐减，背后隐藏着一张盘根错节的利益网络。他必须在盐商和官府的双重威胁下查出真相。",
]


def _make_chapters(count):
    return [
        {"index": i, "text": NOVEL_OPENINGS[i % len(NOVEL_OPENINGS)]}
        for i in range(count)
    ]


class GroupAwareFakeService:
    def __init__(self, group_size=10):
        self.group_size = group_size

    async def generate_chapter_outlines(self, chapters, progress_callback=None):
        if progress_callback:
            result = progress_callback(len(chapters), len(chapters))
            if result is not None:
                await result
        return [
            {
                "index": i,
                "content": {"summary": f"第{i+1}章章纲概括"},
                "summary": f"第{i+1}章章纲概括",
                "status": "COMPLETED",
            }
            for i, _ in enumerate(chapters)
        ]

    async def generate_coarse_outlines(self, chapter_outlines, group_size=10, progress_callback=None):
        completed = [co for co in chapter_outlines if co.get("status") == "COMPLETED"]
        groups = []
        for i in range(0, len(completed), group_size):
            groups.append(completed[i : i + group_size])

        if progress_callback:
            result = progress_callback(len(groups), len(groups))
            if result is not None:
                await result

        coarse = []
        for i, group in enumerate(groups):
            start = i * group_size
            end = min(start + group_size, len(chapter_outlines))
            coarse.append(
                {
                    "index": i,
                    "chapter_range": [start, end - 1],
                    "source_indices": list(range(start, end)),
                    "content": {"summary": f"粗纲{i+1}: {len(group)}章合并"},
                    "summary": f"粗纲{i+1}: {len(group)}章合并",
                    "status": "COMPLETED",
                }
            )
        return coarse

    async def generate_main_outlines(self, coarse_outlines, group_size=10, progress_callback=None):
        completed = [co for co in coarse_outlines if co.get("status") == "COMPLETED"]
        groups = []
        for i in range(0, len(completed), group_size):
            groups.append(completed[i : i + group_size])

        if progress_callback:
            result = progress_callback(len(groups), len(groups))
            if result is not None:
                await result

        main = []
        for i, group in enumerate(groups):
            start = i * group_size
            end = min(start + group_size, len(coarse_outlines))
            main.append(
                {
                    "index": i,
                    "source_indices": list(range(start, end)),
                    "content": {"summary": f"大纲{i+1}: {len(group)}粗纲合并"},
                    "summary": f"大纲{i+1}: {len(group)}粗纲合并",
                    "status": "COMPLETED",
                }
            )
        return main

    async def generate_world_outline(self, main_outlines, progress_callback=None):
        completed = [mo for mo in main_outlines if mo.get("status") == "COMPLETED"]
        if progress_callback:
            result = progress_callback(1, 1)
            if result is not None:
                await result
        return {
            "content": {"summary": f"世界纲: {len(completed)}份大纲合并"},
            "summary": f"世界纲: {len(completed)}份大纲合并",
            "source_indices": list(range(len(main_outlines))),
            "status": "COMPLETED",
        }


class PartialFailGroupService(GroupAwareFakeService):
    def __init__(self, fail_after=7, group_size=10):
        super().__init__(group_size)
        self.fail_after = fail_after

    async def generate_chapter_outlines(self, chapters, progress_callback=None):
        if progress_callback:
            result = progress_callback(len(chapters), len(chapters))
            if result is not None:
                await result
        outlines = []
        for i, _ in enumerate(chapters):
            if i >= self.fail_after:
                outlines.append(
                    {
                        "index": i,
                        "content": {},
                        "summary": "",
                        "status": "FAILED",
                        "error": f"第{i+1}章章纲生成超时",
                    }
                )
            else:
                outlines.append(
                    {
                        "index": i,
                        "content": {"summary": f"第{i+1}章章纲概括"},
                        "summary": f"第{i+1}章章纲概括",
                        "status": "COMPLETED",
                    }
                )
        return outlines


@pytest.fixture
def chapters_5():
    return _make_chapters(5)


@pytest.fixture
def chapters_10():
    return _make_chapters(10)


@pytest.fixture
def chapters_11():
    return _make_chapters(11)


@pytest.fixture
def chapters_15():
    return _make_chapters(15)


@pytest.fixture
def chapters_20():
    return _make_chapters(20)


@pytest.fixture
def chapters_25():
    return _make_chapters(25)


@pytest.fixture
def svc():
    return GroupAwareFakeService()


class TestMultiChapterGrouping:
    @pytest.mark.asyncio
    async def test_5_chapters_produces_1_coarse(self, chapters_5, svc):
        workflow = OutlineGraphWorkflow(outline_service=svc)
        result = await workflow.run(chapters=chapters_5)

        assert len(result["chapter_outlines"]) == 5
        assert all(co["status"] == "COMPLETED" for co in result["chapter_outlines"])
        assert len(result["coarse_outlines"]) == 1
        assert result["coarse_outlines"][0]["chapter_range"] == [0, 4]
        assert result["coarse_outlines"][0]["source_indices"] == [0, 1, 2, 3, 4]
        assert result["errors"] == []

    @pytest.mark.asyncio
    async def test_10_chapters_produces_1_coarse(self, chapters_10, svc):
        workflow = OutlineGraphWorkflow(outline_service=svc)
        result = await workflow.run(chapters=chapters_10)

        assert len(result["chapter_outlines"]) == 10
        assert len(result["coarse_outlines"]) == 1
        assert result["coarse_outlines"][0]["chapter_range"] == [0, 9]
        assert result["coarse_outlines"][0]["source_indices"] == list(range(10))
        assert result["errors"] == []

    @pytest.mark.asyncio
    async def test_11_chapters_produces_2_coarse(self, chapters_11, svc):
        workflow = OutlineGraphWorkflow(outline_service=svc)
        result = await workflow.run(chapters=chapters_11)

        assert len(result["chapter_outlines"]) == 11
        assert len(result["coarse_outlines"]) == 2
        assert result["coarse_outlines"][0]["chapter_range"] == [0, 9]
        assert result["coarse_outlines"][0]["source_indices"] == list(range(10))
        assert result["coarse_outlines"][1]["chapter_range"] == [10, 10]
        assert result["coarse_outlines"][1]["source_indices"] == [10]
        assert result["errors"] == []

    @pytest.mark.asyncio
    async def test_15_chapters_produces_2_coarse(self, chapters_15, svc):
        workflow = OutlineGraphWorkflow(outline_service=svc)
        result = await workflow.run(chapters=chapters_15)

        assert len(result["chapter_outlines"]) == 15
        assert len(result["coarse_outlines"]) == 2
        assert result["coarse_outlines"][0]["chapter_range"] == [0, 9]
        assert result["coarse_outlines"][1]["chapter_range"] == [10, 14]
        assert result["coarse_outlines"][1]["source_indices"] == [10, 11, 12, 13, 14]
        assert result["errors"] == []

    @pytest.mark.asyncio
    async def test_20_chapters_produces_2_coarse(self, chapters_20, svc):
        workflow = OutlineGraphWorkflow(outline_service=svc)
        result = await workflow.run(chapters=chapters_20)

        assert len(result["chapter_outlines"]) == 20
        assert len(result["coarse_outlines"]) == 2
        assert result["coarse_outlines"][0]["chapter_range"] == [0, 9]
        assert result["coarse_outlines"][1]["chapter_range"] == [10, 19]
        assert result["errors"] == []

    @pytest.mark.asyncio
    async def test_25_chapters_produces_3_coarse(self, chapters_25, svc):
        workflow = OutlineGraphWorkflow(outline_service=svc)
        result = await workflow.run(chapters=chapters_25)

        assert len(result["chapter_outlines"]) == 25
        assert len(result["coarse_outlines"]) == 3
        assert result["coarse_outlines"][0]["chapter_range"] == [0, 9]
        assert result["coarse_outlines"][1]["chapter_range"] == [10, 19]
        assert result["coarse_outlines"][2]["chapter_range"] == [20, 24]
        assert result["errors"] == []


class TestMultiLevelHierarchy:
    @pytest.mark.asyncio
    async def test_5_chapters_full_pipeline_hierarchy(self, chapters_5, svc):
        workflow = OutlineGraphWorkflow(outline_service=svc)
        result = await workflow.run(chapters=chapters_5)

        assert len(result["chapter_outlines"]) == 5
        assert len(result["coarse_outlines"]) == 1
        assert len(result["main_outlines"]) == 1
        assert result["world_outline"]["status"] == "COMPLETED"

        coarse = result["coarse_outlines"][0]
        assert set(coarse["source_indices"]) == {0, 1, 2, 3, 4}

        main = result["main_outlines"][0]
        assert main["source_indices"] == [0]

        world = result["world_outline"]
        assert world["source_indices"] == [0]

    @pytest.mark.asyncio
    async def test_11_chapters_full_pipeline_hierarchy(self, chapters_11, svc):
        workflow = OutlineGraphWorkflow(outline_service=svc)
        result = await workflow.run(chapters=chapters_11)

        assert len(result["chapter_outlines"]) == 11
        assert len(result["coarse_outlines"]) == 2
        assert len(result["main_outlines"]) == 1
        assert result["world_outline"]["status"] == "COMPLETED"

        coarse_0 = result["coarse_outlines"][0]
        assert coarse_0["chapter_range"] == [0, 9]
        coarse_1 = result["coarse_outlines"][1]
        assert coarse_1["chapter_range"] == [10, 10]

        main_0 = result["main_outlines"][0]
        assert main_0["source_indices"] == [0, 1]

        world = result["world_outline"]
        assert world["source_indices"] == [0]

    @pytest.mark.asyncio
    async def test_20_chapters_full_pipeline_hierarchy(self, chapters_20, svc):
        workflow = OutlineGraphWorkflow(outline_service=svc)
        result = await workflow.run(chapters=chapters_20)

        assert len(result["chapter_outlines"]) == 20
        assert len(result["coarse_outlines"]) == 2
        assert len(result["main_outlines"]) == 1
        assert result["world_outline"]["status"] == "COMPLETED"

        assert result["coarse_outlines"][0]["source_indices"] == list(range(10))
        assert result["coarse_outlines"][1]["source_indices"] == list(range(10, 20))

        assert result["main_outlines"][0]["source_indices"] == [0, 1]

    @pytest.mark.asyncio
    async def test_25_chapters_full_pipeline_hierarchy(self, chapters_25, svc):
        workflow = OutlineGraphWorkflow(outline_service=svc)
        result = await workflow.run(chapters=chapters_25)

        assert len(result["chapter_outlines"]) == 25
        assert len(result["coarse_outlines"]) == 3
        assert len(result["main_outlines"]) == 1
        assert result["world_outline"]["status"] == "COMPLETED"

        assert result["coarse_outlines"][0]["source_indices"] == list(range(10))
        assert result["coarse_outlines"][1]["source_indices"] == list(range(10, 20))
        assert result["coarse_outlines"][2]["source_indices"] == list(range(20, 25))

        assert result["main_outlines"][0]["source_indices"] == [0, 1, 2]


class TestSourceIndexCompleteness:
    @pytest.mark.asyncio
    async def test_coarse_outlines_cover_all_chapters(self, chapters_15, svc):
        workflow = OutlineGraphWorkflow(outline_service=svc)
        result = await workflow.run(chapters=chapters_15)

        all_covered = set()
        for co in result["coarse_outlines"]:
            all_covered.update(co["source_indices"])

        assert all_covered == set(range(15))

    @pytest.mark.asyncio
    async def test_main_outlines_cover_all_coarse(self, chapters_25, svc):
        workflow = OutlineGraphWorkflow(outline_service=svc)
        result = await workflow.run(chapters=chapters_25)

        all_covered = set()
        for mo in result["main_outlines"]:
            all_covered.update(mo["source_indices"])

        assert all_covered == set(range(len(result["coarse_outlines"])))

    @pytest.mark.asyncio
    async def test_world_outline_references_all_main(self, chapters_25, svc):
        workflow = OutlineGraphWorkflow(outline_service=svc)
        result = await workflow.run(chapters=chapters_25)

        world = result["world_outline"]
        assert set(world["source_indices"]) == set(range(len(result["main_outlines"])))


class TestMixedSuccessFailure:
    @pytest.mark.asyncio
    async def test_partial_chapter_failure_still_produces_coarse(self):
        chapters = _make_chapters(15)
        service = PartialFailGroupService(fail_after=7)
        workflow = OutlineGraphWorkflow(outline_service=service)
        result = await workflow.run(chapters=chapters)

        assert len(result["chapter_outlines"]) == 15
        completed_ch = [co for co in result["chapter_outlines"] if co["status"] == "COMPLETED"]
        failed_ch = [co for co in result["chapter_outlines"] if co["status"] == "FAILED"]
        assert len(completed_ch) == 7
        assert len(failed_ch) == 8

        assert len(result["errors"]) == 8
        assert all(e["stage"] == "CHAPTER_OUTLINE" for e in result["errors"])

        assert len(result["coarse_outlines"]) >= 1
        assert result["coarse_outlines"][0]["status"] == "COMPLETED"

    @pytest.mark.asyncio
    async def test_all_chapters_fail_still_completes_pipeline(self):
        chapters = _make_chapters(10)
        service = PartialFailGroupService(fail_after=0)
        workflow = OutlineGraphWorkflow(outline_service=service)
        result = await workflow.run(chapters=chapters)

        assert len(result["chapter_outlines"]) == 10
        assert all(co["status"] == "FAILED" for co in result["chapter_outlines"])
        assert len(result["errors"]) == 10

        assert len(result["coarse_outlines"]) >= 0
        assert result["world_outline"]["status"] == "COMPLETED"

    @pytest.mark.asyncio
    async def test_single_failure_out_of_many(self):
        chapters = _make_chapters(10)
        service = PartialFailGroupService(fail_after=9)
        workflow = OutlineGraphWorkflow(outline_service=service)
        result = await workflow.run(chapters=chapters)

        assert len(result["chapter_outlines"]) == 10
        assert result["chapter_outlines"][9]["status"] == "FAILED"
        assert result["chapter_outlines"][8]["status"] == "COMPLETED"

        assert len(result["errors"]) == 1
        assert result["errors"][0]["index"] == 9


class TestProgressCallbackMultiChapter:
    @pytest.mark.asyncio
    async def test_progress_tracks_all_stages_with_15_chapters(self, chapters_15, svc):
        calls = []

        async def progress(stage, current, total):
            calls.append((stage, current, total))

        workflow = OutlineGraphWorkflow(outline_service=svc)
        await workflow.run(chapters=chapters_15, progress_callback=progress)

        stages = [item[0] for item in calls]
        assert "CHAPTER_OUTLINE" in stages
        assert "COARSE_OUTLINE" in stages
        assert "MAIN_OUTLINE" in stages
        assert "WORLD_OUTLINE" in stages

        ch_calls = [c for c in calls if c[0] == "CHAPTER_OUTLINE"]
        assert ch_calls[0][1] == 15
        assert ch_calls[0][2] == 15

    @pytest.mark.asyncio
    async def test_progress_callback_null_safe_with_many_chapters(self, chapters_20, svc):
        workflow = OutlineGraphWorkflow(outline_service=svc)
        result = await workflow.run(chapters=chapters_20, progress_callback=None)

        assert len(result["chapter_outlines"]) == 20
        assert result["errors"] == []


class TestChapterContentIntegrity:
    @pytest.mark.asyncio
    async def test_chapter_indices_match_input(self, chapters_15, svc):
        workflow = OutlineGraphWorkflow(outline_service=svc)
        result = await workflow.run(chapters=chapters_15)

        for i, co in enumerate(result["chapter_outlines"]):
            assert co["index"] == i
            assert co["status"] == "COMPLETED"

    @pytest.mark.asyncio
    async def test_coarse_range_no_overlap(self, chapters_25, svc):
        workflow = OutlineGraphWorkflow(outline_service=svc)
        result = await workflow.run(chapters=chapters_25)

        ranges = [tuple(co["chapter_range"]) for co in result["coarse_outlines"]]
        for i in range(len(ranges) - 1):
            assert ranges[i][1] < ranges[i + 1][0], (
                f"Range overlap: {ranges[i]} overlaps with {ranges[i + 1]}"
            )

    @pytest.mark.asyncio
    async def test_coarse_ranges_contiguous(self, chapters_25, svc):
        workflow = OutlineGraphWorkflow(outline_service=svc)
        result = await workflow.run(chapters=chapters_25)

        ranges = [co["chapter_range"] for co in result["coarse_outlines"]]
        for i in range(len(ranges) - 1):
            assert ranges[i][1] + 1 == ranges[i + 1][0], (
                f"Gap between ranges: {ranges[i]} and {ranges[i + 1]}"
            )

        assert ranges[0][0] == 0
        assert ranges[-1][1] == 24

    @pytest.mark.asyncio
    async def test_each_chapter_summary_unique(self, chapters_15, svc):
        workflow = OutlineGraphWorkflow(outline_service=svc)
        result = await workflow.run(chapters=chapters_15)

        summaries = [co["summary"] for co in result["chapter_outlines"]]
        assert len(summaries) == len(set(summaries)), "Chapter summaries should be unique"


class TestEdgeCasesMultiChapter:
    @pytest.mark.asyncio
    async def test_exactly_1_chapter(self):
        workflow = OutlineGraphWorkflow(outline_service=GroupAwareFakeService())
        result = await workflow.run(chapters=_make_chapters(1))

        assert len(result["chapter_outlines"]) == 1
        assert len(result["coarse_outlines"]) == 1
        assert len(result["main_outlines"]) == 1
        assert result["world_outline"]["status"] == "COMPLETED"
        assert result["errors"] == []

    @pytest.mark.asyncio
    async def test_exactly_9_chapters_just_under_group_size(self):
        workflow = OutlineGraphWorkflow(outline_service=GroupAwareFakeService())
        result = await workflow.run(chapters=_make_chapters(9))

        assert len(result["chapter_outlines"]) == 9
        assert len(result["coarse_outlines"]) == 1
        assert result["coarse_outlines"][0]["chapter_range"] == [0, 8]
        assert result["errors"] == []

    @pytest.mark.asyncio
    async def test_exactly_10_chapters_exactly_one_group(self):
        workflow = OutlineGraphWorkflow(outline_service=GroupAwareFakeService())
        result = await workflow.run(chapters=_make_chapters(10))

        assert len(result["chapter_outlines"]) == 10
        assert len(result["coarse_outlines"]) == 1
        assert result["coarse_outlines"][0]["chapter_range"] == [0, 9]
        assert result["errors"] == []

    @pytest.mark.asyncio
    async def test_exactly_21_chapters_boundary(self):
        workflow = OutlineGraphWorkflow(outline_service=GroupAwareFakeService())
        result = await workflow.run(chapters=_make_chapters(21))

        assert len(result["chapter_outlines"]) == 21
        assert len(result["coarse_outlines"]) == 3
        assert result["coarse_outlines"][0]["chapter_range"] == [0, 9]
        assert result["coarse_outlines"][1]["chapter_range"] == [10, 19]
        assert result["coarse_outlines"][2]["chapter_range"] == [20, 20]
        assert result["errors"] == []
