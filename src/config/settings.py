"""全局配置：常量、路径、用户可调项。

约定：所有硬编码常量集中在这里，其他模块不要散落魔法值。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

# --- 应用信息 ---
APP_NAME = "arg.xc"
APP_VERSION = "0.1.0"
APP_TAGLINE = "ARG 创作工具箱"

# --- 路径 ---
ROOT_DIR = Path(__file__).resolve().parents[2]
DOC_DIR = ROOT_DIR / "doc"           # 文档 / 调研
DATA_DIR = ROOT_DIR / "data"         # 运行期数据（工程文件、缓存），首次运行时创建
ASSETS_DIR = ROOT_DIR / "assets"     # 图标、字体等静态资源，按需创建

# --- 窗口 ---
WINDOW_SIZE = (1180, 720)
WINDOW_MIN_SIZE = (960, 620)


class AppearanceMode(str, Enum):
    """CustomTkinter 外观模式。"""

    SYSTEM = "System"
    LIGHT = "Light"
    DARK = "Dark"


class ColorTheme(str, Enum):
    """CustomTkinter 内置配色主题。"""

    BLUE = "blue"
    DARK_BLUE = "dark-blue"
    GREEN = "green"


@dataclass
class AppSettings:
    """用户可调设置。后续可序列化到 DATA_DIR/settings.json。"""

    appearance: AppearanceMode = AppearanceMode.DARK
    theme: ColorTheme = ColorTheme.BLUE
    recent_projects: list[str] = field(default_factory=list)
    last_opened_project: str | None = None
