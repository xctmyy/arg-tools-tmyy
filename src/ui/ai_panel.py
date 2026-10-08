"""右侧 AI 助手面板。

参考 AI IDE 的侧边对话窗口：头部（标题 / 当前上下文 / 关闭）、消息列表、输入区。

**当前只有界面框架，尚未接入任何模型。** 发送后会把消息显示出来，并附一条占位
说明。真正的接入方式见 `plans.md` 的 M4（F8 AI Agent 与提示词）——
届时 `src/ai/agent.py` 接管 `_send()`，消息列表复用本文件的 `add_message()`。

放在这里而不是做成一个页面：AI 助手要在任何页面下都能唤出，
所以它是主窗口的一列，与页面切换无关。
"""

from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from src.ui.widgets import ACCENT, ACCENT_HOVER, CARD_BORDER, MUTED

#: 面板宽度。将来若做拖拽调宽，从这里取值即可。
PANEL_WIDTH = 350

#: 空状态里的预设问题。点击只填入输入框，不触发任何请求。
SUGGESTIONS = (
    "解释这段密文可能是什么编码",
    "帮我想一个入门难度的谜题",
    "这条谜题链的难度曲线合理吗",
)

ROLE_LABEL = {"user": "你", "assistant": "AI", "note": "提示"}
ROLE_BG = {
    "user": ("gray86", "gray23"),
    "assistant": ("gray91", "gray17"),
    "note": ("gray93", "gray14"),
}

#: 文本换行宽度，跟着面板宽度走
WRAP = PANEL_WIDTH - 70


class AiPanel(ctk.CTkFrame):
    """右侧 AI 助手面板。"""

    def __init__(self, master, on_close: Callable[[], None] | None = None):
        super().__init__(master, width=PANEL_WIDTH, corner_radius=0,
                         fg_color=("gray93", "gray13"))
        self.grid_propagate(False)  # 固定宽度，不被子控件撑开
        self._on_close = on_close
        self._empty_state: ctk.CTkFrame | None = None
        self._build()

    # ------------------------------------------------------------------ 构建
    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self._build_header()
        self._build_messages()
        self._build_input()

    def _build_header(self) -> None:
        head = ctk.CTkFrame(self, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", padx=14, pady=(14, 8))
        head.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(head, text="AI 助手", anchor="w",
                     font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=0, column=0, sticky="w")

        if self._on_close is not None:
            ctk.CTkButton(
                head, text="×", width=28, height=28, corner_radius=6,
                fg_color="transparent", text_color=("gray40", "gray70"),
                hover_color=("gray84", "gray24"), command=self._on_close,
            ).grid(row=0, column=1, sticky="e")

        self._context = ctk.CTkLabel(
            head, text="上下文：—", anchor="w",
            font=ctk.CTkFont(size=11), text_color=MUTED,
        )
        self._context.grid(row=1, column=0, columnspan=2, sticky="w", pady=(3, 0))

        ctk.CTkFrame(self, height=1, fg_color=CARD_BORDER).grid(
            row=1, column=0, sticky="ew", padx=14)

    def _build_messages(self) -> None:
        self._messages = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._messages.grid(row=2, column=0, sticky="nsew", padx=6, pady=(8, 0))
        self._messages.grid_columnconfigure(0, weight=1)
        self._show_empty_state()

    def _build_input(self) -> None:
        box = ctk.CTkFrame(self, fg_color="transparent")
        box.grid(row=3, column=0, sticky="ew", padx=14, pady=14)

        self._entry = ctk.CTkTextbox(box, height=68, wrap="word")
        self._entry.pack(fill="x")
        self._entry.bind("<Control-Return>", self._on_ctrl_enter)

        row = ctk.CTkFrame(box, fg_color="transparent")
        row.pack(fill="x", pady=(8, 0))

        ctk.CTkButton(
            row, text="发送", width=76, height=30, corner_radius=6,
            fg_color=ACCENT, hover_color=ACCENT_HOVER, command=self._send,
        ).pack(side="left")
        ctk.CTkButton(
            row, text="清空对话", width=82, height=30, corner_radius=6,
            fg_color="transparent", border_width=1, border_color=CARD_BORDER,
            text_color=("gray30", "gray75"), hover_color=("gray86", "gray24"),
            command=self.clear,
        ).pack(side="left", padx=(6, 0))
        ctk.CTkLabel(row, text="Ctrl+Enter", font=ctk.CTkFont(size=10),
                     text_color=MUTED).pack(side="right")

    # ------------------------------------------------------------------ 空状态
    def _show_empty_state(self) -> None:
        if self._empty_state is not None:
            return
        box = ctk.CTkFrame(self._messages, fg_color="transparent")
        box.grid(row=0, column=0, sticky="ew", padx=8, pady=8)
        self._empty_state = box

        ctk.CTkLabel(box, text="尚未接入模型", anchor="w",
                     font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(
            box,
            text="这里目前只是界面框架。接入方式见 plans.md 的 M4（AI Agent 与提示词）。",
            anchor="w", justify="left", wraplength=WRAP,
            font=ctk.CTkFont(size=11), text_color=MUTED,
        ).pack(anchor="w", pady=(4, 12))

        ctk.CTkLabel(box, text="试试这些（只会填入输入框）", anchor="w",
                     font=ctk.CTkFont(size=11), text_color=MUTED).pack(anchor="w")
        for hint in SUGGESTIONS:
            ctk.CTkButton(
                box, text=hint, anchor="w", height=28, corner_radius=6,
                fg_color="transparent", border_width=1, border_color=CARD_BORDER,
                text_color=("gray25", "gray80"), hover_color=("gray86", "gray24"),
                command=lambda h=hint: self._fill_input(h),
            ).pack(fill="x", pady=(6, 0))

    def _drop_empty_state(self) -> None:
        if self._empty_state is not None:
            self._empty_state.destroy()
            self._empty_state = None

    # ------------------------------------------------------------------ 消息
    def add_message(self, role: str, text: str) -> None:
        """往对话里追加一条消息。role 取 user / assistant / note。

        这是给将来的 Agent 用的接口——接入后由 `src/ai/agent.py` 调用。
        """
        self._drop_empty_state()
        row = len(self._messages.winfo_children())

        bubble = ctk.CTkFrame(self._messages, corner_radius=8,
                              fg_color=ROLE_BG.get(role, ROLE_BG["note"]))
        bubble.grid(row=row, column=0, sticky="ew", padx=4, pady=4)
        bubble.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            bubble, text=ROLE_LABEL.get(role, role), anchor="w",
            font=ctk.CTkFont(size=10, weight="bold"), text_color=MUTED,
        ).grid(row=0, column=0, sticky="w", padx=10, pady=(7, 0))
        ctk.CTkLabel(
            bubble, text=text, anchor="w", justify="left", wraplength=WRAP,
            font=ctk.CTkFont(size=12),
        ).grid(row=1, column=0, sticky="w", padx=10, pady=(2, 8))

        self._scroll_to_bottom()

    def _scroll_to_bottom(self) -> None:
        """等布局算完再滚到底。CTkScrollableFrame 没有公开的滚动接口，
        只能碰内部画布，所以包一层 try 免得版本变化时崩掉。"""
        def do() -> None:
            try:
                self._messages._parent_canvas.yview_moveto(1.0)
            except Exception:  # noqa: BLE001
                pass

        self.after(60, do)

    # ------------------------------------------------------------------ 交互
    def set_context(self, page_title: str) -> None:
        """告诉助手当前在哪个页面。将来会作为提示词的一部分。"""
        self._context.configure(text=f"上下文：{page_title}")

    def _fill_input(self, text: str) -> None:
        self._entry.delete("1.0", "end")
        self._entry.insert("1.0", text)
        self._entry.focus_set()

    def _on_ctrl_enter(self, _event) -> str:
        self._send()
        return "break"

    def _send(self) -> None:
        """发送。目前只把消息显示出来并附一条占位说明，不发起任何请求。"""
        text = self._entry.get("1.0", "end-1c").strip()
        if not text:
            return
        self.add_message("user", text)
        self._entry.delete("1.0", "end")
        self.add_message(
            "note",
            "尚未接入模型——这是占位回复。接入后此处会显示 AI 的回答。",
        )

    def clear(self) -> None:
        for widget in self._messages.winfo_children():
            widget.destroy()
        self._empty_state = None
        self._show_empty_state()
