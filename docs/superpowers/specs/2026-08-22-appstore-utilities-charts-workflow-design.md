# App Store 非国区工具榜扫描工作流 — 设计文档

日期：2026-08-22
状态：待审阅

## 1. 背景与目标

定期抓取 App Store 非中国区市场的工具类（Utilities，分类码 6002）应用榜单，
用 AI 分析每个上榜 App 的主要功能与类型分布，产出中文分析报告。
支持手动触发与定时自动运行两种方式。

**成功标准**：
- 一条命令（或定时自动）产出一份覆盖 10 个区域、3 类榜单的中文分析报告
- 抓取与分析解耦，任一层可独立修改、独立运行
- 三档分析深度可切换，默认档在合理时间内完成

## 2. 已确认的需求决策

| 决策点 | 结论 |
|--------|------|
| 区域 | 美/英/德/法/日/韩/港/台/新加坡/泰国，共 10 个（配置可增删） |
| 榜单 | 免费榜、付费榜、畅销榜，各 Top 50 |
| 分析深度 | 三档：light / standard（默认）/ deep |
| 输出 | 仅当期 Markdown 报告；原始数据按日期存档，不做跨期趋势对比 |
| 触发 | 手动 slash command + launchd 定时（每周一 09:30） |
| 技术路线 | 方案 A：Python 抓取脚本 + Claude Code skill 分析 + launchd 定时 |

## 3. 整体架构

```
┌──────────────────────────────────────────────────┐
│  fetch_charts.py（纯抓取，不依赖 AI）             │
│  10 区域 × 3 榜单 × Top 50 → 原始 JSON           │
│  → 去重合并 + lookup 补全详情 → data/{日期}/     │
└──────────────────────┬───────────────────────────┘
                       ▼
┌──────────────────────────────────────────────────┐
│  /app-scan skill（AI 分析）                       │
│  读 data/{日期}/apps.json                         │
│  → 分层分析（重点详析 + 其余表格化）              │
│  → reports/{日期}-工具榜分析.md                   │
└──────────────────────┬───────────────────────────┘
                       ▼
┌──────────────────────────────────────────────────┐
│  触发层                                           │
│  · 手动：会话内输入 /app-scan [light|standard|deep]│
│  · 定时：launchd → claude -p 无头运行             │
└──────────────────────────────────────────────────┘
```

### 目录结构

```
app榜单分析/
├── fetch_charts.py            # 抓取脚本（Python 3 标准库，免第三方依赖）
├── config.yaml                # 区域列表、TopN、默认深度等
├── tests/                     # fetch_charts.py 的单元测试 + fixture
├── data/{YYYY-MM-DD}/
│   ├── raw/                   # 各区域各榜单原始 RSS/lookup JSON
│   ├── apps.json              # 去重合并 + 详情补全后的 app 清单
│   └── meta.json              # 运行元信息（时间、成功/失败区域、条目数）
├── reports/{YYYY-MM-DD}-工具榜分析.md
├── logs/                      # 定时任务运行日志
├── scripts/install_launchd.sh # 安装/卸载 launchd 定时任务
└── .claude/skills/app-scan/SKILL.md
```

## 4. 抓取层设计（fetch_charts.py）

### 4.1 数据源

| 用途 | 端点 | 说明 |
|------|------|------|
| 免费榜 | `https://itunes.apple.com/{cc}/rss/topfreeapplications/limit={N}/genre=6002/json` | 直接支持工具分类 |
| 付费榜 | `https://itunes.apple.com/{cc}/rss/toppaidapplications/limit={N}/genre=6002/json` | 直接支持工具分类 |
| 畅销榜 | `https://itunes.apple.com/{cc}/rss/topgrossingapplications/limit={N}/genre=6002/json` | genre 支持性待实现时验证；若不支持则去掉 genre 抓全类别，客户端按 app 分类过滤出 Utilities |
| 详情补全 | `https://itunes.apple.com/lookup?id={id1,id2,...}&country={cc}` | 单次最多 200 个 id |

### 4.2 流程

1. 读取 `config.yaml`（区域列表、TopN）
2. 逐区域逐榜单请求 RSS → 存 `data/{日期}/raw/{cc}_{榜单}.json`
3. 解析合并：按 trackId 去重，记录每个 app 出现的区域与榜单排名，
   按"最佳排名"排序。最佳排名定义：免费榜名次 > 付费榜名次 > 畅销榜名次
   （即优先取免费榜最好名次；未上免费榜看付费榜，再不然看畅销榜）
4. 批量 lookup 补全：描述、评分、评论数、价格、内购标志、开发者、
   内容分级、首次发布日期。lookup 的 country 参数用该 app 首次上榜的区域，
   使描述与榜单语言一致
5. 写出 `apps.json` + `meta.json`，stdout 打印摘要

### 4.3 节流与容错

- 请求间隔 ≥ 3 秒（iTunes API 限流约 20 次/分钟）
- 单个请求失败重试 2 次（间隔 5 秒），仍失败则跳过该区域/榜单，
  记录到 `meta.json.skipped`，不中断整体
- 所有区域全部失败 → 非零退出码（供定时任务感知）
- 当天 `data/{日期}/` 已存在时默认跳过抓取（`--refresh` 强制重抓）
- `--date` 参数可指定为某天已有数据补跑分析

## 5. 分析层设计（.claude/skills/app-scan）

### 5.1 分析对象分层

去重后 app 按"最佳排名"（任一区域任一榜单的最高名次）排序，
分层控制 AI 逐个详析的数量：

| 模式 | 详析数量 | 覆盖方式 | 用途 |
|------|---------|---------|------|
| `light` | 0 | 全部表格化（名称/细分类型/一句话功能），仅类型分布统计 | 快速扫榜 |
| `standard`（默认） | Top 120 | 重点 app 详析 + 其余表格化 | 常规周报 |
| `deep` | Top 30 | 详析 + 追加抓取用户评论（customer reviews RSS）亮点与官网信息 | 选题深挖 |

### 5.2 重点 App 详析字段（standard 档）

- 核心功能（2-4 条，中文）
- 目标用户与使用场景
- 变现模式（免费/买断/订阅/内购/广告）
- 一句点评（上榜原因 / 可借鉴之处）

deep 档在此基础上追加：用户好评/差评主题（从评论 RSS 提炼）、
官网/定价页关键信息（如可获取）。

### 5.3 报告结构（reports/{YYYY-MM-DD}-工具榜分析.md）

```
1. 本期总览     —— 快照日期、区域、各榜 App 数、数据完整性说明
2. 类型分布     —— 工具类细分赛道占比（清理/网络/文件/转换/效率…）
                  跨区域共性 vs 区域特色
3. 重点 App 分析 —— 按细分类型分组，逐个详析
4. 完整榜单表格 —— 分区域 × 分榜单（排名、名称、评分、价格）
5. 观察与机会    —— 跨区域趋势、值得注意的上榜信号
```

### 5.4 skill 行为

- `/app-scan`（默认 standard）、`/app-scan light|standard|deep`
- 当天 `data/{日期}/` 不存在 → 先运行 `fetch_charts.py`；存在 → 直接复用
- `/app-scan standard --refresh` 强制重抓当天数据
- 数据缺失的 app：降级为基于名称 + 分类的推断，标注"信息有限"
- 报告开头注明 `meta.json.skipped` 中缺失的区域/榜单

## 6. 触发层设计

### 6.1 手动

在项目目录的 Claude Code 会话中输入 `/app-scan [模式]`。

### 6.2 定时（launchd）

- `scripts/install_launchd.sh` 生成并加载
  `~/Library/LaunchAgents/com.appcharts.scan.plist`
- 计划：每周一 09:30（StartCalendarInterval）
- 动作：`cd 项目目录 && claude -p "/app-scan standard"`（headless 模式），
  stdout/stderr 追加写入 `logs/{日期}.log`
- plist 中显式设置 PATH（launchd 环境 PATH 不含用户自定义路径）
- 不做自动重试；失败看日志，下次手动补跑（YAGNI）

## 7. 测试策略

- `tests/`：对解析、去重合并、畅销榜分类过滤逻辑用固定 JSON fixture
  做单元测试（`python3 -m unittest`，不请求真实 API）
- 真实 API 冒烟：手动执行一次 `fetch_charts.py --date smoke` 验证端点
  与字段假设（尤其畅销榜 genre 支持性），不写入自动测试
- 分析层（SKILL.md 提示词）通过实际运行验收，不做自动化测试

## 8. 非目标（明确不做）

- 跨期趋势对比、排名变化追踪（用户已明确不需要）
- 历史数据库、去重沉淀（数据按日期目录存档即止）
- 评论全量抓取与分析（仅 deep 档取评论亮点）
- 安卓/Google Play 榜单
- 邮件/IM 推送报告（报告落盘，自行查看）

## 9. 风险与应对

| 风险 | 应对 |
|------|------|
| 畅销榜 RSS 不支持 genre 过滤 | 已设计 fallback：抓全类别后按分类过滤 |
| iTunes 接口字段变动/下线 | 原始响应完整存档于 raw/，解析层可离线修复重跑 |
| 限流导致部分区域失败 | 重试 + 跳过记录，报告标注数据完整性 |
| launchd 环境下 claude 不可用 | plist 显式 PATH；安装脚本自检 `claude -p` 可用性 |
| standard 档分析 token 消耗大 | Top 120 详析 + 表格化的分层设计已控制；可在 config.yaml 调低 |
