from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CardDefinition:
    id: str
    name: str
    name_en: str
    arcana: str
    number: int
    suit: str | None
    element: str
    astrology: str | None
    upright: tuple[str, ...]
    reversed: tuple[str, ...]
    base_tone: int


MAJOR_DATA: tuple[tuple[str, str, str, str, tuple[str, ...], tuple[str, ...], int], ...] = (
    ("愚者", "The Fool", "风", "天王星", ("启程", "自由", "信任"), ("冒进", "迷失", "迟疑"), 1),
    (
        "魔术师",
        "The Magician",
        "风",
        "水星",
        ("创造", "专注", "行动"),
        ("操控", "分心", "潜能受阻"),
        1,
    ),
    (
        "女祭司",
        "The High Priestess",
        "水",
        "月亮",
        ("直觉", "静观", "隐秘"),
        ("忽视直觉", "封闭", "信息不明"),
        0,
    ),
    (
        "皇后",
        "The Empress",
        "土",
        "金星",
        ("丰盛", "滋养", "创造力"),
        ("过度付出", "依赖", "停滞"),
        1,
    ),
    (
        "皇帝",
        "The Emperor",
        "火",
        "白羊座",
        ("秩序", "责任", "领导"),
        ("僵化", "控制", "权威冲突"),
        0,
    ),
    (
        "教皇",
        "The Hierophant",
        "土",
        "金牛座",
        ("传统", "学习", "信念"),
        ("教条", "挑战传统", "价值冲突"),
        0,
    ),
    (
        "恋人",
        "The Lovers",
        "风",
        "双子座",
        ("选择", "联结", "一致"),
        ("失衡", "分离", "价值不合"),
        1,
    ),
    (
        "战车",
        "The Chariot",
        "水",
        "巨蟹座",
        ("意志", "推进", "胜利"),
        ("失控", "方向不明", "阻滞"),
        1,
    ),
    (
        "力量",
        "Strength",
        "火",
        "狮子座",
        ("勇气", "耐心", "内在力量"),
        ("自我怀疑", "冲动", "能量低落"),
        1,
    ),
    (
        "隐士",
        "The Hermit",
        "土",
        "处女座",
        ("内省", "求索", "独立"),
        ("孤立", "逃避", "拒绝指引"),
        0,
    ),
    (
        "命运之轮",
        "Wheel of Fortune",
        "火",
        "木星",
        ("转机", "周期", "机遇"),
        ("反复", "延迟", "抗拒变化"),
        1,
    ),
    ("正义", "Justice", "风", "天秤座", ("公平", "因果", "决断"), ("偏见", "失衡", "逃避责任"), 0),
    (
        "倒吊人",
        "The Hanged Man",
        "水",
        "海王星",
        ("暂停", "换位思考", "放下"),
        ("拖延", "徒劳", "不愿牺牲"),
        0,
    ),
    ("死神", "Death", "水", "天蝎座", ("结束", "蜕变", "更新"), ("抗拒结束", "停滞", "余波"), 0),
    (
        "节制",
        "Temperance",
        "火",
        "射手座",
        ("调和", "耐心", "整合"),
        ("过度", "失衡", "节奏混乱"),
        1,
    ),
    (
        "恶魔",
        "The Devil",
        "土",
        "摩羯座",
        ("束缚", "欲望", "阴影"),
        ("松绑", "觉察", "重获自主"),
        -1,
    ),
    (
        "高塔",
        "The Tower",
        "火",
        "火星",
        ("突变", "揭露", "结构瓦解"),
        ("余震", "延缓改变", "危机内化"),
        -1,
    ),
    (
        "星星",
        "The Star",
        "风",
        "水瓶座",
        ("希望", "疗愈", "愿景"),
        ("失望", "信心不足", "愿景模糊"),
        1,
    ),
    (
        "月亮",
        "The Moon",
        "水",
        "双鱼座",
        ("潜意识", "迷雾", "想象"),
        ("迷雾消散", "压抑", "误判"),
        -1,
    ),
    (
        "太阳",
        "The Sun",
        "火",
        "太阳",
        ("活力", "清晰", "成功"),
        ("短暂低落", "延迟喜悦", "过度乐观"),
        1,
    ),
    (
        "审判",
        "Judgement",
        "火",
        "冥王星",
        ("觉醒", "复盘", "召唤"),
        ("自我否定", "拒绝复盘", "迟疑"),
        0,
    ),
    ("世界", "The World", "土", "土星", ("完成", "整合", "圆满"), ("未竟", "缺口", "收尾延迟"), 1),
)

SUITS = {
    "wands": {
        "name": "权杖",
        "element": "火",
        "themes": ("行动", "热情", "创造"),
        "shadow": ("冲动", "耗散", "行动受阻"),
    },
    "cups": {
        "name": "圣杯",
        "element": "水",
        "themes": ("情感", "关系", "直觉"),
        "shadow": ("情绪失衡", "依赖", "沟通受阻"),
    },
    "swords": {
        "name": "宝剑",
        "element": "风",
        "themes": ("思考", "沟通", "决策"),
        "shadow": ("焦虑", "冲突", "判断偏差"),
    },
    "pentacles": {
        "name": "星币",
        "element": "土",
        "themes": ("资源", "现实", "积累"),
        "shadow": ("匮乏感", "停滞", "现实压力"),
    },
}
RANKS: tuple[tuple[str, str, int, tuple[str, ...], tuple[str, ...], int], ...] = (
    ("ace", "首牌", 1, ("开端", "机会"), ("机会延迟", "能量未聚"), 1),
    ("two", "二", 2, ("选择", "平衡"), ("犹豫", "失衡"), 0),
    ("three", "三", 3, ("发展", "协作"), ("配合受阻", "进展迟缓"), 1),
    ("four", "四", 4, ("稳定", "边界"), ("僵持", "基础松动"), 0),
    ("five", "五", 5, ("挑战", "调整"), ("冲突加剧", "拒绝调整"), -1),
    ("six", "六", 6, ("过渡", "支持"), ("过渡迟缓", "支持不足"), 1),
    ("seven", "七", 7, ("评估", "坚持"), ("动摇", "策略失焦"), 0),
    ("eight", "八", 8, ("推进", "熟练"), ("停顿", "重复消耗"), 1),
    ("nine", "九", 9, ("成果", "韧性"), ("疲惫", "成果不稳"), 0),
    ("ten", "十", 10, ("完成", "责任"), ("负担", "收尾困难"), 0),
    ("page", "侍从", 11, ("消息", "探索"), ("消息延误", "经验不足"), 0),
    ("knight", "骑士", 12, ("追求", "行动"), ("鲁莽", "方向偏移"), 0),
    ("queen", "王后", 13, ("成熟", "包容"), ("内耗", "界限不清"), 1),
    ("king", "国王", 14, ("掌控", "担当"), ("固执", "权责失衡"), 1),
)


def build_deck() -> tuple[CardDefinition, ...]:
    cards: list[CardDefinition] = []
    for number, data in enumerate(MAJOR_DATA):
        name, name_en, element, astrology, upright, reversed_, tone = data
        cards.append(
            CardDefinition(
                id=f"major.{number:02d}",
                name=name,
                name_en=name_en,
                arcana="major",
                number=number,
                suit=None,
                element=element,
                astrology=astrology,
                upright=upright,
                reversed=reversed_,
                base_tone=tone,
            )
        )
    for suit_id, suit in SUITS.items():
        for rank_id, rank_name, number, upright, reversed_, tone in RANKS:
            cards.append(
                CardDefinition(
                    id=f"minor.{suit_id}.{rank_id}",
                    name=f"{suit['name']}{rank_name}",
                    name_en=f"{rank_id.title()} of {suit_id.title()}",
                    arcana="minor",
                    number=number,
                    suit=suit_id,
                    element=str(suit["element"]),
                    astrology=None,
                    upright=(*suit["themes"][:2], *upright),
                    reversed=(*suit["shadow"][:2], *reversed_),
                    base_tone=tone,
                )
            )
    return tuple(cards)


DECK = build_deck()
DECK_BY_ID = {card.id: card for card in DECK}

SPREADS: dict[str, tuple[str, ...]] = {
    "single": ("核心指引",),
    "three_card": ("过去", "现在", "未来"),
    "love": ("你的状态", "对方状态", "关系基础", "阻碍", "建议"),
    "celtic_cross": (
        "现状",
        "交叉影响",
        "意识目标",
        "潜在根基",
        "近期过去",
        "近期未来",
        "自我位置",
        "外部环境",
        "希望与恐惧",
        "可能结果",
    ),
    "horseshoe": ("过去", "现在", "隐性因素", "阻碍", "环境", "建议", "结果"),
    "choice": (
        "现状",
        "选项A优势",
        "选项A代价",
        "选项A走向",
        "选项B优势",
        "选项B代价",
        "选项B走向",
    ),
    "mind_body_spirit": ("心智", "身体", "精神"),
    "situation": ("现状", "成因", "挑战", "可用资源", "建议"),
    "yes_no": ("支持因素", "核心答案", "制约因素"),
}
