# App Store 非国区工具榜扫描

定期抓取 10 个区域（美/英/德/法/日/韩/港/台/新/泰）的 App Store
工具类免费/付费/畅销榜，AI 分析每个上榜 App 的功能与类型分布，
产出中文报告。设计文档见 `docs/superpowers/specs/`。

## 使用

    # 手动扫描（默认 standard 档）
    /app-scan
    # 快速扫榜 / 深度研究
    /app-scan light
    /app-scan deep
    # 强制重抓当天数据
    /app-scan --refresh

只抓数据不分析：`python3 fetch_charts.py [--date YYYY-MM-DD] [--refresh]`

## 定时任务

    scripts/install_launchd.sh install    # 安装（每周一 09:30）
    scripts/install_launchd.sh verify     # 检查任务与 claude 可用性
    scripts/install_launchd.sh uninstall  # 卸载

已在 macOS 上完成端到端验证（launchctl start 手动触发：
抓取 30 榜 → 去重 804 app → 生成当日分析报告）。

## 配置

`config.json`：`regions`（区域码）、`charts`（free/paid/grossing）、`top_n`。

## 目录

- `data/{日期}/`：原始 RSS（raw/）、合并清单（apps.json）、运行元信息（meta.json）
- `reports/`：中文分析报告
- `logs/`：定时任务日志

## 测试

    python3 -m unittest discover tests -v
