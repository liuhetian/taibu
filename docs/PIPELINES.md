# 管线目录

当前目录共 26 条。`mode` 含义：`deterministic` 为同输入同输出；
`seeded` 为带种子抽取；`hybrid` 同时支持手工与随机；`assessment` 为问卷或
结构化观察。

| ID | 名称 | mode | 核心输入 | 当前内核 |
|---|---|---|---|---|
| `bazi` | 八字四柱 | deterministic | 出生时间、时区、可选经度 | 节气年/月界、四柱、藏干、十神、纳音、空亡、五行、支关系 |
| `bazi_dayun` | 八字大运 | deterministic | 出生时间、性别 | 阴阳顺逆、节令起运、十年干支 |
| `bazi_pillars_resolve` | 四柱反查 | deterministic | 四柱、年份范围 | 有界公历搜索、候选时辰窗口 |
| `ziwei` | 紫微斗数 | deterministic | 农历年月日、时支 | 十二宫、五行局、十四主星、基础辅曜、四化 |
| `ziwei_horoscope` | 紫微运限 | deterministic | 本命信息、目标农历时间 | 大限、流年、流月、流日、流时 |
| `ziwei_flying_star` | 紫微飞星 | deterministic | 本命信息 | 十二宫宫干飞化、落宫、自化 |
| `qimen` | 奇门遁甲 | deterministic | 时间、时区 | 阴阳遁、局数、九宫天地盘、八门、九星、八神 |
| `daliuren` | 大六壬 | deterministic | 时间、时区 | 月将加时、天地盘、四课、基础三传、十二天将 |
| `taiyi` | 太乙神数 | deterministic | 时间、日计/时计 | 阴阳遁、七十二局、太乙九星、主客将、定目 |
| `xiaoliuren` | 小六壬 | deterministic | 农历月日时数 | 三步六宫计数与落宫 |
| `liuyao` | 六爻 | hybrid | 钱币/时间/手工爻值 | 64 卦、动爻、变互错综卦、纳甲、六亲 |
| `meihua` | 梅花易数 | hybrid | 时间/数字/文字 | 先天数起卦、动爻、体用生克、应期提示 |
| `almanac` | 黄历 | deterministic | 日期、时区 | 干支、节气、建除、二十八宿、方位、十二时辰 |
| `fortune` | 日月运势 | deterministic | 出生时间、目标日期 | 流日/月十神、地支互动、透明结构指数 |
| `tarot` | 塔罗 | seeded | 牌阵、问题 | 完整 78 张、9 牌阵、正逆位、无放回抽牌 |
| `astrology` | 西方占星 | deterministic | 时间、可选经纬度 | 九天体低精度黄经、逆行、相位、上升、等宫 |
| `numerology` | 数字命理 | deterministic | 生日、可选拉丁姓名 | 生命路径、生日、态度、个人年、姓名三数 |
| `compatibility` | 关系合盘 | deterministic | 两组出生信息 | 四柱日主、地支、五行分项比较 |
| `dream` | 梦象解析 | deterministic | 梦境文字、情绪 | 离线母题匹配与反思问题 |
| `mbti` | MBTI 偏好量表 | assessment | 24 题中的至少 8 答 | 四维度计分、强度、完成度 |
| `face` | 面相类象 | assessment | 主动填写的面部形态 | 五官/天庭/地阁文化映射，不做人脸识别 |
| `palm` | 手相类象 | assessment | 主动填写的掌纹形态 | 四线与掌形文化映射，不作健康/寿命推断 |
| `guanyin_oracle` | 观音慈照签 | seeded | 问题、抽取数 | 12 则原创慈悲主题签 |
| `tianshi_oracle` | 天师法度签 | seeded | 问题、抽取数 | 12 则原创秩序主题签 |
| `patriarch_oracle` | 祖师百工签 | seeded | 问题、抽取数 | 12 则原创师承/工艺主题签 |
| `lvzu_oracle` | 吕祖心剑签 | seeded | 问题、抽取数 | 8 则原创修心/取舍主题签 |

## 明确边界

- 八字、黄历与奇门依赖紧凑太阳黄经级数，适合历法分类，不代替专业天文历书。
- 紫微输入直接采用农历数字，避免静默猜测闰月；当前未内置公历转农历。
- 紫微基础盘尚未穷尽全部杂曜、旺陷和所有门派运限。
- 大六壬已实现核心盘与基础课体；复杂涉害深浅、别责、八专等会在新规则版本补充。
- 太乙使用仓库明确的纪元锚点；不同古法纪元不得混算。
- 西方占星是离线低精度轨道模型，不用于天文观测或分钟级校时。
- 面相、手相、MBTI、梦境与签库都不具有诊断或科学预测效力。

这些限制会随每次运行写入 `warnings` 或 `method_notes`，不会只藏在文档中。
