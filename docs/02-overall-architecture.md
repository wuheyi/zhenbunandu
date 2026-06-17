# 整体架构设计

本文描述《朕不南渡》的系统架构。目标是参考当前项目已经跑通的“FastAPI + React + SQLite + 内容文件 + LLM Agent 推演链”，但让新题材拥有自己的核心模型：汴京围城、勤王响应、金宋外交和殿前对质。

## 架构目标

- 单机本地运行，玩家自填 OpenAI-compatible API key。
- 所有历史内容、人物、军队、事件、地区、提示词尽量数据驱动。
- LLM 负责对话、叙事、推演解释；规则层负责账本、状态、边界和持久化。
- 自然语言旨意能转成结构化效果，并能被玩家复盘。
- 支持长期记忆：人物记得玩家提拔、冤枉、清算、承诺过什么。
- 支持短局高压：默认 12-24 个核心回合即可出现一个结局。

## 参考当前项目的模块映射

| 当前项目能力 | 《朕不南渡》对应设计 |
| --- | --- |
| 月度回合 | 旬/月混合。首发建议一回合半月或一月，围城阶段可切成旬。 |
| 奏报 | 朝报、边报、城防报、粮价报、密奏。 |
| 大臣召见 | 召见宰执、台谏、将领、开封府、皇城司、转运使、太学生代表。 |
| 诏书草案 | 圣旨、手诏、御前处分、密札、军令、榜文。 |
| 月末推演 | 朝报回奏 + 战线变化 + 城中舆情 + 金营动向。 |
| 事项 issues | 守汴京、整禁军、追军饷、保太原、催勤王、主和派逼宫等进度条。 |
| 密令 | 皇城司暗查、边臣密奏、金营反间、账册搜检、城门内应排查。 |
| 记忆 | 大臣承诺、被清算者余党、军队旧恩怨、地区旧账。 |
| 地区 | 汴京、京畿、河北、河东、陕西、淮南、江南等。 |
| 军队 | 禁军、西军、河北军、河东军、勤王军、民壮、金军诸路。 |
| 外部势力 | 金国、西夏、辽残余、地方豪强、可能的傀儡政权。 |

## 运行时分层

```text
Web UI
  ↓
API 层
  ↓
GameSession
  ↓
领域模块：朝堂 / 财政 / 地区 / 军队 / 围城 / 外交 / 事项 / 记忆
  ↓
SQLite GameDB
  ↓
content/*.json + prompts/*.md
```

### Web UI

负责展示：

- 主界面汴京与北方舆图。
- 奏报列表、邸报、战报、密奏。
- 朝臣席位与召见面板。
- 诏令编辑器。
- 围城状态、勤王路线、金军压力。
- 殿前对质模式。
- 历史回顾和存档。

UI 不直接改核心状态，只调用 API。

### API 层

建议接口类型：

- `/api/menu/*`：新局、继续、存档、配置。
- `/api/game/state`：当前盘面。
- `/api/court/*`：人物、召见、朝议、殿前对质。
- `/api/directives/*`：草案、确认、驳回、拟旨。
- `/api/decree/*`：颁诏、流式结算、决策点处理。
- `/api/intel/*`：密令、证据、线索。
- `/api/siege/*`：汴京围城细节。
- `/api/history/*`：回合档案、战报、旧记忆。
- `/api/admin/*`：开发调试。

### GameSession

GameSession 是运行时中枢：

- 保存当前局 DB 路径与 LLM 配置。
- 管理召见缓存、朝议状态、待处理决策点。
- 接收自然语言输入，调用角色 agent。
- 把工具调用哨兵转为数据库操作。
- 颁诏时组织 simulator/extractor/memory 流程。
- 控制回合推进、阶段切换和结局判断。

建议阶段：

```text
menu
month_begin
audience
decree_drafting
resolution
decision_pause
month_end
ended
```

围城阶段可加入：

```text
siege_day
assault_resolution
negotiation_window
```

## 内容文件结构

建议新项目内容目录：

```text
content/
  characters.json
  offices.json
  factions.json
  regions.json
  armies.json
  external_powers.json
  events.json
  issue_templates.json
  directive_templates.json
  siege_actions.json
  opening_dream.md
  opening_court_report.md
  historical_anchors.json
  prompts/
    game_world.md
    minister_agent.md
    court_debate_agent.md
    decree_writer.md
    resolution_simulator.md
    score_extractor.md
    memory_extractor.md
    intel_agent.md
    confrontation_agent.md
```

设计原则：

- 人物、地区、军队、派系、事件不在代码里硬编码。
- 历史锚点只负责施压，不强制历史必然发生。
- 每条事件要有“可调查线索”和“可执行方案”，避免纯文本播报。
- 每个主要人物要有至少一个可被玩家改变的命运节点。

## 数据库模块

建议表按领域拆分。以下是首发需要的核心表。

### 全局状态

| 表 | 作用 |
| --- | --- |
| `game_state` | 年月、回合、阶段、剧本、结局状态 |
| `metrics` | 国库、内帑、民心、君威、京城粮储、战意等全局值 |
| `kv_store` | 版本号、设置、运行时元数据 |

### 朝堂

| 表 | 作用 |
| --- | --- |
| `characters` | 人物全档、属性、官职、状态、派系 |
| `offices` | 官职权限、职责、可用工具 |
| `factions` | 主战、主和、旧党、宦官军功集团、边臣等 |
| `appointments` | 任免记录 |
| `court_cases` | 殿前对质案件 |
| `evidence_items` | 证据、账册、密奏、证词 |

### 财政与地区

| 表 | 作用 |
| --- | --- |
| `economy_accounts` | 国库、内帑、军资库 |
| `economy_ledger` | 收支流水 |
| `regions` | 汴京、京畿、河北、河东等地区状态 |
| `logistics_routes` | 汴河、驿路、粮道、勤王路线 |
| `population_groups` | 京城士民、禁军家属、商户、流民、太学生等 |

### 军事与围城

| 表 | 作用 |
| --- | --- |
| `armies` | 禁军、西军、金军诸路、勤王军 |
| `army_logs` | 军队变更 |
| `siege_state` | 汴京城防、城门风险、粮储、水源、火患、降议压力 |
| `city_gates` | 各城门/城段状态 |
| `campaigns` | 河东、河北、汴京外围战役 |

### 事件、事项、记忆

| 表 | 作用 |
| --- | --- |
| `events` | 事件定义与触发 |
| `event_triggers` | 已触发记录 |
| `issues` | 进行中的改革/危机/战线 |
| `issue_advances` | 事项推进日志 |
| `secret_orders` | 密令 |
| `event_memories` | 结构化记忆 |
| `turn_reports` | 每回合正式朝报/战报 |
| `turn_extractions` | LLM 推演输入输出留档 |
| `turn_directives` | 草案、圣旨、军令 |

## LLM Agent 分工

### minister_agent

用于单个大臣召见。输入人物档案、官职权限、本月简报、相关记忆。输出符合人物立场的奏对，可调用工具：

- 建议任免。
- 请求密查。
- 提供证词。
- 拟草案。
- 回忆旧事。

### court_debate_agent

用于多人朝议。让主战、主和、财政、军方、台谏互相交锋。重点是暴露矛盾，而不是给唯一答案。

### intel_agent

用于密令推进和线索分析。负责把“查禁军欠饷”变成若干证据、嫌疑人和风险。

### confrontation_agent

用于殿前对质。根据证据、人物性格、派系压力生成辩解、反咬、认罪、攀咬等戏剧过程。

### decree_writer

把玩家确认的行动草案写成宋代风格但清晰可执行的圣旨或军令。

### resolution_simulator

月末推演。接收：

- 当前盘面。
- 本月旨意。
- 相关记忆。
- 密令。
- 历史锚点。
- 主要事项状态。

输出叙事回奏。

### score_extractor

把推演结果抽取为结构化 JSON：

- 指标变化。
- 地区变化。
- 军队变化。
- 围城变化。
- 派系变化。
- 人物状态变化。
- 新事件与新事项。
- 证据和记忆。

规则层只应用通过 schema 校验的字段。

### memory_extractor

从本月召见、对质、颁诏、战报里抽取记忆卡，让人物和世界记住玩家。

## 回合结算管线

```text
1. 回合初：加载历史锚点、阈值事件、密令进展
2. 奏报：生成本月关键问题
3. 召见：玩家询问、试探、许诺、威胁、下令
4. 密令：暗查线索，积累证据
5. 草案：自然语言行动转为结构化草案
6. 拟旨：decree_writer 生成正式圣旨
7. 推演：resolution_simulator 叙事结算
8. 抽取：score_extractor 输出结构化变化
9. 应用：规则层落库、写流水、推进事项
10. 记忆：写人物/地区/派系/军队记忆
11. 报告：生成朝报、战报、下一月奏报
12. 判定：进入下一回合或结局
```

## 确定性规则与 LLM 的边界

LLM 可以：

- 解释为什么执行偏差发生。
- 生成大臣对话与战报。
- 在合理范围内提出新线索和新危机。
- 判断人物是否推诿、狡辩、认罪、反扑。

LLM 不应直接：

- 无限制改钱粮。
- 杀死或新增关键人物而无事件依据。
- 改写历史锚点而不经过玩家行动。
- 让一个没有证据的清算自动成功。
- 把失败行动包装成纯胜利。

规则层必须：

- 对数值变化做上下限钳制。
- 对钱粮和粮食走账本。
- 对人物状态变化写记录。
- 对城防、军队、地区变化保留日志。
- 对结局条件做明确判断。

## 可复用代码策略

如果从当前项目 fork：

第一阶段应复用：

- LLM 配置与运行时配置。
- SQLite Mixin 拆分方式。
- `GameSession` 大体流程。
- 召见、草案、拟旨、流式结算。
- `issues`、`secret_orders`、`event_memories` 的设计。
- 前端存档、菜单、配置、流式事件处理。

第一阶段应重写：

- `content/*` 全部题材数据。
- 地区、军队、外部势力初始盘面。
- 提示词。
- UI 视觉与主面板布局。
- 新增 `siege_state`、`court_cases`、`evidence_items`。

不建议首发就做：

- 全国超大地图。
- 复杂战棋。
- 多朝代剧本。
- 深度经济产业链。
- 联机或排行榜。

先把“靖康高压短局 + 清算爽点 + 汴京围城”打磨到足够锐利。
