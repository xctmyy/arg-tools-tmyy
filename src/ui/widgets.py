"""可复用的界面构件。

统一各页面的视觉语言：卡片式分区、参数控件工厂、状态行、算法选择器。
集中在这里，新增页面就不必各写一套样式。

配色一律用 `(浅色主题值, 深色主题值)` 二元组，CustomTkinter 会自动按当前
主题取值，因此这里不需要判断主题。
"""

from __future__ import annotations

from tkinter import filedialog
from typing import Callable

import customtkinter as ctk

from src.core.crypto_types import Param, random_hex

# ------------------------------------------------------------ 配色与字体

CARD_BG = ("gray94", "gray15")
CARD_BORDER = ("gray83", "gray27")
MUTED = ("gray45", "gray62")
ACCENT = ("#2f6fb5", "#3d8bd4")
ACCENT_HOVER = ("#255a94", "#326fa9")
ERROR = ("#c0392b", "#ff8a80")
OK_TEXT = ("gray32", "gray72")
FIELD_BG = ("gray88", "gray21")

MONO_FONT = ("Consolas", 12)
MONO_SMALL = ("Consolas", 11)


# ------------------------------------------------------------ 卡片分区


class Card(ctk.CTkFrame):
    """带标题的卡片式分区，内容放进 `card.body`。"""

    def __init__(self, master, title: str = "", subtitle: str = "", **kwargs):
        kwargs.setdefault("corner_radius", 8)
        kwargs.setdefault("fg_color", CARD_BG)
        kwargs.setdefault("border_width", 1)
        kwargs.setdefault("border_color", CARD_BORDER)
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(0, weight=1)

        row = 0
        if title:
            head = ctk.CTkFrame(self, fg_color="transparent")
            head.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 2))
            head.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(
                head, text=title, anchor="w",
                font=ctk.CTkFont(size=13, weight="bold"),
            ).grid(row=0, column=0, sticky="w")
            if subtitle:
                ctk.CTkLabel(
                    head, text=subtitle, anchor="w", justify="left",
                    font=ctk.CTkFont(size=11), text_color=MUTED, wraplength=300,
                ).grid(row=1, column=0, sticky="w", pady=(3, 0))
            row = 1

        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.grid(row=row, column=0, sticky="nsew", padx=14, pady=(8, 12))
        self.body.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(row, weight=1)


class StatusLine(ctk.CTkLabel):
    """一行状态提示，按语义着色，避免用户分不清"正在算"和"出错了"。"""

    def __init__(self, master, **kwargs):
        kwargs.setdefault("anchor", "w")
        kwargs.setdefault("font", ctk.CTkFont(size=11))
        kwargs.setdefault("text_color", OK_TEXT)
        super().__init__(master, text="", **kwargs)

    def info(self, text: str) -> None:
        self.configure(text=text, text_color=OK_TEXT)

    def busy(self, text: str) -> None:
        self.configure(text=text, text_color=ACCENT)

    def error(self, text: str) -> None:
        self.configure(text=text, text_color=ERROR)

    def clear(self) -> None:
        self.configure(text="")


# ------------------------------------------------------------ 算法选择器


class Selector(ctk.CTkFrame):
    """一组互斥按钮，按列数自动换行。比下拉菜单更直观。"""

    def __init__(
        self,
        master,
        items: list[tuple[str, str]],
        command: Callable[[str], None],
        columns: int = 4,
        **kwargs,
    ):
        kwargs.setdefault("fg_color", "transparent")
        super().__init__(master, **kwargs)
        self._command = command
        self._buttons: dict[str, ctk.CTkButton] = {}

        for i, (key, label) in enumerate(items):
            btn = ctk.CTkButton(
                self, text=label, height=30, corner_radius=6,
                fg_color="transparent", text_color=("gray20", "gray85"),
                border_width=1, border_color=CARD_BORDER,
                hover_color=("gray86", "gray25"),
                command=lambda k=key: self._on_click(k),
            )
            btn.grid(row=i // columns, column=i % columns,
                     padx=(0, 6), pady=(0, 6), sticky="ew")
            self._buttons[key] = btn

        for c in range(columns):
            self.grid_columnconfigure(c, weight=1)

    def _on_click(self, key: str) -> None:
        self.set(key)
        self._command(key)

    def set(self, key: str) -> None:
        for k, btn in self._buttons.items():
            if k == key:
                btn.configure(fg_color=ACCENT, hover_color=ACCENT_HOVER,
                              border_color=ACCENT,
                              text_color=("#ffffff", "#ffffff"))
            else:
                btn.configure(fg_color="transparent",
                              hover_color=("gray86", "gray25"),
                              border_color=CARD_BORDER,
                              text_color=("gray20", "gray85"))

    def set_enabled(self, on: bool) -> None:
        state = "normal" if on else "disabled"
        for btn in self._buttons.values():
            btn.configure(state=state)


# ------------------------------------------------------------ 参数控件工厂


def _small_button(row, text: str, command, width: int = 52) -> ctk.CTkButton:
    btn = ctk.CTkButton(row, text=text, width=width, height=26, corner_radius=6,
                        command=command)
    btn.pack(side="left", padx=(4, 0))
    return btn


def _browse(entry: ctk.CTkEntry, kind: str) -> None:
    if kind == "dir":
        path = filedialog.askdirectory(title="选择目录")
    else:
        path = filedialog.askopenfilename(
            title="选择密钥文件",
            filetypes=[("PEM 密钥", "*.pem"), ("所有文件", "*.*")],
        )
    if path:
        entry.delete(0, "end")
        entry.insert(0, path)


def _fill_random(entry: ctk.CTkEntry, size: int) -> None:
    entry.delete(0, "end")
    entry.insert(0, random_hex(size or 16))


def _add_password_toggle(row, entry: ctk.CTkEntry) -> None:
    """口令框的显示/隐藏切换，方便核对有没有打错。"""
    hidden = {"on": True}

    def toggle() -> None:
        hidden["on"] = not hidden["on"]
        entry.configure(show="●" if hidden["on"] else "")
        btn.configure(text="显示" if hidden["on"] else "隐藏")

    btn = _small_button(row, "显示", toggle, width=44)


def make_param_input(
    parent,
    param: Param,
    extra_buttons: list[tuple[str, Callable[[ctk.CTkEntry], None]]] | None = None,
) -> Callable[[], str]:
    """按 `Param.kind` 生成控件，返回取值函数。

    extra_buttons 用于页面特有的附加操作（如「查看指纹」），回调会收到输入框。
    """
    if param.kind == "choice":
        default = param.default or (param.choices[0] if param.choices else "")
        var = ctk.StringVar(value=default)
        ctk.CTkOptionMenu(
            parent, variable=var, values=list(param.choices), width=190,
            fg_color=FIELD_BG, button_color=("gray75", "gray30"),
            button_hover_color=("gray65", "gray38"),
        ).pack(anchor="w")
        return var.get

    row = ctk.CTkFrame(parent, fg_color="transparent")
    row.pack(anchor="w", fill="x")

    width = {"int": 90, "password": 210, "keyfile": 250, "dir": 250,
             "hexkey": 300}.get(param.kind, 210)
    entry = ctk.CTkEntry(
        row, width=width, placeholder_text=param.hint,
        show="●" if param.kind == "password" else "",
    )
    entry.insert(0, param.default)
    entry.pack(side="left")

    if param.kind == "password":
        _add_password_toggle(row, entry)
    elif param.kind in ("keyfile", "dir"):
        _small_button(row, "浏览", lambda: _browse(entry, param.kind))
    elif param.kind == "hexkey":
        _small_button(row, "生成", lambda: _fill_random(entry, param.size))

    for label, callback in extra_buttons or []:
        _small_button(row, label, lambda cb=callback, e=entry: cb(e))

    return entry.get


def param_field(
    parent,
    param: Param,
    extra_buttons: list[tuple[str, Callable[[ctk.CTkEntry], None]]] | None = None,
    label_size: int = 11,
) -> Callable[[], str]:
    """在 parent 里放「标签 + 输入控件」，返回取值函数。"""
    cell = ctk.CTkFrame(parent, fg_color="transparent")
    cell.pack(fill="x", pady=(0, 8))
    ctk.CTkLabel(
        cell, text=param.label, anchor="w", font=ctk.CTkFont(size=label_size)
    ).pack(anchor="w")
    return make_param_input(cell, param, extra_buttons)


def info_row(parent, label: str, value: str = "", width: int = 54) -> Callable[[str], None]:
    """一行「标签 + 值」。值用只读输入框，方便选中复制（指纹常要复制核对）。

    返回设置值的函数。
    """
    frame = ctk.CTkFrame(parent, fg_color="transparent")
    frame.pack(fill="x", pady=1)
    ctk.CTkLabel(
        frame, text=label, width=width, anchor="w",
        font=ctk.CTkFont(size=11), text_color=MUTED,
    ).pack(side="left")
    var = ctk.StringVar(value=value)
    ctk.CTkEntry(
        frame, textvariable=var, height=26, font=ctk.CTkFont(family="Consolas", size=11),
        fg_color="transparent", border_width=0, state="readonly",
    ).pack(side="left", fill="x", expand=True)
    return var.set


def labeled_textbox(parent, label: str, height: int = 0) -> ctk.CTkTextbox:
    """「标签 + 多行文本框」，返回文本框本身。"""
    ctk.CTkLabel(parent, text=label, anchor="w",
                 font=ctk.CTkFont(size=11)).pack(anchor="w")
    box = ctk.CTkTextbox(parent, wrap="word", font=MONO_FONT)
    if height:
        box.configure(height=height)
    box.pack(fill="both", expand=True, pady=(2, 0))
    return box


def read(box: ctk.CTkTextbox) -> str:
    return box.get("1.0", "end-1c")


def write(box: ctk.CTkTextbox, text: str) -> None:
    box.delete("1.0", "end")
    box.insert("1.0", text)


def copy_to_clipboard(widget, text: str) -> None:
    widget.clipboard_clear()
    widget.clipboard_append(text)
