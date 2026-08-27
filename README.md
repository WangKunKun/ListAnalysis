# App Store工具榜分析与产品生成系统

完整的AI驱动产品工作流：从榜单数据分析到UI设计生成的自动化解决方案。

## 核心功能

### 1. 工具榜扫描分析
定期扫描App Store工具榜，生成中文分析报告，含智能品类推荐。

### 2. 品类深度分析  
对指定品类进行竞争格局、功能矩阵、用户痛点深度分析。

### 3. 产品需求文档生成
基于品类分析生成交互式PRD，支持多种商业模式选择。

### 4. UI设计规范生成  
基于PRD生成完整UI设计规范和Stitch prompts，支持交互状态生成。

## 智能推荐系统

系统基于以下维度计算品类机会评分：
- **市场需求强度 (40%)**: 品类app数量 × 平均评分
- **竞争蓝海度 (30%)**: 头部玩家市场份额反向评分  
- **技术可行性 (20%)**: 基于功能复杂度评估
- **用户痛点强度 (10%)**: 高频痛点评论占比

### 推荐输出
每个推荐包含：
- 品类细分方向和机会评分(满分10分)
- 核心机会点描述和市场规模预估
- 目标用户群和技术实现难度
- 与现有品类的差异化分析

## 使用

### 完整产品生成流程

```bash
# 1. 工具榜分析(含智能推荐)
/app-scan standard

# 2. 从推荐结果选择品类进行深度分析
/category-analysis "PDF扫描工具"

# 3. 基于品类分析生成PRD
/cat-prd pdf-scanner --platform ios --mode buyout

# 4. 基于PRD生成UI设计规范
/generate-stitch-ui pdf-scanner
```

### 单独使用各功能

#### 工具榜扫描
```bash
# 手动扫描（默认 ios，standard 档）
/app-scan
# Google Play 扫描
/app-scan play
# 快速扫榜 / 深度研究
/app-scan [ios|play] light
/app-scan [ios|play] deep
# 强制重抓当天数据
/app-scan [ios|play] --refresh
```

#### 品类分析
```bash
# 任意品类双平台竞品与痛点分析
/category-analysis "PDF扫描工具"
/category-analysis "二维码生成器" light
```

#### PRD生成
```bash
# 从品类报告生成自包含 PRD
/cat-prd pdf-scanner --platform ios --mode buyout
/cat-prd qr-code-generator cross subscription
```

#### UI设计生成
```bash
# 从 PRD 生成 UI 设计规范与 Stitch prompts
/generate-stitch-ui pdf-scanner
```

### 只抓数据不分析

```bash
# 榜单数据抓取
python3 -m fetch.charts --platform ios|play|all [--date YYYY-MM-DD] [--refresh]

# 品类数据抓取
python3 -m fetch.category --terms "pdf scanner,ocr scan" --slug pdf-scanner --platform all
```

Play 首次使用：`npm install`（需 node；运行时需代理可访问 play.google.com）。

## 技术架构

### 数据抓取层
平台可拔插架构，`fetch/adapters/` 下实现各平台适配器（ios / play）：
- 新增平台只需实现 `fetch_chart`/`fetch_details` 并注册
- 支持 iTunes Search API 和 Google Play Scraper
- Node桥接脚本处理Play Store数据（`scripts/play_bridge.mjs`）

### AI分析层
- **智能推荐**: 多维度评分模型，自动识别机会品类
- **品类分析**: 竞争格局分析+用户痛点挖掘
- **PRD生成**: 自包含文档，支持外部AI工具独立实现
- **UI生成**: 完整交互状态生成，Stitch MCP自动调用

### 代理配置
```bash
# Google Play 需代理访问
export PLAY_PROXY=http://127.0.0.1:7890
# 或者使用标准环境变量
export HTTPS_PROXY=http://127.0.0.1:7890
```
桥接脚本自动识别代理环境，iOS平台直连。

## 定时任务

```bash
scripts/install_launchd.sh install ios     # 每周一 09:30
scripts/install_launchd.sh install play    # 每周一 09:50
scripts/install_launchd.sh verify [ios|play]
scripts/install_launchd.sh uninstall [ios|play]
```

## 配置

`config.json`：顶层 `regions`/`charts`/`top_n` 为公共默认；
`"ios"`/`"play"` 子字典按平台覆盖（如 `{"play": {"top_n": 50, "detail_top_n": 150}}`）。

## 项目结构

### 数据目录
- `data/{日期}/{平台}/`：原始榜单（raw/）、合并清单（apps.json）、运行元信息（meta.json）
- `data/{日期}/cat-{slug}/`：品类搜索样本（{ios|play}.json 含 source_terms/details、meta.json 记录关键词与统计）
- `reports/`：中文分析报告（`{日期}-工具榜分析-{平台}.md`、`{日期}-品类分析-{slug}.md`、`{日期}-PRD-{slug}.md`）

### 代码目录
- `fetch/`：抓取框架（core 编排 + adapters 平台适配器）
- `scripts/play_bridge.mjs`：Play 数据源桥（google-play-scraper）
- `.claude/skills/`：Claude Code技能定义（app-scan、category-analysis、cat-prd、generate-stitch-ui）
- `tests/`：单元测试和fixtures

### 文档目录
- `docs/superpowers/specs/`：功能规格文档
- `docs/superpowers/plans/`：实施计划和验证清单
- `logs/`：定时任务日志

> 2026-08-24 前的旧 iOS 数据在 `data/{日期}/apps.json`，如需纳入新布局可执行：
> `mkdir -p data/{日期}/ios && mv data/{日期}/apps.json data/{日期}/meta.json data/{日期}/raw data/{日期}/ios/`

## 测试

    python3 -m unittest discover tests -v
