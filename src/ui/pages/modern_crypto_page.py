"""现代密码 工具页。

与「密码 / 编码」页共用同一份算法注册表，但布局是专门设计的：

    左侧  密钥侧 —— 算法参数、密钥信息（类型/长度/指纹）、生成密钥对
    右侧  操作侧 —— 加密 / 解密、输入与输出

之所以单独成页：AES/RSA/ECC 需要的东西（密钥文件、随机密钥、密钥指纹、
密钥对生成）在经典密码那种"一行参数 + 一个下拉"的界面里根本放不下。

线程模型与经典页一致：所有运算走 `TaskRunner` 在后台线程执行，
控件读写只发生在主线程。
"""

from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from src.core import crypto
from src.ui.async_task import TaskRunner
from src.ui.pages.base import BasePage
from src.ui.widgets import (
    ACCENT,
    CARD_BORDER,
    MONO_FONT,
    MUTED,
    Card,
    Selector,
    StatusLine,
    info_row,
    make_param_input,
    read,
    write,
)

GROUP = "现代密码"


class ModernCryptoPage(BasePage):
    title = "现代密码"
    description = "AES / ChaCha20 / RSA / ECC —— 密钥管理、加密与解密"

    def __init__(self) -> None:
        self._codecs = [c for c in crypto.available() if c.group == GROUP]
        self._by_key = {c.name: c for c in self._codecs}
        self._current: crypto.Codec = self._codecs[0]
        self._getters: dict[str, Callable[[], str]] = {}
        self._action_getters: dict[str, Callable[[], str]] = {}
        self._keyinfo_setters: dict[str, Callable[[str], None]] = {}
        #: 右栏按钮（只建一次）与左栏按钮（每次切算法重建），分开管理，
        #: 否则切换算法后 _set_busy 会去操作已销毁的控件
        self._op_buttons: list[ctk.CTkButton] = []
        self._left_buttons: list[ctk.CTkButton] = []
        self._tasks: TaskRunner | None = None

    # ------------------------------------------------------------------ 构建
    def render(self, body: ctk.CTkFrame) -> None:
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(2, weight=1)

        if not crypto.modern_available():
            ctk.CTkLabel(
                body,
                text="⚠ 未安装 cryptography 库，现代算法不可用。请执行："
                     "pip install cryptography",
                anchor="w", font=ctk.CTkFont(size=12),
                text_color=("#c0392b", "#ff8a80"),
            ).grid(row=0, column=0, sticky="ew", pady=(0, 8))

        self._build_selector(body)
        self._build_main(body)

        self._status = StatusLine(body)
        self._status.grid(row=3, column=0, sticky="ew", pady=(8, 0))

        self._tasks = TaskRunner(body)
        self._on_method_change(self._codecs[0].name)

    def _build_selector(self, body: ctk.CTkFrame) -> None:
        wrap = ctk.CTkFrame(body, fg_color="transparent")
        wrap.grid(row=0, column=0, sticky="ew")
        wrap.grid_columnconfigure(0, weight=1)

        self._selector = Selector(
            wrap,
            [(c.name, c.label) for c in self._codecs],
            command=self._on_method_change,
            columns=4,
        )
        self._selector.grid(row=0, column=0, sticky="ew")

        self._note = ctk.CTkLabel(
            wrap, text="", anchor="w", justify="left",
            font=ctk.CTkFont(size=11), text_color=MUTED,
        )
        self._note.grid(row=1, column=0, sticky="ew", pady=(2, 6))

    def _build_main(self, body: ctk.CTkFrame) -> None:
        main = ctk.CTkFrame(body, fg_color="transparent")
        main.grid(row=2, column=0, sticky="nsew")
        main.grid_rowconfigure(0, weight=1)
        main.grid_columnconfigure(1, weight=1)

        # 左：密钥侧。参数可能很多，做成可滚动。
        self._left = ctk.CTkScrollableFrame(main, width=390)
        self._left.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        self._left.grid_columnconfigure(0, weight=1)

        # 右：操作侧
        self._right = ctk.CTkFrame(main, fg_color="transparent")
        self._right.grid(row=0, column=1, sticky="nsew")
        self._right.grid_rowconfigure(0, weight=1)
        self._right.grid_columnconfigure(0, weight=1)
        self._build_operation(self._right)

    def _build_operation(self, parent: ctk.CTkFrame) -> None:
        card = Card(parent, title="加密 / 解密")
        card.grid(row=0, column=0, sticky="nsew")
        b = card.body
        b.grid_rowconfigure(2, weight=1)
        b.grid_rowconfigure(4, weight=1)

        row = ctk.CTkFrame(b, fg_color="transparent")
        row.grid(row=0, column=0, sticky="ew", pady=(0, 8))

        def btn(text: str, cmd, width: int = 90) -> None:
            widget = ctk.CTkButton(row, text=text, width=width, height=30,
                                   corner_radius=6, command=cmd)
            widget.pack(side="left", padx=(0, 6))
            self._op_buttons.append(widget)

        btn("加密 →", self._do_encode)
        btn("解密 ←", self._do_decode)
        btn("交换 ⇅", self._swap, 78)
        btn("复制结果", self._copy_output, 86)
        btn("清空", self._clear, 64)

        ctk.CTkLabel(b, text="明文 / 密文", anchor="w",
                     font=ctk.CTkFont(size=11)).grid(row=1, column=0, sticky="w")
        self._input = ctk.CTkTextbox(b, wrap="word", font=MONO_FONT)
        self._input.grid(row=2, column=0, sticky="nsew", pady=(2, 8))

        ctk.CTkLabel(b, text="结果", anchor="w",
                     font=ctk.CTkFont(size=11)).grid(row=3, column=0, sticky="w")
        self._output = ctk.CTkTextbox(b, wrap="word", font=MONO_FONT)
        self._output.grid(row=4, column=0, sticky="nsew")

    # ------------------------------------------------------------------ 左栏
    def _is_asymmetric(self, codec: crypto.Codec) -> bool:
        return any(p.kind == "keyfile" for p in codec.params)

    def _render_left(self, codec: crypto.Codec) -> None:
        """重建左栏。密钥信息嵌在参数卡片内部，不单独占一行。"""
        for widget in self._left.winfo_children():
            widget.destroy()
        self._getters.clear()
        self._action_getters.clear()
        self._keyinfo_setters.clear()
        self._left_buttons.clear()

        asymmetric = self._is_asymmetric(codec)
        params_card = Card(
            self._left,
            title="密钥对" if asymmetric else "密钥材料",
            subtitle="PEM 密钥文件；加密用公钥，解密用私钥" if asymmetric else "",
        )
        params_card.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        for p in codec.params:
            extra = [("信息", lambda _e: self._load_key_info())] if p.kind == "keyfile" else None
            self._getters[p.name] = self._param_field(params_card.body, p, extra)

        if asymmetric:
            self._render_keyinfo(params_card.body)

        if codec.actions:
            self._render_actions(codec, row=1)

    def _param_field(self, parent, param, extra) -> Callable[[], str]:
        """参数控件。与经典页共用同一工厂，保证两页外观一致。"""
        holder = ctk.CTkFrame(parent, fg_color="transparent")
        holder.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(holder, text=param.label, anchor="w",
                     font=ctk.CTkFont(size=11)).pack(anchor="w")
        return make_param_input(holder, param, extra)

    def _render_keyinfo(self, parent) -> None:
        """密钥信息：类型 / 长度 / 曲线 / 指纹。指纹用只读框，方便复制核对。"""
        ctk.CTkFrame(parent, height=1, fg_color=CARD_BORDER).pack(fill="x", pady=8)
        ctk.CTkLabel(parent, text="密钥信息", anchor="w",
                     font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w")

        box = ctk.CTkFrame(parent, fg_color="transparent")
        box.pack(fill="x", pady=(4, 0))
        for key, label in (("kind", "类型"), ("bits", "长度"),
                           ("curve", "曲线"), ("fp", "指纹")):
            self._keyinfo_setters[key] = info_row(box, label, "—")

        btn = ctk.CTkButton(
            parent, text="读取密钥信息", height=28, corner_radius=6,
            command=self._load_key_info,
        )
        btn.pack(anchor="w", pady=(8, 0))
        self._left_buttons.append(btn)

    def _render_actions(self, codec: crypto.Codec, row: int) -> None:
        for act in codec.actions:
            card = Card(self._left, title=act.label, subtitle=act.note)
            card.grid(row=row, column=0, sticky="ew", pady=(0, 10))
            row += 1

            for p in act.params:
                self._action_getters[p.name] = self._param_field(card.body, p, None)

            btn = ctk.CTkButton(
                card.body, text="生成", height=30, corner_radius=6,
                fg_color=ACCENT, command=lambda a=act: self._run_action(a),
            )
            btn.pack(fill="x")
            self._left_buttons.append(btn)

    # ------------------------------------------------------------------ 交互
    def _on_method_change(self, key: str) -> None:
        codec = self._by_key.get(key)
        if codec is None:
            return
        self._current = codec
        self._selector.set(key)
        self._note.configure(text=codec.note)
        self._render_left(codec)
        write(self._output, "")
        self._status.clear()

    def _set_busy(self, busy: bool) -> None:
        state = "disabled" if busy else "normal"
        for btn in (*self._op_buttons, *self._left_buttons):
            btn.configure(state=state)
        self._selector.set_enabled(not busy)

    # ------------------------------------------------------------------ 运算
    def _do_encode(self) -> None:
        self._run(crypto.encode)

    def _do_decode(self) -> None:
        self._run(crypto.decode)

    def _run(self, fn) -> None:
        if self._tasks is None:
            return
        text = read(self._input)
        if not text:
            self._status.error("输入为空")
            return

        method = self._current.name
        label = self._current.label
        params = {name: get() for name, get in self._getters.items()}

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

    def _run_action(self, action: crypto.Action) -> None:
        if self._tasks is None:
            return
        method = self._current.name
        params = {name: get() for name, get in self._action_getters.items()}

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

    def _load_key_info(self) -> None:
        """读取密钥文件信息。优先公钥，其次私钥。"""
        if self._tasks is None:
            return
        pub = self._getters.get("pubkey", lambda: "")()
        priv = self._getters.get("privkey", lambda: "")()
        password = self._getters.get("password", lambda: "")()
        path = pub or priv
        if not path:
            self._status.error("请先填写公钥或私钥文件路径")
            return

        use_password = password if (not pub and priv) else ""
        if not self._tasks.run(
            lambda: crypto.key_info(path, use_password),
            on_done=self._on_key_info,
            on_error=self._on_error,
        ):
            self._status.error("上一次运算还没结束，请稍候")
            return

        self._set_busy(True)
        self._status.busy("读取密钥信息…")

    def _on_key_info(self, info: dict) -> None:
        self._set_busy(False)
        for key, setter in self._keyinfo_setters.items():
            setter(info.get({"fp": "fingerprint"}.get(key, key), "") or "—")
        self._status.info(f"已读取{info['private']}：{info['path']}")

    # ------------------------------------------------------------------ 其余
    def _swap(self) -> None:
        text = read(self._output)
        if not text:
            self._status.error("结果为空，无可交换内容")
            return
        write(self._input, text)
        write(self._output, "")
        self._status.info("已把结果移到输入")

    def _copy_output(self) -> None:
        text = read(self._output)
        if not text:
            self._status.error("结果为空")
            return
        self.clipboard_clear()
        self.clipboard_append(text)
        self._status.info(f"已复制 {len(text)} 字符到剪贴板")

    def _clear(self) -> None:
        write(self._input, "")
        write(self._output, "")
        self._status.clear()
