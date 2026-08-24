# App Store / Google Play 非国区工具榜扫描

定期抓取 10 个区域（美/英/德/法/日/韩/港/台/新/泰）的 **iOS App Store** 与
**Google Play** 工具类免费/付费/畅销榜，AI 分析每个上榜 App 的功能与类型分布，
产出中文报告。设计文档见 `docs/superpowers/specs/`。

平台可拔插：抓取层为 `fetch/adapters/` 下的适配器（ios / play），
新增平台只需实现 `fetch_chart`/`fetch_details` 并注册。

## 使用

    # 手动扫描（默认 ios，standard 档）
    /app-scan
    # Google Play 扫描
    /app-scan play
    # 快速扫榜 / 深度研究
    /app-scan [ios|play] light
    /app-scan [ios|play] deep
    # 强制重抓当天数据
    /app-scan [ios|play] --refresh

只抓数据不分析：

    python3 -m fetch.charts --platform ios|play|all [--date YYYY-MM-DD] [--refresh]

Play 首次使用：`npm install`（需 node；运行时需代理可访问 play.google.com）。

## 定时任务

    scripts/install_launchd.sh install ios     # 每周一 09:30
    scripts/install_launchd.sh install play    # 每周一 09:50
    scripts/install_launchd.sh verify [ios|play]
    scripts/install_launchd.sh uninstall [ios|play]

## 配置

`config.json`：顶层 `regions`/`charts`/`top_n` 为公共默认；
`"ios"`/`"play"` 子字典按平台覆盖（如 `{"play": {"top_n": 50, "detail_top_n": 150}}`）。

## 目录

- `data/{日期}/{平台}/`：原始榜单（raw/）、合并清单（apps.json）、运行元信息（meta.json）
- `reports/`：中文分析报告（`{日期}-工具榜分析-{平台}.md`）
- `logs/`：定时任务日志
- `fetch/`：抓取框架（core 编排 + adapters 平台适配器）
- `scripts/play_bridge.mjs`：Play 数据源桥（google-play-scraper）

> 2026-08-24 前的旧 iOS 数据在 `data/{日期}/apps.json`，如需纳入新布局可执行：
> `mkdir -p data/{日期}/ios && mv data/{日期}/apps.json data/{日期}/meta.json data/{日期}/raw data/{日期}/ios/`

## 测试

    python3 -m unittest discover tests -v
