# 架构与扩展

## 分层

```text
CLI / 未来 Web、MCP、移动端
              │
              ▼
runtime.py ── 统一校验、种子、时区、结果信封、素材引用
              │
              ▼
registry.py ─ 动态发现 pipelines/* 与数据签库
              │
      ┌───────┴────────┐
      ▼                ▼
算法管线包          content_oracles
pipelines/<id>         │
      │                ▼
      ▼           oracle_packs/*.json
shared/* ── 历法、干支、天文、六十四卦

assets/manifest.json ── 原创图片、提示词、SHA-256
```

`runtime.py` 是唯一推荐入口。它负责：

1. 从注册表取得管线；
2. 用管线的 Pydantic 输入模型拒绝多余字段和非法值；
3. 解析 IANA 时区与有效时间；
4. 为随机管线生成或复用种子；
5. 执行纯计算；
6. 校验输出模型；
7. 附加素材引用、规则身份、run id、警告和免责声明。

## 结果信封

每条管线都返回同一顶层形状：

```json
{
  "schema_version": "1.0",
  "pipeline": {
    "id": "tarot",
    "version": "0.1.0",
    "ruleset": "complete-deck-seeded-draw-v1",
    "mode": "seeded"
  },
  "request": {},
  "result": {},
  "assets": [],
  "reproducibility": {
    "run_id": "…",
    "seed": "…",
    "effective_datetime": "…",
    "timezone": "Asia/Shanghai",
    "locale": "zh-CN"
  },
  "warnings": [],
  "notes": [],
  "disclaimer": "…"
}
```

前端只依赖信封；每条管线自己的 `result` 由输出 Schema 描述。

## 目录职责

```text
src/suanming/
├── cli.py                 # JSON-only CLI
├── contracts.py           # Pydantic 公共契约与 Pipeline 抽象类
├── registry.py            # 包扫描、类注册、实例注册
├── runtime.py             # 统一执行入口
├── assets.py              # 素材清单定位与校验
├── shared/                # 无管线状态的公共算法
├── pipelines/
│   ├── bazi/              # 一种算法一个包
│   ├── qimen/
│   └── content_oracles/   # 数据驱动签库的通用执行器
└── oracle_packs/          # 一份 JSON 自动成为一条新签库管线
```

`shared/` 不导入任何具体管线。算法管线可以导入共享层；管线之间仅在确有
复用价值时导入公开计算函数，例如紫微运限复用紫微本命盘。

## 新增算法管线

1. 新建 `src/suanming/pipelines/<pipeline_id>/__init__.py`。
2. 定义 `Input` 与 `Output` Pydantic 模型，均使用 `extra="forbid"`。
3. 把计算写成可单测的纯函数。
4. 实现 `Pipeline.execute()`。
5. 用 `@register_pipeline` 装饰类。
6. 给 `PipelineManifest` 分配稳定 `id`、语义版本和独立 `ruleset`。
7. 在全目录烟雾测试中加入一份最小合法输入。

CLI 会自动扫描一级管线包，不需要修改命令解析器。

若同一术数存在流派差异，不要在原函数内堆隐藏开关。优先选择：

- 差异小：输入中加入有枚举约束的 `school`，并把选择写进结果；
- 规则表显著不同：提升 `ruleset` 或建立单独管线；
- 输出结构不兼容：提升管线主版本。

## 新增祖师、天师或其他内容签库

内容签库不需要 Python 文件。在 `src/suanming/oracle_packs/` 新增一份 JSON：

```json
{
  "id": "new_oracle",
  "name": "新签库",
  "version": "0.1.0",
  "ruleset": "original-new-lots-v1",
  "tradition": "cultural_inspired",
  "summary": "…",
  "asset_pack": "new-oracle-v1",
  "asset_path": "assets/packs/new-oracle/cover.png",
  "attribution": "本仓库原创内容；非传统签谱转录。",
  "lots": [
    {
      "number": 1,
      "title": "…",
      "image": "…",
      "verse": ["…", "…"],
      "polarity": "balanced",
      "themes": ["…"],
      "guidance": ["…"],
      "cautions": ["…"]
    }
  ]
}
```

启动时 `content_oracles` 会校验并注册它。签库至少 8 签，随机抽取无放回，
相同 seed 可复现。所有宗教人物相关签库必须：

- 清楚标注原创、非经典、非机构神谕；
- 不复制现存签谱；
- 不给出医疗、违法、伤害或高影响决策命令；
- 使用尊重、非戏仿的视觉和文字。

## 随机与确定性

- `deterministic`：缺省种子固定为 `deterministic`。
- `seeded`：不传种子时生成 128 位随机种子；结果中会返回。
- `hybrid`：手工输入时确定，随机起卦时使用同一 RNG。
- `assessment`：由回答决定，不把量表结果包装成诊断。

禁止直接调用模块级 `random`；所有随机性只能来自 `RunContext.rng`。

## 自包含边界

运行依赖只有 Pydantic 与 `tzdata`。天文/历法使用仓库内置紧凑级数，
不访问在线历书、LLM、数据库或第三方 API。wheel 强制包含 `assets/`，
签库 JSON 位于 Python 包内。

## 版本与验证

- 改规则表或算法：至少提升 `ruleset` 后缀或管线版本。
- 改字段但兼容：提升次版本。
- 删除/改义字段：提升主版本与 `schema_version`。
- 新图片：保存提示词，登记 SHA-256，运行 `suanming assets --verify`。
- 所有提交：运行 `uv run pytest` 与一次 wheel 安装烟雾测试。
