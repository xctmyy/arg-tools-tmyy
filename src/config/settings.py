"""全局配置：常量、路径、用户可调项。

约定：所有硬编码常量集中在这里，其他模块不要散落魔法值。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import ClassVar

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
    """用户可调设置。序列化到 DATA_DIR/settings.json。"""

    appearance: AppearanceMode = AppearanceMode.DARK
    theme: ColorTheme = ColorTheme.BLUE
    recent_projects: list[str] = field(default_factory=list)
    last_opened_project: str | None = None

    #: 最近工程最多记这么多条
    MAX_RECENT: ClassVar[int] = 8

    def to_dict(self) -> dict:
        return {
            "appearance": self.appearance.value,
            "theme": self.theme.value,
            "recent_projects": list(self.recent_projects),
            "last_opened_project": self.last_opened_project,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AppSettings":
        def pick(enum_cls, value, fallback):
            try:
                return enum_cls(value)
            except ValueError:
                return fallback

        recent = data.get("recent_projects")
        return cls(
            appearance=pick(AppearanceMode, data.get("appearance"), AppearanceMode.DARK),
            theme=pick(ColorTheme, data.get("theme"), ColorTheme.BLUE),
            recent_projects=[str(p) for p in recent] if isinstance(recent, list) else [],
            last_opened_project=data.get("last_opened_project"),
        )

    def touch_recent(self, path: str | Path) -> None:
        """把某个工程路径提到最近列表最前面（去重、限长）。"""
        key = str(path)
        self.recent_projects = [p for p in self.recent_projects if p != key]
        self.recent_projects.insert(0, key)
        del self.recent_projects[self.MAX_RECENT :]
        self.last_opened_project = key


# ============================================================ 读写

SETTINGS_FILE = DATA_DIR / "settings.json"


def load_settings() -> AppSettings:
    """读取设置；文件缺失或损坏时返回默认值，不抛异常。"""
    try:
        raw = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return AppSettings()
    return AppSettings.from_dict(raw) if isinstance(raw, dict) else AppSettings()


def save_settings(settings: AppSettings) -> None:
    """写入设置；失败时静默忽略（设置丢失不该让程序崩掉）。"""
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        tmp = SETTINGS_FILE.with_suffix(".json.tmp")
        tmp.write_text(
            json.dumps(settings.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        tmp.replace(SETTINGS_FILE)
    except OSError:
        pass
