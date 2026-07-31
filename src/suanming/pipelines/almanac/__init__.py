from __future__ import annotations

from datetime import date as Date
from datetime import datetime as DateTime
from datetime import time

from pydantic import BaseModel, ConfigDict, model_validator

from ...contracts import Pipeline, PipelineExecution, PipelineManifest, PipelineMode, RunContext
from ...registry import register_pipeline
from ...shared.ganzhi import EARTHLY_BRANCHES, four_pillars
from ...shared.time import gregorian_jdn, localize_datetime, solar_term_at, timezone_of

OFFICERS = ("建", "除", "满", "平", "定", "执", "破", "危", "成", "收", "开", "闭")
OFFICER_GUIDANCE = {
    "建": (("出行", "上任", "立约"), ("动土", "安葬")),
    "除": (("清洁", "治疗", "解除"), ("远行", "婚嫁")),
    "满": (("祈愿", "宴会", "庆典"), ("诉讼", "就医")),
    "平": (("修整", "协商", "常务"), ("重大迁移",)),
    "定": (("签约", "会友", "安床"), ("诉讼", "远行")),
    "执": (("执行", "捕捉", "维护"), ("开市", "迁居")),
    "破": (("拆解", "破旧", "治病"), ("婚嫁", "开业", "签约")),
    "危": (("谨慎规划", "祭祀", "安床"), ("登高", "冒险")),
    "成": (("开业", "婚嫁", "入学"), ("争讼",)),
    "收": (("收纳", "回款", "储蓄"), ("开张", "远行")),
    "开": (("开业", "出行", "会友"), ("安葬",)),
    "闭": (("闭关", "整理", "修缮"), ("开业", "婚嫁")),
}
MANSIONS = (
    "角",
    "亢",
    "氐",
    "房",
    "心",
    "尾",
    "箕",
    "斗",
    "牛",
    "女",
    "虚",
    "危",
    "室",
    "壁",
    "奎",
    "娄",
    "胃",
    "昴",
    "毕",
    "觜",
    "参",
    "井",
    "鬼",
    "柳",
    "星",
    "张",
    "翼",
    "轸",
)
HOUR_GODS = (
    "青龙",
    "明堂",
    "天刑",
    "朱雀",
    "金匮",
    "天德",
    "白虎",
    "玉堂",
    "天牢",
    "玄武",
    "司命",
    "勾陈",
)
LUCKY_GODS = {"青龙", "明堂", "金匮", "天德", "玉堂", "司命"}
STEM_DIRECTIONS = {
    "甲": ("东北", "东北", "东南"),
    "乙": ("西北", "东北", "东南"),
    "丙": ("西南", "西南", "正东"),
    "丁": ("正南", "西南", "正东"),
    "戊": ("东南", "正北", "正北"),
    "己": ("东北", "正北", "正南"),
    "庚": ("西北", "正东", "西南"),
    "辛": ("西南", "正东", "西南"),
    "壬": ("正南", "正南", "西北"),
    "癸": ("东南", "正南", "西北"),
}
PENGZU_STEM = {
    "甲": "不开仓，财物耗散",
    "乙": "不栽植，千株不长",
    "丙": "不修灶，必见灾殃",
    "丁": "不剃头，头必生疮",
    "戊": "不受田，田主不祥",
    "己": "不破券，二比并亡",
    "庚": "不经络，织机虚张",
    "辛": "不合酱，主人不尝",
    "壬": "不汲水，更难提防",
    "癸": "不词讼，理弱敌强",
}
PENGZU_BRANCH = {
    "子": "不问卜，自惹祸殃",
    "丑": "不冠带，主不还乡",
    "寅": "不祭祀，神鬼不尝",
    "卯": "不穿井，水泉不香",
    "辰": "不哭泣，必主重丧",
    "巳": "不远行，财物伏藏",
    "午": "不苫盖，屋主更张",
    "未": "不服药，毒气入肠",
    "申": "不安床，鬼祟入房",
    "酉": "不宴客，醉坐颠狂",
    "戌": "不吃犬，作怪上床",
    "亥": "不嫁娶，不利新郎",
}


class AlmanacInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date: Date
    timezone: str = "Asia/Shanghai"

    @model_validator(mode="after")
    def validate_timezone(self) -> AlmanacInput:
        timezone_of(self.timezone)
        return self


class AlmanacHour(BaseModel):
    branch: str
    range: str
    pillar: str
    god: str
    rating: str


class AlmanacOutput(BaseModel):
    date: Date
    timezone: str
    solar_term: str
    solar_longitude: float
    year_pillar: str
    month_pillar: str
    day_pillar: str
    day_officer: str
    lunar_mansion: str
    clash: str
    directions: dict[str, str]
    suitable: list[str]
    avoid: list[str]
    pengzu_taboo: list[str]
    hours: list[AlmanacHour]
    method_notes: list[str]


def calculate_almanac(request: AlmanacInput) -> AlmanacOutput:
    midday = localize_datetime(
        DateTime.combine(request.date, time(12, 0)),
        request.timezone,
    )
    pillars = four_pillars(midday, day_boundary="midnight")
    term = solar_term_at(midday)
    day_branch_index = EARTHLY_BRANCHES.index(pillars.day.branch)
    month_branch_index = EARTHLY_BRANCHES.index(pillars.month.branch)
    officer = OFFICERS[(day_branch_index - month_branch_index) % 12]
    suitable, avoid = OFFICER_GUIDANCE[officer]
    clash_branch = EARTHLY_BRANCHES[(day_branch_index + 6) % 12]
    direction_values = STEM_DIRECTIONS[pillars.day.stem]

    start_god = (day_branch_index * 2) % 12
    hours: list[AlmanacHour] = []
    for branch_index, branch in enumerate(EARTHLY_BRANCHES):
        representative_hour = (branch_index * 2 - 1) % 24
        hour_value = midday.replace(hour=representative_hour)
        hour_pillar = four_pillars(hour_value, day_boundary="zi_hour").hour.name
        god = HOUR_GODS[(start_god + branch_index) % 12]
        start = representative_hour
        end = (representative_hour + 1) % 24
        hours.append(
            AlmanacHour(
                branch=branch,
                range=f"{start:02d}:00-{end:02d}:59",
                pillar=hour_pillar,
                god=god,
                rating="吉" if god in LUCKY_GODS else "凶",
            )
        )

    jdn = gregorian_jdn(request.date.year, request.date.month, request.date.day)
    mansion = MANSIONS[(jdn + 11) % 28]
    return AlmanacOutput(
        date=request.date,
        timezone=request.timezone,
        solar_term=term.name,
        solar_longitude=term.longitude,
        year_pillar=pillars.year.name,
        month_pillar=pillars.month.name,
        day_pillar=pillars.day.name,
        day_officer=f"{officer}日",
        lunar_mansion=f"{mansion}宿",
        clash=f"冲{clash_branch}",
        directions={
            "喜神": direction_values[0],
            "财神": direction_values[1],
            "福神": direction_values[2],
        },
        suitable=list(suitable),
        avoid=list(avoid),
        pengzu_taboo=[
            PENGZU_STEM[pillars.day.stem],
            PENGZU_BRANCH[pillars.day.branch],
        ],
        hours=hours,
        method_notes=[
            "建除十二神按月支与日支的相对位置计算。",
            "十二时辰按日干支生成时柱，并配黄道黑道神序。",
            "二十八宿采用固定日序锚点；规则版本改变时结果会显式升级。",
        ],
    )


@register_pipeline
class AlmanacPipeline(Pipeline[AlmanacInput, AlmanacOutput]):
    manifest = PipelineManifest(
        id="almanac",
        name="黄历",
        version="0.1.0",
        ruleset="day-officer-mansion-hours-v1",
        category="calendar_oracle",
        tradition="chinese",
        mode=PipelineMode.DETERMINISTIC,
        summary="按日期输出干支、节气、建除十二神、二十八宿、方位与十二时辰吉凶。",
        asset_pack="yijing-v1",
        tags=["择日", "建除十二神", "二十八宿", "时辰"],
    )
    input_model = AlmanacInput
    output_model = AlmanacOutput

    def execute(
        self,
        request: AlmanacInput,
        context: RunContext,
    ) -> PipelineExecution:
        return PipelineExecution(result=calculate_almanac(request))
