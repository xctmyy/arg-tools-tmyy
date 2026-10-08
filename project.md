# project.md —— 技术设计文档

## 1. 项目定位

`arg.xc` 是一个面向 **ARG（另类实境游戏）创作者**的桌面工具箱。

ARG 的特点是：谜题散布在真实世界的各种载体上——网页、音频、图片、邮件、电话、
社交平台，玩家需要跨媒介收集线索、解密、拼接，才能推进剧情。创作者在搭建这样一条
链路时，要在十几个互不相干的工具之间反复横跳（在线解码站、音频频谱软件、十六进制
编辑器、网页历史快照……）。

本项目要解决的就是这件事：**把这条链路上高频、可自动化的环节收进一个应用**，
让创作者能在一个窗口里完成"藏 -> 测 -> 编排 -> 校验"的闭环。

## 2. 技术选型

### 2.1 UI 库

| 候选 | 优点 | 缺点 | 结论 |
| --- | --- | --- | --- |
| **CustomTkinter** | 纯 Python，仅需 `pip install customtkinter`；Tk 属标准库，无额外系统依赖；现代扁平深色主题，观感远超原生 tkinter；打包体积小；学习成本低 | 动画与复杂布局能力有限，不适合做重图形界面 | **选用** |
| Flet | 基于 Flutter，观感最现代，支持响应式与动画，可同时打包桌面 / Web / 移动 | 运行时较重，自带异步模型，心智负担高于本项目所需 | 备选 |
| NiceGUI | Web 技术栈，写起来极简，表格 / 图片 / 音频等富内容展示强 | 本质是起一个本地 Web 服务，需浏览器承载，不是纯桌面应用 | 备选 |
| PySide6 / PyQt | 能力最强，控件最全 | 体量大、许可与打包都更复杂，对本项目明显过重 | 不选 |

**结论：CustomTkinter。** 在"足够简单"和"足够美观"之间它是最优解——
装一个包就能跑，深色界面开箱即用，且天然适合本项目这种"表单 + 结果展示"型的工具界面。

外观默认 `Dark` 模式 + `blue` 配色，可在 `src/config/settings.py` 中调整。

### 2.2 分层

```
main.py            仅负责启动
  └── src/app.py          装配：配置 -> 主题 -> 主窗口
        ├── src/config/   常量与用户设置
        ├── src/ui/       界面（主窗口 + 功能页 + 右侧 AI 面板）
        │     ├── pages/  一页一文件，自动注册
        │     └── ai_panel.py  常驻右侧的 AI 助手（与页面切换无关）
        ├── src/core/     业务逻辑（不依赖 UI）
        ├── src/ai/       AI 层：LLM、工具注册表、Agent、提示词（规划）
        ├── src/mcp/      MCP 层：client / server（规划）
        └── src/utils/    日志、路径
```

硬性约定：**`src/core/` 不得 import 任何 UI 库**。这样算法层可以脱离界面被测试、
被脚本调用，将来要换 UI 框架（比如换 Flet）也只需重写 `src/ui/`。

## 3. 模块划分

| 模块 | 职责 | 依赖（规划） |
| --- | --- | --- |
| `core/crypto.py` | 替换密码、编码、哈希 | 标准库 |
| `core/stego.py` | 图像 / 音频 / 文本隐写 | Pillow、numpy |
| `core/media.py` | 音视频转码、抽帧、二维码 | Pillow、ffmpeg |
| `core/analysis.py` | 十六进制、类型嗅探、数据提取、网络查询 | 标准库、requests |
| `core/chain.py` | 谜题链数据模型与校验 | 标准库 |
| `core/store.py` | 工程读写 | 标准库 |
| `core/checklist.py` | 试玩 / TINAG 审查清单 | 标准库 |
| `ai/llm.py` | LLM 客户端抽象（OpenAI 兼容 / 本地模型） | requests |
| `ai/tools.py` | **工具注册表**：聚合 `core/*` 函数与 MCP 工具 | 标准库 |
| `ai/agent.py` | Agent 循环：观察 → 选工具 → 执行 → 收敛判断 | — |
| `ai/prompts/` | 按谜题类型的提示词模板库 | — |
| `mcp/client.py` | 作为 MCP client 接入外部工具 | mcp sdk |
| `mcp/server.py` | 作为 MCP server 暴露自身能力 | mcp sdk |

对应的界面页：`project` / `crypto` / `stego` / `media` / `analysis` / `chain`
（+ 规划中的 `ai` / `settings`），与 `core` 模块一一对应。

### 3.1 AI / MCP 层设计要点

`src/ai/tools.py` 是**唯一的工具入口**：上游是 Agent，下游同时挂着本地 `core/*`
和远端 MCP 工具。Agent 不需要知道某个能力是本地实现还是外部服务，MCP 的接入因此
不需要改动 Agent 逻辑。

这也是 M0 坚持"core 不依赖 UI"的回报——core 里每个函数天然就是可被 Agent 调用的工具。

## 4. 数据模型（草案）

```python
Node(id, title, carrier, method, difficulty, output, platform)
    carrier:  text | image | audio | video | file | website | offline
    method:   对应 crypto/stego 的算法标识
    output:   本节点产出的内容，即下一节点的输入

Chain(name, nodes, links)
    links:    [(from_id, to_id), ...]
    validate() -> list[str]          检查断链、孤立节点、输入输出不匹配
    difficulty_curve() -> list[int]  按链路顺序输出难度序列
```

工程落盘为目录：`project.json` + `clues.json` + `chain.json` + `assets/`。

## 5. 开发路线图

完整任务分解与进度见 [plans.md](plans.md)。里程碑概览：

- **M0 骨架（已完成）** — 目录、分层、UI 外壳、页面注册机制。功能全部为占位。
- **M1 可用核心** — `crypto` 全量实现 + 对应页面；`store` 支持工程新建 / 打开 / 保存。
- **M2 多媒体** — `stego` 图像 LSB 与频谱图、`media` 转码与二维码、`analysis` 文件与网络。
- **M3 编排与审查** — `chain` 节点图可视化与连通性校验、`checklist` 审查清单。
- **M4 AI 解题** — `src/ai/`：LLM 客户端、工具注册表、提示词库、Agent 循环。
- **M5 MCP 集成** — `src/mcp/`：接入外部 MCP 工具、暴露自身能力。
- **M6 打磨与发布** — 设置持久化、主题切换、工程导入导出、打包为单文件 exe。

M4 / M5 按需求排在核心功能之后。

## 6. 开发约定

- 常量集中放 `src/config/settings.py`，不在业务代码里散落魔法值。
- 新增功能页：在 `src/ui/pages/` 建 `xxx_page.py` -> 继承 `BasePage` ->
  登记进 `pages/__init__.py` 的 `PAGES`。主窗口自动生成导航。
- 日志统一走 `src/utils/logger.py` 的 `get_logger()`。
- 路径统一走 `src/utils/paths.py` 的 `resolve()`。

## 7. 参考资料

- [plans.md](plans.md) —— 开发计划与进度跟踪
- [doc/ARG工具调研.md](doc/ARG工具调研.md) —— ARG 创作工具链调研（联网整理）
