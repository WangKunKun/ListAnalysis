# 品类竞品与痛点分析 — 设计文档

**日期:** 2026-08-25
**状态:** 已确认
**前置:** 《App Store 非国区工具榜扫描工作流》(2026-08-22)、《Google Play 多区域榜单检索》(2026-08-24)已完成并线上运行

## 1. 背景与目标

现有系统定期扫描双平台 10 区域工具榜,产出榜单层面的中文分析报告。榜单视角只覆盖
"上榜的头部幸存者"——单期约 600-800 个 app,某细分品类(如 PDF 扫描)在榜的只有
十几到几十个,看不到品类腰部与长尾。

本设计新增**品类级分析能力**:对任意自由描述的品类(如"PDF 扫描"、"个性化二维码
生成"),自动圈定样本、抓取评论、产出该品类的竞争格局、功能矩阵、用户痛点与机会点
报告,回答"这个行业有什么痛点值得切入"。

**核心决策(用户确认):**

| 维度 | 决定 |
|---|---|
| 样本来源 | 关键词搜索扩展 + 现有榜单数据交叉标注 |
| 痛点挖掘 | 头部 10 个 app 评论深挖(复用 deep 模式既有路径) |
| 平台 | 双平台对比(iOS + Play,一份报告) |
| 品类定义 | 自由输入,AI 生成搜索关键词 |
| 实现方案 | 确定性抓取 + AI 分析 skill(沿用现有架构) |

**职责边界:** Python 抓取层只负责"给关键词,回结构化样本",不懂品类语义;
品类归属判断、功能矩阵、痛点提炼等语义工作全部在 AI 分析层完成。

## 2. 架构

```
fetch/
├── core.py            # 不改动
├── charts.py          # 不改动
├── category.py        # 新增:品类搜索编排 + CLI(python3 -m fetch.category)
└── adapters/
    ├── ios.py         # 新增 search_apps():iTunes Search API(纯标准库)
    └── play.py        # 新增 search_apps():Node 桥 search 命令

scripts/play_bridge.mjs   # 新增 {"cmd": "search"} 命令

.claude/skills/cat-scan/SKILL.md   # 新增:品类分析 skill(/cat-scan)

data/{日期}/cat-{slug}/             # 新数据布局
    ├── {platform}.json            # 搜索样本(含 details,去重合并后)
    └── meta.json                  # 关键词、抓取时间、统计

reports/{日期}-品类分析-{slug}.md   # 报告(双平台一份)
```

### 2.1 适配器新增方法

与 `fetch_chart`/`fetch_details` 并列,保持平台可拔插模式:

```python
def search_apps(self, term: str, cc: str, limit: int,
                sleep=time.sleep) -> list[dict] | None
# 返回 [{track_id, name, artist, details?}];失败返回 None
```

- **iOS**:`https://itunes.apple.com/search?term={term}&country={cc}&entity=software&limit={limit}`
  (API 上限 200,CLI 默认 100),复用 `http_get` 重试逻辑。响应自带完整详情
  (描述/评分/评分量/价格/genres/更新时间),一次请求到位,无需再调 lookup。
  解析函数 `parse_search(text)` 独立可测。
- **Play**:桥 `play_bridge.mjs` 新增 `{"cmd": "search", "term", "num", "country"}`
  (google-play-scraper 自带 `search()`),返回 appId 列表;详情复用现有
  `{"cmd": "apps"}` 批量命令与节流(批 30/间隔 1s)。

### 2.2 CLI:`python3 -m fetch.category`

```
python3 -m fetch.category --terms "pdf scanner,document scanner,ocr scan" \
    --slug pdf-scanner --platform ios|play|all \
    [--date YYYY-MM-DD] [--country us] [--limit 100] [--refresh]
```

- `--terms`:逗号分隔英文关键词(由 skill 的 AI 生成后传入;CLI 不做语义判断)
- `--slug`:目录与报告名用标识符(由 skill 生成,如 `pdf-scanner`)
- `--country`:搜索区域,默认 `us`(品类搜索区域差异不大,默认最大市场;可覆盖)
- 编排:每关键词×平台调 `search_apps` → Play 侧补详情 → 按 track_id 合并去重
  (保留评分量最高的一条详情)→ 按 rating_count / min_installs 排序落盘
- 复用判断:已有 `{platform}.json` 且非 `--refresh` 时直接复用(同 charts 行为)
- 错误处理:单关键词失败重试后跳过(记入 meta 的 failed_terms);全部失败退出码非 0

### 2.3 数据契约

`data/{日期}/cat-{slug}/{platform}.json` 元素复用现有统一结构(track_id/name/artist
/details 字段名与 `data/{日期}/{platform}/apps.json` 一致),外加 `source_terms`
(该 app 命中了哪些关键词)便于分析层追溯。meta.json 记录 terms、country、
每关键词命中数、failed_terms、抓取时间。

榜单交叉数据不重抓、不落盘——skill 直接读最近一期的
`data/{最新日期}/{platform}/apps.json`。

## 3. Skill:`/cat-scan`

```
/cat-scan <品类自由文本> [light|standard] [--refresh]
```

五步流程:

1. **生成关键词**:AI 将品类描述翻译为 3-5 个英文搜索关键词(含功能变体,
   如 PDF 扫描 → pdf scanner / document scanner / cam scanner / ocr scan)
   与 slug(kebab-case)
2. **抓样本**:运行 `python3 -m fetch.category --terms ... --slug ... --platform all`
   (工作目录项目根;Play 需 node + 代理)。失败(退出码非 0)→ 报错停止
3. **交叉标注**:取最近一期 `data/{最新日期}/{platform}/apps.json`(当天没有往前找,
   最多回溯 7 天;都没有 → 降级纯搜索样本并注明)。AI 把榜内属于该品类的 app
   与搜索样本合并,获得"是否上榜/最好名次/区域覆盖"竞争地位维度
4. **品类归属过滤 + 头部圈定**:AI 剔除搜索噪声(语义判断,如搜"二维码生成"
   混入的扫码器/收款机),按评分量/下载量/榜单位置综合排出头部;
   standard 模式对头部 10 个抓评论——iOS 用 WebFetch 抓 customerreviews RSS、
   Play 用临时脚本走 google-play-scraper reviews(路径与 app-scan deep 完全一致);
   light 模式跳过评论。过滤后样本 < 5 → 提示关键词可能不当,建议用户调整后重试
5. **生成报告**到 `reports/{日期}-品类分析-{slug}.md`,结构见 §4;
   最后向用户输出 3-5 句执行摘要(竞争格局一句话 + 最痛的 2-3 个痛点 + 最大机会点)

评论抓取失败的 app 标"信息有限"降级,不中断流程(沿用 app-scan 约束)。

## 4. 报告结构

`reports/{日期}-品类分析-{slug}.md`,双平台一份,内部分平台章节 + 对比章节:

1. **品类概览**:品类定义、样本圈定方式(关键词、原始搜索数、过滤后数、榜单
   交叉情况)、头部玩家一句话概览
2. **竞争格局**:双平台头部矩阵表——名称/开发者/评分/评分量/下载量(Play)/
   价格/内购/广告/最近更新/榜单表现
3. **双平台生态对比**:变现模式分布差异(订阅 vs 广告)、竞争密度、头部重合度
4. **功能矩阵与差异化**:品类标配功能(人人都有→无效竞争区)vs 各家差异化卖点
   (有效区隔);从 details.description 提炼
5. **用户痛点**:差评主题提炼,每条附证据(评论摘录 + 出现频率 + 来自哪款 app),
   区分双平台痛点异同。**核心价值节**;light 模式此节基于低分 app 共性与描述推断,标注可信度较低
6. **机会点**:3-6 条产品切入建议(痛点 × 竞争空白交叉推导)
7. **完整样本表**:过滤后全部 app 一览

**约束沿用 app-scan:** 全程中文、app 名保留原文(可附中文释义)、报告数字必须来自
数据文件不臆造、light 模式整份报告 300 行内。

## 5. 测试

与现有 tests/ 风格一致(mock 注入 + fixtures):

- `test_adapter_ios.py` 增补:`parse_search` 解析(fixture 样本,含缺字段容忍)
- `test_adapter_play.py` 增补:`search_apps` 经 mock bridge 的请求/解析/失败路径
- `test_play_bridge.py` 增补:search 命令
- `test_category.py` 新增:多关键词合并去重(详情择优)、CLI 参数解析、
  落盘布局、复用判断、全部失败退出码

## 6. 非目标

- 不做历史趋势对比(多期品类快照累积后再议)
- 不做评论的情感量化统计(主题提炼即可,不上 NLP 打分)
- 不新增定时任务(品类分析按需手动触发)
- 榜单交叉只读不抓(依赖既有 app-scan 调度)
