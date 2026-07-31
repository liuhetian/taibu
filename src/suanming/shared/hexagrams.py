from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Trigram:
    key: tuple[int, int, int]
    name: str
    nature: str
    element: str
    direction: str
    number: int


TRIGRAMS: tuple[Trigram, ...] = (
    Trigram((1, 1, 1), "乾", "天", "金", "西北", 1),
    Trigram((1, 1, 0), "兑", "泽", "金", "西", 2),
    Trigram((1, 0, 1), "离", "火", "火", "南", 3),
    Trigram((1, 0, 0), "震", "雷", "木", "东", 4),
    Trigram((0, 1, 1), "巽", "风", "木", "东南", 5),
    Trigram((0, 1, 0), "坎", "水", "水", "北", 6),
    Trigram((0, 0, 1), "艮", "山", "土", "东北", 7),
    Trigram((0, 0, 0), "坤", "地", "土", "西南", 8),
)
TRIGRAM_BY_KEY = {item.key: item for item in TRIGRAMS}
TRIGRAM_BY_NUMBER = {item.number: item for item in TRIGRAMS}
TRIGRAM_BY_NAME = {item.name: item for item in TRIGRAMS}

# Rows are upper trigram, columns are lower trigram, both in the TRIGRAMS order.
HEXAGRAM_MATRIX: tuple[tuple[tuple[int, str], ...], ...] = (
    (
        (1, "乾为天"),
        (10, "天泽履"),
        (13, "天火同人"),
        (25, "天雷无妄"),
        (44, "天风姤"),
        (6, "天水讼"),
        (33, "天山遁"),
        (12, "天地否"),
    ),
    (
        (43, "泽天夬"),
        (58, "兑为泽"),
        (49, "泽火革"),
        (17, "泽雷随"),
        (28, "泽风大过"),
        (47, "泽水困"),
        (31, "泽山咸"),
        (45, "泽地萃"),
    ),
    (
        (14, "火天大有"),
        (38, "火泽睽"),
        (30, "离为火"),
        (21, "火雷噬嗑"),
        (50, "火风鼎"),
        (64, "火水未济"),
        (56, "火山旅"),
        (35, "火地晋"),
    ),
    (
        (34, "雷天大壮"),
        (54, "雷泽归妹"),
        (55, "雷火丰"),
        (51, "震为雷"),
        (32, "雷风恒"),
        (40, "雷水解"),
        (62, "雷山小过"),
        (16, "雷地豫"),
    ),
    (
        (9, "风天小畜"),
        (61, "风泽中孚"),
        (37, "风火家人"),
        (42, "风雷益"),
        (57, "巽为风"),
        (59, "风水涣"),
        (53, "风山渐"),
        (20, "风地观"),
    ),
    (
        (5, "水天需"),
        (60, "水泽节"),
        (63, "水火既济"),
        (3, "水雷屯"),
        (48, "水风井"),
        (29, "坎为水"),
        (39, "水山蹇"),
        (8, "水地比"),
    ),
    (
        (26, "山天大畜"),
        (41, "山泽损"),
        (22, "山火贲"),
        (27, "山雷颐"),
        (18, "山风蛊"),
        (4, "山水蒙"),
        (52, "艮为山"),
        (23, "山地剥"),
    ),
    (
        (11, "地天泰"),
        (19, "地泽临"),
        (36, "地火明夷"),
        (24, "地雷复"),
        (46, "地风升"),
        (7, "地水师"),
        (15, "地山谦"),
        (2, "坤为地"),
    ),
)

HEXAGRAM_THEMES: dict[int, tuple[str, ...]] = {
    1: ("创造", "主动", "刚健"),
    2: ("承载", "包容", "顺势"),
    3: ("起步艰难", "组织", "耐心"),
    4: ("启蒙", "求教", "建立规则"),
    5: ("等待", "准备", "信任时机"),
    6: ("争议", "边界", "慎讼"),
    7: ("纪律", "组织", "带领"),
    8: ("联合", "亲近", "选择伙伴"),
    11: ("通泰", "交流", "上下相应"),
    12: ("闭塞", "保存实力", "等待转换"),
    24: ("复归", "重新开始", "周期"),
    29: ("险中求通", "反复考验", "守正"),
    30: ("明辨", "依附", "持续照见"),
    63: ("已成", "守成", "防微杜渐"),
    64: ("未成", "谨慎收尾", "继续推进"),
}


@dataclass(frozen=True, slots=True)
class Hexagram:
    number: int
    name: str
    lines: tuple[int, int, int, int, int, int]
    lower: Trigram
    upper: Trigram
    themes: tuple[str, ...]


def _trigram_index(trigram: Trigram) -> int:
    return TRIGRAMS.index(trigram)


def hexagram_from_lines(lines: tuple[int, ...] | list[int]) -> Hexagram:
    normalized = tuple(1 if int(line) else 0 for line in lines)
    if len(normalized) != 6:
        raise ValueError("卦象必须包含六爻。")
    lower = TRIGRAM_BY_KEY[normalized[:3]]
    upper = TRIGRAM_BY_KEY[normalized[3:]]
    number, name = HEXAGRAM_MATRIX[_trigram_index(upper)][_trigram_index(lower)]
    themes = HEXAGRAM_THEMES.get(
        number,
        (upper.nature, lower.nature, "审时度势"),
    )
    return Hexagram(
        number=number,
        name=name,
        lines=normalized,
        lower=lower,
        upper=upper,
        themes=themes,
    )


def hexagram_from_trigrams(upper: Trigram, lower: Trigram) -> Hexagram:
    return hexagram_from_lines((*lower.key, *upper.key))


def changed_hexagram(hexagram: Hexagram, moving_lines: list[int]) -> Hexagram:
    lines = list(hexagram.lines)
    for line_number in moving_lines:
        if not 1 <= line_number <= 6:
            raise ValueError("动爻编号必须在 1..6。")
        lines[line_number - 1] = 1 - lines[line_number - 1]
    return hexagram_from_lines(lines)


def mutual_hexagram(hexagram: Hexagram) -> Hexagram:
    lines = hexagram.lines
    return hexagram_from_lines((lines[1], lines[2], lines[3], lines[2], lines[3], lines[4]))


def opposite_hexagram(hexagram: Hexagram) -> Hexagram:
    return hexagram_from_lines(tuple(1 - line for line in hexagram.lines))


def reversed_hexagram(hexagram: Hexagram) -> Hexagram:
    return hexagram_from_lines(tuple(reversed(hexagram.lines)))


def trigram_relation(body: Trigram, use: Trigram) -> str:
    generates = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
    controls = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}
    if body.element == use.element:
        return "比和"
    if generates[body.element] == use.element:
        return "体生用"
    if generates[use.element] == body.element:
        return "用生体"
    if controls[body.element] == use.element:
        return "体克用"
    return "用克体"


def hexagram_dict(hexagram: Hexagram) -> dict[str, object]:
    return {
        "number": hexagram.number,
        "name": hexagram.name,
        "lines": list(hexagram.lines),
        "binary_top_down": "".join(str(line) for line in reversed(hexagram.lines)),
        "lower_trigram": {
            "name": hexagram.lower.name,
            "nature": hexagram.lower.nature,
            "element": hexagram.lower.element,
            "direction": hexagram.lower.direction,
        },
        "upper_trigram": {
            "name": hexagram.upper.name,
            "nature": hexagram.upper.nature,
            "element": hexagram.upper.element,
            "direction": hexagram.upper.direction,
        },
        "themes": list(hexagram.themes),
    }

