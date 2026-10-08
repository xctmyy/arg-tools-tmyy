# ARG 创作工具调研

> 调研时间：2026-10-08
> 目的：摸清"做一个 ARG 需要哪些工具"，为 `arg.xc` 的功能规划提供依据。
> 方法：联网检索中文 ARG 社区（迷雾论坛 / 迷雾 Wiki）、开源 ARG 工具仓库、
> 英文 ARG 设计文献与技能包，交叉整理。

---

## 1. ARG 是什么，决定了它需要什么工具

ARG（Alternate Reality Game，另类实境游戏）又称"平行实境游戏"。它不把玩家关在一个
客户端里，而是**以真实世界和互联网为舞台**：线索藏在网页源码、音频频谱、图片像素、
电话号码、社交账号、快递包裹里，玩家在现实中协作解密、推进剧情。

两个核心概念：

- **TINAG**（This Is Not A Game）—— 游戏伪装成真实事件。所有载体必须自洽，
  不能出现"这是个游戏"的破绽。这是 ARG 与普通解谜游戏最大的分野。
- **Puppetmaster**（幕后操盘手）—— 创作者不直接露面，而是以"角色"身份
  发布内容、回应玩家，实时调整剧情走向。

因此 ARG 的工具需求天然分成两类：**创作者侧**（怎么把信息藏进去、怎么编排链路）
和**玩家侧**（怎么把它挖出来）。优秀的 ARG 工具往往两边都要能打——创作者必须
先用玩家工具验证自己的谜题可解。

一条典型谜题链的样子：

```
剧情碎片 → 频谱图藏图 → YouTube 音频 → 电话号码 → 电话 IVR 报出密码 → 下一关
```

每个环节都要有工具支撑。

---

## 2. 工具链全景

按创作流程分层，共七层。

### 2.1 叙事与设计层

先有故事，后有谜题。这一层是纯方法论，工具多为"框架"而非"软件"。

| 要素 | 说明 |
| --- | --- |
| 核心叙事 | 一句话讲清"谁、为了什么、藏着什么"。所有谜题必须服务它 |
| 入口（Trailhead） | 玩家第一个能发现的东西。必须"看起来是自然存在的" |
| 连接器（Connector） | 把上一个谜题的产出，变成下一个谜题的输入 |
| 谜题链（Recipe） | `[内容] → [隐藏手法] → [入口] → [连接器] → [下一关]` |
| 节奏与难度曲线 | 难度标定 1-5，全程应有起伏，开头必须极低 |
| 玩家类型 | 不同玩家偏好不同谜题，链路要覆盖多类 |

关键设计原则：**Crimes Against Mimesis**（破坏沉浸感的错误）要极力避免——
错别字、现代网络用语、时间线矛盾、账号注册时间不合理，都会瞬间戳破 TINAG。

### 2.2 密码与编码层

ARG 最核心的工具类别。玩家挖出密文后要靠它还原。

**经典替换 / 移位密码**

| 算法 | 难度 | 说明 |
| --- | --- | --- |
| 凯撒 / ROT13 | 1 | 固定位移替换，最基础的入门密码 |
| Atbash | 1 | 字母表镜像替换 |
| A1Z26 | 1 | 字母转序号（A=1, Z=26） |
| 维吉尼亚密码 | 2 | 由多组凯撒组成，需要密钥 |
| 栅栏密码 | 2 | 字符按位置重排 |
| Playfair | 3 | 双字母组替换，需 5×5 方阵 |
| Nihilist | 3 | 需要密钥方阵 + 数字运算 |
| 书本密码 | 3 | 用"页码-行-字"定位，依赖共享书籍 |

**编码**

Base16/32/64、摩斯电码、二进制、十六进制、ASCII、URL 编码、HTML 实体、
Brainfuck / Ook、ITA2 码、Code49 条形码、Unicode 变体。

**哈希 / 校验**

MD5、SHA 家族（SHA-1 / SHA-256）、CRC 家族、DES / AES / RSA / DSA（用于构造
需要"破解"的场景）。

**推荐工具**

| 工具 | 说明 |
| --- | --- |
| **CyberChef** | GCHQ 出品的"网络瑞士军刀"，数百种编解码/加解密可自由串联。首选 |
| **dCode.fr** | 经典密码工具箱，覆盖极全，含冷门密码 |
| **Cryptii** | 界面友好，支持实时转换与管道式组合 |
| **Quipqiup** | 自动破解替换密码（词频分析） |
| OpenSSL | 命令行加解密，覆盖主流算法 |
| John the Ripper | 哈希破解，支持多种算法 |
| 焖肉面 | 中文 puzzle hunt 工具集，适合中文谜题 |

### 2.3 隐写与多媒体层

"把信息藏进载体"的手段，按载体类型分。

| 载体 | 手法 |
| --- | --- |
| **文本** | 零宽字符、Unicode 同形字、HTML 注释、元数据字段、首字母藏头 |
| **图像** | LSB（最低有效位）隐写、色彩通道分离、图层隐藏、二维码、EXIF 元数据 |
| **音频** | 频谱图藏图、倒放、DTMF 双音多频、变速、声道分离、摩斯音 |
| **视频** | 逐帧插入、字幕轨、时间码、音轨分离 |
| **文件** | 嵌套压缩包、多格式复合文件（polyglot）、附加数据 |

**推荐工具**

| 工具 | 类型 | 说明 |
| --- | --- | --- |
| **Audacity** | 音频 | 开源音频编辑，频谱分析与可视化 |
| **Sonic Visualiser** | 音频 | 专业音频分析，专门用来看频谱里藏的图 |
| RXSSTV | 音频 | SSTV 慢扫描电视信号解码，把音频还原成图像 |
| **StegSolve** | 图像 | 隐写分析，可切换色彩通道、查 LSB |
| Stegdetect | 图像 | 检测 JPEG 中的隐写痕迹 |
| **ExifTool** | 图像 | 读写 EXIF 等元数据 |
| GIMP | 图像 | 开源图像编辑，通道/图层操作 |
| Steganography Online | 在线 | 图像隐写的在线嵌入与提取 |

### 2.4 资源分析层（玩家侧逆向）

玩家拿到一个可疑文件后，需要"往下看一层"。

| 工具 | 说明 |
| --- | --- |
| **Binwalk** | 固件/文件分析，提取嵌套的文件和数据 |
| **HxD** | 十六进制编辑器，查看与编辑二进制 |
| **7-Zip** | 解压缩，支持多格式与深层嵌套 |
| **Wireshark** | 网络协议分析，抓包看流量 |
| **Burp Suite** | Web 安全测试，拦截修改 HTTP 请求 |
| **Postman** | API 调试，构造 HTTP 请求 |
| Wayback Machine | 互联网档案馆，看网站历史快照——ARG 常用"改版"手法 |
| WHOIS Lookup | 域名注册信息查询，验证"这个网站是谁建的" |
| CyberChef / CTF Tools | 综合在线工具集 |

### 2.5 平台与分发层

ARG 的内容要落在真实平台上，这一层决定"玩家在哪里遇到线索"。

| 用途 | 推荐平台 |
| --- | --- |
| 实时互动 | Discord、Telegram、QQ 群 |
| 电话 / 语音 | Twilio（IVR 交互式语音应答） |
| 叙事博客 / 伪官网 | WordPress、Dreamwidth、自建静态站 |
| 内容投放 | YouTube（含"复活彩蛋"）、Pastebin、GitHub |
| 社交账号 | 微博、X/Twitter、B 站、小红书 |
| 线下 | 实体信件、包裹、海报、线下场地 |

**关键点**：入口（Trailhead）必须"有机"——它得像是虚构世界里本来就存在的东西。
一个刚注册三天、只有一条推文的账号，本身就是破绽。

### 2.6 玩家社区与运营层

ARG 是**实时运营**的游戏，Puppetmaster 要在玩的过程中调整剧情。

| 需求 | 说明 |
| --- | --- |
| 玩家协作 | 论坛 / Discord 分区，玩家自发整理线索 |
| 进度追踪 | 哪些谜题被解开了、卡在哪里、需要放水还是加码 |
| 角色扮演 | 以角色身份发布内容，保持人设一致 |
| 应急预案 | 玩家提前破解、卡死、发现破绽时的应对 |
| 内容排期 | 发布时间表，保证节奏 |

中文社区可参考**迷雾论坛 / 迷雾 Wiki**（mistarg.cn），有完整案例库与协作机制。

### 2.7 质量保障层

上线前必须自查。核心是**试玩**：创作者用玩家工具完整走一遍自己的链路。

| 检查项 | 内容 |
| --- | --- |
| 连通性 | 每个谜题的产出，确实是下一个谜题的输入，无断链 |
| 难度曲线 | 开头够简单，中段有起伏，无"劝退墙" |
| 线索冗余 | 关键节点应有多条线索可达，避免单点卡死 |
| TINAG 一致性 | 无破绽：账号时间线、用词、错别字、平台合理性 |
| 游戏外边界 | 玩家不该把剧情误当真实事件去报警/求助 |
| 合规与伦理 | 隐私、版权、不涉及真实伤害、不越界 |

---

## 3. 工具速查表（按类别汇总）

| 类别 | 首选工具 |
| --- | --- |
| 综合编解码 | CyberChef、dCode.fr、Cryptii |
| 替换密码破解 | Quipqiup |
| 音频分析 | Audacity、Sonic Visualiser、RXSSTV |
| 图像隐写 | StegSolve、ExifTool、Steganography Online |
| 文件分析 | Binwalk、HxD、7-Zip |
| 网络分析 | Wireshark、Burp Suite、Postman |
| 网页历史 / 域名 | Wayback Machine、WHOIS |
| 平台分发 | Discord、Telegram、Twilio、WordPress、YouTube |
| 图像编辑 | GIMP |

---

## 4. 经典案例（可参考的谜题链设计）

| 案例 | 年份 | 特点 |
| --- | --- | --- |
| **I Love Bees** | 2004 | 宣传《光环 2》。电话亭、蜂鸣音频、集体协作解谜，ARG 教科书 |
| **Year Zero** | 2007 | Nine Inch Nails 专辑配套。USB 藏在演唱会现场、频谱藏图 |
| **Cicada 3301** | 2012 起 | 极简入口（一张图）层层递进，涉及密码学、隐写、暗网 |
| **iKnowGhost** | — | 中文 ARG 代表作，冰岩 & 烛芯团队 |
| **The Erebus Protocol** | 2026 | 中文 ARG，43 个页面的纯静态站点解谜 |
| 迷雾新手教程 | 2026 | 中文社区做的可实际游玩的教学 ARG，含信息搜索与解密 |

---

## 5. 对 `arg.xc` 的映射

调研结论直接落到项目模块：

| 调研发现 | 对应模块 | 优先级 |
| --- | --- | --- |
| 密码 / 编码是最高频需求 | `core/crypto.py` + `crypto` 页 | M1 |
| 隐写是 ARG 的标志性手法 | `core/stego.py` + `stego` 页 | M2 |
| 音视频加工与二维码 | `core/media.py` + `media` 页 | M2 |
| 文件逆向与网络线索 | `core/analysis.py` + `analysis` 页 | M2 |
| 谜题链编排与连通性校验 | `core/chain.py` + `chain` 页 | M3 |
| 试玩 / TINAG 审查清单 | `core/checklist.py` | M3 |
| 工程与线索管理 | `core/store.py` + `project` 页 | M1 |

**结论**：本项目的差异化不在"再造一个 CyberChef"（在线编解码工具已足够好），
而在于**把"藏"和"解"两端的工具、以及谜题链的编排与校验，收进同一个工作台**——
这正是目前市面上最缺的一环。

---

## 6. 参考来源

- 迷雾 Wiki —— ARG 工具和科普：https://wiki.mistarg.cn/index.php/工具和科普
- 迷雾 Wiki 首页：https://wiki.mistarg.cn/
- 迷雾论坛 · 新人 ARG 创作指南：https://www.mistarg.cn/topic/138/
- 迷雾论坛 · 迷雾新手教程：https://www.mistarg.cn/topic/352/
- 知乎 · ARG 设计经验分享：https://zhuanlan.zhihu.com/p/544518834
- 知乎 · 如何设计一款平行实境游戏：https://www.zhihu.com/question/298471727
- GitHub · NickPaterson/arg-toolkit：https://github.com/NickPaterson/arg-toolkit
- GitHub · PotatoBiscuit/AlternateRealityGameToolkit：https://github.com/PotatoBiscuit/AlternateRealityGameToolkit
- GitHub · Ray2026qd/signal-zero-arg：https://github.com/Ray2026qd/signal-zero-arg
- LobeHub · arg-designer 技能包：https://lobehub.com/zh/skills/greenie-neuko-arg-skills-arg-designer
- ResearchGate · Criteria for Producing Quality Alternate Reality Games
