---
name: cat-scan
description: 对任意品类(如 PDF 扫描、二维码生成)做双平台竞品与痛点分析,产出中文报告。用法:/cat-scan <品类描述> [light|standard] [--refresh]。触发词:品类分析、竞品分析、行业痛点、品类扫描。
---

# 品类竞品与痛点分析

对指定品类做 iOS + Google Play 双平台分析:关键词搜索圈样本、榜单交叉标注、
头部 app 评论深挖,产出竞争格局/功能矩阵/用户痛点/机会点报告。
设计文档:docs/superpowers/specs/2026-08-25-category-analysis-design.md

## 参数解析

从用户输入解析:品类描述(自由文本,必填);模式 light(不抓评论)/
standard(默认,头部 10 个抓评论);--refresh(强制重抓)。

## 流程

1. **生成关键词**:把品类描述译成 3-5 个英文搜索关键词(含功能变体,
   如 PDF 扫描 → pdf scanner / document scanner / cam scanner / ocr scanner),
   并生成 kebab-case slug(如 pdf-scanner)。
2. **抓样本**(工作目录项目根):
   `python3 -m fetch.category --terms "kw1,kw2,..." --slug {slug} --platform all [--refresh]`
   - Play 超时/ECONNRESET → 网络需代理:`export PLAY_PROXY=http://127.0.0.1:7890`
     (或可用 HTTPS_PROXY)后重跑;iOS 直连无需代理。
   - 退出码非 0 → 向用户报告错误并停止。
   - 落盘:`data/{日期}/cat-{slug}/{ios|play}.json`(含 source_terms 与 details)
     与 `meta.json`(terms/country/per_term_counts/failed_terms)。
3. **交叉标注**:取最近一期 `data/{最新日期}/{ios|play}/apps.json`(当天没有
   往前找,最多回溯 7 天;没有 → 纯搜索样本并在报告注明"无榜单交叉数据")。
   把榜内属于该品类的 app 按 track_id 与搜索样本合并,标注上榜情况/最好名次/
   区域覆盖(榜单数据格式见 app-scan skill)。
4. **归属过滤与头部圈定**(语义判断,本 skill 核心职责):
   - 剔除搜索噪声:名字带关键词但不属于品类的(如"二维码生成"里的扫码器、
     收款机;PDF 工具里的阅读器/签名器按目标品类判断去留)。
   - 过滤后样本 < 5 → 告知用户样本过少、给出建议关键词,停止。
   - 头部排序:上榜优先(榜单位置),未上榜按评分量/下载量。standard 模式
     取头部 10 个抓评论:
     - ios:优先 WebFetch 抓
       `https://itunes.apple.com/us/rss/customerreviews/id={track_id}/sortBy=mostRecent/page=1/json`
       提炼好评/差评主题;WebFetch 被域安全拦截时改用
       `curl -s <同 URL>` 抓 JSON 自行提炼;两者都失败标注"信息有限"。
     - play:Bash 写临时脚本 `/tmp/play_reviews.mjs`(内容如下,一字不差)执行后
       删除,cwd 必须为项目根;需代理时命令前加
       `PLAY_PROXY=http://127.0.0.1:7890`:

       ```js
       import { createRequire } from "node:module";
       const require = createRequire(process.cwd() + "/");
       const gplay = require('google-play-scraper').default;
       const proxy = process.env.PLAY_PROXY || process.env.HTTPS_PROXY || '';
       const ro = proxy ? { agent: { https: new (require('hpagent').HttpsProxyAgent)({ proxy }) } } : {};
       gplay.reviews({ appId: process.argv[2], lang: 'en', country: 'us', sort: 2, num: 100, requestOptions: ro })
         .then(r => r.data.forEach(c => console.log(`${c.score}★ | ${(c.text || '').slice(0, 200)}`)))
         .catch(e => { console.error(e.message); process.exit(1); });
       ```

       注意:脚本在 /tmp 但依赖项目的 node_modules,故须用 `createRequire(process.cwd() + "/")`
       解析(.mjs 里裸用 require 会 ReferenceError);运行 `node /tmp/play_reviews.mjs {track_id}`,
       据输出提炼好评/差评主题。
     - 评论抓取失败的 app 标"信息有限",不中断。
5. **写报告**到 `reports/{日期}-品类分析-{slug}.md`(结构见下),完整样本表
   直接写进报告第 7 节。最后向用户输出 3-5 句执行摘要(竞争格局一句话 +
   最痛的 2-3 个痛点 + 最大机会点)。

## 报告结构

1. **品类概览**:品类定义、样本圈定方式(关键词/原始搜索数/过滤后数/榜单
   交叉情况)、头部玩家一句话概览
2. **竞争格局**:双平台头部矩阵表——名称/开发者/评分/评分量/下载量(play)/
   价格/内购/广告/最近更新/榜单表现
3. **双平台生态对比**:变现模式分布差异(订阅 vs 广告)、竞争密度、头部重合度
4. **功能矩阵与差异化**:品类标配功能(人人都有→无效竞争区)vs 各家差异化
   卖点(有效区隔);从 details.description 提炼
5. **用户痛点**:差评主题提炼,每条附证据(评论摘录+出现频率+来自哪款 app),
   区分双平台痛点异同;light 模式此节基于低分 app 共性与描述推断,标注可信度较低
6. **机会点**:3-6 条产品切入建议(痛点 × 竞争空白交叉推导)
7. **完整样本表**:过滤后全部 app 一览

## 约束

- 全程中文输出;app 名称保留原文(可附中文释义)
- 报告中数字必须来自数据文件,不臆造
- light 模式整份报告控制在 300 行内
