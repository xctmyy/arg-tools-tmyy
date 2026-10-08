"""页面基类。

子类只需定义 `title` / `description`（可选）并在需要时覆写 `render()`。
默认 `render()` 会放一个占位提示，因此骨架阶段每个页面都能直接跑起来。
"""

from __future__ import annotations

import customtkinter as ctk


class BasePage:
    """所有功能页的父类。"""

    #: 侧边栏与页面标题
    title: str = "未命名"
    #: 页面副标题（一句话说明）
    description: str = ""

    # ------------------------------------------------------------------ 框架
    def build(self, master: ctk.CTkFrame) -> ctk.CTkFrame:
        """构建页面根 Frame 并返回。由主窗口调用，子类一般不必覆写。"""
        frame = ctk.CTkFrame(master, fg_color="transparent")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(frame, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 6))
        ctk.CTkLabel(
            header, text=self.title, font=ctk.CTkFont(size=22, weight="bold")
        ).pack(anchor="w")
        if self.description:
            ctk.CTkLabel(
                header,
                text=self.description,
                font=ctk.CTkFont(size=12),
                text_color=("gray40", "gray65"),
            ).pack(anchor="w", pady=(3, 0))

        body = ctk.CTkFrame(frame, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=24, pady=(4, 20))
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(0, weight=1)
        self.body = body

        self.render(body)
        return frame

    # ------------------------------------------------------------------ 内容
    def render(self, body: ctk.CTkFrame) -> None:
        """往 body 里填充控件。默认放占位提示，子类覆写。"""
        ctk.CTkLabel(
            body,
            text="TODO · 待实现",
            font=ctk.CTkFont(size=14),
            text_color=("gray50", "gray60"),
        ).grid(row=0, column=0)
