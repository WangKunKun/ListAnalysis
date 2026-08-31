# 品类分析：2FA 验证器（2fa-authenticator）——双平台

> 数据：data/2026-08-28/cat-2fa-authenticator/{ios,play}.json（iTunes Search + Google Play，美区，5 关键词 × limit 100）；iOS 去重 243、剔除噪声 7 后品类内 **236**，Play 品类内 **39**（Play 搜索返回量本身较小）。
> 榜单交叉：data/2026-08-27/ios/apps.json（回溯 1 天，9 款 iOS 在工具榜）；Play 近 7 天无榜单数据，标注"无榜单交叉"。
> 评论：Play 头部 12 款 × 100 条（共 1,200 条真实评论）已落盘 data/2026-08-28/reviews/play/；iOS 评论 RSS 废弃（仅 1 款返回水评，不采信）。
> 模式：standard。

## 1. 品类概览

- **品类定义**：生成 TOTP/OTP 一次性验证码的独立验证器 app（含企业/政务推送型 MFA 客户端；密码管理器附带的 2FA 不算）。
- **头部一句话**：iOS 侧被平台默认（Google Auth 116 万评分）与企业级（Duo 225 万）夹住，独立带靠订阅制或开源免费立足；Play 侧头部换成了**欧洲政务/银行身份 app**（意大利 CieID 10M+ 装机/64.5 万评分、瑞典 BankID、德国 S-pushTAN、西班牙 Cl@ve），且全品类评分系统性偏低（Google Auth 在 Play 仅 3.86 分）。
- **独立开发者生态位**：2FAS（iOS 3.5 万评分 + Play 5M+ 装机）、Aegis（Play 500K+，4.67）、UNSTABLE（4.8 万订阅）证明个人/小队可活，但两端变现文化迥异（iOS 订阅普及 vs Play 几乎全免费）。

## 2. 竞争格局

### 2.1 iOS 头部矩阵（19 款代表）

| 梯队 | App | 开发者 | 评分 | 评分量 | 变现 | 最近更新 | 榜单 |
|---|---|---|---:|---:|---|---|---|
| 平台默认 | Google Authenticator | Google | 4.85 | 1,163,737 | 免费 | 2026-08-24 | 工具榜 10 区 fr1 |
| 平台默认 | Microsoft Authenticator | Microsoft | 4.71 | 688,535 | 免费 | 2026-08-24 | — |
| 企业级 | Duo Mobile | Duo Security | 4.87 | 2,254,907 | 免费(B端) | 2026-08-25 | — |
| 企业级 | SafeNet MobilePASS+ | Thales | 4.77 | 115,948 | 免费 | 2026-06-23 | — |
| 企业级 | ID.me Authenticator | ID.me | 4.33 | 99,585 | 免费 | 2026-04-28 | — |
| 企业级 | Okta Verify | Okta | 4.76 | 37,214 | 免费(B端) | 2026-08-20 | — |
| 密码公司配套 | Twilio Authy | Authy | 4.67 | 53,391 | 免费 | 2026-07-22 | — |
| 密码公司配套 | LastPass Authenticator | LastPass | 4.65 | 44,437 | 免费 | 2026-06-08 | — |
| 密码公司配套 | Proton Authenticator | Proton AG | 4.40 | 241 | 免费/开源 | 2026-08-26 新发布 | — |
| 独立/开源 | Authenticator App | UNSTABLE SL | 4.64 | 48,394 | 免费+订阅 | 2026-08-05 | — |
| 独立/开源 | 2FAS | 2FAS Inc. | 4.73 | 34,981 | 开源免费 | 2026-04-26 | — |
| 独立/开源 | OneAuth | Zoho | 4.68 | 33,442 | 免费+增值 | 2026-08-03 | — |
| 独立/开源 | Authenticator · | SMM service | 4.64 | 26,252 | 免费+广告 | 2026-08-08 | 5 区 fr43 |
| 独立/开源 | Authenticator App ™ | Codenhagen.IO | 4.37 | 24,296 | 免费+订阅 | 2024-05-17 停更 | — |
| 独立/开源 | AppyFactor TOTP | AppyFactor | 4.71 | 3,867 | 免费+订阅 | 2026-08-03 | — |
| 独立/开源 | TOTP Authenticator | Sparrow Code | 4.41 | 671 | 免费+订阅 | — | 2 区畅销 gr17 |
| 独立/开源 | Authenticator App | FLOOMIX | 4.58 | 576 | 免费+订阅 | — | 2 区畅销 gr27 |
| 独立/开源 | Ente Auth | Ente | 4.65 | 283 | 开源免费 | 2026-08-03 | — |
| 独立/开源 | OTP Auth | Roland Moers | 4.64 | 476 | 买断内购 | 2023-09-29 弃更 | — |

iOS 长尾：236 款中 195 款（83%）评分量 <500，含 17+ 款"Authenticator App＋装饰符"式 ASO 克隆。

### 2.2 Play 头部矩阵（按装机量）

| 梯队 | App | 开发者 | 评分 | 评分量 | 装机 | 变现 |
|---|---|---|---:|---:|---|---|
| 平台默认 | Microsoft Authenticator | Microsoft | 4.65 | 2,772,636 | 100M+ | 免费 |
| 平台默认 | Google Authenticator | Google | **3.86** | 676,835 | 100M+ | 免费 |
| 政务/银行 | CieID（意大利电子身份） | Istituto Poligrafico | 4.72 | 645,250 | 10M+ | 免费 |
| 政务/银行 | BankID（瑞典） | Finansiell ID-Teknik | 3.17 | 55,167 | 10M+ | 免费 |
| 政务/银行 | S-pushTAN（德国银行） | Star Finanz | 2.95 | 53,916 | 10M+ | 免费 |
| 政务/银行 | Cl@ve（西班牙政务） | Agencia Estatal | 2.42 | 31,015 | 10M+ | 免费 |
| 政务/银行 | itsme（比利时）/Smart-ID（波罗的海） | — | 4.69/4.47 | 408,535/240,227 | 5M+ | 免费 |
| 企业级 | Duo Mobile | Cisco | 4.18 | 86,626 | 50M+ | 免费 |
| 企业级 | Okta Verify | Okta | 3.98 | 43,502 | 10M+ | 免费 |
| 企业级 | RSA / PingID | — | 3.31/2.75 | 18,007/8,164 | 10M+/5M+ | 免费 |
| 独立/开源 | Authenticator App | Starnest JSC | 4.13 | 104,271 | 10M+ | **IAP+广告** |
| 独立/开源 | 2FAS | 2FAS | 4.28 | 32,438 | 5M+ | 免费 |
| 独立/开源 | Aegis Authenticator | Beem Development | 4.67 | 6,208 | 500K+ | 免费 |
| 独立/开源 | Proton Authenticator | Proton | 4.87 | 13,443 | 500K+ | 免费 |
| 独立/开源 | Bitwarden Authenticator | Bitwarden | 3.94 | 1,389 | 100K+ | 免费 |
| 独立/开源 | Ente Auth | Ente | 4.59 | 2,461 | 100K+ | 免费 |
| 独立/开源 | TOTP Authenticator | Sparrow Code | 4.36 | 2,091 | 100K+ | 免费+IAP |

## 3. 双平台生态对比

1. **头部构成不同**：iOS 是"平台默认+企业级"；Play 搜索头部被**欧洲政务/银行身份 app**占据（CieID 评分量 64.5 万超过除 Google/微软外的一切）——受监管机构垄断，个人不可攻，但它们 2.4-3.2 分的体验灾难反衬独立 TOTP 工具的价值。
2. **评分系统性差异**：同款产品 Play 评分显著低于 iOS（Google Auth 3.86 vs 4.85、Authy 3.67 vs 4.67、Duo 4.18 vs 4.87、FreeOTP 3.06 vs 3.19）——Android 端备份/迁移/小厂适配的坑更深，体验空档更大。
3. **变现文化相反**：iOS 独立梯队 17+ 款走订阅；Play 侧除 Starnest（IAP+广告，104,271 评分量）和个别土耳其系小厂外几乎全员免费（2FAS/Aegis/Proton/Ente/Bitwarden 全开源免费）——**Play 靠付费验证器收钱的先例极少，买断变现应锚定 iOS**。
4. **开源阵营 Play 更强**：Aegis（Play 独占生态位）、Bitwarden Authenticator（新入场 3.94 分）、Stratum（jmh.me，4.80）等仅在 Play 出现；iOS 侧开源代表是 2FAS/Ente。

## 4. 功能矩阵与差异化

### 4.1 iOS 头部功能矩阵

| App | 主要功能 | 特色功能 |
|---|---|---|
| Google Authenticator | TOTP/扫码添加/云同步 | **Google 账号体系默认绑定** |
| Microsoft Authenticator | TOTP/推送/无密码/密码填充 | **passwordless** |
| Duo Mobile | TOTP/推送/Watch | **B 端事实标准** |
| Authy | TOTP/多设备/加密备份 | **多设备同步（桌面端已关停）** |
| 2FAS | TOTP/浏览器扩展/加密备份 | **开源+免费无广告** |
| UNSTABLE | TOTP/iCloud 端到端加密 | **E2EE 云同步（订阅）** |
| AppyFactor | TOTP/云同步/浏览器扩展 | **桌面扩展联动（>5 账号重度用户）** |
| SMM · | TOTP+密码+私密浏览 | **三合一（广告变现）** |
| Ente Auth | TOTP/E2EE 备份/离线 | **开源+跨平台备份** |
| Proton Auth | TOTP/离线优先/E2EE | **瑞士隐私法+开源，8-26 新入场** |
| OTP Auth | TOTP/iCloud/Siri/Watch | **无广告买断（已弃更）** |
| Yubico | TOTP/硬件密钥 | **密钥存硬件** |

### 4.2 品类标配（无效竞争区）
TOTP 生成、扫码添加、本地加密、生物锁、云同步、Watch 支持、导入导出。

### 4.3 有效差异化方向
1. **开源+E2EE 备份**：2FAS/Ente/Proton（+Play 侧 Aegis/Bitwarden）——已强占且巨头化。
2. **迁移与备份无忧**：Authy 桌面关停与泄露事件、OTP Auth 弃更留下的迁移潮（评论证据见第 5 节①）。
3. **隐私 ROM/去 Google 化用户**：大厂全面启用 Play Integrity 封杀自定义 ROM（评论证据见第 5 节②），Aegis 独占此需求。
4. **企业推送/B 端**：Duo/Okta/PingID——资质壁垒，不可入。
5. **三合一密码库**：SMM——撞密码管理器信任墙（上轮结论）。

## 5. 用户痛点（Play 12 款 × 100 条评论实证，共 1,200 条）

1. **换机/丢机即丢账号（最痛，跨 6 款有证据）** — Aegis："lost all my authentication codes after my old phone got damaged…lost my access permanently to my Facebook"；"换新手机后没有恢复选项"；Google Auth："This app is the reason most of my accounts are now locked out"；Authy："把我登出后要求在另一台设备批准——我从没有过另一台"；Duo："忘记密码后无任何恢复途径"。
2. **Play Integrity 封杀自定义 ROM（4 款大厂中招，隐私人群刚需）** — Authy："thought you supported open source…they don't support GrapheneOS. Boycott!"；Duo："Play integrity checks…only whitelists non-Google systems"；S-pushTAN："Actively blocks usage on GrapheneOS…只能手动装旧版本"；BankID：封锁第三方启动器与密码管理器。
3. **导出锁定（连口碑最好的独立产品也有）** — 2FAS 差评："no export option for tokens"——用户对锁定式备份警惕，"自由导出"本身是卖点。
4. **新手引导缺失** — 2FAS："For a beginner like me, I couldn't…"；Aegis："no instructions…QR 就在这台手机上怎么扫？"——扫码添加在同一台手机上自举是普遍困惑。
5. **订阅/广告陷阱与山寨混淆（iOS 长尾 + Play Starnest）** — Starnest 100 条评论中 26 条差评："$12.42 每周扣费我没用过"、"伪装成 ID.me"、"too many ads"——头部关键词被滥用，抬高正牌获客成本。
6. **锁屏绕过类安全 bug** — Google Auth（Play 3.86 分主因之一）："按返回键绕过指纹锁直接看码"（Pixel 11/小米均有报告）。
7. **机构 app 体验灾难（不可攻但反衬价值）** — Cl@ve 100 条中 90 条差评、S-pushTAN 65 条、BankID 61 条、Okta 60 条："为了访问一个网站被迫装整个 app"。

## 6. 机会点（痛点 × 竞争空白交叉）

1. **"迁移+备份无忧+自由导出"的买断制 iOS TOTP 工具** — 评级：**中高**
   证据链：痛点①③（换机丢码为 6 款共有 + 用户明确要求导出自由）× 竞争空白（买断位 OTP Auth 2023 弃更、Codenhagen 停更 15 个月无人接盘；订阅疲劳见 Starnest 差评）。
   技术难度：低。差异化：$4.99-9.99 一次性买断、加密备份+明文导出双通道、迁移向导（Google/Authy/2FAS/Aegis 一键导入）。AI 定性评估：窗口真实、规模有限，iOS 先行。
2. **多端联动体验（watchOS/Mac/iPad/浏览器）** — 评级：**中**
   证据：AppyFactor 以浏览器扩展立足（4.71/3,867）；Okta 差评"为一台设备装一个 app"反映多端疲劳。小团队可及的体验差异。
3. **Play 侧"隐私 ROM 友好"定位（Aegis 的补位者）** — 评级：**中低**
   证据：痛点②，4 款大厂主动放弃的去 Google 化人群。但 Play 变现文化免费为主（第 3 节），适合作为 iOS 主产品的免费引流端而非收入端。
4. **不建议**：开源免费位（2FAS/Proton/Ente/Aegis/Bitwarden 五重占位）、政务银行身份（监管壁垒）、三合一密码库（信任墙）。

## 7. 完整样本表

### 7.1 iOS（品类内 236 款，按评分量降序）

| 名称 | 开发者 | 评分 | 评分量 | 最近更新 | 价格 |
|---|---|---|---|---|---|
| Duo Mobile | Duo Security LLC | 4.87471 | 2254907 | 2026-08-25 | Free |
| Google Authenticator | Google LLC | 4.85079 | 1163737 | 2026-08-24 | Free |
| Microsoft Authenticator | Microsoft Corporation | 4.71369 | 688535 | 2026-08-24 | Free |
| SafeNet MobilePASS+ | Thales DIS (Singapore) Pte | 4.77191 | 115948 | 2026-06-23 | Free |
| Dashlane Password Manager | Dashlane | 4.78522 | 106634 | 2026-08-24 | Free |
| ID.me Authenticator | ID.me, Inc. | 4.32555 | 99585 | 2026-04-28 | Free |
| Twilio Authy | Authy Inc. | 4.67368 | 53391 | 2026-07-22 | Free |
| Authenticator App | UNSTABLE, SL | 4.64049 | 48394 | 2026-08-05 | Free |
| LastPass Authenticator | LastPass US LP | 4.64912 | 44437 | 2026-06-08 | Free |
| Okta Verify | Okta, Inc. | 4.7552 | 37214 | 2026-08-20 | Free |
| 2FA Authenticator (2FAS) | Two Factor Authentication  | 4.72642 | 34981 | 2026-04-26 | Free |
| Authenticator App - OneAuth | Zoho Corporation | 4.6752 | 33442 | 2026-08-03 | Free |
| Authenticator · | SMM service, s.r.o. | 4.63938 | 26252 | 2026-08-08 | Free |
| Authenticator App ™ | Codenhagen.IO ApS | 4.37265 | 24296 | 2024-05-17 | Free |
| Authenticator App+ | Rocket Apps GmbH | 4.79983 | 11870 | 2026-07-13 | Free |
| UniFi Verify | Ubiquiti Inc. | 4.8484 | 11438 | 2026-03-26 | Free |
| Authenticator app - 2FA, MFA | Maxima Apps | 4.6029 | 5709 | 2026-08-26 | Free |
| Authenticator ℠ App | BEGAMOB GLOBAL LIMITED | 4.30583 | 4885 | 2026-08-11 | Free |
| Salesforce Authenticator | salesforce.com | 4.57376 | 4284 | 2025-04-14 | Free |
| TOTP Authenticator – Fast 2FA | AppyFactor | 4.71347 | 3867 | 2026-08-03 | Free |
| Authenticator App - Authkey | SKYRISE LIMITED | 4.69437 | 3393 | 2026-01-06 | Free |
| Authenticator ® App | MATECHMOBILE SOFTWARE JOIN | 4.42648 | 3271 | 2026-08-05 | Free |
| Authenticator+ App | ENGIN MEYVE VE SEBZE GIDA  | 4.53019 | 2965 | 2026-07-28 | Free |
| The Authenticator‎ App | DEEP BLUE LABS LIMITED | 4.53952 | 2619 | 2026-06-24 | Free |
| Authenticator App† | Appqe LLC | 4.46108 | 2531 | 2025-10-10 | Free |
| Authenticator - 2FA App | Vitalii Kuprenko | 4.67304 | 2459 | 2026-07-24 | Free |
| Authenticator © | HUAMEI INDUSTRY TRADE CO., | 4.26708 | 2385 | 2025-12-24 | Free |
| BlazeAuth - MFA Authenticator | Kanatom Limited | 4.52195 | 2096 | 2026-08-11 | Free |
| Authenticator App - 2FA Auth + | Appshub Bilgi Teknolojiler | 4.5031 | 1775 | 2026-05-28 | Free |
| OneSpan Mobile Authenticator | OneSpan International GmbH | 4.82179 | 1532 | 2025-12-03 | Free |
| Authenticator App  #1 | Web Titans Limited | 4.62692 | 1367 | 2026-01-07 | Free |
| Authenticator App ＋ | Accebits Tech Limited | 3.40534 | 1236 | 2025-12-17 | Free |
| Authenticator App ◦ | Apex Innovate Limited | 4.36595 | 981 | 2024-10-14 | Free |
| Authenticator App • 2FA • MFA | RHO DEVELOPERS LLC | 4.6181 | 906 | 2026-06-23 | Free |
| Authenticator App ⁸ | AGILE CODE LIMITED | 4.57317 | 902 | 2026-07-14 | Free |
| Authenticator App ^ | AUTHENTICATOR APP 2FA AUTH | 4.8842 | 734 | 2024-12-18 | Free |
| Authenticator App : 2FA & MFA | NETRON LLC | 4.47409 | 656 | 2026-06-17 | Free |
| Authentication App - MFA, tOTP | Soufiane Benabid | 4.27627 | 590 | 2026-06-29 | Free |
| Authenticator App © | IntelliVision limited | 3.89948 | 577 | 2026-08-18 | Free |
| Authenticator App－2FAS・MFA・OTP | FLOOMIX LTD | 4.5816 | 576 | 2026-05-04 | Free |
| Authenticator App - 2FA | Fire Technologies Hong Kon | 4.36015 | 547 | 2026-01-13 | Free |
| Authenticator© App | To Ngoc Mai | 4.64947 | 485 | 2026-08-06 | Free |
| OTP Auth | Roland Moers | 4.63655 | 476 | 2023-09-29 | Free |
| authenticator . app | Mustafa Uz | 4.6933 | 463 | 2026-01-29 | Free |
| Authenticator™ App | BOHEM HALICILIK BILISIM IN | 4.07432 | 444 | 2024-10-15 | Free |
| Authenticator App - Two Factor | MAS-MEDIA d.o.o. | 4.6566 | 431 | 2023-02-19 | Free |
| Authenticator | Ali El Malki | 4.31702 | 429 | 2026-04-08 | Free |
| Authenticator | Matt Rubin | 3.67381 | 420 | 2019-06-01 | Free |
| Authenticator App · 2FA | Shanghai FirstOrder Techno | 4.22105 | 380 | 2026-04-11 | Free |
| Authenticator App - Fast 2FA | 珉予 翟 | 4.42626 | 373 | 2023-01-03 | Free |
| Authhy: Authenticator App | 婷 兰 | 4.18082 | 365 | 2024-02-15 | Free |
| Authenticator App ∞ | Rushdata Limited | 3.88131 | 337 | 2025-07-07 | Free |
| RSA Authenticator (SecurID) | RSA Security | 2.68293 | 328 | 2026-07-28 | Free |
| Authenticator - Secure 2fa | Fiision Studio Company Lim | 4.28472 | 288 | 2022-08-26 | Free |
| Yubico Authenticator | Yubico Limited | 3.67018 | 285 | 2026-03-11 | Free |
| Authenticator App ‘ | FLEXI TECH LIMITED | 4.17957 | 284 | 2025-11-23 | Free |
| Namirial OTP | Namirial Spa | 4.58451 | 284 | 2026-07-23 | Free |
| Ente Auth - 2FA Authenticator | Ente Technologies, Inc. | 4.64663 | 283 | 2026-08-03 | Free |
| Authenticator App ¹ | GITU LIMITED | 4.1828 | 279 | 2025-07-27 | Free |
| Authenticator App - 2FA &. MFA | APPLY DIJITAL HIZMETLER TI | 4.31985 | 272 | 2026-05-27 | Free |
| Yandex ID – 2FA Authenticator | DIRECT CURSUS COMPUTER SYS | 4.5748 | 254 | 2026-08-11 | Free |
| Proton Authenticator | Proton AG | 4.39834 | 241 | 2026-08-26 | Free |
| Authenticator App: 2FA・MFA・OTP | Fenix Point d.o.o. | 4.3445 | 209 | 2026-04-01 | Free |
| Internet Protection App 2FA+ | Bayram Gezek | 4.16176 | 204 | 2026-08-26 | Free |
| Authenticator App ' | Prism Lens Limited | 3.6802 | 197 | 2023-08-14 | Free |
| Authy Authenticator | APPIOS BILISIM TEKNOLOJILE | 4.40313 | 191 | 2025-11-24 | Free |
| 2FA App - Authenticator | Nguyen Viet Anh | 4.74074 | 189 | 2026-06-29 | Free |
| Authy Authenticator: MFA & 2FA | Level Clash Apps S.L. | 3.44974 | 189 | 2026-07-24 | Free |
| Raivo - 2FA Authenticator app | MOBIME | 4.37704 | 183 | 2026-06-16 | Free |
| Authenticator: 2FA OTP Codes | Arpit Kakadiya | 4.43258 | 178 | 2026-08-21 | Free |
| OTP Manager | Carlos de Boer Ver Voorn | 4.5 | 176 | 2022-10-22 | Free |
| 2FA Authenticator Secure | 25 Degrees Apps LLC | 4.43678 | 174 | 2026-07-01 | Free |
| FreeOTP Authenticator | Red Hat, Inc. | 3.15116 | 172 | 2025-11-19 | Free |
| TOTP Authenticator | Sparrow Code LTD | 4.7625 | 160 | 2026-08-25 | Free |
| Two Factor Authenticator & OTP | HENRY FOSTER | 4.49681 | 157 | 2026-01-05 | Free |
| Octopus Authenticator | SECRET DOUBLE OCTOPUS LTD | 2.40384 | 156 | 2026-08-19 | Free |
| 2FA Authenticator: OTP Codes | AdSpark OU | 4.52597 | 154 | 2026-06-01 | Free |
| App Authenticator - 2fas Auth | Vipul Prajapati | 4.56163 | 146 | 2026-07-01 | Free |
| Authenticator: OTP, 2FA & Code | YILDIZCO YAZILIM IC VE DIS | 4.66912 | 136 | 2026-06-17 | Free |
| Authenticator: Mobile 2FA, MFA | Zipo Apps Ltd. | 4.52593 | 135 | 2026-08-28 | Free |
| Authenticator App – 2FA & MFA | BEYLER SAGLIK BILISIM SAVU | 4.48148 | 135 | 2025-12-15 | Free |
| Authen・2FA & MFA Authenticator | Thumbmagic Labs LLP | 4.67969 | 128 | 2025-07-24 | Free |
| Authenticator 2FA, MFA, OTP | Steadfast Craft.s.r.o. | 4.47656 | 128 | 2026-08-26 | Free |
| 2FA Authenticator™ MFA Authy | 2fa authenticator L.L.C-FZ | 3.6378 | 127 | 2026-07-09 | Free |
| Authenticator: 2FA & Password | Solid Apps L.L.C-FZ | 3.97561 | 123 | 2026-08-13 | Free |
| Authenticator App - 2FA ◦ MFA | Z ZET LTD | 4.38136 | 118 | 2026-08-28 | Free |
| Authenticator App · 2FA & MFA | Muhammet Yalcın Ozdemir Ha | 4.65812 | 117 | 2026-06-04 | Free |
| MFA Authenticator: Secure 2FA | MINT APPS CAPITAL LTD | 4.44339 | 106 | 2025-05-26 | Free |
| Tofu Authenticator | Calle Luks | 4.56436 | 101 | 2021-10-02 | Free |
| Bitwarden Authenticator | Bitwarden Inc | 3.47368 | 95 | 2026-08-20 | Free |
| Authenticator App - MFA, 2FA | ADRIA GUSTO d.o.o. | 4.70213 | 94 | 2023-07-03 | Free |
| Authe for Google Authenticator | Ravi Patel | 4.38889 | 90 | 2025-07-28 | Free |
| Authenticator App: 2FA - MFA | SAN MOBILE YAZILIM TICARET | 4.46591 | 88 | 2026-01-20 | Free |
| Authenticator App: 2FA, MFA | Hearttell US Limited | 4.1954 | 87 | 2026-04-01 | Free |
| Authenticator・2FA・MFA・OTP | JUST COOL COMPANY DOO | 4.6125 | 80 | 2026-08-14 | Free |
| The authenticator App - 2FA | NEXTPIXEL APPS LLP | 4.39394 | 66 | 2025-01-25 | Free |
| Authenticator: Secure 2FA, MFA | DEDUSHKA DEVELOPMENT - FZC | 4.51613 | 62 | 2026-04-30 | Free |
| MFA Authenticator ‒ Secure 2FA | Uka Osim | 4.41667 | 60 | 2026-08-06 | Free |
| 2FA Authenticator - Auth App | Alina Kubiak | 4.57627 | 59 | 2026-06-10 | Free |
| Authenticator App． | QUANTUM NET LIMITED | 4.45455 | 55 | 2026-06-04 | Free |
| Two Factor Authenticator App | Zipo Apps Ltd. | 4.43635 | 55 | 2026-05-13 | Free |
| Authenticator App | 2FA | JESUS SRL | 4.76596 | 47 | 2026-01-28 | Free |
| Authenticator App ⋆ | Silver Elm Systems LLC | 4 | 47 | 2025-05-14 | Free |
| Multi Authenticator: OTP, MFA | Jadvyga Jusel | 4.66667 | 45 | 2025-09-24 | Free |
| Authenticator App- MFA,2FA,OTP | Foshan Youcheng Intellectu | 4.46666 | 45 | 2026-03-13 | Free |
| Authenticator App－2FAS・OTP・MFA | Global Mobile App Limited | 4.22222 | 45 | 2026-06-10 | Free |
| Authenticator - OTP Manager | FATIH CAN YAZICI | 4.47727 | 44 | 2026-06-12 | Free |
| 2FA: TOTP Authenticator App | Taras Markevych | 4.63415 | 41 | 2026-08-24 | Free |
| Authenticator ℠ | NextGen Software LLC | 3.22222 | 36 | 2026-06-08 | Free |
| iD: Authenticator App | 丹丹 李 | 4.5 | 32 | 2026-01-04 | Free |
| Authenticator: Secure 2FA App | Piotr Kalita | 4.29032 | 31 | 2026-08-27 | Free |
| Authenticator App ｀ | WISDOM DATA LIMITED | 4.29032 | 31 | 2024-12-04 | Free |
| 2FA Authenticator • MFA Verify | Kerli Vahtre | 4.70967 | 31 | 2024-06-27 | Free |
| Two Factor Authenticator | Vinay Jain | 4.3871 | 31 | 2026-07-29 | Free |
| Authenticator App : Scan & 2FA | XSOFT GLOBAL LIMITED | 5 | 29 | 2026-08-04 | Free |
| 2FA Authenticator: MFA RSA | SERAPHINA VINER | 4.67856 | 28 | 2025-08-29 | Free |
| Authy Authenticator: 2FA & MFA | Enveloc, Inc. | 4.92856 | 28 | 2026-02-03 | Free |
| 2FA Verify: Authenticator App | Caprinix LLC | 4.03846 | 26 | 2023-06-16 | Free |
| Smart Log On | Acceptto Corporation | 2.96154 | 26 | 2026-08-08 | Free |
| Authenticator: Secure 2FA Auth | Timon Scherzinger | 4.51999 | 25 | 2025-08-06 | Free |
| MFA Authenticator App | Petr Polasek | 4.17391 | 23 | 2026-07-08 | Free |
| Authenticator App - 2FA Totp | Paroh Kozokero | 4.43478 | 23 | 2025-09-08 | Free |
| Flagscape Authenticator™ | Bank of America | 2.54545 | 22 | 2026-07-06 | Free |
| Password Manager (2FAS Pass) | Two Factor Authentication  | 4.59091 | 22 | 2026-08-24 | Free |
| Authenticator App ＊ | CodeEx Technology Limited | 4.14286 | 21 | 2026-02-05 | Free |
| Authenticator 2FA by GA | Shanghai Rushenzhu Technol | 3.2381 | 21 | 2026-08-14 | Free |
| SecureAuth Authenticate | SecureAuth Corporation | 2.44444 | 18 | 2026-08-03 | Free |
| Authenticator App - DuoShield | ROT GRUPPE DOO | 4.52941 | 17 | 2023-10-09 | Free |
| Authenticator App - Official ™ | TRIPLE IT LTD | 5 | 15 | 2025-02-25 | Free |
| Authenticator App • 2FA | MOBILEOCEAN BILISIM YAZILI | 5 | 14 | 2026-07-01 | Free |
| Authenticator Duo: Two Factor | Quentin Powell | 5 | 14 | 2024-06-19 | Free |
| Authenticator App - 2FA / OTP | SOLID DIJITAL HIZMETLER LI | 4 | 13 | 2026-07-18 | Free |
| Authenticator + 2FA | 长金 陶 | 4.75 | 12 | 2022-11-30 | Free |
| Authenticator: AuthSnap | STAMP Q SIA | 4.45455 | 11 | 2025-08-27 | Free |
| Open Authenticator by Skyost | Hugo Delaunay | 4.54545 | 11 | 2026-06-30 | Free |
| VerifyPro - 2FA Authenticator | TordellApp LLC | 4 | 10 | 2023-02-07 | Free |
| Authenticator App-MFA&2FA Auth | Beijing Fenglan Technology | 4.8 | 10 | 2026-02-09 | Free |
| Authenticator App ：2FA, MFA | Global Mind Cloud GmbH | 4.8 | 10 | 2026-02-19 | Free |
| Authenticator App - SafeAuth | Brilliant App Limited | 5 | 9 | 2026-01-15 | Free |
| Authenticator App - OTP, 2FA | Specter Apps Inc | 4.33333 | 9 | 2026-08-21 | Free |
| Authenticator: Password Keeper | CROSSING PUB LTD | 4.5 | 8 | 2025-03-25 | Free |
| Authenticator Duo - Two Factor | Adan Malon | 3.875 | 8 | 2024-08-19 | Free |
| Authenticator App: 2FA MFA | Valerii Fedorak | 5 | 7 | 2026-07-19 | Free |
| Authenticator App・ 2FA, MFA | 090Bravo Hong Kong Limited | 4.57143 | 7 | 2026-07-16 | Free |
| 2FA Authenticator・OTP Authy | Dritan Kola | 4 | 7 | 2025-11-14 | Free |
| Authenticatorⓒ App | MTWOM LIMITED | 4.42856 | 7 | 2026-08-24 | Free |
| Secure Authenticator: OTP, MFA | Preston Rice | 4.57143 | 7 | 2025-01-17 | Free |
| Authenticator App! | Var Meta Technology Joint  | 4.33333 | 6 | 2026-07-16 | Free |
| Authenticator App - Authy, 2FA | 满 李 | 4.33333 | 6 | 2025-08-14 | Free |
| 2FA Authenticator - All in one | HYPERLINK INFOSYSTEM INC. | 5 | 6 | 2026-08-12 | Free |
| Authenticator - OTP Security. | Toni Pessey | 4.16667 | 6 | 2024-10-17 | Free |
| Authenticator - Two Factor App | Mats Vink | 3.83333 | 6 | 2024-10-19 | Free |
| VMP Authenticator App | VPN VPN VPN Proxy Master U | 5 | 5 | 2026-08-04 | Free |
| 2FA and MFA Authenticator | John Harvey | 4.59999 | 5 | 2026-07-24 | Free |
| Authenticator App One | BLUE ARC LIMITED LIABILITY | 4.8 | 5 | 2026-08-16 | Free |
| Mobile 2FA Authenticator App | Phoebe Crowhurst | 4.2 | 5 | 2026-02-12 | Free |
| Authenticator App 2FA, MFA | Jonas Endthaller | 4.2 | 5 | 2026-08-25 | Free |
| 2FA Authenticator Password App | FOODS SH.P.K. | 4 | 4 | 2026-07-20 | Free |
| TOTP Authenticator - OTP | Abuzer Firdousi | 5 | 4 | 2025-08-01 | Free |
| 2FA Authenticator-MFA,OTP,Auth | 朝虹 陈 | 5 | 4 | 2025-01-16 | Free |
| Authenticator - OTP Security | Jay Clauer | 5 | 4 | 2024-10-01 | Free |
| 2FA Authenticator - OTP Auth | Yildirimhan Atcioglu | 4.25 | 4 | 2026-07-22 | Free |
| Auth | Oliver Hayman | 5 | 4 | 2026-07-07 | Free |
| Authenticator App -2FA Secure | Authenticator Technology L | 3 | 3 | 2026-01-29 | Free |
| Sign&go Authenticator | ILEX | 2.33333 | 3 | 2025-09-25 | Free |
| Authenticator App - 2FA, OTP | KRUTAGNA INFOTECH | 4.5 | 2 | 2026-07-30 | Free |
| Authenticator: 2FA Auth & MFA | .ARSAN SOFIA LARSAN | 5 | 2 | 2026-06-01 | Free |
| 2FA Authenticator - MFA Auth. | Thinkabout LTD | 5 | 2 | 2026-06-09 | Free |
| Authenticator 2FA TOTP OTP MFA | LYKOV STUDIO LTD | 5 | 2 | 2026-08-20 | Free |
| MFA Authenticator - Secure 2FA | Zahid Ullah | 4.5 | 2 | 2026-07-20 | Free |
| Authenticator: 2FA Code & OTP | 志兵 袁 | 4.5 | 2 | 2026-08-22 | Free |
| TOTP Authenticator - 2FA | 悦 刘 | 4 | 2 | 2024-05-01 | Free |
| Argus - TOTP Authenticator | 晖 金 | 4.5 | 2 | 2021-09-22 | Free |
| QuickOTP Authenticator Passkey | Bruno Tereso | 5 | 2 | 2026-07-17 | Free |
| Authenticator - 2FA Auth App | 兵 张 | 5 | 2 | 2026-05-11 | $0.99 |
| Authenticator - 2FA/MFA | 园 周 | 5 | 2 | 2026-04-08 | Free |
| Authenticator App - Auth Code | Pro App Company Limited | 5 | 1 | 2026-08-26 | Free |
| Alinma Authenticator | Alinma Bank | 5 | 1 | 2025-05-21 | Free |
| 2FA Authenticator App - TOTP | Himanshu Rupareliya | 3 | 1 | 2024-03-17 | Free |
| Authenticator App: Safe 2FA | 4INGENS doo Novi Sad | 5 | 1 | 2026-01-20 | Free |
| 2FA Authenticator: Moat | 俊峰 罗 | 5 | 1 | 2026-08-20 | Free |
| 2FA Authenticator Code | FUTUREFOOD LLC | 5 | 1 | 2026-08-19 | Free |
| 2FA Authenticator: Mabi Auth | Roberto Culpepper | 5 | 1 | 2026-08-06 | Free |
| HotKey OTP: 2FA Authenticator | Hayk Bareghamyan | 5 | 1 | 2026-07-19 | Free |
| Minimo Authenticator - 2FA | MINIMO TECH | 3 | 1 | 2025-12-10 | Free |
| Authenticator: 2FA Authy & MFA | Rizki ARDYANSAH | 5 | 1 | 2026-08-25 | Free |
| SystoLOCK Companion | Systola GmbH | 5 | 1 | 2026-08-25 | Free |
| TOTP | Vinod Mathew | 1 | 1 | 2020-07-26 | Free |
| Authenticator App₊ | VUNYO BILGI TEKNOLOJILERI  | 5 | 1 | 2026-07-07 | Free |
| Authenticator: 2FA,MFA & OTP | AQUAWOOD PTE. LTD. | 5 | 1 | 2026-05-20 | Free |
| Authenticator: 2FA & OTP App | Hitesh Bhagchandani | 5 | 1 | 2026-08-24 | Free |
| 2 factor authentication | Appnap Technologies Limite | 5 | 1 | 2024-10-24 | Free |
| Authenticator App: OTP and 2FA | Sky Stack Systems LLC | 5 | 1 | 2026-05-24 | Free |
| Authenticator App º | Softcap | 5 | 1 | 2026-05-25 | Free |
| MFA Authenticator & 2FA | Dayana Networks Ltd | 5 | 1 | 2023-04-04 | Free |
| Authenticator App| 2FA Authy | Ahmad Waheed | - | - | 2026-08-27 | Free |
| Authenticator App: 2FA & MFA. | ESSA STUDIO, MCHJ | - | - | 2026-08-05 | Free |
| Authenticator App - 2FA App | Temurbek Rakhimov | - | - | 2026-08-26 | Free |
| Authenticator App : SafeAuth | Arvind Murali | - | - | 2026-07-29 | Free |
| Authenticator App: Secure 2FA | HUYNH DUONG VAN | - | - | 2025-09-15 | Free |
| Authenticator App‧‧ | MP 36 LLC | - | - | 2026-06-04 | Free |
| Authenticator App - 2FA PRO | Denis Vithani | - | - | 2024-12-04 | Free |
| Authenticator app ・ 2FA & MFA | Olivia Martinez | - | - | 2026-02-11 | Free |
| Authenticator App: 2FA MFA. | Denis Kondratovich | - | - | 2026-01-23 | Free |
| MyID Authenticator | Intercede Limited | - | - | 2026-06-01 | Free |
| Authenticator App 2FA - Vats | GOKTUG CETIN | - | - | 2026-08-08 | Free |
| Authenticator App - Secure 2FA | Quntm Technology Group LLC | - | - | 2026-04-21 | Free |
| Tap2 - 2FA Authenticator App | Bodrya Hardikkummar Vinodb | - | - | 2025-06-13 | Free |
| G Authenticator App: 2FA & MFA | Calify LTD | - | - | 2026-08-17 | Free |
| 2FA Authenticator App: Codexa | Pulsebyte Studios Inc. | - | - | 2026-08-11 | Free |
| eScan Authenticator | MicroWorld Technologies In | - | - | 2025-12-17 | Free |
| KeyVault Authenticator App | Polydez | - | - | 2026-01-22 | Free |
| Authenticator app universal | HEYOKA BILISIM ANONIM SIRK | - | - | 2025-10-30 | Free |
| 2FA Authenticator App MFA, OTP | Sandy Radadiya | - | - | 2026-05-13 | Free |
| 2FA Authenticator: TrueAuth | Thomas Weschke | - | - | 2026-07-22 | Free |
| 2FA Authenticator - MFA Auth | Muhammad Ajmal Shah | - | - | 2024-05-18 | Free |
| Authenticator 2FA-MFA,TOTP | 泽雄 陈 | - | - | 2026-08-08 | Free |
| Authenticator 2FA & OTP – Ring | MOBNESS LTD | - | - | 2026-03-29 | Free |
| Authenticator App - 2FA AI | Fluxiva Dijital Hizmetler  | - | - | 2025-10-21 | Free |
| Authenticator App : 2FA & MFA | Ahmad Zohaib | - | - | 2025-06-24 | Free |
| Secure Authenticator: 2FA | BORIS BOBROV | - | - | 2026-06-15 | Free |
| Authenticator: 2FA & Passkey | AQUAWOOD PTE. LTD. | - | - | 2025-12-20 | Free |
| Authenticator App : OTP & 2FA | ELGO LEARNING LIMITED | - | - | 2026-04-15 | Free |
| Cloud Authenticator: MFA & 2FA | DEVSIG TECHNOLOGIES PRIVAT | - | - | 2025-02-24 | Free |
| 2FA Authenticator - KeyFort | Westeresch B.V. | - | - | 2026-03-31 | Free |
| TrustOTP: 2FA Authenticator | Jeancandio Akademi, LLC. | - | - | 2026-08-28 | Free |
| Authenticator TOTP | Boris Spiro | - | - | 2026-08-11 | Free |
| TOTP Authenticator - 2FA OTP | Keita Iwasaki | - | - | 2026-04-13 | Free |
| Level - 2FA Authenticator | MediabyteCo Ltd. | - | - | 2026-02-13 | Free |
| TOTPFree | Guangzhou Xigou Technology | - | - | 2026-03-20 | Free |
| AICC Authenticator | ALMANTIQ ALAMIN COMPANY | - | - | 2023-12-19 | Free |
| OTP Authenticator | Swiss SafeLab GmbH | - | - | 2015-08-25 | Free |
| 2FA Authenticator: OTP Auth | APPREKA YAZILIM TEKNOLOJIL | - | - | 2026-07-16 | Free |
| OTP Authenticator - TOTP 验证器 | 凯 程 | - | - | 2021-05-04 | Free |
| Two Factor: Authenticator | Roman Baulin | - | - | 2025-04-16 | Free |
| Multifactor authentication mfa | ALEKSANDR NESTEROV, IE | - | - | 2026-02-03 | Free |

### 7.2 Play（品类内 39 款，按装机量降序）

| 名称 | 开发者 | 评分 | 评分量 | 装机 | 变现 |
|---|---|---|---|---|---|
| Microsoft Authenticator | Microsoft Corporation | 4.645919 | 2772636 | 100,000,000+ | 无变现 |
| Google Authenticator | Google LLC | 3.8579113 | 676835 | 100,000,000+ | 无变现 |
| Duo Mobile | Cisco Systems, Inc. | 4.184526 | 86626 | 50,000,000+ | 无变现 |
| CieID | Istituto Poligrafico e Zec | 4.72 | 645250 | 10,000,000+ | 无变现 |
| Authenticator App | Starnest JSC | 4.128039 | 104271 | 10,000,000+ | IAP+广告 |
| Twilio Authy Authenticator | Authy | 3.671005 | 96741 | 10,000,000+ | 无变现 |
| BankID security app | Finansiell ID-Teknik BID A | 3.17 | 55167 | 10,000,000+ | 无变现 |
| S-pushTAN - sichere Freigaben | Star Finanz GmbH | 2.950495 | 53916 | 10,000,000+ | 无变现 |
| Okta Verify | Okta Inc. | 3.9837337 | 43502 | 10,000,000+ | 无变现 |
| Cl@ve | Agencia Estatal de Adminis | 2.42 | 31015 | 10,000,000+ | 无变现 |
| RSA Authenticator (SecurID) | RSA Security | 3.3076923 | 18007 | 10,000,000+ | 无变现 |
| NH올원뱅크(농협은행 대표 플랫폼) | NH농협 | 4.357143 | 8427 | 10,000,000+ | 无变现 |
| itsme | Belgian Mobile ID | 4.69 | 408535 | 5,000,000+ | 无变现 |
| Smart-ID | SK ID Solutions AS | 4.47 | 240227 | 5,000,000+ | 无变现 |
| Commerzbank photoTAN | Commerzbank AG | 4.36 | 81590 | 5,000,000+ | 无变现 |
| ID.me Authenticator | ID.me | 3.5219743 | 72704 | 5,000,000+ | 无变现 |
| 2FA Authenticator (2FAS) | 2FAS | 4.2806325 | 32438 | 5,000,000+ | 无变现 |
| PingID | Ping Identity Corporation | 2.745098 | 8164 | 5,000,000+ | 无变现 |
| NINAuth | Technology Innovation Team | 4.7345133 | 84406 | 1,000,000+ | 无变现 |
| Authenticator App - 2FA Auth | Universe Digital Hizmetler | 4.576389 | 78209 | 1,000,000+ | IAP+ |
| LastPass Authenticator | LastPass US LP | 4.470588 | 17625 | 1,000,000+ | 无变现 |
| Authenticator 2FA: OTP Backup | SUNMARE DIGITAL TEKNOLOJI  | 4.3137255 | 13081 | 1,000,000+ | IAP+ |
| Authenticator App - OneAuth | Zoho Corporation | 4.71 | 9276 | 1,000,000+ | 无变现 |
| FreeOTP Authenticator | Red Hat | 3.06 | 5801 | 1,000,000+ | 无变现 |
| TOTP Authenticator – 2FA Cloud | Nexora Digitech | 3.67 | 5637 | 1,000,000+ | IAP+ |
| Proton Authenticator | Proton AG | 4.8656716 | 13443 | 500,000+ | 无变现 |
| Aegis Authenticator - 2FA App | Beem Development | 4.67 | 6208 | 500,000+ | 无变现 |
| Ente Auth - 2FA Authenticator | Ente Technologies, Inc. | 4.5940595 | 2461 | 100,000+ | 无变现 |
| TOTP Authenticator | Sparrow Code | 4.357143 | 2091 | 100,000+ | IAP+ |
| Bitwarden Authenticator | Bitwarden Inc. | 3.94 | 1389 | 100,000+ | 无变现 |
| Authenticator App: 2FA & OTP | Vidus6 | 4.7 | 3111 | 50,000+ | IAP+ |
| Authenticator Secure App | Wallet Assistant | 3.1351352 | 529 | 50,000+ | IAP+ |
| OTP Authenticator App | Polydez | - | - | 50,000+ | IAP+ |
| Stratum - Authenticator App | jmh.me | 4.8 | 601 | 10,000+ | 无变现 |
| UserLock Push | IS Decisions | 4.7105265 | 154 | 10,000+ | 无变现 |
| Authenticator 2FA by KeepSolid | KeepSolid Inc | 3.7058823 | 50 | 5,000+ | 无变现 |
| Sentinel 2FA Authenticator | Tommaso Carpi | 4.5 | 104 | 1,000+ | IAP+ |
| Card Authenticator | WEX, Inc. | 3.8888888 | 9 | 1,000+ | 无变现 |
| iShield Key TOTP | Swissbit AG | - | - | 500+ | 无变现 |
