from __future__ import annotations

import unicodedata
from datetime import date as Date

from pydantic import BaseModel, ConfigDict, Field

from ...contracts import Pipeline, PipelineExecution, PipelineManifest, PipelineMode, RunContext
from ...registry import register_pipeline

NUMBER_MEANINGS = {
    1: ("开创者", ("独立", "行动", "领导")),
    2: ("协调者", ("合作", "敏感", "平衡")),
    3: ("表达者", ("创意", "沟通", "乐观")),
    4: ("建造者", ("秩序", "务实", "稳定")),
    5: ("探索者", ("变化", "自由", "适应")),
    6: ("照顾者", ("责任", "关系", "审美")),
    7: ("研究者", ("分析", "内省", "求真")),
    8: ("管理者", ("资源", "目标", "执行")),
    9: ("整合者", ("理想", "同理", "完成")),
    11: ("启发者", ("直觉", "愿景", "传递")),
    22: ("大建造者", ("系统", "落地", "长期影响")),
    33: ("教导者", ("慈悲", "服务", "示范")),
}


def reduce_number(value: int, *, keep_master: bool = True) -> int:
    value = abs(value)
    while value >= 10 and not (keep_master and value in {11, 22, 33}):
        value = sum(int(digit) for digit in str(value))
    return value


def life_path_number(value: Date) -> int:
    return reduce_number(sum(int(digit) for digit in value.strftime("%Y%m%d")))


def _latin_values(name: str) -> tuple[list[int], list[int], list[int]]:
    normalized = unicodedata.normalize("NFKD", name).upper()
    letters = [char for char in normalized if "A" <= char <= "Z"]
    vowels = {"A", "E", "I", "O", "U", "Y"}
    all_values = [(ord(char) - ord("A")) % 9 + 1 for char in letters]
    vowel_values = [(ord(char) - ord("A")) % 9 + 1 for char in letters if char in vowels]
    consonant_values = [(ord(char) - ord("A")) % 9 + 1 for char in letters if char not in vowels]
    return all_values, vowel_values, consonant_values


class NumerologyInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    birth_date: Date
    name: str | None = Field(default=None, max_length=200)
    target_year: int | None = Field(default=None, ge=1, le=9999)


class NumberProfile(BaseModel):
    number: int
    archetype: str
    keywords: list[str]
    calculation: str


class NumerologyOutput(BaseModel):
    birth_date: Date
    name: str | None
    life_path: NumberProfile
    birthday: NumberProfile
    attitude: NumberProfile
    personal_year: NumberProfile
    expression: NumberProfile | None
    soul_urge: NumberProfile | None
    personality: NumberProfile | None
    method_notes: list[str]


def _profile(number: int, calculation: str) -> NumberProfile:
    archetype, keywords = NUMBER_MEANINGS[number]
    return NumberProfile(
        number=number,
        archetype=archetype,
        keywords=list(keywords),
        calculation=calculation,
    )


def calculate_numerology(request: NumerologyInput, current_year: int) -> NumerologyOutput:
    target_year = request.target_year or current_year
    life_path = life_path_number(request.birth_date)
    birthday = reduce_number(request.birth_date.day)
    attitude = reduce_number(request.birth_date.month + request.birth_date.day)
    personal_year = reduce_number(
        request.birth_date.month
        + request.birth_date.day
        + sum(int(digit) for digit in str(target_year))
    )
    expression = soul_urge = personality = None
    if request.name:
        all_values, vowel_values, consonant_values = _latin_values(request.name)
        if all_values:
            expression_number = reduce_number(sum(all_values))
            expression = _profile(expression_number, "拉丁字母全名数值总和")
        if vowel_values:
            soul_number = reduce_number(sum(vowel_values))
            soul_urge = _profile(soul_number, "拉丁字母元音数值总和")
        if consonant_values:
            personality_number = reduce_number(sum(consonant_values))
            personality = _profile(personality_number, "拉丁字母辅音数值总和")
    return NumerologyOutput(
        birth_date=request.birth_date,
        name=request.name,
        life_path=_profile(life_path, "出生年月日全部数字相加后归约"),
        birthday=_profile(birthday, "出生日归约"),
        attitude=_profile(attitude, "出生月与出生日相加后归约"),
        personal_year=_profile(personal_year, f"出生月日与 {target_year} 年数相加后归约"),
        expression=expression,
        soul_urge=soul_urge,
        personality=personality,
        method_notes=[
            "保留 11、22、33 三个主数字。",
            "姓名数采用毕达哥拉斯拉丁字母映射；非拉丁姓名不会被任意转码。",
        ],
    )


@register_pipeline
class NumerologyPipeline(Pipeline[NumerologyInput, NumerologyOutput]):
    manifest = PipelineManifest(
        id="numerology",
        name="数字命理",
        version="0.1.0",
        ruleset="pythagorean-date-name-v1",
        category="number_oracle",
        tradition="western_esoteric",
        mode=PipelineMode.DETERMINISTIC,
        summary="计算生命路径、生日、态度、个人年与可选拉丁姓名数字。",
        asset_pack="numerology-v1",
        tags=["生命路径", "主数字", "个人年"],
    )
    input_model = NumerologyInput
    output_model = NumerologyOutput

    def execute(
        self,
        request: NumerologyInput,
        context: RunContext,
    ) -> PipelineExecution:
        output = calculate_numerology(request, context.effective_datetime.year)
        warnings = (
            ["姓名未含可识别拉丁字母，因此未计算姓名数字。"]
            if request.name and output.expression is None
            else []
        )
        return PipelineExecution(result=output, warnings=warnings)
