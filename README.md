# arg-tools-tmyy

ARG（Alternate Reality Game，另类实境游戏）创作工具箱。

把设计一条谜题链路上会用到的零散工具收进一个桌面应用：密码编解码、隐写与提取、
多媒体加工、文件与网络分析、谜题链编排、工程与线索管理。

后续规划还包括 **AI 解题**（Agent + 提示词库）与 **MCP 集成**（外部工具调用 /
对外暴露能力），排在核心功能之后。

> 当前状态：**M1 已完成**。「密码 / 编码」与「项目」两页可用，其余页面仍为占位。
> 进度见 [plans.md](plans.md)，设计见 [project.md](project.md)。

## 快速开始

```bash
pip install -r requirements.txt
python main.py
```

启动后会看到一个带左侧导航的窗口。目前可用：

- **项目** —— 新建 / 打开工程，线索库增删改查与搜索，最近工程记录
- **密码 / 编码** —— 31 种经典算法
  - 替换密码：凯撒、ROT13/47、Atbash、A1Z26、培根
  - 需密钥：维吉尼亚、栅栏、Playfair、Nihilist、书本密码、仿射、列置换、异或
  - 编码：Base16/32/64/85、摩斯、二进制、十六进制、URL、HTML 实体、
    Quoted-Printable、Brainfuck、Ook
  - 哈希：MD5、SHA-1/256/512、CRC32
  - 摩斯支持中文（Unicode 模式，完全可逆）；支持编码类型自动识别与暴力枚举
- **现代密码** —— 7 种算法，独立界面
  - AES-GCM / CBC / ECB、ChaCha20、ChaCha20-Poly1305、RSA、ECC（ECIES）
  - 左栏密钥侧：随机密钥生成、密钥对生成、密钥指纹（SHA-256）
  - RSA 支持长文本自动混合加密（RSA 包 AES 密钥）
  - 运算在后台线程执行，大输入不会冻住界面

右侧还有一个 **AI 助手面板**（侧边栏按钮或 `Ctrl+I` 切换）：目前只有界面框架，
尚未接入模型，发送后只显示占位回复。接入计划见 [plans.md](plans.md) 的 M4。

其余页面（隐写 / 多媒体 / 文件网络 / 谜题链）仍为占位。

## 测试

```bash
python -m unittest discover -s tests -t .
```

132 项单元测试，覆盖算法的已知向量与往返一致性、现代密码的随机性与篡改检测、
密钥指纹、混合加密、工程持久化、线索 CRUD、设置持久化、后台任务调度。

> 现代密码算法依赖 `cryptography`。没装也能启动，只是「现代密码」分组的算法
> 会提示缺少依赖；相关测试会自动跳过。

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
    │   ├── crypto_types.py 密码模块的数据结构与注册表
    │   ├── crypto.py       经典密码 / 编码 / 哈希
    │   ├── crypto_modern.py AES / ChaCha20 / RSA / ECC（依赖 cryptography）
    │   ├── stego.py        隐写
    │   ├── media.py        音视频 / 图像 / 二维码
    │   ├── analysis.py     文件 / 网络分析
    │   ├── chain.py        谜题链与叙事地图
    │   ├── store.py        工程持久化
    │   └── checklist.py    试玩与设计审查
    ├── ui/
    │   ├── main_window.py  主窗口：侧边栏 + 内容区 + AI 面板
    │   ├── ai_panel.py     右侧 AI 助手面板（界面框架，未接入模型）
    │   ├── async_task.py   后台任务：把耗时运算挪出 UI 线程
    │   ├── widgets.py      可复用构件：卡片、状态行、按钮组、参数控件工厂
    │   └── pages/          功能页，一页一文件
    └── utils/              日志、路径等通用工具
tests/                      单元测试
```

## 设计约定

- **core 不依赖 UI**。`src/core/` 里任何模块都不 import `customtkinter`，
  保证算法层可被脚本、CLI、单元测试独立调用。
- **页面自动注册**。新增功能页只需在 `src/ui/pages/` 建文件并登记进
  `pages/__init__.py` 的 `PAGES`，导航按钮自动生成。
- **常量集中**。所有硬编码值放 `src/config/settings.py`。

## 许可证

[MIT](LICENSE) © 2026 _tmyy

