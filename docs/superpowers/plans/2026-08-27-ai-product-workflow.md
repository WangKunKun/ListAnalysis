# AI驱动产品工作流实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建从App Store榜单分析到产品UI生成的完整工作流，包括智能品类推荐、交互式PRD生成和Stitch MCP集成。

**Architecture:** 基于独立skill链式架构，每个环节可独立调用或链式执行。核心组件包括：品类分析引擎、智能推荐算法、PRD生成器、UI设计规范生成器和Stitch MCP集成层。

**Tech Stack:** Python 3标准库、Claude Code skills、Stitch MCP、markdown文档生成

---

## 文件结构总览

### 新增文件
```
.claude/skills/category-analysis/SKILL.md          # 品类分析skill
.claude/skills/generate-prd/SKILL.md              # PRD生成skill (更新)
.claude/skills/generate-stitch-ui/SKILL.md        # UI生成skill (更新)
fetch/category.py                                  # 品类抓取编排
fetch/adapters/ios.py                              # iTunes搜索API适配器  
fetch/adapters/play.py                             # Play搜索API适配器
scripts/play_bridge.mjs                            # Node桥接脚本
tests/test_category.py                             # 品类抓取测试
tests/fixtures/category_search.json                # 测试fixtures
```

### 修改文件
```
.claude/skills/app-scan/SKILL.md                   # 扩展智能推荐功能
```

---

## Task 1: 扩展 /app-scan skill 增加智能推荐

**Files:**
- Modify: `.claude/skills/app-scan/SKILL.md`

- [ ] **Step 1: 在现有分析报告中增加智能推荐章节**

在 `.claude/skills/app-scan/SKILL.md` 的报告结构部分，增加"智能推荐"章节：

```markdown
## 报告结构

1. **本期总览** - 日期、区域、各榜app数、数据完整性
2. **类型分布** - 细分赛道表格 + 共性vs区域特色分析  
3. **重点App分析** - 按细分赛道分组逐个详析
4. **完整榜单表格** - 分区域×分榜单
5. **观察与机会** - 跨区域趋势与机会点
6. **智能推荐** (新增) - 基于分析结果推荐最有潜力的3-5个品类方向
```

- [ ] **Step 2: 在skill流程中增加推荐逻辑**

在skill流程部分增加推荐生成步骤：

```markdown
## 流程

1. **取数** - 若数据不存在，先运行fetch_charts.py
2. **读数据** - 读apps.json与meta.json  
3. **类型分布** - 把app归入细分赛道
4. **分层分析** - light/standard/deep模式
5. **智能推荐** (新增) - 基于品类分析生成推荐：
   - 计算机会评分 = 市场需求×0.4 + 竞争蓝海×0.3 + 技术可行×0.2 + 痛点强度×0.1
   - 输出Top 3-5推荐品类，每个包含：品类名称、评分、机会点、市场规模、竞争强度
6. **写报告** - 生成reports/{日期}-工具榜分析.md
```

- [ ] **Step 3: 增加推荐算法实现细节**

在skill末尾增加推荐算法说明：

```markdown
## 智能推荐算法

### 评分模型
```python
机会评分 = (市场需求强度 × 0.4) + (竞争蓝海度 × 0.3) + 
          (技术可行性 × 0.2) + (用户痛点强度 × 0.1)

其中：
- 市场需求强度 = (品类app数量 × 平均评分) / 1000
- 竞争蓝海度 = 1 - (头部5家app的市场份额 / 100)  
- 技术可行性 = 基于功能复杂度评估(简单=1.0, 中等=0.7, 复杂=0.4)
- 用户痛点强度 = 高频未解决需求的评论占比 × 10
```

### 推荐输出格式
```markdown
## 智能推荐

基于本期榜单分析，推荐以下3个品类方向：

### 1. PDF扫描工具 (评分: 8.5/10)
- **机会点**: 移动办公需求增长，现有产品功能单一
- **市场规模**: 约20个相关app，平均评分4.2
- **竞争强度**: 中等，头部3家占60%市场
- **技术难度**: 中等，需要OCR和图像处理

### 2. 隐私保护工具 (评分: 7.8/10)  
- **机会点**: 用户隐私意识提升，现有产品过度复杂
- **市场规模**: 约15个相关app，平均评分4.0
- **竞争强度**: 较低，市场分散
- **技术难度**: 较低，主要依赖系统API

### 3. 二维码生成器 (评分: 7.2/10)
- **机会点**: 个性化定制需求，现有产品设计同质化
- **市场规模**: 约25个相关app，平均评分4.3
- **竞争强度**: 较高，头部5家占70%市场  
- **技术难度**: 较低，核心算法成熟
```
```

- [ ] **Step 4: 更新skill描述和触发词**

修改skill头部描述：

```markdown
---
name: app-scan
description: 扫描App Store工具榜并生成中文分析报告，含智能品类推荐。用法：/app-scan [light|standard|deep] [--refresh]。触发词：扫榜、工具榜分析、app榜单、品类推荐。
---
```

- [ ] **Step 5: 测试扩展功能**

```bash
# 在项目目录运行测试
/app-scan standard

# 检查生成的报告包含智能推荐章节
cat reports/$(date +%Y-%m-%d)-工具榜分析.md | grep -A 20 "智能推荐"
```

Expected: 报告中包含智能推荐章节，有3-5个推荐品类

- [ ] **Step 6: 提交变更**

```bash
git add .claude/skills/app-scan/SKILL.md
git commit -m "feat: app-scan增加智能品类推荐功能

- 基于市场需求、竞争强度、技术可行性评分
- 输出Top 3-5推荐品类方向
- 每个推荐包含机会点分析和可行性评估

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 2: 创建品类抓取基础设施

**Files:**
- Create: `fetch/category.py`
- Create: `fetch/adapters/ios.py` (修改现有文件)
- Create: `fetch/adapters/play.py` (修改现有文件) 
- Create: `scripts/play_bridge.mjs`
- Create: `tests/test_category.py`
- Create: `tests/fixtures/category_search.json`

- [ ] **Step 1: 创建iOS搜索适配器**

修改 `fetch/adapters/ios.py`，增加搜索方法：

```python
def search_apps(self, term: str, cc: str, limit: int = 100,
                sleep=time.sleep) -> list[dict] | None:
    """iTunes Search API搜索应用
    
    Args:
        term: 搜索关键词(英文)
        cc: 国家代码
        limit: 返回数量上限(API上限200)
        sleep: 休眠函数(可注入用于测试)
    
    Returns:
        应用列表，失败返回None
    """
    url = f"https://itunes.apple.com/search?term={term}&country={cc}&entity=software&limit={limit}"
    text = http_get(url, opener=self.urlopen, sleep=sleep)
    if text is None:
        return None
    
    return parse_search(text)

def parse_search(text: str) -> list[dict]:
    """解析iTunes搜索响应"""
    data = json.loads(text)
    results = []
    for app in data.get("results", []):
        results.append({
            "track_id": str(app.get("trackId", "")),
            "name": app.get("trackName", ""),
            "artist": app.get("sellerName", ""),
            "details": {
                "description": app.get("description", ""),
                "price": app.get("formattedPrice", ""),
                "rating": app.get("averageUserRating"),
                "rating_count": app.get("userRatingCount", 0),
                "genres": app.get("genres", []),
                "release_date": app.get("currentVersionReleaseDate", ""),
                "track_view_url": app.get("trackViewUrl", "")
            }
        })
    return results
```

- [ ] **Step 2: 创建Play搜索适配器**

修改 `fetch/adapters/play.py`，增加搜索方法：

```python  
def search_apps(self, term: str, cc: str, limit: int = 100,
                sleep=time.sleep) -> list[dict] | None:
    """Google Play搜索应用
    
    Args:
        term: 搜索关键词(英文)
        cc: 国家代码
        limit: 返回数量上限
        sleep: 休眠函数
        
    Returns:
        应用列表，失败返回None
    """
    cmd = {
        "cmd": "search",
        "term": term,
        "num": limit,
        "country": cc
    }
    
    try:
        result = subprocess.run(
            ["node", "scripts/play_bridge.mjs"],
            input=json.dumps(cmd),
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode != 0:
            return None
            
        data = json.loads(result.stdout)
        app_ids = data.get("results", [])
        
        # 批量获取详情
        return self.fetch_details(app_ids, cc, sleep)
        
    except (subprocess.TimeoutExpired, json.JSONDecodeError) as e:
        print(f"Play搜索失败: {e}", flush=True)
        return None
```

- [ ] **Step 3: 创建Node桥接脚本**

创建 `scripts/play_bridge.mjs`：

```javascript
#!/usr/bin/env node
/**
 * Google Play scraper桥接脚本
 * 支持search和apps命令
 */

import { search, app } from 'google-play-scraper';

const cmd = JSON.parse(await readline());

try {
  let result;
  
  if (cmd.cmd === 'search') {
    result = await search({
      term: cmd.term,
      num: cmd.num,
      country: cmd.country,
      fullDetail: false
    });
    
    // 返回appId列表
    console.log(JSON.stringify({
      success: true,
      results: result.map(app => app.appId)
    }));
    
  } else if (cmd.cmd === 'apps') {
    // 批量获取详情
    const details = await Promise.all(
      cmd.appIds.map(appId => app({ appId }))
    );
    
    // 转换为统一格式
    const results = details.map(detail => ({
      track_id: detail.appId,
      name: detail.title,
      artist: detail.developer,
      details: {
        description: detail.description,
        price: detail.priceText || 'Free',
        rating: detail.score,
        rating_count: detail.reviews,
        genres: detail.genres || [],
        release_date: detail.released || '',
        track_view_url: detail.url || ''
      }
    }));
    
    console.log(JSON.stringify({
      success: true,
      results: results
    }));
  }
  
} catch (error) {
  console.error(JSON.stringify({
    success: false,
    error: error.message
  }));
  process.exit(1);
}

async function readline() {
  return new Promise(resolve => {
    let data = '';
    process.stdin.on('data', chunk => data += chunk);
    process.stdin.on('end', () => resolve(data));
  });
}
```

- [ ] **Step 4: 创建品类抓取编排脚本**

创建 `fetch/category.py`：

```python
#!/usr/bin/env python3
"""品类应用抓取编排"""

import json
import argparse
import time
from pathlib import Path
from datetime import date

from fetch.adapters.ios import ITunesAdapter
from fetch.adapters.play import PlayAdapter


def merge_search_results(all_results):
    """合并多关键词搜索结果，去重并保留评分量最高的详情"""
    merged = {}
    for track_id, app_list in all_results.items():
        if track_id not in merged:
            merged[track_id] = max(app_list, 
                key=lambda x: x.get('details', {}).get('rating_count', 0))
    return merged

def fetch_category(terms, slug, platforms, country, limit, data_dir, refresh):
    """抓取品类应用数据"""
    
    data_dir = Path(data_dir) / f"{date.today()}" / f"cat-{slug}"
    meta_file = data_dir / "meta.json"
    
    # 复用判断
    if not refresh and meta_file.exists():
        with open(meta_file) as f:
            meta = json.load(f)
        print(f"复用现有数据: {data_dir}", flush=True)
        return meta
    
    data_dir.mkdir(parents=True, exist_ok=True)
    
    all_results = {}
    failed_terms = []
    
    # 分平台抓取
    for platform in platforms:
        platform_results = {}
        
        for term in terms:
            print(f"搜索 {platform}: {term}", flush=True)
            time.sleep(3)  # 节流
            
            if platform == 'ios':
                adapter = ITunesAdapter()
                results = adapter.search_apps(term, country, limit)
            else:  # play
                adapter = PlayAdapter()
                results = adapter.search_apps(term, country, limit)
            
            if results is None:
                failed_terms.append(f"{platform}:{term}")
                continue
                
            for app in results:
                track_id = app['track_id']
                if track_id not in platform_results:
                    platform_results[track_id] = []
                platform_results[track_id].append(app)
        
        # 合并去重
        merged = merge_search_results(platform_results)
        
        # 落盘
        platform_file = data_dir / f"{platform}.json"
        with open(platform_file, 'w', encoding='utf-8') as f:
            json.dump(list(merged.values()), f, ensure_ascii=False, indent=2)
        
        all_results[platform] = merged
    
    # 元信息
    meta = {
        'slug': slug,
        'terms': terms,
        'country': country,
        'platforms': platforms,
        'failed_terms': failed_terms,
        'fetched_at': date.today().isoformat(),
        'counts': {
            platform: len(results) 
            for platform, results in all_results.items()
        }
    }
    
    with open(meta_file, 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    
    print(f"完成: {data_dir}", flush=True)
    return meta

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--terms', required=True, help='逗号分隔搜索关键词')
    parser.add_argument('--slug', required=True, help='品类标识符')
    parser.add_argument('--platform', default='all', choices=['ios', 'play', 'all'])
    parser.add_argument('--country', default='us', help='国家代码')
    parser.add_argument('--limit', type=int, default=100, help='搜索数量')
    parser.add_argument('--date', help='数据日期(YYYY-MM-DD)')
    parser.add_argument('--refresh', action='store_true')
    
    args = parser.parse_args()
    
    terms = [t.strip() for t in args.terms.split(',')]
    platforms = ['ios', 'play'] if args.platform == 'all' else [args.platform]
    data_dir = Path('data')
    if args.date:
        data_dir /= args.date
    
    meta = fetch_category(
        terms=terms,
        slug=args.slug,
        platforms=platforms,
        country=args.country,
        limit=args.limit,
        data_dir=data_dir,
        refresh=args.refresh
    )
    
    # 全部失败返回非0退出码
    if meta.get('failed_terms') and len(meta.get('failed_terms', [])) == len(terms) * len(platforms):
        return 1
    
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
```

- [ ] **Step 5: 创建测试文件**

创建 `tests/test_category.py`：

```python
import unittest
from unittest import mock
import json
from pathlib import Path
import fetch.category

class TestCategorySearch(unittest.TestCase):
    
    def test_merge_search_results(self):
        """测试搜索结果合并去重"""
        results = {
            "app1": [
                {"track_id": "app1", "details": {"rating_count": 100}},
                {"track_id": "app1", "details": {"rating_count": 200}}
            ],
            "app2": [
                {"track_id": "app2", "details": {"rating_count": 50}}
            ]
        }
        
        merged = fetch.category.merge_search_results(results)
        
        self.assertEqual(len(merged), 2)
        self.assertEqual(merged["app1"]["details"]["rating_count"], 200)
        self.assertEqual(merged["app2"]["details"]["rating_count"], 50)

class TestCategoryCLI(unittest.TestCase):
    
    @mock.patch('fetch.category.fetch_category')
    @mock.patch('sys.argv', ['category.py', '--terms', 'pdf,scanner', '--slug', 'test'])
    def test_cli_args_parsing(self, mock_fetch):
        """测试CLI参数解析"""
        mock_fetch.return_value = {"counts": {"ios": 10}}
        
        result = fetch.category.main()
        
        self.assertEqual(result, 0)
        mock_fetch.assert_called_once()
        call_args = mock_fetch.call_args
        self.assertEqual(call_args.kwargs['slug'], 'test')
        self.assertEqual(call_args.kwargs['terms'], ['pdf', 'scanner'])
```

- [ ] **Step 6: 创建测试fixtures**

创建 `tests/fixtures/category_search.json`：

```json
{
  "resultCount": 2,
  "results": [
    {
      "trackId": 12345,
      "trackName": "PDF Scanner Pro",
      "sellerName": "Test Inc",
      "description": "Scan documents with OCR",
      "formattedPrice": "$4.99",
      "averageUserRating": 4.5,
      "userRatingCount": 1200,
      "genres": ["Business", "Productivity"],
      "currentVersionReleaseDate": "2026-08-01T00:00:00Z",
      "trackViewUrl": "https://apps.apple.com/app/id12345"
    },
    {
      "trackId": 67890,
      "trackName": "Doc Scanner",
      "sellerName": "Test Corp",
      "description": "Fast document scanning",
      "formattedPrice": "Free",
      "averageUserRating": 4.2,
      "userRatingCount": 800,
      "genres": ["Utilities"],
      "currentVersionReleaseDate": "2026-07-15T00:00:00Z",
      "trackViewUrl": "https://apps.apple.com/app/id67890"
    }
  ]
}
```

- [ ] **Step 7: 运行测试验证**

```bash
python3 -m unittest tests.test_category -v
```

Expected: 所有测试通过

- [ ] **Step 8: 赋予执行权限并提交**

```bash
chmod +x fetch/category.py scripts/play_bridge.mjs
git add fetch/category.py fetch/adapters/ios.py fetch/adapters/play.py \
        scripts/play_bridge.mjs tests/test_category.py tests/fixtures/
git commit -m "feat: 品类应用抓取基础设施

- iOS/Play搜索API适配器
- Node桥接脚本支持Google Play搜索
- 品类抓取编排逻辑
- 测试覆盖和fixtures

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 3: 创建品类分析skill

**Files:**
- Create: `.claude/skills/category-analysis/SKILL.md`

- [ ] **Step 1: 创建skill基础结构**

创建 `.claude/skills/category-analysis/SKILL.md`：

```markdown
---
name: category-analysis  
description: 基于App Store榜单数据进行品类竞争格局与痛点分析，生成智能推荐。用法：/category-analysis <品类描述> [light|standard] [--refresh]。触发词：品类分析、竞品分析、痛点分析。
---

# 品类竞品与痛点分析

分析指定品类的竞争格局、功能矩阵、用户痛点与机会点，产出中文分析报告。

## 参数解析

品类描述(必填)、模式 light|standard(默认)、是否强制重新抓取 --refresh。

## 流程

1. **关键词生成**: AI将品类描述翻译为3-5个英文搜索关键词
2. **数据抓取**: 调用品类抓取脚本获取相关应用数据  
3. **榜单交叉**: 与现有榜单数据交叉标注竞争地位
4. **深度分析**: standard模式抓取头部应用用户评论
5. **报告生成**: 生成结构化品类分析报告
6. **智能推荐**: 基于分析结果推荐产品机会点
```

- [ ] **Step 2: 增加详细流程说明**

```markdown
## 详细流程

### 1. 关键词生成与slug生成

AI将用户输入的品类描述(如"PDF扫描工具")翻译为：
- **搜索关键词**: 3-5个英文搜索词，如"pdf scanner,document scanner,ocr scan"
- **品类slug**: kebab-case标识符，如"pdf-scanner"

### 2. 数据抓取

运行: `python3 -m fetch.category --terms "关键词列表" --slug {slug} --platform all`

失败(退出码非0) → 报错并停止

### 3. 榜单交叉标注

取最近一期 `data/{最新日期}/{platform}/apps.json`，AI判断榜内应用是否属于该品类，获得竞争地位维度。

### 4. 品类归属过滤与头部圈定

AI剔除搜索噪声，按评分量/下载量排出头部应用。standard模式对头部10个抓取用户评论。

### 5. 报告生成

生成 `reports/{日期}-品类分析-{slug}.md`，结构见下节。

### 6. 智能推荐与交互选择

基于分析结果计算机会评分，推荐Top 3-5个品类方向供用户选择。
```

- [ ] **Step 3: 定义报告结构**

```markdown
## 报告结构

`reports/{日期}-品类分析-{slug}.md`

### 1. 品类概览
- 品类定义与范围
- 样本圈定方式(关键词、原始搜索数、过滤后数、榜单交叉情况)  
- 头部玩家一句话概览

### 2. 竞争格局
双平台头部矩阵表：名称/开发者/评分/评分量/价格/内购/广告/最近更新/榜单表现

### 3. 双平台生态对比
- 变现模式分布差异(订阅vs广告)
- 竞争密度对比
- 头部产品重合度

### 4. 功能矩阵与差异化
- 品类标配功能(人人都有)
- 各家差异化卖点

### 5. 用户痛点
差评主题提炼，每条附证据(评论摘录+出现频率+来源应用)

### 6. 机会点(智能推荐核心)
基于痛点×竞争空白推导的3-6个产品切入建议，每个包含：
- 机会评分(满分10分)
- 市场规模预估
- 技术难度评估  
- 推荐理由

### 7. 完整样本表
过滤后全部应用一览
```

- [ ] **Step 4: 增加智能推荐算法**

```markdown
## 智能推荐算法

### 评分模型

```python
机会评分 = (市场需求强度 × 0.4) + (竞争蓝海度 × 0.3) + 
          (技术可行性 × 0.2) + (用户痛点强度 × 0.1)

其中：
- 市场需求强度 = min(10, (品类app数量 × 平均评分) / 100)
- 竞争蓝海度 = max(0, 10 - (头部5家市场份额 × 10))  
- 技术可行性 = 基于功能复杂度评估(简单=10, 中等=7, 复杂=4)
- 用户痛点强度 = min(10, 高频痛点评论占比 × 100)
```

### 推荐输出

每个推荐包含：
- 品类细分方向
- 机会评分(满分10分)
- 核心机会点描述
- 目标用户群
- 技术实现难度
- 与现有品类的差异化
```

- [ ] **Step 5: 增加质量约束和错误处理**

```markdown
## 质量约束

- 全程中文输出，app名保留原文
- 报告数字必须来自数据文件，不臆造  
- 痛点提炼必须附评论证据
- light模式报告控制在300行内

## 错误处理

- 搜索样本<5个 → 提示关键词可能不当，建议调整
- 抓取失败 → 报告错误并停止
- 榜单数据缺失 → 降级纯搜索样本并注明
- 评论抓取失败 → 标注"信息有限"继续流程
```

- [ ] **Step 6: 提交skill**

```bash
git add .claude/skills/category-analysis/SKILL.md
git commit -m "feat: 品类分析skill

- 基于榜单数据的品类竞争格局分析
- 智能推荐算法和多维度评分模型
- 用户痛点挖掘和机会点识别
- 结构化报告输出和交互式选择

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 4: 更新PRD生成skill

**Files:**
- Modify: `.claude/skills/generate-prd/SKILL.md`

- [ ] **Step 1: 更新skill连接新的品类分析**

修改 `.claude/skills/generate-prd/SKILL.md` 的定位报告逻辑：

```markdown
## 流程

1. **定位报告**: 
   - 优先查找品类分析报告: `reports/*-品类分析-{slug}.md`
   - 如不存在，降级查找工具榜报告: `reports/*-工具榜分析.md`
   - 找不到 → 提示先跑分析，停止
```

- [ ] **Step 2: 增强智能推荐处理**

```markdown
2. **智能推荐处理**:
   - 如果是品类分析报告，提取其智能推荐章节
   - 如果是工具榜报告，提取类型分布和观察与机会章节
   - 展示推荐机会点供用户选择
   - 提供AI推荐选项(按痛点强度×竞争空白评分)
```

- [ ] **Step 3: 优化PRD结构连接品类分析**

```markdown
## PRD结构增强

### 3. 定位与差异化主张
- 内联品类分析报告的痛点证据(评论摘录+频率)
- 引用竞品基准数据证明市场空白
- 明确与现有产品的差异化主张

### 4. 竞品基准表
- 从品类分析报告的竞争格局节提取数据
- 包含双平台对比(如适用)
- 标注数据快照日期

### 5. 功能规格
- P0功能基于品类分析的标配功能清单
- P1功能直接支撑选定的定位主张  
- P2功能基于痛点分析得出的增强点
```

- [ ] **Step 4: 增加质量追溯**

```markdown
## 质量约束(增强)

### 数据来源追溯
- 竞品数据标注来源: "基于{报告日期}的品类快照"
- 痛点证据标注来源app和评论数量
- 功能需求标注基于的分析维度

### 自包含验证
- PRD可单独交给外部AI工具实现
- 所有数据内联，无外部引用
- 技术栈可替换但功能契约不变
```

- [ ] **Step 5: 提交更新**

```bash
git add .claude/skills/generate-prd/SKILL.md  
git commit -m "feat: PRD生成skill对接品类分析

- 支持品类分析报告和工具榜报告
- 智能推荐处理和机会点提取
- 增强数据追溯和自包含验证
- 优化竞品基准和功能规格连接

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 5: 创建UI生成skill

**Files:**
- Create: `.claude/skills/generate-stitch-ui/SKILL.md`

- [ ] **Step 1: 创建skill基础框架**

创建 `.claude/skills/generate-stitch-ui/SKILL.md`：

```markdown
---
name: generate-stitch-ui
description: 基于PRD生成UI设计规范和Stitch prompts，支持交互状态生成和自动MCP调用。用法：/generate-stitch-ui <品类slug>。触发词：UI设计、界面设计、生成UI、Stitch设计。
---

# PRD → UI设计规范与Stitch生成

读PRD文档，推导UI设计规范，生成每屏Stitch prompts，Stitch MCP可用时自动生成设计稿。

## 流程(四步)

1. **定位PRD**: 查找 `reports/*-PRD-{slug}.md`
2. **设计推导**: 从PRD推导设计方向、设计系统、信息架构
3. **文档产出**: 生成6节UI设计规范文档
4. **智能生成**: 检测Stitch MCP并调用生成UI
```

- [ ] **Step 2: 增加详细设计推导流程**

```markdown
## 设计推导流程

### 1. 设计方向推导

从PRD第3节(定位与差异化主张)推导3个设计关键词：
- 从定位主张提取核心设计理念
- 从用户痛点推导设计策略  
- 从功能特征提炼设计风格

### 2. 设计系统tokens推导

基于设计方向生成具体数值：
- **色板**: 主色/辅色/浅色模式/深色模式(hex值)
- **字阶**: 标题/正文/辅助文字的字号行高字重
- **间距**: 基于4pt网格的间距系统
- **圆角**: 统一的圆角半径规范  
- **阴影**: 克制使用(≤3处)

### 3. 信息架构推导

从PRD功能规格推导页面结构：
- 按P0/P1/P2优先级排序页面
- 核心屏≤6个(状态变体不计入)
- 超出按里程碑优先裁剪
```

- [ ] **Step 3: 定义交互状态生成规则**

```markdown
## 交互状态生成规则

### 状态分类体系

| 交互类型 | 状态变体 |
|---------|----------|
| 点击类(按钮) | 常态、悬停态、禁用态、点击后态 |
| 选项卡 | 选中态、未选中态、切换中态 |
| 列表项 | 空态、单条态、多条态、加载态 |
| 表单输入 | 空值态、填写中态、已填写态、错误态 |
| 导航类 | 首页态、子页面态、返回态 |

### 生成策略

- **必选状态**: 空态、加载态、错误态  
- **交互状态**: 基于具体交互元素生成
- **业务状态**: 根据功能特点定制

### 状态命名规范

```
screen-{序号}-{功能名称}[{状态}]

示例:
- screen-01-home
- screen-02-scanner[result-mode]  
- screen-03-settings[edit-mode]
```
```

- [ ] **Step 4: 定义文档结构**

```markdown
## 文档结构(6节)

### 1. 设计方向
3个关键词+风格基调，每词注明推导来源

### 2. 设计系统tokens  
色板/字阶/间距/圆角/阴影/核心组件规格

### 3. 信息架构与页面流
导航结构图+页面列表(标注来源功能ID)

### 4. 页面详细规范
每屏包含：目的/布局/关键元素/交互状态/空态

### 5. 每屏Stitch prompts
- 统一Style anchor(主色/字体/风格/画布尺寸)
- 每屏一段默认态prompt
- 每个UI有变化的状态各一段变体prompt

### 6. 交付与衔接
- 给Stitch的手动路径步骤
- 给Figma的导出核对要点  
- 给编码工具的tokens与PRD AC对应关系
```

- [ ] **Step 5: 增加Stitch MCP集成**

```markdown
## Stitch MCP集成

### 智能检测

```python
def detect_stitch_mcp() -> bool:
    available_tools = list_mcp_tools()
    return any('stitch' in tool.name.lower() for tool in available_tools)
```

### 调用流程

1. **基础检测**: 检查Stitch MCP可用性
2. **逐屏生成**: 按优先级生成默认态→交互状态→错误状态  
3. **重试机制**: 单屏失败重试一次，再失败降级为手动
4. **状态追踪**: 记录生成成功/失败的屏数和原因

### 降级策略

- MCP不可用 → 输出prompts文档，提供手动路径指引
- 单屏失败 → 跳过该屏，继续其他屏
- 部分状态失败 → 生成已成功的状态，标注失败部分
```

- [ ] **Step 6: 增加质量约束**

```markdown
## 质量约束

### 功能可追溯  
- 每屏标注来源功能ID(F-P0-01等)
- 付费/打断类UI决策引用PRD非功能条款编号

### 状态完整性
- 逐屏核对交互状态/空态
- UI有变化的状态必须有对应变体prompt
- 不得只给默认态

### tokens具体化
- 颜色给hex值
- 字号给px/行高值
- 间距给4pt网格值
- 组件给具体尺寸

### 设计不臆造
- UI层只呈现PRD已有功能
- 不引入PRD之外的新功能
```

- [ ] **Step 7: 提交skill**

```bash
git add .claude/skills/generate-stitch-ui/SKILL.md
git commit -m "feat: UI设计规范与Stitch生成skill

- 基于PRD推导设计系统和信息架构
- 完整的交互状态生成规则和命名规范  
- Stitch MCP智能检测和调用机制
- 多级降级策略保证稳定性

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 6: 端到端测试和文档完善

**Files:**
- Create: `README.md` (更新)
- Create: `docs/superpowers/plans/verification-checklist.md`

- [ ] **Step 1: 创建验证清单**

创建 `docs/superpowers/plans/verification-checklist.md`：

```markdown
# AI驱动产品工作流验证清单

## 完整流程验证

### 1. 工具榜分析→智能推荐
- [ ] 运行 `/app-scan standard`
- [ ] 检查报告包含智能推荐章节
- [ ] 验证推荐评分算法正确
- [ ] 确认推荐包含机会点分析

### 2. 品类分析→推荐生成
- [ ] 选择推荐品类运行 `/category-analysis "PDF扫描工具"`
- [ ] 验证数据抓取成功
- [ ] 检查品类分析报告完整
- [ ] 确认智能推荐输出正确

### 3. PRD生成
- [ ] 基于品类分析运行 `/generate-prd pdf-scanner`
- [ ] 验证PRD结构完整(10节)
- [ ] 检查功能规格包含验收标准
- [ ] 确认竞品数据来源清晰

### 4. UI设计生成
- [ ] 基于PRD运行 `/generate-stitch-ui pdf-scanner`
- [ ] 验证UI设计规范文档完整(6节)
- [ ] 检查交互状态prompts完整
- [ ] 确认Stitch MCP调用或降级路径

## 分环节验证

### 品类分析skill
- [ ] 关键词生成准确
- [ ] 搜索结果去重正确
- [ ] 竞争格局分析合理
- [ ] 痛点提炼有证据支撑

### PRD生成skill  
- [ ] 自包含性验证(外部AI可独立实现)
- [ ] 数据来源追溯完整
- [ ] 功能优先级分层合理
- [ ] 验收标准可测试

### UI生成skill
- [ ] 设计方向推导合理
- [ ] 设计系统tokens具体
- [ ] 交互状态覆盖完整
- [ ] Stitch prompts格式正确

## 质量标准验证

### 文档质量
- [ ] 所有输出文档自包含
- [ ] 数字和数据来源清晰
- [ ] 无外部引用
- [ ] 中英文混合正确

### 生成质量  
- [ ] 智能推荐基于数据驱动
- [ ] 交互状态覆盖UI变化场景
- [ ] Stitch prompts包含Style anchor
- [ ] 错误处理机制有效

### 可追溯性
- [ ] 每个UI屏幕有功能ID来源
- [ ] 每个设计决策有PRD条款引用
- [ ] 每个推荐有数据支撑理由
```

- [ ] **Step 2: 更新项目README**

在项目README中增加新功能说明：

```markdown
# App Store工具榜分析与产品生成

## 核心功能

### 1. 工具榜扫描分析
定期扫描App Store工具榜，生成中文分析报告，含智能品类推荐。

### 2. 品类深度分析  
对指定品类进行竞争格局、功能矩阵、用户痛点深度分析。

### 3. 产品需求文档生成
基于品类分析生成交互式PRD，支持多种商业模式选择。

### 4. UI设计规范生成  
基于PRD生成完整UI设计规范和Stitch prompts，支持交互状态生成。

## 使用流程

```bash
# 1. 工具榜分析(含智能推荐)
/app-scan standard

# 2. 选择推荐品类进行深度分析
/category-analysis "PDF扫描工具"

# 3. 基于品类分析生成PRD
/generate-prd pdf-scanner --platform ios --mode buyout

# 4. 基于PRD生成UI设计
/generate-stitch-ui pdf-scanner
```

## 智能推荐

系统基于以下维度计算机会评分：
- 市场需求强度 (40%)
- 竞争蓝海度 (30%)  
- 技术可行性 (20%)
- 用户痛点强度 (10%)
```

- [ ] **Step 3: 运行端到端测试**

```bash
# 完整流程测试
/app-scan standard

# 选择一个推荐品类
/category-analysis "推荐的品类名"

# 生成PRD
/generate-prd {品类slug} --platform ios --mode buyout

# 生成UI设计
/generate-stitch-ui {品类slug}
```

Expected: 每个环节成功，产出相应文档

- [ ] **Step 4: 检查文档完整性**

```bash
# 检查生成的文档
ls -la reports/ | grep $(date +%Y-%m-%d)
ls -la prd/ 2>/dev/null || echo "PRD目录待创建"
ls -la stitch-prompts/ 2>/dev/null || echo "Stitch prompts目录待创建"
```

Expected: 各目录有对应日期的文档生成

- [ ] **Step 5: 提交完善文档**

```bash
git add README.md docs/superpowers/plans/verification-checklist.md
git commit -m "docs: 完善项目文档和验证清单

- 更新README说明完整产品生成流程
- 增加端到端验证清单
- 提供使用示例和智能推荐说明

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 7: 性能优化和错误处理完善

**Files:**
- Modify: 各skill的错误处理部分
- Create: `docs/error-handling-guide.md`

- [ ] **Step 1: 创建错误处理指南**

创建 `docs/error-handling-guide.md`：

```markdown
# 错误处理和降级策略指南

## 错误分类和处理策略

### Level 1: 数据获取错误

#### 品类分析数据缺失
**错误**: `品类分析报告不存在`
**处理**: 
```python
if not category_report_exists:
    print("请先运行品类分析: /category-analysis '品类名'")
    return 1
```

#### PRD文档过期  
**错误**: `PRD文档距离生成时间>90天`
**处理**:
```python  
if (datetime.now() - prd_date).days > 90:
    print("警告: PRD文档可能过时，建议重新生成")
    # 不阻塞，标注数据来源日期继续执行
```

#### Stitch MCP不可用
**错误**: `检测不到Stitch MCP工具`
**处理**:
```python
if not detect_stitch_mcp():
    print("Stitch MCP不可用，将生成prompts文档供手动使用")
    # 降级为手动prompts输出
```

### Level 2: AI分析错误

#### 品类样本不足
**错误**: `搜索结果<5个应用`
**处理**:
```python
if len(search_results) < 5:
    print("搜索结果较少，关键词可能不够准确，建议:")
    print("1. 调整搜索关键词")
    print("2. 扩大搜索范围")
    # 不阻塞，继续分析但标注数据有限
```

#### PRD功能缺失
**错误**: `PRD缺少功能规格章节`  
**处理**:
```python
if '功能规格' not in prd:
    print("PRD格式不符，降级为基础UI框架")
    # 生成通用设计系统
```

#### 状态生成失败
**错误**: `某个交互状态prompt生成失败`
**处理**:
```python
failed_states = []
for state in states:
    try:
        generate_state_prompt(state)
    except Exception as e:
        failed_states.append(state)
        print(f"状态{state}生成失败，跳过")

if failed_states:
    print(f"部分状态生成失败: {failed_states}")
```

### Level 3: 生成错误

#### 单屏Stitch调用失败
**错误**: `Stitch API调用失败`
**处理**:
```python
for screen in screens:
    for attempt in range(2):  # 重试一次
        try:
            call_stitch(screen)
            break
        except Exception as e:
            if attempt == 0:
                print(f"屏幕{screen}生成失败，重试中...")
            else:
                print(f"屏幕{screen}生成失败，跳过")
                # 继续其他屏幕
```

## 降级策略矩阵

| 失败类型 | 降级路径 | 用户体验 |
|---------|---------|---------|
| 品类分析失败 | 手动输入品类信息 | 需要手动操作 |
| PRD生成失败 | 使用标准模板 | 功能可能不精确 |
| UI推导失败 | 生成通用设计系统 | 设计不够定制化 |
| Stitch MCP全部失败 | 输出prompts文档 | 需要手动操作 |
| 部分屏生成失败 | 混合模式(自动+手动) | 部分手动操作 |

## 错误日志规范

所有错误应包含：
- 错误类型和原因
- 影响范围
- 建议的解决方案
- 降级路径说明
```

- [ ] **Step 2: 完善各skill的错误处理**

在各skill的SKILL.md中增加对应的错误处理章节。

- [ ] **Step 3: 增加性能监控**

在关键环节增加性能日志：

```python
import time

start = time.time()
# 执行操作
duration = time.time() - start
if duration > 30:  # 超过30秒
    print(f"性能提醒: {operation} 耗时 {duration:.1f}秒")
```

- [ ] **Step 4: 提交错误处理完善**

```bash
git add docs/error-handling-guide.md
git add .claude/skills/*/SKILL.md
git commit -m "feat: 完善错误处理和降级策略

- 创建错误处理指南和降级策略矩阵
- 完善各skill的错误处理章节
- 增加性能监控和日志规范

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## 验收总结

完成所有任务后，系统应具备：

✅ **完整的产品生成流程**: 从榜单分析到UI设计的完整链路  
✅ **智能推荐机制**: 基于数据驱动的多维度评分  
✅ **交互式PRD生成**: 用户可选择和编辑产品需求  
✅ **分层UI生成**: P0/P1/P2功能分层+完整交互状态  
✅ **Stitch MCP集成**: 自动检测调用+多级降级  
✅ **错误处理**: 完善的错误处理和降级策略  
✅ **文档完善**: 用户体验文档和验证清单  

整个工作流实现了从数据分析到产品UI生成的自动化，每个环节都可以独立调用或组合使用，为产品创建提供了完整的数据驱动解决方案。