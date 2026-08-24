# Google Play 多区域榜单检索 — 设计文档

**日期:** 2026-08-24
**状态:** 已确认
**前置:** 《App Store 非国区工具榜扫描工作流》(2026-08-22)已完成并线上运行

## 1. 背景与目标

现有系统抓取 App Store(iOS)10 区域工具榜并 AI 分析生成中文报告。本设计将抓取层改造为**可拔插的平台适配器架构**,新增 Google Play(Android)适配器,分析层与调度层复用。

**核心原则(用户确认):**

1. 能复用的必须复用——合并去重、落盘、复用判断、AI 分析、调度全部平台无关
2. 数据来源不同,后续分析相同——靠统一数据契约实现
3. 可拔插——未来新增平台(如 Amazon Appstore)只需一个 adapter 文件 + 注册一行

## 2. 数据源结论(已调研)

Google Play **无官方榜单 API**。采用 Python 库 `google-play-scraper`(v1.2.7, MIT, 库自身零外部依赖):

- `top(collection, category, num, country, lang)` → TOP_FREE / TOP_PAID / TOP_GROSSING × 分类 × 区域
- `app(appId, country, lang)` → 详情:installs/realInstalls/score/ratings/histogram/offersIAP/inAppProductPrice/containsAds/released/updated/version/description 等(比 iTunes lookup 丰富)
- `reviews(appId, lang, country, sort, count)` → 评论(deep 分析直接用,无需 WebFetch)
- 风险:逆向 Google 内部接口,可能失效。缓解:版本 pin;库有每日 e2e CI 跟进接口变更;失败降级不影响 iOS。

**打破旧约束:** 原系统"仅标准库"约束在 Play 适配器范围内解除,新增 `requirements.txt`(`google-play-scraper==1.2.7`)。iOS 适配器保持纯标准库不受影响。

## 3. 架构

```
fetch/
├── __init__.py
├── core.py          # 平台无关:merge_apps/best_rank_key/run()编排/落盘/复用/跳过记录
├── adapters/
│   ├── __init__.py  # 注册表 {"ios": IosAdapter, "play": PlayAdapter}
│   ├── ios.py       # parse_rss/filter_utilities/parse_lookup/chunk_ids/http_get(自现 fetch_charts.py 迁入)
│   └── play.py      # google-play-scraper 封装(运行时 import)
└── charts.py        # CLI 入口:python3 -m fetch.charts

fetch_charts.py      # 根目录薄转发入口(向后兼容)
requirements.txt     # google-play-scraper==1.2.7
```

### 3.1 适配器接口

```python
class PlatformAdapter:
    name: str                       # "ios" / "play"
    charts: dict                    # {"free":..., "paid":..., "grossing":...}
    request_interval: float         # 请求间隔秒数

    def fetch_chart(cc: str, chart: str, top_n: int) -> list[dict] | None
        # 返回 [{track_id, name, artist, genre_id, rank}];失败返回 None → 记入 skipped

    def fetch_details(ids: list[str], cc: str) -> dict[str, dict]
        # 返回 {track_id: {统一 details 结构}};单 id 失败容忍(缺该 id 即可)

    def needs_genre_filter() -> bool
        # ios: True(畅销榜可能忽略 genre 参数,客户端过滤);play: False
```

core.run() 消费适配器:遍历 regions × charts 调 fetch_chart → (可选 genre 过滤) → merge → 对排名前 detail_top_n 逐个/批量补详情 → 落盘。逻辑即现有 run() 的泛化。

### 3.2 适配器差异对照

| 维度 | iOS(重构迁入) | Play(新增) |
|---|---|---|
| 榜单 | iTunes RSS `genre=6002` | `top(category="TOOLS")` |
| 详情 | lookup 批量 200/请求 | `app()` 逐个,间隔 1s |
| genre 过滤 | 客户端过滤(防御) | 不需要 |
| 依赖 | 纯标准库 | google-play-scraper |
| 语言 | storefront 本地化 | lang 固定 en(title 随 country 本地化) |

## 4. 统一数据契约

`apps.json` 元素**保持现有字段名不变**(分析层零改动复用):

```jsonc
{
  "track_id": "com.example.app",     // Play 用包名
  "name": "...", "artist": "...",
  "ranks": {"us": {"free": 3}}, "regions": ["us"],
  "best_chart": "free", "best_rank": 3,
  "details": {
    // 公共字段(iOS/Play 同名,Play 映射来源)
    "name": "title", "developer": "developer",
    "description": "description",
    "genres": ["Tools"],              // Play: [genre] + categories[].name
    "price": "Free",                  // free→"Free";付费→"{currency} {price}"
    "rating": "score", "rating_count": "ratings",
    "release_date": "released", "track_view_url": "url",
    // Play 新增键(iOS 无则缺省):
    "installs": "100,000+", "min_installs": 100000,
    "offers_iap": true, "iap_price": "$0.99 - $99.99",
    "contains_ads": true, "updated": 1654116395
  }
}
```

`meta.json` 新增 `"platform": "ios|play"` 与 `"detail_top_n"` 字段,其余(skipped/all_failed/app_count 等)不变。

## 5. 数据布局与兼容

```
data/{日期}/{platform}/apps.json + meta.json + raw/
```

- 旧 iOS 数据 `data/{日期}/apps.json` 不自动迁移;README 提供一次性迁移命令(`mv data/{日期}/apps.json data/{日期}/ios/` 等)。未迁移的旧数据仅不被新代码识别(同日重跑 iOS 会重抓),无其他影响
- 旧报告 `reports/{日期}-工具榜分析.md` 不动;新报告统一 `reports/{日期}-工具榜分析-{platform}.md`

## 6. Play 适配器设计细节

- **charts 映射**:free→TOP_FREE,paid→TOP_PAID,grossing→TOP_GROSSING;分类 TOOLS(确切常量名与 category 写法列入冒烟验证)
- **详情分层**:`top()` 自带字段(title/developer/score/price/genre 等)直接构成基础记录;合并去重后仅对**最佳排名前 `detail_top_n`(默认 150)名**逐个 `app()` 拉完整详情,间隔 1 秒,单个失败跳过不中断。iOS 侧 `detail_top_n` 默认不限制(lookup 批量请求,全量拉取成本低,保持现状)
- **未安装依赖**:import 失败时输出明确提示(`pip install -r requirements.txt`)并以退出码 2 结束;iOS 流程完全不受影响
- **限流防御**:沿用重试 2 次/间隔 5 秒模式(包装库调用);30 榜请求间隔默认 3 秒,与 iOS 一致

## 7. CLI 与配置

```jsonc
// config.json —— 顶层旧键照常工作,作为公共默认;平台键可选覆盖
{
  "regions": ["us","gb","de","fr","jp","kr","hk","tw","sg","th"],
  "charts": ["free","paid","grossing"],
  "top_n": 50,
  "play": { "top_n": 50, "detail_top_n": 150 }   // 可选
}
```

```bash
python3 -m fetch.charts --platform ios|play|all [--date YYYY-MM-DD] [--refresh] [--config PATH]
# --platform 默认 ios(向后兼容);all = 顺序执行两平台,任一 all_failed 则退出码 1
```

## 8. 分析层(SKILL.md 参数化)

- 用法:`/app-scan [ios|play] [light|standard|deep] [--refresh]`,默认 ios(向后兼容)
- 取数:`data/{日期}/{platform}/apps.json` 不存在或 --refresh 时,先 `python3 -m fetch.charts --platform {platform} [--refresh]`
- 五节报告结构、赛道归类、详析格式、light 300 行限制等全部复用
- Play 增强:
  - 详析变现维度加入下载数量级(`installs`)、内购(`offers_iap`/`iap_price`)、广告(`contains_ads`)
  - deep 模式评论改用 `python3 -c "from google_play_scraper import reviews..."` 直接拉最新约 100 条(Sort.NEWEST),不依赖 WebFetch(iOS deep 仍用 WebFetch)
- 执行摘要最后输出(沿用现有 3-5 句)

## 9. 调度(launchd)

`install_launchd.sh` 参数化: `install|uninstall|verify [ios|play]`,两个独立 LaunchAgent(失败隔离):

- `com.appcharts.scan.ios` — 每周一 09:30(自动迁移现有 `com.appcharts.scan`)
- `com.appcharts.scan.play` — 每周一 09:50(错开 20 分钟,避免同时请求)

安装脚本 install 时若发现旧 label 已加载,先 unload 并删除旧 plist。

## 10. 测试策略

- **迁移现有测试**(20 个):`parse_rss`/`filter_utilities`/`parse_lookup`/`http_get` → `tests/test_adapter_ios.py`(改 import 路径,断言不变);`merge_apps`/`best_rank_key`/`run`/`main` → `tests/test_core.py`,run 测试改为注入 fake adapter(不再 mock opener 链)
- **Play 新增测试**(fixture 用调研到的真实响应结构浓缩):
  - `top()` 返回 → 统一契约字段映射(含 price 格式化、Play 新增键)
  - 未安装依赖时的降级(mock import 失败)
  - fetch_chart 单榜单失败 → skipped 记录
- **冒烟验证**(手动,不进自动测试):Play us 区 3 榜 top 10 + 前 10 名详情,确认三点:① top() 的 num 上限/分页行为;② TOOLS 分类常量写法;③ top() 实际返回字段集

## 11. 实施顺序概要

1. 目录重构:fetch/ 包建立,现有代码迁入 core + ios 适配器,测试迁移,全绿(行为不变)
2. core.run 泛化(注入 adapter,detail_top_n)
3. Play 适配器 + 依赖文件 + 测试
4. Play 真实冒烟(验证 §10 三点)
5. SKILL.md 参数化 + Play 报告验收
6. launchd 参数化与迁移安装
7. README 更新与全量验收
