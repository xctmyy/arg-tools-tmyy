# plans.md —— 开发计划与进度

> 最后更新：2026-10-08
> 状态图例：`[x]` 已完成 · `[~]` 进行中 · `[ ]` 未开始 · `[-]` 已取消

---

## 1. 项目目标

`arg.xc` 是面向 **ARG（另类实境游戏）创作者**的桌面工具箱，解决三个问题：

1. **藏** —— 把信息藏进图片 / 音频 / 文本 / 文件的各种载体。
2. **解** —— 把挖出来的密文、隐写、可疑文件还原成明文。
3. **编排与校验** —— 把散落的谜题串成一条链路，检查连通性、难度曲线与沉浸感一致性。

在此之上增加两个扩展方向：

4. **AI 解题** —— 用 Agent + 提示词库自动走通"线索 → 试解 → 验证"的循环。
5. **MCP** —— 通过 Model Context Protocol 接入外部工具，同时把自身能力暴露给外部 AI 客户端。

差异化定位：不重造 CyberChef，而是把"藏"与"解"两端工具、谜题链编排、以及 AI 辅助
收进同一个工作台。详见 [doc/ARG工具调研.md](doc/ARG工具调研.md) 第 5 节。

---

## 2. 功能总览

| 编号 | 功能 | 说明 | 优先级 |
| --- | --- | --- | --- |
| F1 | 工程与线索管理 | 新建 / 打开 / 保存 ARG 工程，线索库增删改查 | P0 |
| F2 | 密码与编码 | 经典密码、Base / 摩斯 / 二进制、哈希、AES / ChaCha20 / RSA / ECC、自动识别 | P0 |
| F3 | 隐写 | 图像 LSB、通道分离、EXIF、音频频谱、零宽字符 | P0 |
| F4 | 多媒体 | 音视频转码、抽帧、二维码生成与识别 | P1 |
| F5 | 文件与网络分析 | 十六进制、类型嗅探、数据提取、WHOIS / 网页快照 | P1 |
| F6 | 谜题链编排 | 节点图、连接器、连通性校验、难度曲线 | P1 |
| F7 | 试玩与设计审查 | 清单式自查：连通性 / 难度 / TINAG / 合规 | P2 |
| F8 | **AI Agent 与提示词** | 接入 LLM，按谜题类型调用提示词模板，自动试解并记录推理链 | P1 |
| F9 | **MCP 集成** | 作为 client 接入外部 MCP 工具；作为 server 暴露自身能力 | P2 |

---

## 3. 里程碑与进度

| 里程碑 | 内容 | 状态 | 完成度 |
| --- | --- | --- | --- |
| **M0** | 项目骨架：目录分层、UI 外壳、页面注册机制 | `[x]` 已完成 | 100% |
| **M1** | 可用核心：F1 工程管理 + F2 密码编码 | `[x]` 已完成 | 100% |
| **M2** | 多媒体能力：F3 隐写 + F4 多媒体 + F5 文件网络 | `[ ]` 未开始 | 0% |
| **M3** | 编排与审查：F6 谜题链 + F7 审查清单 | `[ ]` 未开始 | 0% |
| **M4** | **AI 解题：F8 Agent + 提示词库** | `[~]` 进行中（仅界面框架） | 15% |
| **M5** | **MCP：F9 双向集成** | `[ ]` 未开始 | 0% |
| **M6** | 打磨与发布：设置持久化、打包 exe | `[ ]` 未开始 | 0% |

M4 / M5 按用户要求**排在核心功能之后**，先保证 F1-F7 可用。

---

## 4. 详细任务分解

### M0 骨架（已完成）

- [x] 目录分层：`doc/`、`src/{config,core,ui/pages,utils}/`
- [x] 入口 `main.py`（路径注入 + 启动，保持极薄）
- [x] 配置层 `src/config/settings.py`（常量、路径、用户设置）
- [x] 工具层 `src/utils/{logger,paths}.py`
- [x] UI 外壳 `src/ui/main_window.py`（侧边栏 + 懒加载内容区）
- [x] 页面基类与自动注册机制 `src/ui/pages/`
- [x] 六个功能页占位：project / crypto / stego / media / analysis / chain
- [x] core 七个模块接口占位 + `CAPABILITIES` 清单
- [x] 文档：README、project.md、doc/ARG工具调研.md
- [x] 冒烟测试：页面切换、模块导入、数据模型实例化均通过

### M1 可用核心（已完成）

**F1 工程与线索管理（`core/store.py` + `project` 页）**
- [x] `Project.create / open / save` 实现，落盘格式为 `project.json` + `clues.json` + `chain.json` + `assets/`
- [x] 原子写（临时文件 + 替换），避免中途失败损坏工程
- [x] 线索（clue）数据模型：标题、内容、来源、标签、关联节点、创建时间
- [x] 线索增删改查 + 按关键词 / 标签搜索
- [x] 工程页 UI：新建 / 打开对话框、线索列表、搜索框、编辑器
- [x] 最近打开记录（`AppSettings.recent_projects`，最多 8 条）
- [x] 设置持久化 `data/settings.json`（`load_settings` / `save_settings`）

**F2 密码与编码（`core/crypto.py` + `core/crypto_modern.py` + `crypto` 页）**

经典算法（`crypto.py`，注册表与数据结构在 `crypto_types.py`）
- [x] 替换密码：凯撒、ROT13、ROT47、Atbash、A1Z26、培根密码
- [x] 需密钥：维吉尼亚、栅栏、Playfair、Nihilist、书本密码、仿射、列置换、异或
- [x] 编码：Base16/32/64、Base85、摩斯、二进制、十六进制、URL、HTML 实体、
      Quoted-Printable、Brainfuck/Ook
- [x] 哈希：MD5、SHA-1、SHA-256、SHA-512、CRC32（单向，解码时报错）
- [x] **摩斯电码中文支持**：新增「字符集」参数
      - 标准模式：仅 ASCII，遇到中文给出可读提示并指明切模式
      - Unicode 模式：按字符码点的十六进制逐位转摩斯，**完全可逆**，中文与空格都不丢
- [x] `detect()`：启发式识别输入可能的编码类型
- [x] 暴力枚举：凯撒全位移、栅栏全栏数、培根两种符号集、仿射全 312 种 (a,b) 组合

现代算法（`crypto_modern.py`，依赖 `cryptography`，**不手搓任何密码原语**）
- [x] AES-256-GCM：口令经 PBKDF2 派生，密文头部自带迭代次数与盐，解密不必重填参数
- [x] AES-CBC：原始 hex 密钥 + IV，PKCS7 填充
- [x] AES-ECB：原始 hex 密钥（仅供复现谜题，注释里点明其弱点）
- [x] ChaCha20：原始 hex 密钥 + 16 字节 nonce
- [x] ChaCha20-Poly1305：RFC 8439，12 字节 nonce，认证加密
- [x] RSA：PEM 公钥加密 / 私钥解密，OAEP-SHA256 与 PKCS1v15 两种填充；
      **长文本自动混合加密**（RSA 包住随机 AES 密钥，正文交给 AES-GCM，
      密文带 `AXH1` 魔数以便解码时区分）；私钥文件误填进公钥栏会自动取公钥部分
- [x] ECC / ECIES：临时密钥 ECDH + HKDF + AES-GCM，P-256/384/521 可选
- [x] `key_info()`：读取 PEM 密钥，给出类型 / 长度 / 曲线 / **SHA-256 指纹**
      （同一密钥对的公钥与私钥指纹一致，用于核对密钥身份）
- [x] 动作机制：算法可挂「生成密钥对」这类非编解码操作，UI 自动渲染参数与按钮
- [x] 依赖缺失时不崩：算法照常列出，调用时提示 `pip install cryptography`

界面与线程
- [x] **现代密码独立成页**（`modern_crypto_page.py`）：与经典页共用注册表但布局专门设计
      - 顶部算法选择器（7 个互斥按钮，比下拉更直观）
      - 左栏「密钥侧」：密钥材料 / 密钥对、密钥信息（类型 / 长度 / 曲线 / 指纹）、生成密钥对
      - 右栏「操作侧」：加密 / 解密、明文与结果上下分栏（密文很长，需要整行宽度）
- [x] **随机密钥生成**：密钥 / IV / Nonce 字段带「生成」按钮，用 `secrets` 产生
      密码学安全随机值（不是 `random`）
- [x] 经典页：算法下拉（分组）+ 参数表单自动生成 + 输入/输出双栏 +
      编码/解码/交换/复制/清空/识别/枚举
- [x] 参数控件按类型渲染：text / int / password（掩码 + 显示切换）/ keyfile / dir
      （带浏览）/ choice / **hexkey（带生成）**
- [x] 算法注册表 `REGISTRY` 驱动 UI：新增算法只需改 core 层
- [x] **后台线程执行**：编码 / 解码 / 暴力枚举 / 工具动作走 `src/ui/async_task.py` 的
      `TaskRunner`，大输入、RSA 密钥生成、Brainfuck 解释不再冻住界面；
      忙碌期间禁用交互并拒绝重复提交

界面整体
- [x] 新增 `src/ui/widgets.py` 可复用构件：`Card` 卡片分区、`StatusLine` 语义化状态
      （忙碌 / 成功 / 错误分色）、`Selector` 互斥按钮组、参数控件工厂
- [x] 页面统一版式：标题 + 说明 + 分隔线 + 内容区（`BasePage.build`）
- [x] 侧边栏：品牌区、分隔线、选中项高亮为强调色
- [x] 未实现的页面不再显示干巴巴的「TODO」，改为列出 `planned` 里的规划能力

**测试**
- [x] `tests/test_crypto.py`：覆盖已知向量、往返一致性、错误分支、detect、
      暴力枚举、摩斯中文模式
- [x] `tests/test_crypto_modern.py`：AES/ChaCha20/RSA/ECIES 往返、随机性、
      篡改检测、密钥长度与类型错误；未装 cryptography 时整组跳过
- [x] `tests/test_store.py`：工程生命周期、线索 CRUD、搜索、落盘往返
- [x] `tests/test_async_task.py`：后台任务的成功/失败/忙碌拒绝/线程归属

> 注：在本机沙箱环境下 store 测试较慢（约 40 秒），原因是**删除目录极慢**
> （实测清理 16 个子目录需 33 秒，约 2 秒/目录），非代码问题。测试逻辑本身
> 每个仅 0.02 秒。已改为按测试类共享临时根目录，减少清理次数。

### M2 多媒体能力

**F3 隐写（`core/stego.py` + `stego` 页）**
- [ ] 图像：LSB 嵌入 / 提取、通道分离与图层查看
- [ ] 图像：EXIF 等元数据读写
- [ ] 音频：频谱图生成与查看、倒放、DTMF 解码
- [ ] 文本：零宽字符、Unicode 同形字检测
- [ ] 依赖引入：Pillow、numpy

**F4 多媒体（`core/media.py` + `media` 页）**
- [ ] 音频裁剪 / 倒放 / 变速 / 转码
- [ ] 图像缩放 / 裁剪 / 转码 / 批量处理
- [ ] 视频抽帧 / 截取
- [ ] 二维码生成与识别
- [ ] 依赖引入：ffmpeg（外部二进制，需检测并提示）

**F5 文件与网络（`core/analysis.py` + `analysis` 页）**
- [ ] 十六进制查看器
- [ ] 魔术字节类型嗅探
- [ ] 嵌套 / 附加数据提取（类 binwalk）
- [ ] 元数据读取：EXIF、PDF、Office 属性
- [ ] 网络：WHOIS、Wayback 快照、HTTP 请求调试
- [ ] 依赖引入：requests

### M3 编排与审查

**F6 谜题链（`core/chain.py` + `chain` 页）**
- [ ] `Chain.validate()`：断链、孤立节点、输入输出不匹配
- [ ] `Chain.difficulty_curve()`：难度曲线
- [ ] 节点图可视化（画布拖拽 / 连线）
- [ ] 导出为 DOT / PNG

**F7 审查清单（`core/checklist.py`）**
- [ ] 五个分组的清单内容落地：narrative / puzzle / platform / operation / legal
- [ ] `run_audit()` 对工程跑全量自查，输出报告
- [ ] 审查结果页 UI

### M4 AI 解题（F8）

目标：给一个线索，Agent 自己决定用什么工具、按什么顺序试，最后给出结论和推理过程。

- [ ] **`src/ai/llm.py` —— LLM 客户端抽象**
  - [ ] 统一接口：`chat(messages, tools=None) -> Response`
  - [ ] 适配 OpenAI 兼容 API（可配置 base_url，兼容国产模型）
  - [ ] 预留本地模型适配（Ollama / llama.cpp）
  - [ ] API Key 存 `data/settings.json`，不写进代码库
- [ ] **`src/ai/tools.py` —— 工具注册表**
  - [ ] 把 `core/*` 的函数包装成 LLM 可调用的 tool schema
  - [ ] 自动从各模块的 `CAPABILITIES` 生成工具描述
  - [ ] 与 MCP 工具合并到同一注册表（见 M5）
  - [ ] 工具调用白名单与沙箱约束（不让模型执行任意代码）
- [ ] **`src/ai/prompts/` —— 提示词库**
  - [ ] 按谜题类型分模板：密码破译 / 隐写分析 / 文件逆向 / 频谱读图
  - [ ] 系统提示：ARG 语境、TINAG 意识、输出格式约定
  - [ ] Few-shot 示例集（可引用 doc/ARG工具调研.md 的算法清单）
  - [ ] 模板支持变量注入（当前线索、已有工具输出、历史推理）
- [ ] **`src/ai/agent.py` —— Agent 循环**
  - [ ] 主循环：观察 → 选工具 → 执行 → 记录 → 判断是否收敛
  - [ ] 步数 / 时间 / token 上限，防死循环
  - [ ] 推理链记录：每步的工具、输入、输出、结论
  - [ ] 与 `core/store.py` 打通，线索库作为 agent 的长期记忆
  - [ ] 人工介入点：可暂停、可纠正方向、可回滚到某一步
- [x] **`src/ui/ai_panel.py` —— 右侧 AI 助手面板（界面框架已完成）**
      - 参考 AI IDE 的侧边对话窗口：头部（标题 / 当前上下文 / 关闭）+ 消息列表 + 输入区
      - 做成主窗口的一列而非独立页面：任何页面下都能唤出，与页面切换互不影响
      - 侧边栏「AI 助手」按钮切换，`Ctrl+I` 快捷键，显隐状态随设置落盘
      - 消息支持 user / assistant / note 三种角色；空状态含预设问题（仅填入输入框）
      - 页面切换时自动同步「上下文：xxx」
      - `add_message(role, text)` 是留给 `src/ai/agent.py` 的接口
  - [ ] 把 `_send()` 接到 `src/ai/agent.py`，替换当前的占位回复
  - [ ] 展示推理过程：把每步工具调用与结果折叠展示
  - [ ] 一键把结论写回线索库
  - [ ] 模型与参数配置区（模型、温度、最大步数）—— 放 `settings_page`
  - [ ] 面板宽度可拖拽调整
- [ ] 提示词库可编辑：模板存为可读文件，用户能自己改

### M5 MCP 集成（F9）

- [ ] **`src/mcp/client.py` —— 作为 MCP client**
  - [ ] 连接外部 MCP server（stdio / SSE）
  - [ ] 拉取远端工具清单，注入 `src/ai/tools.py` 的注册表
  - [ ] 连接配置读写（`data/mcp.json`），支持启停单个 server
  - [ ] 连接状态与工具列表的 UI 展示
- [ ] **`src/mcp/server.py` —— 作为 MCP server**
  - [ ] 把 `core/crypto`、`core/stego` 等能力暴露为标准 MCP 工具
  - [ ] 支持 stdio 传输，便于被 Claude / 其他 MCP 客户端接入
  - [ ] 只读优先，写操作需显式开关
- [ ] **`src/ui/pages/settings_page.py`**（新增页）
  - [ ] MCP server 管理：增删、测试连接、查看工具
  - [ ] AI 模型配置、外观与主题

### M6 打磨与发布

- [x] `AppSettings` 序列化到 `data/settings.json`（提前到 M1 完成）
- [ ] 主题切换（深色 / 浅色 / 跟随系统）
- [ ] 工程导入 / 导出为单文件包
- [ ] PyInstaller 打包为单文件 exe
- [ ] 使用文档与示例工程

---

## 5. 架构补充（AI / MCP 层）

M0 定下的分层不变，新增两层，且**同样遵守 core 不依赖 UI 的约定**：

```
main.py
  └── src/app.py
        ├── src/config/     配置
        ├── src/ui/         界面（已有 ai_panel；规划 settings_page）
        ├── src/ai/         AI 层（新增）
        │     ├── llm.py    LLM 客户端
        │     ├── tools.py  工具注册表  ← 同时收 core 函数与 MCP 工具
        │     ├── agent.py  Agent 循环
        │     └── prompts/  提示词模板
        ├── src/mcp/        MCP 层（新增）
        │     ├── client.py 接入外部工具
        │     └── server.py 暴露自身能力
        ├── src/core/       业务逻辑（无 UI 依赖，被 ai 层当作工具调用）
        └── src/utils/
```

关键设计：**`src/ai/tools.py` 是唯一的工具入口**，上游是 Agent，下游同时挂着
本地 `core/*` 和远端 MCP 工具。这样 Agent 不需要知道某个能力是本地实现还是外部服务，
也让 M5 的 MCP 接入不需要改动 Agent 逻辑。

这也是 M0 坚持"core 不依赖 UI"的回报——core 里的每个函数天然就是可被 Agent 调用的工具。

---

## 6. 风险与待决问题

| # | 问题 | 状态 |
| --- | --- | --- |
| R1 | 本机管理版 Python 3.13.12 不含 tkinter，需用系统版 3.13.4 | 已知，见 README |
| R2 | ffmpeg 是外部二进制，打包时需一并处理或做运行时检测 | 待 M2 决策 |
| R3 | LLM API Key 的存储方式（明文 json / 系统凭据管理器） | 待 M4 决策 |
| R4 | Agent 工具调用的安全边界：是否需要完全禁用代码执行 | 待 M4 决策 |
| R5 | MCP server 暴露写操作的风险与开关粒度 | 待 M5 决策 |
| R6 | 隐写 / 逆向类功能可能被误用，是否需加入使用声明 | 待决策 |

---

## 7. 进度记录

| 日期 | 内容 |
| --- | --- |
| 2026-10-08 | M0 完成。搭建目录分层、UI 外壳、页面注册机制、core 接口占位；完成 ARG 工具链调研并写入 doc/；冒烟测试通过。新增 F8（AI Agent）与 F9（MCP）两项规划，排入 M4 / M5。 |
| 2026-10-08 | **M1 完成**。`core/crypto.py` 实现 23 个算法（替换密码 4 + 需密钥 5 + 编码 10 + 哈希 5，含 SHA-512），带注册表驱动 UI；`core/store.py` 实现工程持久化与线索 CRUD；`crypto` 页与 `project` 页落地；设置持久化与最近工程记录提前完成；新增 `tests/` 共 40 项单元测试全部通过。 |
| 2026-10-08 | **编码/解码改为后台线程执行**。新增 `src/ui/async_task.py`（`TaskRunner`）：工作线程只算、主线程用 `after()` 轮询取结果，避免跨线程碰控件。`crypto` 页的编码/解码/暴力枚举接入，忙碌期间禁用按钮并拒绝重复提交。顺带修掉一个真 bug：`base64/base32/base16` 解码遇非 ASCII 输入时，标准库抛的普通 `ValueError` 绕过了只捕获 `binascii.Error` 的 except，导致英文报错直透界面；已改为先校验字符集再解码。测试增至 52 项。 |
| 2026-10-08 | **新增现代密码算法与摩斯中文支持**。算法数由 23 增至 38。拆分出 `crypto_types.py`（数据结构与注册表，供经典/现代两层共用，避免循环依赖）与 `crypto_modern.py`（AES-GCM/CBC/ECB、ChaCha20、ChaCha20-Poly1305、RSA、ECC/ECIES，全部基于 `cryptography` 库，**不手搓任何密码原语**）。引入「动作」机制支持生成密钥对。摩斯新增「字符集」参数：标准模式仅 ASCII 并给出切模式提示，Unicode 模式按码点十六进制编码，中文完全可逆。UI 参数控件扩展为 text/int/password/keyfile/dir/choice 六种。新增依赖 `cryptography>=42`。测试增至 100 项。 |
| 2026-10-08 | **界面优化 + 现代密码独立成页**。新增 `src/ui/widgets.py` 可复用构件（Card 卡片、StatusLine 语义状态、Selector 按钮组、参数控件工厂），页面统一版式（标题+说明+分隔线），侧边栏加品牌区与选中高亮，未实现页面改为列出规划能力。现代密码从经典页拆出，独立成 `modern_crypto_page.py`：左栏密钥侧（密钥材料 / 密钥对 / 密钥信息 / 生成密钥对），右栏操作侧（加密解密 + 上下分栏）。密钥、IV、Nonce 字段加「生成」按钮（用 `secrets`）。新增 `key_info()` 展示密钥类型、长度与 SHA-256 指纹。RSA 加长文本混合加密（RSA 包 AES 密钥，密文带 `AXH1` 魔数）。测试增至 118 项。 |
| 2026-10-09 | **右侧 AI 助手面板（仅界面框架）**。新增 `src/ui/ai_panel.py`：参考 AI IDE 的侧边对话窗口，头部（标题 / 当前上下文 / 关闭）+ 消息列表 + 输入区。做成主窗口的一列而非独立页面，任何页面下都能唤出；侧边栏按钮与 `Ctrl+I` 均可切换，显隐状态随设置落盘。消息支持 user / assistant / note 三种角色，空状态含预设问题（仅填入输入框），页面切换时同步上下文。**尚未接入模型**，发送只显示占位回复；`add_message()` 是留给 `src/ai/agent.py` 的接口。顺带补上 `tests/test_settings.py`（14 项）覆盖设置持久化与最近工程维护。测试增至 132 项。 |
