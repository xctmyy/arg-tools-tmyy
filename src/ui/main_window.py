"""主窗口骨架：左侧导航 + 右侧内容区。

本文件只负责"壳"——导航、页面切换、主题应用。
具体功能页面在 src/ui/pages/ 下实现，新增页面无需改动本文件。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import customtkinter as ctk

from src.config.settings import APP_NAME, APP_TAGLINE, APP_VERSION, AppSettings
from src.ui.pages import PAGES
from src.ui.widgets import ACCENT, ACCENT_HOVER

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
        sidebar = ctk.CTkFrame(self, width=222, corner_radius=0,
                               fg_color=("gray90", "gray11"))
        sidebar.grid(row=0, column=0, sticky="nsw")
        sidebar.grid_propagate(False)
        sidebar.grid_columnconfigure(0, weight=1)
        sidebar.grid_rowconfigure(len(PAGES) + 3, weight=1)
        self.sidebar = sidebar

        brand = ctk.CTkFrame(sidebar, fg_color="transparent")
        brand.grid(row=0, column=0, sticky="ew", padx=18, pady=(20, 4))
        ctk.CTkLabel(
            brand, text=APP_NAME, anchor="w",
            font=ctk.CTkFont(size=17, weight="bold"),
        ).pack(anchor="w")
        ctk.CTkLabel(
            brand, text=APP_TAGLINE, anchor="w", font=ctk.CTkFont(size=11),
            text_color=("gray45", "gray52"),
        ).pack(anchor="w", pady=(2, 0))

        ctk.CTkFrame(sidebar, height=1, fg_color=("gray84", "gray26")).grid(
            row=1, column=0, sticky="ew", padx=18, pady=(14, 10)
        )

        for i, (key, page) in enumerate(PAGES.items(), start=2):
            btn = ctk.CTkButton(
                sidebar,
                text=page.title,
                anchor="w",
                height=36,
                corner_radius=6,
                fg_color="transparent",
                text_color=("gray25", "gray80"),
                hover_color=("gray84", "gray22"),
                command=lambda k=key: self._select(k),
            )
            btn.grid(row=i, column=0, padx=12, pady=2, sticky="ew")
            self._buttons[key] = btn

        ctk.CTkLabel(
            sidebar,
            text=f"v{APP_VERSION}  ·  开发中",
            anchor="w",
            font=ctk.CTkFont(size=10),
            text_color=("gray55", "gray45"),
        ).grid(row=len(PAGES) + 3, column=0, padx=18, pady=(0, 16), sticky="sw")

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
            active = k == key
            btn.configure(
                fg_color=ACCENT if active else "transparent",
                hover_color=ACCENT_HOVER if active else ("gray84", "gray22"),
                text_color=("#ffffff", "#ffffff") if active else ("gray25", "gray80"),
            )
