from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from itertools import combinations

from .time import gregorian_jdn, solar_longitude

HEAVENLY_STEMS: tuple[str, ...] = (
    "甲",
    "乙",
    "丙",
    "丁",
    "戊",
    "己",
    "庚",
    "辛",
    "壬",
    "癸",
)
EARTHLY_BRANCHES: tuple[str, ...] = (
    "子",
    "丑",
    "寅",
    "卯",
    "辰",
    "巳",
    "午",
    "未",
    "申",
    "酉",
    "戌",
    "亥",
)
STEM_ELEMENTS: dict[str, str] = {
    "甲": "木",
    "乙": "木",
    "丙": "火",
    "丁": "火",
    "戊": "土",
    "己": "土",
    "庚": "金",
    "辛": "金",
    "壬": "水",
    "癸": "水",
}
BRANCH_ELEMENTS: dict[str, str] = {
    "子": "水",
    "丑": "土",
    "寅": "木",
    "卯": "木",
    "辰": "土",
    "巳": "火",
    "午": "火",
    "未": "土",
    "申": "金",
    "酉": "金",
    "戌": "土",
    "亥": "水",
}
HIDDEN_STEMS: dict[str, tuple[str, ...]] = {
    "子": ("癸",),
    "丑": ("己", "癸", "辛"),
    "寅": ("甲", "丙", "戊"),
    "卯": ("乙",),
    "辰": ("戊", "乙", "癸"),
    "巳": ("丙", "戊", "庚"),
    "午": ("丁", "己"),
    "未": ("己", "丁", "乙"),
    "申": ("庚", "壬", "戊"),
    "酉": ("辛",),
    "戌": ("戊", "辛", "丁"),
    "亥": ("壬", "甲"),
}
GENERATES: dict[str, str] = {
    "木": "火",
    "火": "土",
    "土": "金",
    "金": "水",
    "水": "木",
}
CONTROLS: dict[str, str] = {
    "木": "土",
    "土": "水",
    "水": "火",
    "火": "金",
    "金": "木",
}
NAYIN_PAIRS: tuple[str, ...] = (
    "海中金",
    "炉中火",
    "大林木",
    "路旁土",
    "剑锋金",
    "山头火",
    "涧下水",
    "城头土",
    "白蜡金",
    "杨柳木",
    "泉中水",
    "屋上土",
    "霹雳火",
    "松柏木",
    "长流水",
    "沙中金",
    "山下火",
    "平地木",
    "壁上土",
    "金箔金",
    "覆灯火",
    "天河水",
    "大驿土",
    "钗钏金",
    "桑柘木",
    "大溪水",
    "沙中土",
    "天上火",
    "石榴木",
    "大海水",
)


@dataclass(frozen=True, slots=True)
class Ganzhi:
    stem: str
    branch: str
    index: int

    @property
    def name(self) -> str:
        return self.stem + self.branch


@dataclass(frozen=True, slots=True)
class FourPillars:
    year: Ganzhi
    month: Ganzhi
    day: Ganzhi
    hour: Ganzhi


def ganzhi_at(index: int) -> Ganzhi:
    normalized = index % 60
    return Ganzhi(
        stem=HEAVENLY_STEMS[normalized % 10],
        branch=EARTHLY_BRANCHES[normalized % 12],
        index=normalized,
    )


def sexagenary_index(stem: str, branch: str) -> int:
    for index in range(60):
        item = ganzhi_at(index)
        if item.stem == stem and item.branch == branch:
            return index
    raise ValueError(f"干支组合不存在：{stem}{branch}")


def four_pillars(
    value: datetime,
    *,
    day_boundary: str = "midnight",
) -> FourPillars:
    longitude = solar_longitude(value)
    effective_year = value.year
    if value.month <= 2 and longitude < 315.0:
        effective_year -= 1

    year_index = (effective_year - 4) % 60
    year = ganzhi_at(year_index)

    month_offset = int(((longitude - 315.0) % 360.0) // 30.0)
    month_branch_index = (2 + month_offset) % 12
    first_month_stem = (year_index % 10 * 2 + 2) % 10
    month_stem_index = (first_month_stem + month_offset) % 10
    month = Ganzhi(
        stem=HEAVENLY_STEMS[month_stem_index],
        branch=EARTHLY_BRANCHES[month_branch_index],
        index=sexagenary_index(
            HEAVENLY_STEMS[month_stem_index],
            EARTHLY_BRANCHES[month_branch_index],
        ),
    )

    day_value = value
    if day_boundary == "zi_hour" and value.hour >= 23:
        day_value = value + timedelta(days=1)
    day_jdn = gregorian_jdn(day_value.year, day_value.month, day_value.day)
    day = ganzhi_at((day_jdn + 49) % 60)

    hour_branch_index = ((value.hour + 1) // 2) % 12
    hour_stem_index = ((day.index % 10) * 2 + hour_branch_index) % 10
    hour = Ganzhi(
        stem=HEAVENLY_STEMS[hour_stem_index],
        branch=EARTHLY_BRANCHES[hour_branch_index],
        index=sexagenary_index(
            HEAVENLY_STEMS[hour_stem_index],
            EARTHLY_BRANCHES[hour_branch_index],
        ),
    )
    return FourPillars(year=year, month=month, day=day, hour=hour)


def yin_yang_of_stem(stem: str) -> str:
    return "阳" if HEAVENLY_STEMS.index(stem) % 2 == 0 else "阴"


def yin_yang_of_branch(branch: str) -> str:
    return "阳" if EARTHLY_BRANCHES.index(branch) % 2 == 0 else "阴"


def ten_god(day_stem: str, target_stem: str) -> str:
    day_element = STEM_ELEMENTS[day_stem]
    target_element = STEM_ELEMENTS[target_stem]
    same_polarity = yin_yang_of_stem(day_stem) == yin_yang_of_stem(target_stem)

    if day_element == target_element:
        return "比肩" if same_polarity else "劫财"
    if GENERATES[day_element] == target_element:
        return "食神" if same_polarity else "伤官"
    if GENERATES[target_element] == day_element:
        return "偏印" if same_polarity else "正印"
    if CONTROLS[day_element] == target_element:
        return "偏财" if same_polarity else "正财"
    return "七杀" if same_polarity else "正官"


def nayin_of(index: int) -> str:
    return NAYIN_PAIRS[(index % 60) // 2]


def kongwang_of(day_index: int) -> tuple[str, str]:
    xun_index = (day_index % 60) // 10
    start = (10 - 2 * xun_index) % 12
    return (
        EARTHLY_BRANCHES[start],
        EARTHLY_BRANCHES[(start + 1) % 12],
    )


def five_element_statistics(pillars: FourPillars) -> dict[str, float]:
    stats = {"木": 0.0, "火": 0.0, "土": 0.0, "金": 0.0, "水": 0.0}
    weights = (0.6, 0.3, 0.1)
    for pillar in (pillars.year, pillars.month, pillars.day, pillars.hour):
        stats[STEM_ELEMENTS[pillar.stem]] += 1.0
        stats[BRANCH_ELEMENTS[pillar.branch]] += 1.0
        for index, hidden in enumerate(HIDDEN_STEMS[pillar.branch]):
            stats[STEM_ELEMENTS[hidden]] += weights[index]
    return {key: round(value, 2) for key, value in stats.items()}


SIX_COMBINATIONS = {
    frozenset(("子", "丑")): "六合",
    frozenset(("寅", "亥")): "六合",
    frozenset(("卯", "戌")): "六合",
    frozenset(("辰", "酉")): "六合",
    frozenset(("巳", "申")): "六合",
    frozenset(("午", "未")): "六合",
}
SIX_CLASHES = {
    frozenset(("子", "午")): "六冲",
    frozenset(("丑", "未")): "六冲",
    frozenset(("寅", "申")): "六冲",
    frozenset(("卯", "酉")): "六冲",
    frozenset(("辰", "戌")): "六冲",
    frozenset(("巳", "亥")): "六冲",
}
SIX_HARMS = {
    frozenset(("子", "未")): "六害",
    frozenset(("丑", "午")): "六害",
    frozenset(("寅", "巳")): "六害",
    frozenset(("卯", "辰")): "六害",
    frozenset(("申", "亥")): "六害",
    frozenset(("酉", "戌")): "六害",
}
THREE_HARMONIES = {
    frozenset(("申", "子", "辰")): "申子辰三合水局",
    frozenset(("亥", "卯", "未")): "亥卯未三合木局",
    frozenset(("寅", "午", "戌")): "寅午戌三合火局",
    frozenset(("巳", "酉", "丑")): "巳酉丑三合金局",
}
THREE_MEETINGS = {
    frozenset(("寅", "卯", "辰")): "寅卯辰三会木局",
    frozenset(("巳", "午", "未")): "巳午未三会火局",
    frozenset(("申", "酉", "戌")): "申酉戌三会金局",
    frozenset(("亥", "子", "丑")): "亥子丑三会水局",
}


def branch_relations(pillars: FourPillars) -> list[dict[str, str]]:
    named = {
        "year": pillars.year.branch,
        "month": pillars.month.branch,
        "day": pillars.day.branch,
        "hour": pillars.hour.branch,
    }
    results: list[dict[str, str]] = []
    for left, right in combinations(named, 2):
        pair = frozenset((named[left], named[right]))
        for mapping in (SIX_COMBINATIONS, SIX_CLASHES, SIX_HARMS):
            if pair in mapping:
                results.append(
                    {
                        "type": mapping[pair],
                        "pillars": f"{left},{right}",
                        "branches": f"{named[left]}{named[right]}",
                    }
                )
    branch_set = frozenset(named.values())
    for pattern, label in {**THREE_HARMONIES, **THREE_MEETINGS}.items():
        if pattern.issubset(branch_set):
            results.append(
                {
                    "type": label,
                    "pillars": "multiple",
                    "branches": "".join(sorted(pattern)),
                }
            )
    return results
