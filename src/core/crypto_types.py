"""密码 / 编码模块的公共数据结构与工具。

单独成文件，是为了让「经典算法」（`crypto.py`）和「现代算法」
（`crypto_modern.py`）能共用同一套注册表，而不会互相 import 造成循环依赖。

`crypto.py` 会把这里的名字再导出一次，所以外部照旧 `crypto.Codec` 即可。
"""

from __future__ import annotations

import base64
import re
import secrets
from dataclasses import dataclass
from typing import Callable

# ============================================================ 数据结构


@dataclass(frozen=True)
class Param:
    """算法的一个参数。UI 据此生成输入控件。

    kind 取值：
        text      单行文本框
        int       整数输入（窄框）
        password  口令（掩码显示，带显示/隐藏切换）
        keyfile   密钥文件路径 + 浏览按钮
        dir       目录路径 + 选择按钮
        choice    下拉选择，需同时给 choices
        hexkey    十六进制密钥/IV/Nonce，带「生成」随机值按钮，用 size 指定字节数
    """

    name: str
    label: str
    default: str = ""
    kind: str = "text"
    hint: str = ""
    choices: tuple[str, ...] = ()
    #: hexkey 的字节长度，「生成」按钮据此产生随机值
    size: int = 0


@dataclass(frozen=True)
class Action:
    """不是编码/解码的一次性操作，例如「生成密钥对」。

    `fn(**params) -> str`，返回值是要展示给用户的一句话。
    文件写入等副作用由 fn 自己完成。
    """

    name: str
    label: str
    fn: Callable[..., str]
    params: tuple[Param, ...] = ()
    note: str = ""


@dataclass(frozen=True)
class Codec:
    """一个算法。"""

    name: str
    label: str
    group: str
    encode: Callable[..., str] | None
    decode: Callable[..., str] | None
    params: tuple[Param, ...] = ()
    note: str = ""
    actions: tuple[Action, ...] = ()

    @property
    def reversible(self) -> bool:
        """是否可逆（有解码方向）。哈希类不可逆。"""
        return self.decode is not None


# ============================================================ 注册表

REGISTRY: dict[str, Codec] = {}

#: 分组顺序（UI 侧边顺序即此）
GROUPS: tuple[str, ...] = ("替换密码", "需密钥", "编码", "现代密码", "哈希")


def register(codec: Codec) -> None:
    REGISTRY[codec.name] = codec


def available() -> list[Codec]:
    """按分组顺序返回全部算法。"""
    return [c for g in GROUPS for c in REGISTRY.values() if c.group == g]


# ============================================================ 通用工具


def as_int(value: object, label: str) -> int:
    """把 UI 传来的字符串转成整数，失败时给中文提示。"""
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        raise ValueError(f"参数「{label}」需要整数，收到 {value!r}") from None


def random_hex(nbytes: int) -> str:
    """生成 nbytes 字节的密码学安全随机数，返回十六进制字符串。

    用 `secrets` 而不是 `random`——后者是可预测的伪随机，拿来生成密钥等于没加密。
    """
    if nbytes <= 0:
        raise ValueError("随机字节数必须为正")
    return secrets.token_hex(nbytes)


def illegal_chars(raw: str, pattern: str) -> str:
    """找出不合法字符，用于给出比标准库更清楚的中文报错。

    标准库在遇到非 ASCII 输入时抛的是英文 `ValueError`
    （"string argument should contain only ASCII characters"），
    直接透给用户很难懂，所以先自己检查一遍字符集。
    """
    bad = sorted(set(re.findall(pattern, raw)))
    return " ".join(bad[:8])


def as_utf8(data: bytes, label: str) -> str:
    """把解出的字节按 UTF-8 转文本，失败时给出可读的提示。"""
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as e:
        raise ValueError(f"{label} 解出的字节不是 UTF-8 文本：{e}") from None


# ------------------------------------------------------------ 密文的文本表示

#: 现代密码产生的是二进制密文，必须转成文本才能放进输入框
OUT_ENCODINGS: tuple[str, ...] = ("base64", "hex", "base32")


def encode_bytes(data: bytes, how: str = "base64") -> str:
    """把二进制密文转成可粘贴的文本。"""
    if how == "hex":
        return data.hex()
    if how == "base32":
        return base64.b32encode(data).decode("ascii")
    return base64.b64encode(data).decode("ascii")


def decode_bytes(text: str, how: str = "base64") -> bytes:
    """把文本密文还原成二进制。"""
    raw = re.sub(r"\s+", "", text)
    try:
        if how == "hex":
            return bytes.fromhex(raw)
        if how == "base32":
            return base64.b32decode(raw.upper() + "=" * (-len(raw) % 8))
        return base64.b64decode(raw + "=" * (-len(raw) % 4), validate=True)
    except Exception as e:  # noqa: BLE001 —— 各种编码错误统一转成中文提示
        raise ValueError(f"密文不是合法的 {how}：{e}") from None


def hex_to_bytes(value: str, label: str, lengths: tuple[int, ...]) -> bytes:
    """把十六进制字符串转成定长字节串，长度不符时给中文提示。"""
    raw = re.sub(r"[\s:_-]", "", value or "")
    if not raw:
        raise ValueError(f"请填写{label}（十六进制）")
    bad = illegal_chars(raw, r"[^0-9A-Fa-f]")
    if bad:
        raise ValueError(f"{label}含非十六进制字符：{bad}")
    if len(raw) % 2:
        raise ValueError(f"{label}的十六进制长度必须是偶数")
    data = bytes.fromhex(raw)
    if lengths and len(data) not in lengths:
        want = " 或 ".join(f"{n} 字节（{n * 2} 个十六进制字符）" for n in lengths)
        raise ValueError(f"{label}长度应为 {want}，当前 {len(data)} 字节")
    return data
