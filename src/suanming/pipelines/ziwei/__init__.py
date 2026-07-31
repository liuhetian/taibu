from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ...contracts import Pipeline, PipelineExecution, PipelineManifest, PipelineMode, RunContext
from ...registry import register_pipeline
from ...shared.ganzhi import (
    EARTHLY_BRANCHES,
    HEAVENLY_STEMS,
    nayin_of,
    sexagenary_index,
)

PALACE_BRANCHES = ("寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥", "子", "丑")
PALACE_NAMES = (
    "命宫",
    "兄弟",
    "夫妻",
    "子女",
    "财帛",
    "疾厄",
    "迁移",
    "仆役",
    "官禄",
    "田宅",
    "福德",
    "父母",
)
BUREAU_BY_ELEMENT = {"水": 2, "木": 3, "金": 4, "土": 5, "火": 6}
ZIWEI_OFFSETS = {
    "紫微": 0,
    "天机": -1,
    "太阳": -3,
    "武曲": -4,
    "天同": -5,
    "廉贞": -8,
}
TIANFU_OFFSETS = {
    "天府": 0,
    "太阴": 1,
    "贪狼": 2,
    "巨门": 3,
    "天相": 4,
    "天梁": 5,
    "七杀": 6,
    "破军": 10,
}
FOUR_TRANSFORMATIONS = {
    "甲": {"禄": "廉贞", "权": "破军", "科": "武曲", "忌": "太阳"},
    "乙": {"禄": "天机", "权": "天梁", "科": "紫微", "忌": "太阴"},
    "丙": {"禄": "天同", "权": "天机", "科": "文昌", "忌": "廉贞"},
    "丁": {"禄": "太阴", "权": "天同", "科": "天机", "忌": "巨门"},
    "戊": {"禄": "贪狼", "权": "太阴", "科": "右弼", "忌": "天机"},
    "己": {"禄": "武曲", "权": "贪狼", "科": "天梁", "忌": "文曲"},
    "庚": {"禄": "太阳", "权": "武曲", "科": "太阴", "忌": "天同"},
    "辛": {"禄": "巨门", "权": "太阳", "科": "文曲", "忌": "文昌"},
    "壬": {"禄": "天梁", "权": "紫微", "科": "左辅", "忌": "武曲"},
    "癸": {"禄": "破军", "权": "巨门", "科": "太阴", "忌": "贪狼"},
}
LUCUN_BRANCH = {
    "甲": "寅",
    "乙": "卯",
    "丙": "巳",
    "丁": "午",
    "戊": "巳",
    "己": "午",
    "庚": "申",
    "辛": "酉",
    "壬": "亥",
    "癸": "子",
}
LIFE_LORD = {
    "子": "贪狼",
    "丑": "巨门",
    "寅": "禄存",
    "卯": "文曲",
    "辰": "廉贞",
    "巳": "武曲",
    "午": "破军",
    "未": "武曲",
    "申": "廉贞",
    "酉": "文曲",
    "戌": "禄存",
    "亥": "巨门",
}
BODY_LORD = {
    "子": "火星",
    "丑": "天相",
    "寅": "天梁",
    "卯": "天同",
    "辰": "文昌",
    "巳": "天机",
    "午": "火星",
    "未": "天相",
    "申": "天梁",
    "酉": "天同",
    "戌": "文昌",
    "亥": "天机",
}


class ZiweiInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lunar_year: int = Field(ge=1600, le=2600)
    lunar_month: int = Field(ge=1, le=12)
    lunar_day: int = Field(ge=1, le=30)
    hour_branch: Literal["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
    gender: Literal["male", "female", "unspecified"] = "unspecified"
    leap_month: bool = False


class ZiweiStar(BaseModel):
    name: str
    group: str
    transformation: str | None = None


class ZiweiPalace(BaseModel):
    branch: str
    stem: str
    name: str
    is_body_palace: bool
    stars: list[ZiweiStar]
    trine_branches: list[str]
    opposite_branch: str


class ZiweiOutput(BaseModel):
    lunar_birth: dict[str, object]
    year_pillar: str
    life_palace: str
    body_palace: str
    life_lord: str
    body_lord: str
    five_element_bureau: str
    bureau_number: int
    transformations: dict[str, str]
    palaces: list[ZiweiPalace]
    method_notes: list[str]


def _ziwei_index(day: int, bureau: int) -> int:
    quotient, remainder = divmod(day, bureau)
    if remainder == 0:
        return (quotient - 1) % 12
    adjustment = bureau - remainder
    base = quotient
    return (base + adjustment if adjustment % 2 == 0 else base - adjustment) % 12


def calculate_ziwei(request: ZiweiInput) -> ZiweiOutput:
    year_index = (request.lunar_year - 4) % 60
    year_stem = HEAVENLY_STEMS[year_index % 10]
    year_branch = EARTHLY_BRANCHES[year_index % 12]
    hour_index = EARTHLY_BRANCHES.index(request.hour_branch)
    life_index = (request.lunar_month - 1 - hour_index) % 12
    body_index = (request.lunar_month - 1 + hour_index) % 12

    palace_stem_start = (HEAVENLY_STEMS.index(year_stem) * 2 + 2) % 10
    palace_stems = [HEAVENLY_STEMS[(palace_stem_start + index) % 10] for index in range(12)]
    life_branch = PALACE_BRANCHES[life_index]
    life_stem = palace_stems[life_index]
    life_nayin = nayin_of(sexagenary_index(life_stem, life_branch))
    bureau_element = life_nayin[-1]
    bureau = BUREAU_BY_ELEMENT[bureau_element]

    stars_by_index: dict[int, list[tuple[str, str]]] = {index: [] for index in range(12)}
    ziwei_index = _ziwei_index(request.lunar_day, bureau)
    tianfu_index = (-ziwei_index) % 12
    for star, offset in ZIWEI_OFFSETS.items():
        stars_by_index[(ziwei_index + offset) % 12].append((star, "紫微星系"))
    for star, offset in TIANFU_OFFSETS.items():
        stars_by_index[(tianfu_index + offset) % 12].append((star, "天府星系"))

    # Month/hour/year auxiliaries keep the chart useful without hiding their rule.
    left_index = (2 + request.lunar_month - 1) % 12
    right_index = (8 - (request.lunar_month - 1)) % 12
    wenchang_index = (8 - hour_index) % 12
    wenqu_index = (2 + hour_index) % 12
    for index, name in (
        (left_index, "左辅"),
        (right_index, "右弼"),
        (wenchang_index, "文昌"),
        (wenqu_index, "文曲"),
    ):
        stars_by_index[index].append((name, "辅曜"))
    lucun_index = PALACE_BRANCHES.index(LUCUN_BRANCH[year_stem])
    stars_by_index[lucun_index].append(("禄存", "辅曜"))
    stars_by_index[(lucun_index + 1) % 12].append(("擎羊", "煞曜"))
    stars_by_index[(lucun_index - 1) % 12].append(("陀罗", "煞曜"))

    transformations = FOUR_TRANSFORMATIONS[year_stem]
    transform_by_star = {star: kind for kind, star in transformations.items()}
    palace_name_by_index = {
        (life_index - offset) % 12: name for offset, name in enumerate(PALACE_NAMES)
    }
    palaces: list[ZiweiPalace] = []
    for index, branch in enumerate(PALACE_BRANCHES):
        stars = [
            ZiweiStar(
                name=name,
                group=group,
                transformation=transform_by_star.get(name),
            )
            for name, group in stars_by_index[index]
        ]
        palaces.append(
            ZiweiPalace(
                branch=branch,
                stem=palace_stems[index],
                name=palace_name_by_index[index],
                is_body_palace=index == body_index,
                stars=stars,
                trine_branches=[
                    PALACE_BRANCHES[(index + 4) % 12],
                    PALACE_BRANCHES[(index + 8) % 12],
                ],
                opposite_branch=PALACE_BRANCHES[(index + 6) % 12],
            )
        )
    return ZiweiOutput(
        lunar_birth={
            "year": request.lunar_year,
            "month": request.lunar_month,
            "day": request.lunar_day,
            "hour_branch": request.hour_branch,
            "leap_month": request.leap_month,
            "gender": request.gender,
        },
        year_pillar=year_stem + year_branch,
        life_palace=life_stem + life_branch,
        body_palace=palace_stems[body_index] + PALACE_BRANCHES[body_index],
        life_lord=LIFE_LORD[life_branch],
        body_lord=BODY_LORD[year_branch],
        five_element_bureau={
            2: "水二局",
            3: "木三局",
            4: "金四局",
            5: "土五局",
            6: "火六局",
        }[bureau],
        bureau_number=bureau,
        transformations=transformations,
        palaces=palaces,
        method_notes=[
            "输入直接采用农历年月日与时支，避免在内核中静默猜测闰月。",
            "命宫由寅起正月顺数月份、逆数时支；身宫顺数时支。",
            "五行局取命宫干支纳音；十四主星采用五行局与生日商余安紫微，再布紫府两系。",
            "当前版本含十四主星、左右昌曲、禄羊陀与生年四化；杂曜、旺陷和运限由后续独立规则层扩展。",
        ],
    )


@register_pipeline
class ZiweiPipeline(Pipeline[ZiweiInput, ZiweiOutput]):
    manifest = PipelineManifest(
        id="ziwei",
        name="紫微斗数",
        version="0.1.0",
        ruleset="lunar-fourteen-main-stars-v1",
        category="natal_chart",
        tradition="chinese",
        mode=PipelineMode.DETERMINISTIC,
        summary="按农历出生信息安十二宫、五行局、十四主星、基础辅曜与生年四化。",
        asset_pack="ziwei-v1",
        tags=["十二宫", "十四主星", "四化", "三方四正"],
    )
    input_model = ZiweiInput
    output_model = ZiweiOutput

    def execute(self, request: ZiweiInput, context: RunContext) -> PipelineExecution:
        return PipelineExecution(
            result=calculate_ziwei(request),
            warnings=["紫微斗数流派众多；本输出明确对应 lunar-fourteen-main-stars-v1 规则集。"],
        )
