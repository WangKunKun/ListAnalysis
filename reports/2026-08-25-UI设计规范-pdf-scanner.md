# UI 设计规范:诚实买断 PDF 扫描 App(跨平台 / 一次性买断)

- 日期:2026-08-25
- 上游文档:`reports/2026-08-25-PRD-pdf-scanner.md`(功能契约来源)
- 用途:高保真 UI 生成的输入(本文档每屏附可直接粘贴的 Stitch prompt);
  也是编码阶段的设计 tokens 与页面契约来源
- 平台:iOS + Android(cross,遵循各自平台规范:iOS HIG / Material 3,
  tokens 双端共用)
- 声明:UI 层只呈现 PRD 已有功能(F-P0-01~07 / F-P1-01~05 / P2 仅 §4 附注),
  不引入 PRD 之外的新功能与数字

## 1. 设计方向

**三个关键词:可靠、高效、安静的可信。**

- **可靠**(定位推导):PRD 一句话定位是"可以放心用十年的文档扫描仪"——
  界面永远给出确定的状态反馈:边缘检测高亮、页数计数、进度可见;付费入口
  只在设置页与 P1 功能入口出现,全流程无打断弹窗(F-P0-07:"禁止扫描中途
  弹付费墙")
- **高效**(品类痛点推导):差评高频是"扫 1 份文件却被塞进订阅流程"——
  首启零 onboarding、零注册(N-03 零账号),打开即相机,快门即结果,
  N-01 要求快门到预览 ≤ 3 秒,UI 不添加任何拖慢感知的中间层
- **安静的可信**(差异化主张推导):四条承诺(无订阅/无广告/无水印/权益
  永不降级)不是营销横幅而是承诺页里可核验的文案;全 App 无广告位、无促销
  倒计时、无交叉推广(N-04),视觉上的"少"本身就是信任的来源

**风格基调**:专业效率工具风。相机取景是全 App 的视觉主角(深色全屏),
其余页面浅色极简、以内容(文档缩略图)为中心;色彩仅用于功能:主色=操作,
语义色=状态,绝无装饰性色彩。

## 2. 设计系统 Tokens

### 2.1 色板(浅色模式)

| Token | 值 | 用途 |
|---|---|---|
| `color/primary` | `#0F766E`(Teal 700) | 主按钮、选中态、边缘检测框 |
| `color/primary-pressed` | `#115E59` | 按下态 |
| `color/bg` | `#F8FAFA` | 页面背景 |
| `color/surface` | `#FFFFFF` | 卡片、列表、sheet |
| `color/text-primary` | `#0F172A` | 主文字 |
| `color/text-secondary` | `#475569` | 辅助文字 |
| `color/text-tertiary` | `#94A3B8` | 占位符、说明 |
| `color/success` | `#059669` | 已解锁、OCR 完成 |
| `color/warning` | `#D97706` | 暗光提示、低对比提示 |
| `color/danger` | `#DC2626` | 删除、二次确认强调 |
| `color/border` | `#E2E8F0` | 分割线、描边 |
| `color/camera-bg` | `#0B0F14` | 相机屏背景(全屏取景) |

暗色模式:`bg #0D1117` / `surface #1A2029` / `text-primary #F1F5F9` /
`border #2D3748`;primary 提亮为 `#14B8A6`(暗底对比度);
相机屏本身即深色,tokens 不变。

### 2.2 字体与排印

- 字体族:**Inter**(跨平台一致;系统回退 SF Pro / Roboto)
- 字阶:`display 28/34 semibold`(页内大标题)、`title 20/26 semibold`、
  `body 16/24 regular`、`caption 13/18 regular`、`label 12/16 medium`
  (tab、徽标、页码计数)

### 2.3 间距 / 圆角 / 阴影

- 间距:4pt 网格;页面水平边距 16,卡片内边距 16,元素间 12
- 圆角:按钮 12,卡片 16,bottom sheet 顶部 20,缩略图 8,取景框 24
- 阴影:仅三处——bottom sheet(0,-4,24,`rgba(15,23,42,.12)`)、
  文档库加密分区卡(0,2,12,`rgba(15,23,42,.08)`)、导出完成提示卡
  (0,2,12,`rgba(15,23,42,.08)`);其余用描边分层,不用阴影

### 2.4 核心组件规格

- **快门按钮**:直径 72,白描边 4pt 内白圆;连拍中周围显示已拍页数徽标
  (label 字号);长按区域 ≥44pt
- **已拍页缩略栏**(相机屏底部):高 64,横向滚动,缩略图 48×64 圆角 8,
  当前编辑页 primary 描边 2pt;尾部"+"补拍格
- **滤镜分段控件**:4 段(黑白/灰度/彩色/原图),横向等宽,选中段
  primary 底白字胶囊,逐页独立(F-P0-03 AC2)
- **主按钮**:高 52,全宽,primary 底白字,16 semibold
- **文档条目**:缩略图 48×48 圆角 8 + 标题(body)+ 页数徽标(label)+
  日期(caption);长按多选,左滑删除
- **买断卡片**(设置页,非阻断):primary 描边卡片,权益 4 行(签名/加密
  分区/PDF 工具/云备份+迁移)、价格大字 "$14.99 一次性"(展示区间
  $14.99-$19.99 的落点值由商店配置,界面永远显示实际单价 + "一次性买断"
  字样,N-07)、主按钮"解锁"、次级文字按钮"恢复购买";无倒计时、无试用
  自动扣费话术(F-P0-07 AC②)

## 3. 信息架构与页面流

```
底部导航(3 tab)
├── ① 扫描(Scan)——默认 tab,启动直达相机(F-P0-01/02/03)
│     └→ 取景 → 快门 → 缩略栏 → 点缩略图进页面编辑
│        → "完成" → 导出 sheet(③的入口之一)
├── ② 文档库(Library)——本地文档 + 搜索(F-P0-06)
│     ├→ 文档查看/OCR 文本(F-P0-05)
│     ├→ 加密证件分区(F-P1-02,PIN/生物识别门)
│     └→ PDF 工具:合并/拆分/抽页(F-P1-03)
└── ③ 设置(设置入口亦在①右上角齿轮)
      ├→ 买断卡片 → 承诺页(F-P0-07)
      ├→ 云备份(iCloud/Drive,用户自有网盘,F-P1-04)
      ├→ 竞品文档迁移导入(F-P1-05)
      └→ 隐私声明 / 关于
导出与分享(F-P0-04)为 bottom sheet,挂在扫描完成与文档查看两处,
不占 tab
```

首启无 onboarding、无注册、无付费引导(诚实买断定位:打开即工具;
免费档已完整可用)。核心 5 屏覆盖 P0 全流程:相机屏(一屏多态承载
F-P0-01+02+03)、页面编辑屏、文档库屏、设置屏、承诺/解锁页;
F-P0-04/05 以导出 sheet 与 OCR 视图嵌入上述屏。P1 各功能均为核心屏内
入口(见 §4 附注),不新增独立 tab。

## 4. 页面详细规范(5 屏)

### Screen 1 扫描相机页 [F-P0-01, F-P0-02, F-P0-03]

- **目的**:打开即扫、连拍即册;全 App 唯一全屏深色屏,视觉主角
- **布局**(状态 A 取景):全屏取景(`camera-bg`)→ 自动检测到文档边缘时
  四角显示 primary 描边高亮框(AC:2 秒内出现)→ 顶部一行 caption
  "检测到文档,直接拍摄"(边缘稳定时)/"移近以检测边缘"(未检出时)→
  右上手电与齿轮(设置)→ 底部:**已拍页缩略栏**(状态 B 出现,含补拍
  "+")→ 快门按钮(72)→ 模式切换文字按钮"证件"(进 F-P1-02 专用流程,
  免费档可见入口)
- **状态 B 拍后校正**:快门后 ≤3 秒进入(N-01):显示裁剪结果页,四角
  拖动手柄(primary 圆点,44pt 触达区)可手动重调(AC③),底部"重拍/
  保留"按钮;保留后回到状态 A,缩略栏 +1、徽标计数更新
- **交互状态**:暗光时取景框上方 warning 条"光线较暗,文本增强效果更好";
  连拍 10 页缩略栏正常滚动显示且顺序=拍摄顺序(F-P0-02 AC①);
  中途删除某页后自动补位编号(AC③)
- **空态/首启**:无已拍页时缩略栏隐藏,快门居中;首次使用顶部一次性
  caption"对准文档,边缘识别后自动裁剪"(可关)

### Screen 2 页面编辑屏 [F-P0-02, F-P0-03, F-P0-05, F-P1-01]

- **目的**:单页的滤镜与校正微调、OCR 与签名入口;从缩略栏点入
- **布局**:顶部横向页缩略条(可左右切换当前页,长按拖动重排,F-P0-02
  AC②)→ 大图预览区(占屏 ~55%,双指缩放)→ 滤镜分段控件 4 段,逐页
  独立、即时预览(F-P0-03 AC②)→ 操作行:四角重调(回校正态)/ 旋转 /
  **OCR**(运行后此页下方显示可复制文本区,caption 标注"端内识别")/
  **签名**(F-P1-01,锁形徽标;未解锁时点击弹非阻断 bottom sheet,见
  Screen 5 同款,N-07)→ 底部主按钮"完成,去导出"
- **交互状态**:OCR 运行中按钮转进度;黑白滤镜下手写字迹对比增强可见
  (F-P0-03 AC③);未解锁功能在操作行可见但带锁徽标——**可见可期,点击
  才说明,不隐藏**(差异化主张的界面化)
- **空态**:本屏必由已拍页进入,无空态

### Screen 3 导出 bottom sheet [F-P0-04]

- **目的**:一次会话产出 PDF/JPEG,分享即走;非阻断 sheet(N-07 精神的
  延伸:产出环节永不插付费提示,F-P0-07 AC①)
- **布局**:底部滑出 sheet(圆角 20 + 阴影)→ 格式分段"PDF(多页合一)/
  JPEG(逐页)"→ 页序预览缩略条(与页面管理顺序一致,AC①)→ caption
  "共 N 页 · 原生分辨率,无降采样"(N-05 的界面化)→ 主按钮"导出"→
  次级按钮行"系统分享 / 保存到相册";导出完成显示 success 提示卡
  "已导出,N 页 PDF"
- **交互状态**:20 页 PDF 导出进度条(≤10 秒,N-01);分享面板拉起系统
  分享(邮件/WhatsApp 等至少 2 目标,AC③);导出后自动入库文档库
  (F-P0-06)
- **空态**:无

### Screen 4 文档库页 [F-P0-06, F-P0-05, F-P1-02, F-P1-03]

- **目的**:本地文档管理——重命名/搜索/整理;隐私感的界面化
- **布局**:标题"文档"(display)→ 搜索框(圆角 10,placeholder
  "搜索名称或文档内文字"——即 OCR 全文搜索,F-P0-05 AC②)→ **加密
  证件分区卡**(primary 描边 + 锁图标,"证件 · 端内加密";点按先过
  PIN/生物识别门再进分区列表,F-P1-02 AC①;入口免费档可见)→ 条目列表
  (缩略图/标题/页数徽标/日期;默认名含日期时间如 2026-08-25 1430,
  不重名,AC①)→ 长按多选(批量删除/**合并为 PDF**,F-P1-03,未解锁
  显示锁徽标)→ 条目点入:文档查看(页滚动/OCR 文本视图切换/导出
  sheet/抽页拆分入口 F-P1-03 AC②)
- **交互状态**:搜索命中 OCR 文本时该词在结果内高亮(AC②);重命名后
  列表与导出文件名同步(AC②);加密分区导出需二次确认对话框,取消不生成
  文件(F-P1-02 AC③)
- **空态**:插画位 + "扫描的文档会保存在这里(仅本机)" + 主按钮"去扫描";
  页脚 caption"所有文档仅存储在本机,不上传任何服务器"(N-03 的界面化)

### Screen 5 设置与解锁页 [F-P0-07, F-P1-04, F-P1-05]

- **目的**:安静的付费入口、四条承诺与可控感
- **布局**:标题"设置" → **买断卡片**(置顶:免费档说明一行"扫描、导出、
  OCR 已全部免费,无水印无页数限制" + 权益 4 行 + 价格大字"$14.99
  一次性"(实际商店价,区间 $14.99-$19.99,N-07:先示价格与"一次性买断"
  字样)+ 主按钮"解锁" + 文字链"恢复购买";已解锁后卡片变为
  "已解锁全部功能 ∞ 权益永不降级" + "恢复购买")→ **承诺页入口**
  ("我们的四条承诺"→ 承诺页:无订阅/无广告/无水印/已购权益永不降级,
  四条完整文案,F-P0-07 AC③)→ **云备份**(iCloud / Google Drive,
  "备份到你自己的网盘";自动备份开关;caption"我们没有任何服务器存储
  你的文档",F-P1-04 AC③)→ **迁移导入**("从其他扫描 App 导入 PDF",
  F-P1-05;支持断点续传,AC②)→ **隐私**(隐私政策 + "数据不出设备"
  声明,N-03)→ 关于(版本/崩溃上报开关)
- **基调**:全页无任何促销装饰;买断卡片是唯一的强调块;无试用话术、
  无自动扣费机制(AC②,N-07)
- **空态**:无

**§4 附注(并入的屏)**:签名编辑器(F-P1-01)与文本填字从 Screen 2
"签名"入口模态进入;加密分区列表(F-P1-02)从 Screen 4 分区卡进入;
PDF 合并/拆分工作台(F-P1-03)复用 Screen 4 多选与文档查看;承诺页
(F-P0-07)从 Screen 5 进入;P2 功能(F-P2-01~04)按里程碑 3 后续迭代,
本版不设计屏,仅保证买断卡片"后续所有更新免费"文案衔接(PRD §7)。

## 5. 每屏 Stitch Prompt(直接粘贴用,英文)

> 使用方法:Stitch 新建项目,逐屏粘贴;先生成 Screen 1 定基调,满意后把
> "Style anchor"句附加到其余 prompt 保持一致。

**通用 Style anchor**(每条 prompt 开头都带):

```
Professional minimal utility app, Inter font, primary teal #0F766E,
light background #F8FAFA, white surface cards with 16px radius,
no ads, no banners, no countdowns, clean productive tool aesthetic.
Mobile screen, 390x844.
```

**Screen 1 — Scan (Camera):**

```
{Style anchor} Document scanner camera screen, full-screen dark
viewfinder #0B0F14. Detected document edges highlighted with teal
corner brackets forming a rounded rectangle. Top caption "Document
detected — tap to scan". Torch icon and settings gear top-right.
Bottom: horizontally scrollable thumbnail strip of 5 captured pages
(48x64, one highlighted with teal border) followed by a "+" retake
cell, then a large 72px white-ringed shutter button centered, and a
text button "ID Mode" below it. Small page-count badge "5" near the
shutter.
```

**Screen 2 — Page Editor:**

```
{Style anchor} Scan page editor screen. Top: horizontal strip of page
thumbnails (current page with teal border). Middle 55%: large document
page preview on white. Below: 4-segment filter control (B&W / Grayscale
/ Color / Original), B&W selected as teal pill. Action row of icon
buttons: Adjust Corners, Rotate, OCR, Signature (Signature shows a
small lock badge). Bottom: full-width teal primary button
"Done — Export". Calm, tool-like, document is the hero.
```

**Screen 3 — Export Sheet:**

```
{Style anchor} Bottom sheet over the editor, top corners rounded 20.
Segmented control "PDF (multi-page) / JPEG (per page)", PDF selected.
Below: small page-order thumbnail strip of 6 pages. Caption
"6 pages · full resolution, no downsampling". Full-width teal primary
button "Export". Secondary row: "Share…" and "Save to Photos"
text buttons. A small success card variant at top-right showing
"Exported — 6-page PDF".
```

**Screen 4 — Library:**

```
{Style anchor} Document library screen. Large title "Documents".
Search field "Search names or text inside documents". Below: a
teal-bordered locked card "ID & Sensitive — encrypted on device"
with lock icon. Then list entries: 48px page thumbnail, title
"2026-08-25 1430", page-count badge "10p", date caption. One entry
shows left-swipe delete revealed. Footer caption: "All documents stay
on this device only — nothing is uploaded." Empty-state variant at
bottom of canvas: illustration placeholder, "Scans are saved here
(on-device only)", teal button "Start Scanning".
```

**Screen 5 — Settings:**

```
{Style anchor} Settings screen. Top group: unlock card with teal
border — line "Scanning, export and OCR are fully free — no watermark,
no page limits", 4 benefit lines (Signature / Encrypted ID vault /
Merge & split PDFs / Cloud backup & migration), large price
"$14.99 one-time", primary button "Unlock", quiet text link
"Restore Purchase". Groups below as plain list rows with dividers:
"Our Four Promises", Backup (iCloud, Google Drive, auto-backup
toggle, note "We have no servers storing your documents"),
Migration ("Import PDFs from other scanner apps"), Privacy (policy
link, "Your data never leaves this device"), About (version, crash
reporting toggle). No promotional graphics anywhere.
```

## 6. 交付与衔接

- **给 Stitch**:逐屏粘贴 §5 prompt;5 屏画布一次放下,生成后微调
  (Screen 1 深色相机屏与其余浅色屏的对比是品类特征,不要强行统一)
- **给 Figma**:Stitch 导出 Figma → 按 §2 tokens 核对,重点:快门 72、
  滤镜段 4 个、tab 3 个、买断卡片显示实际单价 + "one-time"字样、
  全部页面无广告/促销/倒计时元素(N-04/N-07)
- **给编码工具**:本规范 §2(tokens)+ §3(信息架构)与 PRD 各功能 AC
  对应——Screen 1 ↔ F-P0-01/02/03 AC,Screen 2 ↔ F-P0-03 AC②③ +
  F-P0-05 AC①,Screen 3 ↔ F-P0-04 AC①-④,Screen 4 ↔ F-P0-06 AC①-③ +
  F-P1-02/03 AC,Screen 5 ↔ F-P0-07 AC①-④ + F-P1-04/05 AC;
  页面截图作为视觉验收基准,实现偏差以 tokens 为准,不追求像素级
