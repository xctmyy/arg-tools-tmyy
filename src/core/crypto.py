"""密码与编码算法。

统一对外接口（待实现）：
    encode(text, method, **params) -> str
    decode(text, method, **params) -> str
    detect(text) -> list[str]          # 猜测可能的编码 / 密码类型
"""

from __future__ import annotations

#: 支持（规划中）的算法标识
CAPABILITIES: tuple[str, ...] = (
    # 经典替换密码
    "caesar", "rot13", "atbash", "vigenere", "rail_fence", "a1z26",
    "playfair", "nihilist", "book_cipher",
    # 编码
    "base16", "base32", "base64", "morse", "binary", "hex",
    "brainfuck", "ook", "url", "html_entity",
    # 哈希 / 校验
    "md5", "sha1", "sha256", "crc32",
)


def encode(text: str, method: str, **params: object) -> str:
    """按 method 加密 / 编码文本。"""
    raise NotImplementedError(f"encode: {method!r} 尚未实现")


def decode(text: str, method: str, **params: object) -> str:
    """按 method 解密 / 解码文本。"""
    raise NotImplementedError(f"decode: {method!r} 尚未实现")


def detect(text: str) -> list[str]:
    """启发式猜测输入可能是什么编码，按可能性从高到低返回。"""
    raise NotImplementedError("编码类型识别尚未实现")
