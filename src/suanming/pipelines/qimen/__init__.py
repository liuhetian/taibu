from __future__ import annotations

from datetime import datetime as DateTime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ...contracts import (
    AssetReference,
    Pipeline,
    PipelineExecution,
    PipelineManifest,
    PipelineMode,
    RunContext,
)
from ...registry import register_pipeline
from ...shared.ganzhi import four_pillars
from ...shared.time import localize_datetime, solar_term_at

PALACES: dict[int, dict[str, str]] = {
    1: {"trigram": "坎", "direction": "北", "element": "水"},
    2: {"trigram": "坤", "direction": "西南", "element": "土"},
    3: {"trigram": "震", "direction": "东", "element": "木"},
    4: {"trigram": "巽", "direction": "东南", "element": "木"},
    5: {"trigram": "中", "direction": "中央", "element": "土"},
    6: {"trigram": "乾", "direction": "西北", "element": "金"},
    7: {"trigram": "兑", "direction": "西", "element": "金"},
    8: {"trigram": "艮", "direction": "东北", "element": "土"},
    9: {"trigram": "离", "direction": "南", "element": "火"},
}
STARS = {
    1: "天蓬",
    2: "天芮",
    3: "天冲",
    4: "天辅",
    5: "天禽",
    6: "天心",
    7: "天柱",
    8: "天任",
    9: "天英",
}
DOORS = {
    1: "休门",
    2: "死门",
    3: "伤门",
    4: "杜门",
    5: "中门",
    6: "开门",
    7: "惊门",
    8: "生门",
    9: "景门",
}
DEITIES = ("值符", "螣蛇", "太阴", "六合", "白虎", "玄武", "九地", "九天")
QI_YI = ("戊", "己", "庚", "辛", "壬", "癸", "丁", "丙", "乙")
XUN_CONCEALED = ("戊", "己", "庚", "辛", "壬", "癸")
LUCKY_DOORS = {"开门", "休门", "生门"}
NEUTRAL_DOORS = {"景门", "杜门", "中门"}
LUCKY_STARS = {"天辅", "天心", "天任", "天禽"}
NEUTRAL_STARS = {"天冲", "天英"}

JU_TABLE: dict[str, tuple[int, int, int]] = {
    "冬至": (1, 7, 4),
    "小寒": (2, 8, 5),
    "大寒": (3, 9, 6),
    "立春": (8, 5, 2),
    "雨水": (9, 6, 3),
    "惊蛰": (1, 7, 4),
    "春分": (3, 9, 6),
    "清明": (4, 1, 7),
    "谷雨": (5, 2, 8),
    "立夏": (4, 1, 7),
    "小满": (5, 2, 8),
    "芒种": (6, 3, 9),
    "夏至": (9, 3, 6),
    "小暑": (8, 2, 5),
    "大暑": (7, 1, 4),
    "立秋": (2, 5, 8),
    "处暑": (1, 4, 7),
    "白露": (9, 3, 6),
    "秋分": (7, 1, 4),
    "寒露": (6, 9, 3),
    "霜降": (5, 8, 2),
    "立冬": (6, 9, 3),
    "小雪": (5, 8, 2),
    "大雪": (4, 7, 1),
}


class QimenInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    datetime: DateTime
    timezone: str = "Asia/Shanghai"
    question: str | None = Field(default=None, max_length=500)
    method: Literal["rotating"] = "rotating"
    yuan: Literal["auto", "upper", "middle", "lower"] = "auto"
    day_boundary: Literal["midnight", "zi_hour"] = "zi_hour"

    @model_validator(mode="after")
    def validate_timezone(self) -> QimenInput:
        localize_datetime(self.datetime, self.timezone)
        return self


class QimenPalace(BaseModel):
    palace: int = Field(ge=1, le=9)
    trigram: str
    direction: str
    element: str
    earth_stem: str
    heaven_stem: str
    star: str
    door: str
    deity: str | None
    rating: Literal["吉", "平", "凶"]
    signals: list[str]


class QimenOutput(BaseModel):
    datetime: DateTime
    timezone: str
    question: str | None
    solar_term: str
    solar_longitude: float
    yuan: str
    dun: Literal["阳遁", "阴遁"]
    ju: int = Field(ge=1, le=9)
    day_pillar: str
    hour_pillar: str
    xun_head: str
    concealed_jia: str
    chief_star: str
    chief_door: str
    chief_palace: int
    palaces: list[QimenPalace]
    method_notes: list[str]


def _advance(palace: int, offset: int, direction: int) -> int:
    return ((palace - 1 + offset * direction) % 9) + 1


def _rating(door: str, star: str) -> Literal["吉", "平", "凶"]:
    door_score = 1 if door in LUCKY_DOORS else (0 if door in NEUTRAL_DOORS else -1)
    star_score = 1 if star in LUCKY_STARS else (0 if star in NEUTRAL_STARS else -1)
    score = door_score + star_score
    if score >= 1:
        return "吉"
    if score <= -1:
        return "凶"
    return "平"


def calculate_qimen(request: QimenInput) -> QimenOutput:
    local = localize_datetime(request.datetime, request.timezone)
    term = solar_term_at(local)
    pillars = four_pillars(local, day_boundary=request.day_boundary)

    if request.yuan == "auto":
        days_into_term = term.phase_degrees / 0.98564736
        yuan_index = min(2, int(days_into_term // 5))
    else:
        yuan_index = {"upper": 0, "middle": 1, "lower": 2}[request.yuan]
    yuan_name = ("上元", "中元", "下元")[yuan_index]

    is_yang = term.name in {
        "冬至",
        "小寒",
        "大寒",
        "立春",
        "雨水",
        "惊蛰",
        "春分",
        "清明",
        "谷雨",
        "立夏",
        "小满",
        "芒种",
    }
    direction = 1 if is_yang else -1
    dun: Literal["阳遁", "阴遁"] = "阳遁" if is_yang else "阴遁"
    ju = JU_TABLE[term.name][yuan_index]

    earth_plate: dict[int, str] = {}
    for offset, stem in enumerate(QI_YI):
        earth_plate[_advance(ju, offset, direction)] = stem

    xun_index = pillars.hour.index // 10
    concealed = XUN_CONCEALED[xun_index]
    xun_head = ("甲子", "甲戌", "甲申", "甲午", "甲辰", "甲寅")[xun_index]
    chief_palace = next(palace for palace, stem in earth_plate.items() if stem == concealed)
    chief_star = STARS[chief_palace]
    chief_door = DOORS[chief_palace]

    target_stem = concealed if pillars.hour.stem == "甲" else pillars.hour.stem
    target_palace = next(
        (palace for palace, stem in earth_plate.items() if stem == target_stem),
        chief_palace,
    )

    source_for_destination: dict[int, int] = {}
    for offset in range(9):
        source = _advance(chief_palace, offset, direction)
        destination = _advance(target_palace, offset, direction)
        source_for_destination[destination] = source

    deity_by_palace: dict[int, str] = {}
    for offset, deity in enumerate(DEITIES):
        deity_by_palace[_advance(target_palace, offset, direction)] = deity

    palaces: list[QimenPalace] = []
    for palace in range(1, 10):
        source = source_for_destination[palace]
        star = STARS[source]
        door = DOORS[source]
        rating = _rating(door, star)
        signals = [
            f"{door}{'属吉门' if door in LUCKY_DOORS else '需结合用事判断'}",
            f"{star}{'偏助力' if star in LUCKY_STARS else '偏考验' if star not in NEUTRAL_STARS else '力量中性'}",
        ]
        if earth_plate[palace] == earth_plate[source]:
            signals.append("天地盘同干")
        palaces.append(
            QimenPalace(
                palace=palace,
                trigram=PALACES[palace]["trigram"],
                direction=PALACES[palace]["direction"],
                element=PALACES[palace]["element"],
                earth_stem=earth_plate[palace],
                heaven_stem=earth_plate[source],
                star=star,
                door=door,
                deity=deity_by_palace.get(palace),
                rating=rating,
                signals=signals,
            )
        )

    return QimenOutput(
        datetime=local,
        timezone=request.timezone,
        question=request.question,
        solar_term=term.name,
        solar_longitude=term.longitude,
        yuan=yuan_name,
        dun=dun,
        ju=ju,
        day_pillar=pillars.day.name,
        hour_pillar=pillars.hour.name,
        xun_head=xun_head,
        concealed_jia=concealed,
        chief_star=chief_star,
        chief_door=chief_door,
        chief_palace=target_palace,
        palaces=palaces,
        method_notes=[
            "采用时家转盘、节气三元定局的自包含规则集。",
            "三元 auto 依据进入当前节气的近似天数分为上中下三元。",
            "值符随时干、九星与八门按阴阳遁方向旋布。",
            "宫位吉平凶是门星组合的可解释标签，不代替具体用神判断。",
        ],
    )


@register_pipeline
class QimenPipeline(Pipeline[QimenInput, QimenOutput]):
    manifest = PipelineManifest(
        id="qimen",
        name="奇门遁甲",
        version="0.1.0",
        ruleset="rotating-pan-solar-term-v1",
        category="spatiotemporal_chart",
        tradition="chinese",
        mode=PipelineMode.DETERMINISTIC,
        summary="按时间、节气和三元起阴阳遁九宫盘，输出天地盘、九星、八门与八神。",
        asset_pack="qimen-v1",
        tags=["九宫", "八门", "九星", "八神", "转盘"],
    )
    input_model = QimenInput
    output_model = QimenOutput

    def execute(
        self,
        request: QimenInput,
        context: RunContext,
    ) -> PipelineExecution:
        return PipelineExecution(
            result=calculate_qimen(request),
            assets=[
                AssetReference(
                    id="qimen.cover",
                    pack="qimen-v1",
                    role="pipeline-cover",
                    path="assets/packs/qimen/cover.png",
                    media_type="image/png",
                    status="available",
                )
            ],
            warnings=["当前规则集固定为时家转盘法；不同门派的置闰、拆补与飞盘法结果可能不同。"],
        )
