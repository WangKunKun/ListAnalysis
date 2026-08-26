# UI 设计规范:个性化二维码生成器(跨平台 / 一次性买断)

- 日期:2026-08-25
- 上游文档:`reports/2026-08-25-PRD-qr-code-generator.md`(功能契约来源)
- 用途:高保真 UI 生成的输入(本文档每屏附可直接粘贴的 Stitch prompt);
  也是编码阶段的设计 tokens 与页面契约来源
- 平台:iOS + Android(cross,遵循各自平台规范:iOS HIG / Material 3,
  tokens 双端共用)

## 1. 设计方向

**三个关键词:诚实、克制、工具本身即审美示范。**

- **诚实**(定位推导):无广告位、无促销横幅、无倒计时——界面里不出现任何
  制造紧迫感的元素;付费入口只有一个安静的卡片,触发点在动作发生时而非打断时
- **克制**(品类噪音推导):竞品界面塞满模板墙与交叉推广;我们采用"一屏一事"
  ——创建页只做创建,预览永远占据视觉中心
- **审美示范**(品类核心是"个性化审美"):样式编辑器与模板预览的精致度就是
  产品能力的直接广告——预览区的渲染质量必须像素级还原导出效果

**风格基调**:现代极简工具风。大量留白,内容即装饰;色彩仅用于功能(主色=
操作、语义色=状态),二维码预览是页面上唯一"浓墨重彩"的元素。

## 2. 设计系统 Tokens

### 2.1 色板(浅色模式)

| Token | 值 | 用途 |
|---|---|---|
| `color/primary` | `#4F46E5`(Indigo 600) | 主按钮、选中态、进度 |
| `color/primary-pressed` | `#4338CA` | 按下态 |
| `color/bg` | `#FAFAFC` | 页面背景 |
| `color/surface` | `#FFFFFF` | 卡片、输入框、sheet |
| `color/text-primary` | `#111827` | 主文字 |
| `color/text-secondary` | `#6B7280` | 辅助文字 |
| `color/text-tertiary` | `#9CA3AF` | 占位符、说明 |
| `color/success` | `#059669` | 扫码成功、已解锁 |
| `color/warning` | `#D97706` | 对比度过低警告(F-P0-03 AC3) |
| `color/danger` | `#DC2626` | 删除、错误 |
| `color/border` | `#E5E7EB` | 分割线、描边 |

暗色模式:`bg #0F1117` / `surface #1A1D27` / `text-primary #F3F4F6` /
`border #2A2E3A`;primary 不变(在暗底上对比度已达标)。其余语义色按
Material 3 暗色映射提亮一档。

### 2.2 字体与排印

- 字体族:**Inter**(跨平台一致;系统回退 SF Pro / Roboto)
- 字阶:`display 28/34 semibold`(页内大标题)、`title 20/26 semibold`、
  `body 16/24 regular`、`caption 13/18 regular`、`label 12/16 medium`(tab、
  徽标)
- 大字号模式(F-P2-04):全局 ×1.25,布局不得截断

### 2.3 间距 / 圆角 / 阴影

- 间距:4pt 网格;页面水平边距 16,卡片内边距 16,元素间 12
- 圆角:按钮 12,卡片 16,bottom sheet 顶部 20,输入框 10,预览卡 20
- 阴影:仅两处——预览卡(0,2,12,`rgba(17,24,39,.08)`)与 bottom sheet
  (0,-4,24,`rgba(17,24,39,.12)`);其余用描边分层,不用阴影

### 2.4 核心组件规格

- **主按钮**:高 52,全宽,primary 底白字,`label` 字号 16 semibold;
  禁用态 `#E5E7EB` 底 `#9CA3AF` 字(仅表单未完成时)
- **分段控件(内容类型)**:横向滚动 7 段(URL/文本/WiFi/名片/SMS/电话/邮箱),
  选中段 primary 底白字胶囊,未选中 surface 底描边
- **二维码预览卡**:居中,边距 24,白底圆角 20 + 阴影;码区最小 240×240,
  内边距 32(码四周留白保证扫码);下方 caption 显示纠错等级与版本
- **历史条目**:缩略图 48×48 圆角 8 + 标题(body)+ 类型徽标(label)+
  时间(caption);左滑删除、点按进入再编辑
- **付费 bottom sheet(非阻断,N-06)**:标题"解锁全部样式"、正文 3 行权益
  (全部模板/艺术形状与渐变/SVG 与批量导出)、价格大字 "$6.99 一次性"、
  主按钮"解锁"、次级文字按钮"暂不需要"(≥44pt,立即响应,无延迟);
  **无关闭红叉**以外的任何花样,无倒计时,无"今日特惠"

## 3. 信息架构与页面流

```
底部导航(4 tab)
├── ① 创建(Create)——默认 tab
│     └→ ② 样式编辑器(从预览卡"自定义样式"进入,模态推入)
├── ③ 扫码(Scan)
├── ④ 历史(History)──→ 条目再编辑 → 回到①带参
└── 设置(设置入口在①右上角齿轮,非独立 tab)
        └→ 付费卡片 / 迁移 / 隐私 / 主题
```

首启无 onboarding 强制页(诚实定位:打开即工具);首次进入创建页时预填
URL 类型与示例内容,让用户 3 秒内看到第一个码。

## 4. 页面详细规范(5 屏)

### Screen 1 创建页(Create)

- **目的**:3 秒内从内容到可见的码
- **布局**(自上而下):标题"创建"(display)+ 齿轮(右上)→ 内容类型分段
  控件 → 对应表单(单列;WiFi 为 SSID/密码/加密三行;名片为姓名/电话/邮箱)→
  **二维码预览卡**(实时刷新,N-04 ≤300ms)→ "自定义样式"文字按钮(带
  调色板图标)→ 底部主按钮"导出"(PNG/SVG 选项在其内展开)
- **状态**:表单无效时预览卡显示浅灰占位码+提示;对比度<2:1 时预览卡上方
  出现 warning 条(F-P0-03 AC3);超长文本自动升版本,预览卡 caption 显示
  "已自动提升纠错等级"
- **空态/首启**:预填 URL 类型与 `https://` 前缀,预览占位

### Screen 2 样式编辑器(Style Editor)

- **目的**:所见即所得的个性化,预览质量=产品广告
- **布局**:顶部保留 40% 高度的实时预览(与创建页同源渲染,编辑即变)→
  下部 tab 分四组:**颜色**(前景/背景色板 + 渐变双色 + HEX 输入 + 吸管)、
  **码点**(方形/圆点/圆角/心形/水滴/几何,6 选 1 网格)、**眼睛**(3+ 样式
  横排)、**Logo**(从相册选/内置图标/移除;选后显示安全面积提示)。顶部
  另有"模板"入口胶囊(30+ 模板横滑,买断前可预览,导出时触发付费 sheet)
- **状态**:艺术形状/渐变在未付费时可直接编辑预览(免费试用可预览,
  F-P1-03 AC2),导出时才触发付费 sheet——**编辑永不打断**
- **保存**:右上"完成"回创建页,样式随码保存

### Screen 3 扫码页(Scan)

- **目的**:识别并给动作,识别框克制
- **布局**:全屏取景器 + 顶部说明 caption("对准二维码,自动识别")+
  中央取景框(280×280 圆角 24,四角 primary 描边)→ 识别成功后底部滑出
  **结果卡**(surface 底圆角 20):类型徽标 + 结构化内容(URL 可预览域名/
  WiFi 显示 SSID/vCard 显示姓名电话)+ 动作按钮组(打开链接/一键连 WiFi/
  添加到通讯录/复制/生成同款码——"生成同款"把扫到的内容带回创建页,闭环)
- **状态**:暗光提示(打开手电按钮在取景框右上);相册识别入口(左下"相册"
  按钮);连续扫码开关(右上)

### Screen 4 历史页(History)

- **目的**:本地码库,再编辑与收藏(P2 码库的基础)
- **布局**:标题"历史"(display)+ 搜索框(圆角 10,surface 底)→ 分段
  "全部 / 收藏"→ 条目列表(缩略图/标题/类型徽标/时间;收藏条目右上星标)→
  长按多选(批量删除/批量导出)
- **空态**:插画位 + "你生成的码会保存在这里(仅本机)"+ 主按钮"去创建"
- **隐私表达**:页脚 caption"所有记录仅存储在本机,不上传任何服务器"(N-07
  的界面化)

### Screen 5 设置页(Settings)

- **目的**:安静的付费入口与可控感
- **布局**:分组列表——**解锁卡片**(置顶:未付费时显示权益 3 行 + $6.99
  大字 + 解锁按钮;已付费后显示"已解锁全部功能 ∞"与"恢复购买"文字链)、
  **外观**(跟随系统/浅色/深色;大字号开关)、**数据**(导出迁移文件/
  导入迁移文件——JSON,F-P1-04;导出码库备份)、**隐私**(隐私政策链接+
  "本应用不收集二维码内容"声明文案)、**关于**(版本/崩溃上报开关,N-09
  可关闭)
- **基调**:全页无任何促销装饰;解锁卡片是唯一的强调块(primary 描边卡片)

## 5. 每屏 Stitch Prompt(直接粘贴用,英文)

> 使用方法:Stitch 新建项目,逐屏粘贴;先生成 Screen 1 定基调,满意后把
> "Style anchor"句附加到其余 prompt 保持一致。

**通用 Style anchor**(每条 prompt 开头都带):

```
Minimal modern utility app, generous whitespace, Inter font,
primary indigo #4F46E5, background #FAFAFC, white surface cards with
16px radius, no ads, no banners, no countdowns, clean professional
tool aesthetic. Mobile screen, 390x844.
```

**Screen 1 — Create:**

```
{Style anchor} QR code generator "Create" screen. Top: large title
"Create" with a small settings gear icon top-right. Below: horizontally
scrollable segmented control with 7 content types (URL, Text, WiFi,
Contact, SMS, Phone, Email), URL selected as white pill on indigo.
Then a simple URL input field. Center: large white preview card with a
QR code, caption "ECC Level M · Version 3" below the code. Under the
card: text button "Customize Style" with palette icon. Bottom: full-width
indigo primary button "Export". Footer tab bar with 4 tabs:
Create (active), Scan, History, and settings gear.
```

**Screen 2 — Style Editor:**

```
{Style anchor} QR style editor screen opened as modal over Create.
Top 40%: live QR code preview on white card. Below: template entry pill
"Templates" leading to 30+ preset styles strip. Then 4 tabs:
Color, Dots, Eyes, Logo. Color tab active showing: foreground color
swatches row, background swatches row, two-color gradient picker, and
HEX input field. Bottom: "Done" text button top-right of screen.
Keep everything calm and tool-like, preview is the visual hero.
```

**Screen 3 — Scan:**

```
{Style anchor} QR scanner screen. Full-screen dark camera viewfinder.
Center: 280x280 scanning frame with rounded corners and indigo corner
brackets. Top caption "Point at a QR code". Bottom sheet sliding up
with scan result: type badge "WiFi", structured content showing
network name "CoffeeShop_5G", and action buttons row: "Join Network"
(primary), "Copy", "Create Same Code" (secondary buttons).
Torch icon top-right of frame, "Album" button bottom-left.
```

**Screen 4 — History:**

```
{Style anchor} History screen. Large title "History". Search field
with rounded corners on white surface. Segmented control "All /
Favorites". List of QR entries: 48px thumbnail, title, small type
badge, timestamp caption, star icon on favorited items. One entry
shows left-swipe delete action revealed. Footer caption:
"All records stay on this device only — nothing is uploaded."
```

**Screen 5 — Settings:**

```
{Style anchor} Settings screen. Top group: unlock card with indigo
border — 3 benefit lines (All templates / Art shapes & gradients /
SVG & batch export), large price "$6.99 one-time", primary button
"Unlock", quiet text link "Restore Purchase". Groups below as plain
list rows with dividers: Appearance (theme: Auto/Light/Dark, Large
text toggle), Data (Export migration file, Import migration file),
Privacy (Privacy policy link, note "This app never collects your QR
content"), About (version, crash reporting toggle). No promotional
graphics anywhere.
```

### 5.1 状态变体 prompts(每屏 UI 有变化的状态)

> 与默认态同屏不同状态;每条需重述基础布局(Stitch 无跨屏记忆)。
> 布局不变仅文字变化的状态不单开(见本节末尾"合并注明")。

**Screen 1 — Create [empty](表单无效/首启):**

```
{Style anchor} QR code generator "Create" screen, empty/initial state.
Top: large title "Create" with settings gear top-right. Segmented control
with 7 content types, URL selected. URL input pre-filled with placeholder
"https://" only. Center: white preview card showing a LIGHT GRAY
PLACEHOLDER QR pattern with muted hint text "Enter content to generate a
QR code" below it (no real code). Bottom primary button "Export" in
DISABLED state (light gray #E5E7EB background, gray #9CA3AF text).
Footer tab bar 4 tabs, Create active.
```

**Screen 1 — Create [low-contrast](F-P0-03 AC3 警告态):**

```
{Style anchor} QR code generator "Create" screen, warning state. Same
layout as default: title "Create", 7-type segmented control (URL
selected), URL input, central white preview card with QR code,
"Customize Style" text button, Export primary button, 4-tab footer.
ONE difference: above the preview card an amber warning banner (#D97706)
with warning icon, text "Low contrast — code may be hard to scan", and a
small dismiss "×" on the right. The QR preview shows a low-contrast
light-gray-on-white code.
```

**Screen 1 — Create [text / wifi / contact / sms / phone / email 表单变体]:**

> 分段控件切换后表单区随类型变化;公共布局(标题/分段控件/预览卡/
> Customize Style/Export/4 tab)与默认态相同,选中段切换为对应类型,
> 表单预填示例数据。六条 prompt 仅表单区不同:

```
{Style anchor} QR code generator "Create" screen, TEXT type selected.
Same chrome as default (title "Create", gear top-right, 7-type segmented
control with TEXT selected as indigo pill, preview card with QR code and
caption "ECC Level M · Version 2", "Customize Style" text button, indigo
"Export" button, 4-tab footer Create active). Form area: one multi-line
text area (4 rows tall) with label "Text", pre-filled with
"Hello! Check out this app :)".
```

```
{Style anchor} QR code generator "Create" screen, WIFI type selected.
Same chrome as default with WIFI selected in the segmented control.
Form area: three single-line inputs stacked — label "Network name (SSID)"
filled "CoffeeShop_5G"; label "Password" filled with dots •••••••• and a
show/hide eye icon at right; label "Security" as a small segmented
control WPA/WPA2 (selected) / WEP / None.
```

```
{Style anchor} QR code generator "Create" screen, CONTACT type selected.
Same chrome as default with CONTACT selected. Form area: three
single-line inputs stacked — "Full name" filled "Alex Chen"; "Phone"
filled "+1 555 0100"; "Email" filled "alex@example.com".
```

```
{Style anchor} QR code generator "Create" screen, SMS type selected.
Same chrome as default with SMS selected. Form area: one single-line
input "Phone number" filled "+1 555 0123", then one multi-line text area
(3 rows) "Message" filled "Meet me at the coffee shop at 3?".
```

```
{Style anchor} QR code generator "Create" screen, PHONE type selected.
Same chrome as default with PHONE selected. Form area: a single
single-line input "Phone number" filled "+1 555 0147" with a numeric
keypad hint icon.
```

```
{Style anchor} QR code generator "Create" screen, EMAIL type selected.
Same chrome as default with EMAIL selected. Form area: two single-line
inputs stacked — "Email address" filled "hello@example.com"; "Subject"
filled "Quick question".
```

**Screen 2 — Style Editor [dots tab]:**

```
{Style anchor} QR style editor screen, "Dots" tab active. Same chrome as
default: top 40% live QR preview on white card, Templates entry pill,
"Done" top-right. Tab row Color / Dots / Eyes / Logo with DOTS active.
Content: 2×3 grid of dot shape options — Square, Rounded, Dots, Heart,
Droplet, Geometric — each cell a mini QR fragment preview in that shape,
Square selected with indigo border. Calm tool-like layout.
```

**Screen 2 — Style Editor [eyes tab]:**

```
{Style anchor} QR style editor screen, "Eyes" tab active. Same chrome:
top 40% live QR preview, Templates pill, "Done" top-right. Tab row with
EYES active. Content: horizontal row of 4 corner-eye style options —
Square, Rounded, Circle, Leaf — each shown as a large QR finder-pattern
glyph, Rounded selected with indigo border. Caption below: "Applies to
all three corner eyes". Minimal, tool-like.
```

**Screen 2 — Style Editor [logo tab]:**

```
{Style anchor} QR style editor screen, "Logo" tab active. Same chrome:
top 40% live QR preview with a small centered logo visible inside the
code, Templates pill, "Done" top-right. Tab row with LOGO active.
Content: "Choose source" three list rows — "Choose from Album",
"Built-in Icons", "Remove Logo"; below a small grid of built-in icons
(link, wifi, phone, mail, heart, star); footer hint caption "Keep logo
within the safe area (30% of code size)".
```

**Paywall bottom sheet [paywall](N-06 非阻断,导出时触发):**

```
{Style anchor} Paywall bottom sheet over a dimmed Create screen (60%
dark scrim). The sheet: white surface, top radius 20, slides from
bottom, standard small "×" close icon top-right — nothing else. Content:
title "Unlock All Styles", three benefit lines with small icons —
"All 30+ templates", "Art shapes & gradients", "SVG & batch export";
large price "$6.99 one-time"; full-width indigo primary button "Unlock";
below a quiet text button "Not now" (44pt tap target). NO countdown, NO
"today only" badge, no promotional graphics.
```

**Screen 3 — Scan [scanning](识别前):**

```
{Style anchor} QR scanner screen, scanning state (no result yet).
Full-screen dark camera viewfinder. Center: 280×280 scanning frame with
rounded corners and indigo corner brackets, subtle scan line. Top caption
"Point at a QR code". Torch icon top-right of frame, "Album" button
bottom-left. NO result sheet visible — bottom shows only the 4-tab bar
(Scan active).
```

**Screen 4 — History [empty]:**

```
{Style anchor} History screen, empty state. Large title "History". Search
field and "All / Favorites" segmented control still visible at top.
Center: simple line-art illustration placeholder (QR code outline with a
sparkle), muted caption "Codes you create are saved here (on-device
only)", full-width indigo primary button "Create One". Footer privacy
caption "All records stay on this device only — nothing is uploaded."
4-tab bar, History active.
```

**Screen 4 — History [multiselect](长按多选):**

```
{Style anchor} History screen, multi-select state. Header title replaced
by "3 selected" with an "×" cancel icon on the left. Search field
hidden. List of QR entries: each row with a leading round checkbox
(3 checked indigo, others empty outline). No swipe actions. Bottom:
contextual action bar replaces the tab bar — icon buttons "Export" and
"Delete" (danger red #DC2626) plus "Select all" text link.
```

**Screen 5 — Settings [unlocked](已付费):**

```
{Style anchor} Settings screen, after purchase (unlocked state). Same
grouped list layout: Appearance / Data / Privacy / About groups
identical to default. Top group card now shows: success green #059669
checkmark circle icon, title "All features unlocked ∞", and a quiet
text link "Restore Purchase" — no price, no buy button. Card keeps its
indigo border, calmer tone. No promotional graphics anywhere.
```

**合并注明(布局不变,不单开 prompt)**:Screen 1 超长文本时预览卡
caption 变为"已自动提升纠错等级";Screen 1 Export 按钮点按展开 PNG/SVG
选项(组件内 popover);Screen 3 暗光时手电按钮高亮提示、右上连续扫码
开关切换。

## 6. 交付与衔接

- **给 Stitch**:逐屏粘贴 §5 prompt;5 屏画布一次放下,生成后微调
- **给 Figma**:Stitch 导出 Figma → 按 §2 tokens 检查(重点:主按钮 52 高、
  预览卡 240+、tab 4 个、无任何广告/促销元素混入)
- **给编码工具**:本规范 §2(tokens)+ §3(信息架构)与 PRD 的 AC 对应;
  页面截图作为视觉验收基准(实现 UI 与设计稿的偏差以 tokens 为准,
  不追求像素级)
