"""密码 / 编码 工具页（经典算法）。

现代密码（AES / ChaCha20 / RSA / ECC）在「现代密码」页单独呈现——它们需要
密钥文件、随机密钥、指纹这类经典页放不下的东西。

界面由 `core.crypto.REGISTRY` 驱动：算法下拉、参数表单、工具按钮都读注册表生成，
因此新增算法只需改 core 层。

线程模型
--------
编码 / 解码 / 暴力枚举都在后台线程执行（`src.ui.async_task.TaskRunner`），
避免大文本或 Brainfuck 解释把界面冻住。控件读写只发生在主线程。
"""

from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from src.core import crypto
from src.ui.async_task import TaskRunner
from src.ui.pages.base import BasePage
from src.ui.widgets import (
    MONO_FONT,
    Card,
    StatusLine,
    make_param_input,
    read,
    write,
)

#: 本页只放经典算法，现代算法在「现代密码」页
EXCLUDED_GROUPS = {"现代密码"}

BRUTE_FORCE_METHODS = {"caesar", "rail_fence", "rot13", "rot47", "atbash",
                       "bacon", "affine"}


class CryptoPage(BasePage):
    title = "密码 / 编码"
    description = "经典密码、Base / 摩斯编码与哈希"

    def __init__(self) -> None:
        self._codecs = [c for c in crypto.available() if c.group not in EXCLUDED_GROUPS]
        self._by_display = {self._display(c): c for c in self._codecs}
        self._param_getters: dict[str, Callable[[], str]] = {}
        self._current: crypto.Codec = self._codecs[0]
        self._buttons: list[ctk.CTkButton] = []
        self._tasks: TaskRunner | None = None

    # ------------------------------------------------------------------ 工具
    @staticmethod
    def _display(codec: crypto.Codec) -> str:
        return f"{codec.group} · {codec.label}"

    def _selected(self) -> crypto.Codec:
        return self._by_display[self._method_var.get()]

    def _params(self) -> dict[str, str]:
        return {name: get() for name, get in self._param_getters.items()}

    # ------------------------------------------------------------------ 构建
    def render(self, body: ctk.CTkFrame) -> None:
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(2, weight=1)

        self._build_toolbar(body)
        self._build_params_card(body)
        self._build_io(body)
        self._build_actions(body)
        self._build_results(body)

        self._tasks = TaskRunner(body)
        self._on_method_change(self._method_var.get())

    def _build_toolbar(self, body: ctk.CTkFrame) -> None:
        bar = ctk.CTkFrame(body, fg_color="transparent")
        bar.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        bar.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(bar, text="算法").grid(row=0, column=0, padx=(0, 8))

        self._method_var = ctk.StringVar(value=self._display(self._codecs[0]))
        self._method_menu = ctk.CTkOptionMenu(
            bar, variable=self._method_var,
            values=[self._display(c) for c in self._codecs],
            width=260, command=self._on_method_change,
        )
        self._method_menu.grid(row=0, column=1, sticky="w")

        self._note = ctk.CTkLabel(
            bar, text="", anchor="w", font=ctk.CTkFont(size=11),
            text_color=("gray45", "gray62"),
        )
        self._note.grid(row=0, column=2, sticky="e")

    def _build_params_card(self, body: ctk.CTkFrame) -> None:
        self._param_card = Card(body, title="参数")
        self._param_card.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        # 参数横向排列；算法附带的动作（若有）排在下一行
        self._param_row = ctk.CTkFrame(self._param_card.body, fg_color="transparent")
        self._param_row.pack(anchor="w", fill="x")
        self._tool_row = ctk.CTkFrame(self._param_card.body, fg_color="transparent")
        self._tool_row.pack(anchor="w", fill="x", pady=(10, 0))

    def _build_io(self, body: ctk.CTkFrame) -> None:
        io = ctk.CTkFrame(body, fg_color="transparent")
        io.grid(row=2, column=0, sticky="nsew")
        io.grid_columnconfigure(0, weight=1, uniform="io")
        io.grid_columnconfigure(1, weight=1, uniform="io")
        io.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(io, text="输入", anchor="w",
                     font=ctk.CTkFont(size=11)).grid(row=0, column=0, sticky="w", padx=4)
        ctk.CTkLabel(io, text="输出", anchor="w",
                     font=ctk.CTkFont(size=11)).grid(row=0, column=1, sticky="w", padx=4)

        self._input = ctk.CTkTextbox(io, wrap="word", font=MONO_FONT)
        self._input.grid(row=1, column=0, sticky="nsew", padx=(0, 6))
        self._output = ctk.CTkTextbox(io, wrap="word", font=MONO_FONT)
        self._output.grid(row=1, column=1, sticky="nsew", padx=(6, 0))

    def _build_actions(self, body: ctk.CTkFrame) -> None:
        row = ctk.CTkFrame(body, fg_color="transparent")
        row.grid(row=3, column=0, sticky="ew", pady=(10, 4))

        def btn(text: str, cmd, width: int = 88) -> None:
            widget = ctk.CTkButton(row, text=text, width=width, height=30,
                                   corner_radius=6, command=cmd)
            widget.pack(side="left", padx=(0, 6))
            self._buttons.append(widget)

        btn("编码 →", self._do_encode)
        btn("解码 ←", self._do_decode)
        btn("交换 ⇅", self._swap, 78)
        btn("复制输出", self._copy_output, 88)
        btn("清空", self._clear, 64)
        btn("识别编码", self._detect, 88)

        self._brute_btn = ctk.CTkButton(
            row, text="暴力枚举", width=88, height=30, corner_radius=6,
            fg_color=("gray72", "gray32"), hover_color=("gray62", "gray40"),
            command=self._brute_force,
        )
        self._brute_btn.pack(side="left", padx=(0, 6))
        self._buttons.append(self._brute_btn)

        self._status = StatusLine(body)
        self._status.grid(row=4, column=0, sticky="ew", pady=(0, 6))

    def _build_results(self, body: ctk.CTkFrame) -> None:
        self._results = ctk.CTkScrollableFrame(body, height=180, label_text="枚举结果")
        self._results.grid(row=5, column=0, sticky="ew")
        self._results.grid_columnconfigure(0, weight=1)
        self._results.grid_remove()

    # ------------------------------------------------------------------ 忙碌态
    def _set_busy(self, busy: bool) -> None:
        state = "disabled" if busy else "normal"
        for widget in self._buttons:
            widget.configure(state=state)
        self._method_menu.configure(state=state)
        if not busy:
            self._sync_brute_button()

    def _sync_brute_button(self) -> None:
        self._brute_btn.configure(
            state="normal" if self._current.name in BRUTE_FORCE_METHODS else "disabled"
        )

    # ------------------------------------------------------------------ 切换算法
    def _on_method_change(self, _display: str) -> None:
        codec = self._selected()
        self._current = codec

        for widget in self._param_row.winfo_children():
            widget.destroy()
        self._param_getters.clear()
        for col, p in enumerate(codec.params):
            cell = ctk.CTkFrame(self._param_row, fg_color="transparent")
            cell.grid(row=0, column=col, padx=(0, 16), sticky="w")
            ctk.CTkLabel(cell, text=p.label, anchor="w",
                         font=ctk.CTkFont(size=11)).pack(anchor="w")
            self._param_getters[p.name] = make_param_input(cell, p)

        self._render_tools(codec)
        self._note.configure(text=codec.note)
        self._sync_brute_button()
        self._hide_results()
        self._status.clear()

    def _render_tools(self, codec: crypto.Codec) -> None:
        """算法附带的动作（若有）。经典算法目前都没有，整行隐藏。"""
        for widget in self._tool_row.winfo_children():
            widget.destroy()
        self._tool_row.pack_forget()
        if not codec.actions:
            return

        for act in codec.actions:
            box = ctk.CTkFrame(self._tool_row, fg_color="transparent")
            box.pack(side="left", padx=(0, 16))
            ctk.CTkLabel(box, text=act.label, anchor="w",
                         font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w")
            getters: dict[str, Callable[[], str]] = {}
            for p in act.params:
                cell = ctk.CTkFrame(box, fg_color="transparent")
                cell.pack(side="left", padx=(0, 10))
                ctk.CTkLabel(cell, text=p.label, anchor="w",
                             font=ctk.CTkFont(size=10)).pack(anchor="w")
                getters[p.name] = make_param_input(cell, p)
            btn = ctk.CTkButton(box, text="执行", width=64, height=28,
                                corner_radius=6,
                                command=lambda a=act, g=getters: self._run_action(a, g))
            btn.pack(side="left", padx=(6, 0), pady=(14, 0))
            self._buttons.append(btn)

        self._tool_row.pack(anchor="w", fill="x", pady=(10, 0))

    # ------------------------------------------------------------------ 运算
    def _do_encode(self) -> None:
        self._run(crypto.encode)

    def _do_decode(self) -> None:
        self._run(crypto.decode)

    def _run(self, fn) -> None:
        """快照输入与参数（主线程），再把计算丢到后台线程。"""
        if self._tasks is None:
            return
        text = read(self._input)
        if not text:
            self._status.error("输入为空")
            return

        method = self._current.name
        label = self._current.label
        params = self._params()

        if not self._tasks.run(
            lambda: fn(text, method, **params),
            on_done=lambda result: self._on_computed(result, label),
            on_error=self._on_error,
        ):
            self._status.error("上一次运算还没结束，请稍候")
            return

        self._set_busy(True)
        self._status.busy(f"{label} 计算中…")

    def _on_computed(self, result: str, label: str) -> None:
        self._set_busy(False)
        write(self._output, result)
        self._status.info(f"{label} 完成，输出 {len(result)} 字符")

    def _on_error(self, error: Exception) -> None:
        self._set_busy(False)
        self._status.error(str(error) or error.__class__.__name__)

    def _run_action(self, action: crypto.Action, getters: dict) -> None:
        if self._tasks is None:
            return
        method = self._current.name
        params = {name: get() for name, get in getters.items()}

        if not self._tasks.run(
            lambda: crypto.run_action(method, action.name, **params),
            on_done=self._on_action_done,
            on_error=self._on_error,
        ):
            self._status.error("上一次运算还没结束，请稍候")
            return

        self._set_busy(True)
        self._status.busy(f"{action.label} 执行中…")

    def _on_action_done(self, message: str) -> None:
        self._set_busy(False)
        write(self._output, message)
        self._status.info(message)

    # ------------------------------------------------------------------ 其余按钮
    def _swap(self) -> None:
        text = read(self._output)
        if not text:
            self._status.error("输出为空，无可交换内容")
            return
        write(self._input, text)
        write(self._output, "")
        self._status.info("已把输出移到输入")

    def _copy_output(self) -> None:
        text = read(self._output)
        if not text:
            self._status.error("输出为空")
            return
        self.clipboard_clear()
        self.clipboard_append(text)
        self._status.info(f"已复制 {len(text)} 字符到剪贴板")

    def _clear(self) -> None:
        write(self._input, "")
        write(self._output, "")
        self._hide_results()
        self._status.clear()

    def _detect(self) -> None:
        hits = crypto.detect(read(self._input))
        if not hits:
            self._status.info("没有识别出已知编码特征")
            return
        names = "、".join(crypto.REGISTRY[h].label for h in hits)
        self._status.info(f"可能是：{names}")

    def _brute_force(self) -> None:
        if self._tasks is None:
            return
        text = read(self._input)
        if not text:
            self._status.error("输入为空")
            return

        method = self._current.name
        if not self._tasks.run(
            lambda: crypto.brute_force(text, method),
            on_done=self._on_brute_done,
            on_error=self._on_error,
        ):
            self._status.error("上一次运算还没结束，请稍候")
            return

        self._set_busy(True)
        self._status.busy("枚举中…")

    def _on_brute_done(self, rows: list[tuple[str, str]]) -> None:
        self._set_busy(False)
        self._hide_results()
        for i, (label, result) in enumerate(rows):
            ctk.CTkLabel(self._results, text=label, font=MONO_FONT, width=96,
                         anchor="w").grid(row=i, column=0, sticky="w", padx=(4, 8))
            ctk.CTkLabel(self._results, text=result or "（空）", font=MONO_FONT,
                         anchor="w").grid(row=i, column=1, sticky="w")
        self._results.grid()
        self._status.info(f"枚举出 {len(rows)} 种可能，见下方列表")

    def _hide_results(self) -> None:
        for widget in self._results.winfo_children():
            widget.destroy()
        self._results.grid_remove()
