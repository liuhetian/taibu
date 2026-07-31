from __future__ import annotations

from datetime import datetime as DateTime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ...contracts import Pipeline, PipelineExecution, PipelineManifest, PipelineMode, RunContext
from ...registry import register_pipeline
from ...shared.astronomy import (
    BODY_ORDER,
    ascendant_longitude,
    is_retrograde,
    planetary_positions,
)
from ...shared.time import localize_datetime

BODY_NAMES = {
    "sun": "太阳",
    "moon": "月亮",
    "mercury": "水星",
    "venus": "金星",
    "mars": "火星",
    "jupiter": "木星",
    "saturn": "土星",
    "uranus": "天王星",
    "neptune": "海王星",
    "ascendant": "上升点",
}
SIGNS = (
    "白羊座",
    "金牛座",
    "双子座",
    "巨蟹座",
    "狮子座",
    "处女座",
    "天秤座",
    "天蝎座",
    "射手座",
    "摩羯座",
    "水瓶座",
    "双鱼座",
)
ASPECTS = (
    ("合相", 0.0, 8.0),
    ("六分相", 60.0, 5.0),
    ("四分相", 90.0, 7.0),
    ("三分相", 120.0, 7.0),
    ("对分相", 180.0, 8.0),
)


class AstrologyInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    datetime: DateTime
    timezone: str = "Asia/Shanghai"
    latitude: float | None = Field(default=None, ge=-66, le=66)
    longitude: float | None = Field(default=None, ge=-180, le=180)

    @model_validator(mode="after")
    def validate_location(self) -> AstrologyInput:
        localize_datetime(self.datetime, self.timezone)
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("latitude 与 longitude 必须同时提供。")
        return self


class AstrologyPoint(BaseModel):
    id: str
    name: str
    longitude: float
    latitude: float
    sign: str
    degree_in_sign: float
    retrograde: bool
    house: int | None


class AstrologyAspect(BaseModel):
    first: str
    second: str
    aspect: str
    angle: float
    orb: float


class AstrologyOutput(BaseModel):
    datetime: DateTime
    timezone: str
    coordinates: dict[str, float] | None
    house_system: str | None
    ascendant: AstrologyPoint | None
    points: list[AstrologyPoint]
    aspects: list[AstrologyAspect]
    element_balance: dict[str, int]
    modality_balance: dict[str, int]
    method_notes: list[str]


def _sign(longitude: float) -> tuple[str, float, int]:
    index = int(longitude // 30) % 12
    return SIGNS[index], longitude % 30, index


def _house(longitude: float, ascendant: float | None) -> int | None:
    if ascendant is None:
        return None
    return int(((longitude - ascendant) % 360) // 30) + 1


def calculate_astrology(request: AstrologyInput) -> AstrologyOutput:
    effective = localize_datetime(request.datetime, request.timezone)
    positions = planetary_positions(effective)
    ascendant_value = (
        ascendant_longitude(effective, request.latitude, request.longitude)
        if request.latitude is not None and request.longitude is not None
        else None
    )
    points: list[AstrologyPoint] = []
    sign_indices: list[int] = []
    for body in BODY_ORDER:
        position = positions[body]
        sign, degree, sign_index = _sign(position.longitude)
        sign_indices.append(sign_index)
        points.append(
            AstrologyPoint(
                id=body,
                name=BODY_NAMES[body],
                longitude=round(position.longitude, 6),
                latitude=round(position.latitude, 6),
                sign=sign,
                degree_in_sign=round(degree, 6),
                retrograde=is_retrograde(body, effective),
                house=_house(position.longitude, ascendant_value),
            )
        )

    ascendant_model = None
    if ascendant_value is not None:
        sign, degree, _ = _sign(ascendant_value)
        ascendant_model = AstrologyPoint(
            id="ascendant",
            name=BODY_NAMES["ascendant"],
            longitude=round(ascendant_value, 6),
            latitude=0.0,
            sign=sign,
            degree_in_sign=round(degree, 6),
            retrograde=False,
            house=1,
        )

    aspects: list[AstrologyAspect] = []
    for left_index, left in enumerate(points):
        for right in points[left_index + 1 :]:
            separation = abs((left.longitude - right.longitude + 180) % 360 - 180)
            for name, target, allowed_orb in ASPECTS:
                orb = abs(separation - target)
                if orb <= allowed_orb:
                    aspects.append(
                        AstrologyAspect(
                            first=left.id,
                            second=right.id,
                            aspect=name,
                            angle=round(separation, 4),
                            orb=round(orb, 4),
                        )
                    )
                    break

    elements = ("火", "土", "风", "水")
    modalities = ("本位", "固定", "变动")
    element_balance = dict.fromkeys(elements, 0)
    modality_balance = dict.fromkeys(modalities, 0)
    for index in sign_indices:
        element_balance[elements[index % 4]] += 1
        modality_balance[modalities[index % 3]] += 1

    return AstrologyOutput(
        datetime=effective,
        timezone=request.timezone,
        coordinates=(
            {"latitude": request.latitude, "longitude": request.longitude}
            if request.latitude is not None and request.longitude is not None
            else None
        ),
        house_system="equal_house" if ascendant_value is not None else None,
        ascendant=ascendant_model,
        points=points,
        aspects=aspects,
        element_balance=element_balance,
        modality_balance=modality_balance,
        method_notes=[
            "行星黄经使用仓库内置的低精度轨道元素与开普勒方程计算。",
            "未提供经纬度时不计算上升点与宫位。",
            "宫位采用等宫制；适合内核可复现计算，不等同于专业星历软件。",
        ],
    )


@register_pipeline
class AstrologyPipeline(Pipeline[AstrologyInput, AstrologyOutput]):
    manifest = PipelineManifest(
        id="astrology",
        name="西方占星",
        version="0.1.0",
        ruleset="self-contained-orbital-elements-v1",
        category="natal_chart",
        tradition="western_astrology",
        mode=PipelineMode.DETERMINISTIC,
        summary="离线计算九大天体黄经、星座、逆行、主要相位与可选等宫制宫位。",
        asset_pack="astrology-v1",
        tags=["本命盘", "星座", "相位", "等宫制"],
    )
    input_model = AstrologyInput
    output_model = AstrologyOutput

    def execute(
        self,
        request: AstrologyInput,
        context: RunContext,
    ) -> PipelineExecution:
        return PipelineExecution(
            result=calculate_astrology(request),
            warnings=["低精度轨道级数不用于天文观测、航海或高精度合盘。"],
        )
