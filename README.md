# Suanming Kernel

一个从零实现、运行时离线、面向 JSON 的可扩展命理与象征性预测内核。

当前 `0.1.0` 已完成“门类全覆盖”的第一版：26 条可执行管线、统一
Pydantic 契约、可复现随机、自动发现、完整 JSON Schema、47 项测试，
以及 17 个带 SHA-256 校验的原创视觉文件。没有搬运参考仓库的代码、
规则表或图片。

> 所有结果用于传统文化研究、自我反思与娱乐，不构成医疗、法律、财务、
> 心理诊断、关系或其他高影响决策建议。

## 快速开始

需要 Python 3.12 和 [uv](https://docs.astral.sh/uv/)：

```powershell
uv sync --all-groups
uv run suanming list --pretty
uv run suanming schema bazi --kind input --pretty
uv run pytest
```

执行管线：

```powershell
uv run suanming run tarot --seed demo `
  --input '{"spread":"three_card","question":"近期项目怎样推进？"}' `
  --pretty
```

也可从 stdin 或 UTF-8 文件读取 JSON：

```powershell
'{"datetime":"1990-05-15T15:30:00","timezone":"Asia/Shanghai"}' |
  uv run suanming run bazi --pretty

uv run suanming run ziwei --input '@examples/ziwei.json' --pretty
```

成功时 stdout 只含 JSON；错误写入 stderr 并返回非零退出码。随机管线可用
`--seed` 完整复现。不传种子时，每次生成安全随机种子，并在结果信封中返回。

## 管线

主要门类包括：

- 中国命盘：八字、八字大运、四柱反查、紫微、紫微运限、紫微飞星
- 三式与时占：奇门遁甲、大六壬、太乙神数、小六壬
- 易学占测：六爻、梅花易数、黄历、日月运势
- 西方与卡牌：西方占星、塔罗、数字命理
- 关系与观察：关系合盘、面相类象、手相类象、MBTI 偏好量表、梦象解析
- 原创内容签库：观音慈照签、天师法度签、祖师百工签、吕祖心剑签

完整输入、算法边界与规则版本见
[管线目录](docs/PIPELINES.md)。可直接运行 `suanming schema <id>` 获取机器可读
输入/输出 Schema。

## 设计目标

- **内核优先**：没有 Web、数据库、账号、MCP 或 LLM 依赖。
- **完全自包含**：历法级数、干支、六十四卦、78 张塔罗数据、签库和图片随包分发。
- **可解释**：输出结构化中间量、规则版本、警告和方法说明，不只返回一句断语。
- **可扩展**：新增算法管线无需修改 CLI；新增内容签库只需一份 JSON。
- **可复现**：确定性管线固定输出；随机管线以 SHA-256 派生 RNG。
- **诚实分层**：复杂术数先实现明确命名的基础规则集，不把某一门派包装成唯一标准。

整体布局与扩展教程见
[架构文档](docs/ARCHITECTURE.md)，视觉规则见
[视觉系统](docs/VISUAL_STYLE.md)。

## 素材

所有位图都通过 imagegen 为本项目重新生成。统一母风格为“天象档案”：
靛黑手工纸、矿物色、旧金线、朱砂与青玉点色；不同管线使用不同的核心构图，
例如四柱竖向石版、奇门九宫格、六爻六层线、紫微十二宫环和塔罗叙事卡片。

```powershell
uv run suanming assets --pretty
uv run suanming assets --verify --pretty
```

清单、原始提示词和校验值均在 `assets/` 内。素材会被打入 wheel，安装后仍可离线读取。

## Python 调用

```python
from suanming.runtime import run_pipeline

envelope = run_pipeline(
    "meihua",
    {"method": "two_numbers", "numbers": [17, 29]},
    seed="example",
)
print(envelope.model_dump(mode="json"))
```

未来网页或服务层只需调用 `run_pipeline()`，无需改变内核。

## 项目状态

`0.1.0` 是完整门类的基础版，不等于穷尽所有门派细则。紫微杂曜/旺陷、
大六壬全部特殊课体、太乙其他纪元、精密天文星历和完整逐张塔罗插画，适合在
兼容现有 JSON 契约的 `0.x` 版本继续加深。当前每个已列管线都可执行、可校验、
可序列化，不存在仅占位的算法模块。

发布前请由仓库所有者选择许可证；当前未替用户预设开源许可。
