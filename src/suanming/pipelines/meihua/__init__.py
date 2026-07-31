from __future__ import annotations

from datetime import datetime as DateTime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ...contracts import Pipeline, PipelineExecution, PipelineManifest, PipelineMode, RunContext
from ...registry import register_pipeline
from ...shared.ganzhi import EARTHLY_BRANCHES, four_pillars
from ...shared.hexagrams import (
    TRIGRAM_BY_NUMBER,
    Trigram,
    changed_hexagram,
    hexagram_dict,
    hexagram_from_trigrams,
    mutual_hexagram,
    opposite_hexagram,
    reversed_hexagram,
    trigram_relation,
)
from ...shared.time import localize_datetime, timezone_of


class MeihuaInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    method: Literal["time", "two_numbers", "three_numbers", "text"] = "time"
    question: str | None = Field(default=None, max_length=500)
    datetime: DateTime | None = None
    timezone: str = "Asia/Shanghai"
    numbers: list[int] | None = Field(default=None, min_length=2, max_length=3)
    text: str | None = Field(default=None, min_length=1, max_length=200)

    @model_validator(mode="after")
    def validate_method(self) -> MeihuaInput:
        timezone_of(self.timezone)
        if self.datetime is not None:
            localize_datetime(self.datetime, self.timezone)
        if self.method == "two_numbers" and (self.numbers is None or len(self.numbers) != 2):
            raise ValueError("two_numbers 模式需要两个数字。")
        if self.method == "three_numbers" and (self.numbers is None or len(self.numbers) != 3):
            raise ValueError("three_numbers 模式需要三个数字。")
        if self.method == "text" and not self.text:
            raise ValueError("text 模式需要 text。")
        return self


class MeihuaOutput(BaseModel):
    method: str
    question: str | None
    datetime: DateTime
    source_numbers: list[int]
    moving_line: int = Field(ge=1, le=6)
    body_trigram: str
    use_trigram: str
    body_use_relation: str
    primary: dict[str, object]
    changed: dict[str, object]
    mutual: dict[str, object]
    opposite: dict[str, object]
    reversed: dict[str, object]
    timing_hint: dict[str, object]
    method_notes: list[str]


def _trigram(number: int) -> Trigram:
    normalized = ((number - 1) % 8) + 1
    return TRIGRAM_BY_NUMBER[normalized]


def _derive_numbers(request: MeihuaInput, effective: DateTime) -> tuple[int, int, int, list[int]]:
    if request.method in {"two_numbers", "three_numbers"}:
        assert request.numbers is not None
        first, second = request.numbers[:2]
        moving_source = request.numbers[2] if request.method == "three_numbers" else first + second
        return first, second, moving_source, list(request.numbers)
    if request.method == "text":
        assert request.text is not None
        values = [ord(char) for char in request.text if not char.isspace()]
        midpoint = max(1, len(values) // 2)
        first = sum(values[:midpoint])
        second = sum(values[midpoint:]) or first
        total = sum(values)
        return first, second, total, [first, second, total]

    pillars = four_pillars(effective, day_boundary="zi_hour")
    year_number = EARTHLY_BRANCHES.index(pillars.year.branch) + 1
    hour_number = EARTHLY_BRANCHES.index(pillars.hour.branch) + 1
    first = year_number + effective.month + effective.day
    second = first + hour_number
    return first, second, second, [year_number, effective.month, effective.day, hour_number]


def calculate_meihua(request: MeihuaInput, context: RunContext) -> MeihuaOutput:
    effective = localize_datetime(
        request.datetime or context.effective_datetime,
        request.timezone,
    )
    upper_value, lower_value, moving_value, sources = _derive_numbers(request, effective)
    upper = _trigram(upper_value)
    lower = _trigram(lower_value)
    moving_line = ((moving_value - 1) % 6) + 1
    primary = hexagram_from_trigrams(upper, lower)
    changed = changed_hexagram(primary, [moving_line])

    if moving_line <= 3:
        body, use = upper, lower
    else:
        body, use = lower, upper
    relation = trigram_relation(body, use)
    timing_units = {
        "乾": 1,
        "兑": 2,
        "离": 3,
        "震": 4,
        "巽": 5,
        "坎": 6,
        "艮": 7,
        "坤": 8,
    }
    return MeihuaOutput(
        method=request.method,
        question=request.question,
        datetime=effective,
        source_numbers=sources,
        moving_line=moving_line,
        body_trigram=body.name,
        use_trigram=use.name,
        body_use_relation=relation,
        primary=hexagram_dict(primary),
        changed=hexagram_dict(changed),
        mutual=hexagram_dict(mutual_hexagram(primary)),
        opposite=hexagram_dict(opposite_hexagram(primary)),
        reversed=hexagram_dict(reversed_hexagram(primary)),
        timing_hint={
            "base_units": timing_units[use.name],
            "unit": "按问题尺度解释为日、周、月或年",
            "basis": f"用卦{use.name}先天数",
        },
        method_notes=[
            "先天八卦数为乾一、兑二、离三、震四、巽五、坎六、艮七、坤八。",
            "动爻所在经卦为用，另一经卦为体。",
            "time 模式使用公历月日与时支数；规则版本明确记录，避免混用门派。",
        ],
    )


@register_pipeline
class MeihuaPipeline(Pipeline[MeihuaInput, MeihuaOutput]):
    manifest = PipelineManifest(
        id="meihua",
        name="梅花易数",
        version="0.1.0",
        ruleset="xiantian-numbering-v1",
        category="hexagram_oracle",
        tradition="chinese",
        mode=PipelineMode.HYBRID,
        summary="支持时间、两数、三数与文字起卦，输出体用生克与多种派生卦。",
        asset_pack="yijing-v1",
        tags=["先天数", "体用", "动爻", "应期"],
    )
    input_model = MeihuaInput
    output_model = MeihuaOutput

    def execute(self, request: MeihuaInput, context: RunContext) -> PipelineExecution:
        return PipelineExecution(result=calculate_meihua(request, context))
