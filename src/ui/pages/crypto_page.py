"""密码 / 编码 工具页。

界面完全由 `core.crypto.REGISTRY` 驱动：算法下拉、参数表单、暴力枚举开关
都是读注册表生成的。因此新增算法只需改 core 层，本文件不用动。

线程模型
--------
编码 / 解码 / 暴力枚举都在后台线程执行（`src.ui.async_task.TaskRunner`），
避免大文本或 Brainfuck 解释把界面冻住。所有控件读写都发生在主线程：
启动前先把输入和参数快照成纯数据，计算完再回主线程写结果。

布局
----
    工具栏    算法下拉 + 算法说明
    参数区    随算法动态生成（位移、密钥、分隔符……）
    输入/输出 双栏文本框
    操作行    编码 / 解码 / 交换 / 清空 / 识别 / 暴力枚举
    结果区    暴力枚举结果（默认隐藏）
"""

from __future__ import annotations

import customtkinter as ctk

from src.core import crypto
from src.ui.async_task import TaskRunner
from src.ui.pages.base import BasePage

MONO = ("Consolas", 12)
BRUTE_FORCE_METHODS = {"caesar", "rail_fence", "rot13", "atbash"}


class CryptoPage(BasePage):
    title = "密码 / 编码"
    description = "替换密码、Base/摩斯编码与哈希计算"

    def __init__(self) -> None:
        self._codecs = crypto.available()
        self._by_display: dict[str, crypto.Codec] = {
            self._display(c): c for c in self._codecs
        }
        self._param_widgets: dict[str, ctk.CTkEntry] = {}
        self._current: crypto.Codec = self._codecs[0]
        self._action_buttons: list[ctk.CTkButton] = []
        self._tasks: TaskRunner | None = None

    # ------------------------------------------------------------------ 工具
    @staticmethod
    def _display(codec: crypto.Codec) -> str:
        return f"{codec.group} · {codec.label}"

    def _selected(self) -> crypto.Codec:
        return self._by_display[self._method_var.get()]

    def _params(self) -> dict[str, str]:
        return {name: w.get() for name, w in self._param_widgets.items()}

    def _set_status(self, text: str, error: bool = False) -> None:
        self._status.configure(
            text=text,
            text_color=("#c0392b", "#ff8a80") if error else ("gray40", "gray65"),
        )

    # ------------------------------------------------------------------ 构建
    def render(self, body: ctk.CTkFrame) -> None:
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(2, weight=1)

        self._build_toolbar(body)
        self._build_params(body)
        self._build_io(body)
        self._build_actions(body)
        self._build_results(body)

        self._tasks = TaskRunner(body)
        self._on_method_change(self._method_var.get())

    def _build_toolbar(self, body: ctk.CTkFrame) -> None:
        bar = ctk.CTkFrame(body, fg_color="transparent")
        bar.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        bar.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(bar, text="算法").grid(row=0, column=0, padx=(0, 8))

        self._method_var = ctk.StringVar(value=self._display(self._codecs[0]))
        self._method_menu = ctk.CTkOptionMenu(
            bar,
            variable=self._method_var,
            values=[self._display(c) for c in self._codecs],
            width=240,
            command=self._on_method_change,
        )
        self._method_menu.grid(row=0, column=1, sticky="w")

        self._note = ctk.CTkLabel(
            bar, text="", font=ctk.CTkFont(size=11), text_color=("gray45", "gray60")
        )
        self._note.grid(row=0, column=2, sticky="e")

    def _build_params(self, body: ctk.CTkFrame) -> None:
        self._param_frame = ctk.CTkFrame(body, fg_color="transparent")
        self._param_frame.grid(row=1, column=0, sticky="ew", pady=(0, 8))

    def _build_io(self, body: ctk.CTkFrame) -> None:
        io = ctk.CTkFrame(body, fg_color="transparent")
        io.grid(row=2, column=0, sticky="nsew")
        io.grid_columnconfigure(0, weight=1, uniform="io")
        io.grid_columnconfigure(1, weight=1, uniform="io")
        io.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(io, text="输入").grid(row=0, column=0, sticky="w", padx=4)
        ctk.CTkLabel(io, text="输出").grid(row=0, column=1, sticky="w", padx=4)

        self._input = ctk.CTkTextbox(io, wrap="word", font=MONO)
        self._input.grid(row=1, column=0, sticky="nsew", padx=(0, 6))
        self._output = ctk.CTkTextbox(io, wrap="word", font=MONO)
        self._output.grid(row=1, column=1, sticky="nsew", padx=(6, 0))

    def _build_actions(self, body: ctk.CTkFrame) -> None:
        row = ctk.CTkFrame(body, fg_color="transparent")
        row.grid(row=3, column=0, sticky="ew", pady=(10, 4))

        def btn(text: str, cmd, width: int = 88) -> None:
            b = ctk.CTkButton(row, text=text, width=width, command=cmd)
            b.pack(side="left", padx=(0, 6))
            self._action_buttons.append(b)

        btn("编码 →", self._do_encode)
        btn("解码 ←", self._do_decode)
        btn("交换 ⇅", self._swap, 76)
        btn("复制输出", self._copy_output, 88)
        btn("清空", self._clear, 64)
        btn("识别编码", self._detect, 88)

        self._brute_btn = ctk.CTkButton(
            row, text="暴力枚举", width=88, command=self._brute_force,
            fg_color=("gray70", "gray30"), hover_color=("gray60", "gray40"),
        )
        self._brute_btn.pack(side="left", padx=(0, 6))
        self._action_buttons.append(self._brute_btn)

        self._status = ctk.CTkLabel(
            body, text="", font=ctk.CTkFont(size=11), anchor="w"
        )
        self._status.grid(row=4, column=0, sticky="ew", pady=(0, 6))

    def _build_results(self, body: ctk.CTkFrame) -> None:
        self._results = ctk.CTkScrollableFrame(body, height=170, label_text="枚举结果")
        self._results.grid(row=5, column=0, sticky="ew")
        self._results.grid_columnconfigure(0, weight=1)
        self._results.grid_remove()  # 默认隐藏

    # ------------------------------------------------------------------ 忙碌态
    def _set_busy(self, busy: bool) -> None:
        """运算期间禁用交互，防止重复提交与参数被改到一半。"""
        state = "disabled" if busy else "normal"
        for b in self._action_buttons:
            b.configure(state=state)
        self._method_menu.configure(state=state)
        if not busy:
            self._sync_brute_button()

    def _sync_brute_button(self) -> None:
        self._brute_btn.configure(
            state="normal" if self._current.name in BRUTE_FORCE_METHODS else "disabled"
        )

    # ------------------------------------------------------------------ 交互
    def _on_method_change(self, _display: str) -> None:
        """切换算法：重建参数表单，更新说明与按钮可用性。"""
        codec = self._selected()
        self._current = codec

        for w in self._param_frame.winfo_children():
            w.destroy()
        self._param_widgets.clear()

        for col, p in enumerate(codec.params):
            cell = ctk.CTkFrame(self._param_frame, fg_color="transparent")
            cell.grid(row=0, column=col, padx=(0, 14), sticky="w")
            ctk.CTkLabel(cell, text=p.label, font=ctk.CTkFont(size=11)).pack(anchor="w")
            entry = ctk.CTkEntry(cell, width=170 if p.kind == "text" else 80,
                                 placeholder_text=p.hint)
            entry.insert(0, p.default)
            entry.pack(anchor="w")
            self._param_widgets[p.name] = entry

        self._note.configure(text=codec.note)
        self._sync_brute_button()
        self._hide_results()
        self._set_status("")

    def _do_encode(self) -> None:
        self._run(crypto.encode)

    def _do_decode(self) -> None:
        self._run(crypto.decode)

    def _run(self, fn) -> None:
        """快照输入与参数（主线程），再把计算丢到后台线程。"""
        if self._tasks is None:
            return
        text = self._input.get("1.0", "end-1c")
        if not text:
            self._set_status("输入为空", error=True)
            return

        method = self._current.name
        label = self._current.label
        params = self._params()  # 必须在主线程读取控件

        if not self._tasks.run(
            lambda: fn(text, method, **params),
            on_done=lambda result: self._on_computed(result, label),
            on_error=self._on_compute_error,
        ):
            self._set_status("上一次运算还没结束，请稍候", error=True)
            return

        self._set_busy(True)
        self._set_status(f"{label} 计算中…")

    def _on_computed(self, result: str, label: str) -> None:
        self._set_busy(False)
        self._output.delete("1.0", "end")
        self._output.insert("1.0", result)
        self._set_status(f"{label} 完成，输出 {len(result)} 字符")

    def _on_compute_error(self, error: Exception) -> None:
        self._set_busy(False)
        self._set_status(str(error) or error.__class__.__name__, error=True)

    def _swap(self) -> None:
        text = self._output.get("1.0", "end-1c")
        if not text:
            self._set_status("输出为空，无可交换内容", error=True)
            return
        self._input.delete("1.0", "end")
        self._input.insert("1.0", text)
        self._output.delete("1.0", "end")
        self._set_status("已把输出移到输入")

    def _copy_output(self) -> None:
        text = self._output.get("1.0", "end-1c")
        if not text:
            self._set_status("输出为空", error=True)
            return
        self.clipboard_clear()
        self.clipboard_append(text)
        self._set_status(f"已复制 {len(text)} 字符到剪贴板")

    def _clear(self) -> None:
        self._input.delete("1.0", "end")
        self._output.delete("1.0", "end")
        self._hide_results()
        self._set_status("")

    def _detect(self) -> None:
        text = self._input.get("1.0", "end-1c")
        hits = crypto.detect(text)
        if not hits:
            self._set_status("没有识别出已知编码特征")
            return
        names = "、".join(crypto.REGISTRY[h].label for h in hits)
        self._set_status(f"可能是：{names}")

    def _brute_force(self) -> None:
        if self._tasks is None:
            return
        text = self._input.get("1.0", "end-1c")
        if not text:
            self._set_status("输入为空", error=True)
            return

        method = self._current.name
        if not self._tasks.run(
            lambda: crypto.brute_force(text, method),
            on_done=self._on_brute_done,
            on_error=self._on_compute_error,
        ):
            self._set_status("上一次运算还没结束，请稍候", error=True)
            return

        self._set_busy(True)
        self._set_status("枚举中…")

    def _on_brute_done(self, rows: list[tuple[str, str]]) -> None:
        self._set_busy(False)
        self._hide_results()
        for i, (label, result) in enumerate(rows):
            ctk.CTkLabel(
                self._results, text=label, font=MONO, width=76, anchor="w"
            ).grid(row=i, column=0, sticky="w", padx=(4, 8))
            ctk.CTkLabel(
                self._results, text=result or "（空）", font=MONO, anchor="w"
            ).grid(row=i, column=1, sticky="w")
        self._results.grid()
        self._set_status(f"枚举出 {len(rows)} 种可能，见下方列表")

    def _hide_results(self) -> None:
        for w in self._results.winfo_children():
            w.destroy()
        self._results.grid_remove()
