---
name: app-scan
description: 扫描 App Store(iOS)或 Google Play(Android)非国区工具榜并生成中文分析报告。用法:/app-scan [ios|play] [light|standard|deep] [--refresh]。默认 ios。触发词:扫榜、工具榜分析、app榜单。
---

# App Store / Google Play 工具榜扫描分析

分析 `data/{今天日期 YYYY-MM-DD}/{platform}/apps.json` 中的非国区工具榜数据
(platform=ios 或 play),生成中文分析报告到 `reports/{日期}-工具榜分析-{platform}.md`。

## 参数解析

从用户输入解析:平台 `ios`(默认)/ `play`;模式 `light` / `standard`(默认)/ `deep`;`--refresh`。

## 流程

1. **取数**:若 `data/{日期}/{platform}/apps.json` 不存在或带 `--refresh`,
   先运行 `python3 -m fetch.charts --platform {platform} [--refresh]`(工作目录为项目根)。
   脚本失败(退出码非 0)→ 向用户报告错误并停止。
   play 平台依赖:需 node + 项目根已 `npm install`,且运行时需代理可访问 play.google.com。
2. **读数据**:读 `apps.json`(已按最佳排名排序)与 `meta.json`。
   `meta.json` 的 `skipped` 非空 → 报告"本期总览"须注明缺失的区域/榜单。
3. **类型分布**(所有模式):把 app 归入细分赛道(如 清理加速 / 网络VPN /
   文件管理 / 格式转换 / 效率工具 / 安全隐私 / 输入法 / 小组件壁纸 /
   扫描识别 / 测试与其他)。依据 `details.genres`、名称与描述关键词。
   统计各赛道数量与占比,指出跨区域共性赛道与区域特色赛道。
4. **分层分析**:
   - `light`:无逐个详析,全部表格化。
   - `standard`:取前 120 个逐个详析,其余表格化。
   - `deep`:取前 30 个逐个详析;评论与页面信息按下平台获取:
     - ios:用 WebFetch 抓
       `https://itunes.apple.com/{regions[0]}/rss/customerreviews/id={track_id}/sortBy=mostRecent/page=1/json`
       提炼好评/差评主题,并抓 `details.track_view_url` 补充页面信息
       (抓不到就跳过并标注"信息有限")。
     - play:用 Bash 写临时脚本 `/tmp/play_reviews.mjs` 执行后删除,
       脚本 `require('google-play-scraper').default.reviews({appId: '{track_id}',
       lang: 'en', country: '{regions[0]}', sort: 2, num: 100})`
       (cwd 为项目根以复用 node_modules;返回 {data: [{score, text, ...}]})
       逐行打印 `评分★ | 前200字评论`,据此提炼好评/差评主题;
       无需抓页面(details 已含 installs/内购/广告)。
5. **写报告**到 `reports/{日期}-工具榜分析-{platform}.md`,结构见下。
   完整榜单表格必须直接写进报告第 4 节(不要只留在中间文件)。
6. 最后向用户输出 3-5 句执行摘要(本期亮点赛道、值得注意的 app)。

## 重点 app 详析格式(standard/deep 共用)

每个 app 一小节:核心功能(2-4 条中文)/ 目标用户与场景 /
变现模式(免费、买断、订阅、内购或广告——ios 从 `details.price` 与描述推断;
play 直接看 `details.offers_iap`/`iap_price`/`contains_ads` 并引用
`details.installs` 下载量级)/ 一句点评(上榜原因或可借鉴之处)。
`details` 缺失的 app:基于名称与分类推断,并标注"信息有限"。

## 报告结构

1. **本期总览**:日期、平台、区域数、各榜 app 数、数据完整性(skipped)
2. **类型分布**:细分赛道表格(数量/占比/代表 app)+ 共性 vs 区域特色分析
3. **重点 App 分析**:按细分赛道分组逐个详析(数量按模式)
4. **完整榜单表格**:分区域 × 分榜单,列=排名/名称/开发者/评分/价格(play 加下载量)
5. **观察与机会**:3-6 条跨区域趋势观察与机会点

## 约束

- 全程中文输出;app 名称保留原文(可附中文释义)
- 报告中数字必须来自数据文件,不臆造
- light 模式整份报告控制在 300 行内
