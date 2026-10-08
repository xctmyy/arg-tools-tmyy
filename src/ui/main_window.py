"""主窗口骨架：左侧导航 + 右侧内容区。

本文件只负责"壳"——导航、页面切换、主题应用。
具体功能页面在 src/ui/pages/ 下实现，新增页面无需改动本文件。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import customtkinter as ctk

from src.config.settings import APP_TAGLINE, APP_VERSION, AppSettings
from src.ui.pages import PAGES

if TYPE_CHECKING:
    from src.ui.pages.base import BasePage


class MainWindow(ctk.CTk):
    """应用主窗口。"""

    def __init__(
        self,
        title: str,
        size: tuple[int, int],
        min_size: tuple[int, int],
        settings: AppSettings,
    ) -> None:
        self.settings = settings
        # 外观必须在创建控件前设置
        ctk.set_appearance_mode(settings.appearance.value)
        ctk.set_default_color_theme(settings.theme.value)

        super().__init__()
        self.title(title)
        self.geometry(f"{size[0]}x{size[1]}")
        self.minsize(*min_size)

        self._frames: dict[str, ctk.CTkFrame] = {}
        self._buttons: dict[str, ctk.CTkButton] = {}
        self._current: str | None = None

        self._build_layout()
        if PAGES:
            self._select(next(iter(PAGES)))

    # ------------------------------------------------------------------ 布局
    def _build_layout(self) -> None:
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()

        self.content = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)

    def _build_sidebar(self) -> None:
        sidebar = ctk.CTkFrame(self, width=208, corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="nsw")
        sidebar.grid_propagate(False)
        sidebar.grid_rowconfigure(len(PAGES) + 2, weight=1)
        self.sidebar = sidebar

        ctk.CTkLabel(
            sidebar,
            text="arg.xc",
            font=ctk.CTkFont(size=21, weight="bold"),
        ).grid(row=0, column=0, padx=20, pady=(22, 0), sticky="w")

        ctk.CTkLabel(
            sidebar,
            text=APP_TAGLINE,
            font=ctk.CTkFont(size=11),
            text_color=("gray45", "gray60"),
        ).grid(row=1, column=0, padx=20, pady=(0, 16), sticky="w")

        for i, (key, page) in enumerate(PAGES.items(), start=2):
            btn = ctk.CTkButton(
                sidebar,
                text=page.title,
                anchor="w",
                height=34,
                corner_radius=6,
                fg_color="transparent",
                text_color=("gray20", "gray85"),
                hover_color=("gray80", "gray28"),
                command=lambda k=key: self._select(k),
            )
            btn.grid(row=i, column=0, padx=12, pady=3, sticky="ew")
            self._buttons[key] = btn

        ctk.CTkLabel(
            sidebar,
            text=f"v{APP_VERSION}  ·  骨架阶段",
            font=ctk.CTkFont(size=10),
            text_color=("gray55", "gray50"),
        ).grid(row=len(PAGES) + 3, column=0, padx=20, pady=(0, 16), sticky="sw")

    # -------------------------------------------------------------- 页面切换
    def _select(self, key: str) -> None:
        """切换到指定页面（懒加载：首次进入才构建）。"""
        if key == self._current:
            return
        if self._current is not None:
            self._frames[self._current].grid_forget()

        frame = self._frames.get(key)
        if frame is None:
            page: BasePage = PAGES[key]
            page.window = self  # 让页面能访问 settings 等窗口级状态
            frame = page.build(self.content)
            self._frames[key] = frame
        frame.grid(row=0, column=0, sticky="nsew")

        self._current = key
        for k, btn in self._buttons.items():
            btn.configure(fg_color=("gray78", "gray24") if k == key else "transparent")
