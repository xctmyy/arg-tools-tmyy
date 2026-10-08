# arg-tools-tmyy

ARG（Alternate Reality Game，另类实境游戏）创作工具箱。

把设计一条谜题链路上会用到的零散工具收进一个桌面应用：密码编解码、隐写与提取、
多媒体加工、文件与网络分析、谜题链编排、工程与线索管理。

后续规划还包括 **AI 解题**（Agent + 提示词库）与 **MCP 集成**（外部工具调用 /
对外暴露能力），排在核心功能之后。

> 当前状态：**骨架阶段**。目录结构、模块边界、UI 外壳已就位，具体功能均为
> `NotImplementedError` 占位。进度见 [plans.md](plans.md)，设计见 [project.md](project.md)。

## 快速开始

```bash
pip install -r requirements.txt
python main.py
```

启动后会看到一个带左侧导航的空壳窗口，六个功能页均可点击切换，页面内容为占位提示。

> **环境要求**：Python 3.10+，且解释器需自带 `tkinter`（CustomTkinter 的底层依赖）。
> Windows / macOS 官网安装包默认包含；若报 `No module named 'tkinter'`，
> 说明用的是精简版或嵌入式发行版，换官方安装包即可。
> 已实测：本机管理版 Python 3.13.12 **不含** tkinter，系统版 3.13.4 含 tkinter 8.6。

## 目录结构

```
arg-tools-tmyy/
├── main.py                 入口：加入 import 路径并启动应用
├── requirements.txt
├── README.md
├── LICENSE                 MIT
├── .gitignore
├── project.md              技术设计文档（选型、架构、路线图）
├── plans.md                开发计划与进度跟踪
├── doc/                    文档与调研
│   └── ARG工具调研.md       ARG 创作需要哪些工具 —— 联网调研结果
└── src/
    ├── app.py              应用装配层
    ├── config/             配置：常量、路径、用户设置
    ├── core/               核心逻辑（纯 Python，不依赖 UI）
    │   ├── crypto.py       密码 / 编码
    │   ├── stego.py        隐写
    │   ├── media.py        音视频 / 图像 / 二维码
    │   ├── analysis.py     文件 / 网络分析
    │   ├── chain.py        谜题链与叙事地图
    │   ├── store.py        工程持久化
    │   └── checklist.py    试玩与设计审查
    ├── ui/
    │   ├── main_window.py  主窗口外壳
    │   └── pages/          功能页，一页一文件
    └── utils/              日志、路径等通用工具
```

## 设计约定

- **core 不依赖 UI**。`src/core/` 里任何模块都不 import `customtkinter`，
  保证算法层可被脚本、CLI、单元测试独立调用。
- **页面自动注册**。新增功能页只需在 `src/ui/pages/` 建文件并登记进
  `pages/__init__.py` 的 `PAGES`，导航按钮自动生成。
- **常量集中**。所有硬编码值放 `src/config/settings.py`。

## 许可证

[MIT](LICENSE) © 2026 _tmyy

