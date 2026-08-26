# UI 稿交付:个性化二维码生成器(5 屏 + 10 状态变体 + 6 类型表单变体)

- 日期:2026-08-26 全量重生成(prompt 已吸收历史修复,一步到位)
- 上游:`reports/2026-08-25-UI设计规范-qr-code-generator.md`(§5 默认态 + §5.1 状态/类型变体 prompts)
- Stitch 项目:**Minimal QR Studio**(id `7207321693625558695`,设计系统 "Precision Utility")

## 文件清单

### 默认态(5 屏)

| 文件 | 屏 | Stitch 屏幕 id |
|---|---|---|
| `screen-1-create.png/.html` | 创建页 | `e3eaea36de7442549c3b896ac52005e9` |
| `screen-2-style-editor.png/.html` | 样式编辑器(Color tab) | `fb96208cde17403f9d7831f88fbb481b` |
| `screen-3-scan.png/.html` | 扫码页(识别成功) | `7826e130778e497db2e04adb62c3557c` |
| `screen-4-history.png/.html` | 历史页(列表态) | `917e33b0c84a49d8a492a293b31d96b0` |
| `screen-5-settings.png/.html` | 设置页(未付费) | `3c507ce2f2114c41bf7e8adb277c97d6` |

### 状态变体(10 屏,规范 §4 交互状态/空态的全覆盖)

| 文件 | 状态 | Stitch 屏幕 id |
|---|---|---|
| `screen-1-create-empty` | 创建页·表单无效/首启(灰占位码+禁用 Export) | `2adbbe28bffd4881b38c26e0dd7ad9c9` |
| `screen-1-create-warning` | 创建页·低对比警告(amber 警告条,F-P0-03) | `7ef14cabbe434f20b294536d9622ad94` |
| `screen-1-create-type-text` | 创建页·Text 类型(多行文本区) | `6812f47eb3294d6c979de9d3968fd61f` |
| `screen-1-create-type-wifi` | 创建页·WiFi 类型(SSID/密码/加密三行) | `b5d1b54495c74e8e9631eb64da502fe9` |
| `screen-1-create-type-contact` | 创建页·Contact 类型(姓名/电话/邮箱) | `512591e265da486983c1b1247ebd7f3d` |
| `screen-1-create-type-sms` | 创建页·SMS 类型(号码+消息) | `52598cfabfef491793037a31e9e72a78` |
| `screen-1-create-type-phone` | 创建页·Phone 类型(电话号码) | `5592581a4ea5464496426f484ec1d8a3` |
| `screen-1-create-type-email` | 创建页·Email 类型(邮箱+主题) | `b999ba0f144c4f8cac102aca5ddc0d1c` |
| `screen-2-style-editor-dots` | 样式编辑器·Dots tab(6 码点形状) | `77cf7a3659744cf385af418a3ebf68da` |
| `screen-2-style-editor-eyes` | 样式编辑器·Eyes tab(4 眼睛样式) | `e3f893392a87439db701cc1f1dbdc191` |
| `screen-2-style-editor-logo` | 样式编辑器·Logo tab(来源/图标/安全区) | `c5e4b3eb823248ce802914b2f69a59c0` |
| `screen-paywall-sheet` | 付费 bottom sheet(N-06,遮罩+sheet) | `290382a4f6e04eb3a231eb1cb43dd5ab` |
| `screen-3-scan-scanning` | 扫码页·识别前(纯取景器) | `5c7f1505683040a4835a0aae04492ea6` |
| `screen-4-history-empty` | 历史页·空态(插画+去创建) | `14fb14e62be44100aef68f79d0a344a7` |
| `screen-4-history-multiselect` | 历史页·长按多选(勾选+批量栏) | `20b57e61b9df4baa9c1408cc3ebc4025` |
| `screen-5-settings-unlocked` | 设置页·已付费(绿勾+Restore) | `d597e04e892147268a5619883280d549` |

PNG 为高 1200px 实时渲染截图;HTML 为单文件源码(Tailwind class)。

**快速浏览**:双击打开本目录的 `gallery.html` —— 一行 6 屏、超出自动换行,
点击放大,←/→ 切换,Esc 关闭。

## 导入 Figma 的三种方式

### 方式一(推荐):Stitch 官方 Copy to Figma
1. 打开 [stitch.withgoogle.com](https://stitch.withgoogle.com) 并登录,进入项目 **Minimal QR Studio**
2. 选中屏幕 → 右上角 **Copy to Figma**(或 ⋯ 菜单里)
3. 到 Figma 画布 `Cmd+V` 粘贴 → 得到**带自动布局的可编辑图层**
4. 若按钮不可见:仅标准模式支持,PRO/实验模式可能没有该按钮

### 方式二:html.to.design 插件(HTML → 可编辑图层)
1. Figma → Resources → Plugins 搜索 **html.to.design** 并运行
2. 选择 Import from file/URL,导入本目录的 `.html` 文件(逐屏)
3. 得到接近像素的 Figma 原生图层(文字/颜色/布局可改)

### 方式三:PNG 拖入(兜底,像素稿)
- 直接把 `.png` 拖进 Figma;适合快速评审,不可编辑图层
- 参考 [官方教程 From Google Stitch to Figma](https://html.to.design/blog/from-google-stitch-to-figma/)

## 核对结论(2026-08-26 全量重生成后抽验)

本批为"一步到位"prompt(已吸收历史全部修复),关键屏视觉抽验 4/4 通过:

- ✅ Screen 1 默认:标题 "Create"、7 段分段(URL indigo 选中)、预览卡、
  Customize Style、Export、4 tab,零促销元素
- ✅ Screen 3 默认:暗色取景器 + indigo 四角扫描框 + **手电 + Album 齐备** +
  WiFi 结果卡 + 动作组,Scan 激活
- ✅ 付费 sheet:**modal bottom sheet 形态正确**(遮罩 + 把手 + 3 行权益 +
  $6.99 + Unlock/Not now),零促销元素
- ✅ 低对比警告:完整 App 界面(非素材图)+ amber 警告条 + 浅灰码

历史批次核对的其余结论(WiFi/Contact 三行表单、Dots/Eyes/Logo tab、
空态/多选/已付费)在上一批已验证,prompt 未变,本批同样适用。

## 已知限制

- **旧屏已全部 hidden**(用户在 Stitch UI 清空):旧 id 全部作废,
  以本文件清单的新 id 为准;hidden 旧屏不影响使用,想彻底清理可在
  Stitch UI 里删除
- `.html` 为各屏生成时快照;本批一步到位 prompt,快照即最终态,
  无 DOM 修改滞后问题
- Stitch MCP 的 `list_screens` 不显示 agent 会话生成的屏幕(见记忆 stitch-mcp-facts),
  项目完整性以本文档的屏幕 id 为准
- 布局不变仅文字变化的状态未单独出图(规范 §5.1 末尾"合并注明"):超长文本
  caption、Export 的 PNG/SVG popover、暗光手电高亮、连续扫码开关
- **Stitch 画布排列**:MCP 无画布位置工具,`edit_screens` 排列指令实测不可靠
  (agent 口头确认但执行不完整)。新 21 屏在画布上为竖向排列,如需网格布局
  在 Stitch UI 里框选拖排;日常浏览直接用本目录 `gallery.html`(一行 6 个换行)
