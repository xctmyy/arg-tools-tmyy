"""页面基类。

子类只需定义 `title` / `description`（可选）并在需要时覆写 `render()`。
默认 `render()` 会列出 `planned` 里规划中的能力，因此骨架阶段每个页面
都能直接跑起来，且一眼看得出这个页面将来做什么。
"""

from __future__ import annotations

import customtkinter as ctk

from src.ui.widgets import MUTED, Card


class BasePage:
    """所有功能页的父类。"""

    #: 侧边栏与页面标题
    title: str = "未命名"
    #: 页面副标题（一句话说明）
    description: str = ""
    #: 规划中的能力清单，未实现时用作占位内容
    planned: tuple[str, ...] = ()
    #: 由主窗口在构建前注入，页面可借此访问 window.settings 等
    window: object | None = None

    # ------------------------------------------------------------------ 框架
    def build(self, master: ctk.CTkFrame) -> ctk.CTkFrame:
        """构建页面根 Frame 并返回。由主窗口调用，子类一般不必覆写。

        统一版式：标题 + 说明 -> 分隔线 -> 内容区。
        """
        frame = ctk.CTkFrame(master, fg_color="transparent")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(2, weight=1)

        header = ctk.CTkFrame(frame, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(18, 8))
        ctk.CTkLabel(
            header, text=self.title, anchor="w",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).pack(anchor="w")
        if self.description:
            ctk.CTkLabel(
                header, text=self.description, anchor="w",
                font=ctk.CTkFont(size=12), text_color=("gray45", "gray62"),
            ).pack(anchor="w", pady=(3, 0))

        ctk.CTkFrame(frame, height=1, fg_color=("gray84", "gray26")).grid(
            row=1, column=0, sticky="ew", padx=24
        )

        body = ctk.CTkFrame(frame, fg_color="transparent")
        body.grid(row=2, column=0, sticky="nsew", padx=24, pady=(14, 20))
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(0, weight=1)
        self.body = body

        self.render(body)
        return frame

    # ------------------------------------------------------------------ 内容
    def render(self, body: ctk.CTkFrame) -> None:
        """默认占位内容：列出规划中的能力。子类覆写以实现真实界面。"""
        card = Card(body, title="规划中的能力",
                    subtitle="这个页面尚未实现。以下是它的目标功能：")
        card.grid(row=0, column=0, sticky="new")

        if not self.planned:
            ctk.CTkLabel(card.body, text="（待补充）", anchor="w",
                         text_color=MUTED).pack(anchor="w")
            return

        for item in self.planned:
            ctk.CTkLabel(
                card.body, text=f"·   {item}", anchor="w",
                font=ctk.CTkFont(size=12), justify="left", wraplength=760,
            ).pack(anchor="w", pady=2)
