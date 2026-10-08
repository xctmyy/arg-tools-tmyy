"""密码与编码算法实现（经典算法）。

现代算法（AES / ChaCha20 / RSA / ECC）在 `crypto_modern.py`，
本模块在末尾 import 它，两者共用 `crypto_types.REGISTRY` 注册表。

对外接口
--------
    encode(text, method, **params) -> str      加密 / 编码
    decode(text, method, **params) -> str      解密 / 解码
    detect(text) -> list[str]                  猜测可能的编码类型
    brute_force(text, method) -> list[tuple]   无密钥暴力枚举
    REGISTRY                                   算法注册表（UI 据此生成表单）

设计说明
--------
每个算法是一个 `Codec`，登记进 `REGISTRY`。UI 读取 `params` 自动生成参数输入框，
因此新增算法只需在注册表里加一条，不必改界面代码。
"""

from __future__ import annotations

import base64
import hashlib
import html
import math
import quopri
import re
import string
import urllib.parse
import zlib
from typing import Callable

from src.core.crypto_types import (
    GROUPS,
    OUT_ENCODINGS,
    REGISTRY,
    Codec,
    Param,
    as_int as _as_int,
    as_utf8 as _as_utf8,
    available,
    decode_bytes as _decode_bytes,
    encode_bytes as _encode_bytes,
    illegal_chars as _illegal_chars,
    register as _register,
)


# ============================================================ 基础工具

UPPER = string.ascii_uppercase
LOWER = string.ascii_lowercase


def _map_letters(text: str, table: dict[str, str]) -> str:
    """按表替换字母，保留大小写与非字母字符。"""
    out = []
    for ch in text:
        if ch in table:
            out.append(table[ch])
        elif ch.isalpha() and ch.upper() in table:
            out.append(table[ch.upper()].lower())
        else:
            out.append(ch)
    return "".join(out)


def _caesar_shift(text: str, shift: int) -> str:
    out = []
    for ch in text:
        if ch in UPPER:
            out.append(UPPER[(UPPER.index(ch) + shift) % 26])
        elif ch in LOWER:
            out.append(LOWER[(LOWER.index(ch) + shift) % 26])
        else:
            out.append(ch)
    return "".join(out)


# ============================================================ 替换密码


def _rot13(text: str, **_: object) -> str:
    return _caesar_shift(text, 13)


def _rot47(text: str, **_: object) -> str:
    """ROT47：对 33-126 的可打印 ASCII 做 47 位移，加密即解密。"""
    out = []
    for ch in text:
        o = ord(ch)
        out.append(chr(33 + (o - 33 + 47) % 94) if 33 <= o <= 126 else ch)
    return "".join(out)


def _atbash(text: str, **_: object) -> str:
    table = {UPPER[i]: UPPER[25 - i] for i in range(26)}
    return _map_letters(text, table)


def _a1z26_encode(text: str, sep: str = "-", **_: object) -> str:
    nums = [str(ord(ch.upper()) - 64) for ch in text if ch.isalpha()]
    return sep.join(nums)


def _a1z26_decode(text: str, sep: str = "-", **_: object) -> str:
    parts = [p for p in re.split(r"[^0-9]+", text) if p]
    out = []
    for p in parts:
        n = int(p)
        if not 1 <= n <= 26:
            raise ValueError(f"A1Z26 数值越界：{n}（应在 1-26）")
        out.append(UPPER[n - 1])
    return "".join(out)


# ============================================================ 需密钥


def _vigenere(text: str, key: str = "", decrypt: bool = False, **_: object) -> str:
    letters = [c for c in key.upper() if c.isalpha()]
    if not letters:
        raise ValueError("维吉尼亚密码需要密钥（至少一个字母）")
    out = []
    ki = 0
    for ch in text:
        if ch.isalpha():
            base = ord("A") if ch.isupper() else ord("a")
            k = ord(letters[ki % len(letters)]) - ord("A")
            if decrypt:
                k = -k
            out.append(chr((ord(ch) - base + k) % 26 + base))
            ki += 1
        else:
            out.append(ch)
    return "".join(out)


def _rail_pattern(length: int, rails: int) -> list[int]:
    """之字形栅栏的轨道序列。"""
    pattern = []
    r, step = 0, 1
    for _ in range(length):
        pattern.append(r)
        if r == 0:
            step = 1
        elif r == rails - 1:
            step = -1
        r += step
    return pattern


def _rail_fence_encode(text: str, rails: str = "2", **_: object) -> str:
    n = _as_int(rails, "栏数")
    if n < 2:
        return text
    rows: list[list[str]] = [[] for _ in range(n)]
    for ch, r in zip(text, _rail_pattern(len(text), n)):
        rows[r].append(ch)
    return "".join("".join(row) for row in rows)


def _rail_fence_decode(text: str, rails: str = "2", **_: object) -> str:
    n = _as_int(rails, "栏数")
    if n < 2:
        return text
    pattern = _rail_pattern(len(text), n)
    counts = [pattern.count(i) for i in range(n)]
    rows, idx = [], 0
    for c in counts:
        rows.append(list(text[idx : idx + c]))
        idx += c
    ptrs = [0] * n
    out = []
    for r in pattern:
        out.append(rows[r][ptrs[r]])
        ptrs[r] += 1
    return "".join(out)


def _polybius(key: str = "") -> list[str]:
    """构造 25 字母方阵（I/J 合并），返回按行列展开的字母表。"""
    seen: list[str] = []
    for ch in key.upper() + UPPER:
        if not ch.isalpha():
            continue
        ch = "I" if ch == "J" else ch
        if ch not in seen:
            seen.append(ch)
    return seen


def _playfair_pairs(text: str) -> list[tuple[str, str]]:
    letters = [("I" if c == "J" else c) for c in text.upper() if c.isalpha()]
    pairs, i = [], 0
    while i < len(letters):
        a = letters[i]
        if i + 1 < len(letters):
            b = letters[i + 1]
            if a == b:
                pairs.append((a, "X"))
                i += 1
            else:
                pairs.append((a, b))
                i += 2
        else:
            pairs.append((a, "X"))
            i += 1
    return pairs


def _playfair_shift(text: str, key: str, step: int) -> str:
    sq = _polybius(key)
    pos = {ch: divmod(i, 5) for i, ch in enumerate(sq)}
    out = []
    for a, b in _playfair_pairs(text):
        ra, ca = pos[a]
        rb, cb = pos[b]
        if ra == rb:  # 同行：左右移
            out.append(sq[ra * 5 + (ca + step) % 5])
            out.append(sq[rb * 5 + (cb + step) % 5])
        elif ca == cb:  # 同列：上下移
            out.append(sq[((ra + step) % 5) * 5 + ca])
            out.append(sq[((rb + step) % 5) * 5 + cb])
        else:  # 矩形：交换列
            out.append(sq[ra * 5 + cb])
            out.append(sq[rb * 5 + ca])
    return "".join(out)


def _playfair_encode(text: str, key: str = "", **_: object) -> str:
    return _playfair_shift(text, key, 1)


def _playfair_decode(text: str, key: str = "", **_: object) -> str:
    raw = _playfair_shift(text, key, -1)
    # 抹掉加密阶段插入的填充 X：位于两个相同字母之间，或位于结尾
    out: list[str] = []
    i = 0
    while i < len(raw):
        ch = raw[i]
        if ch == "X":
            nxt = raw[i + 1] if i + 1 < len(raw) else ""
            prev = out[-1] if out else ""
            if i == len(raw) - 1 or nxt == prev:
                i += 1
                continue
        out.append(ch)
        i += 1
    return "".join(out)


def _nihilist_encode(
    text: str, key: str = "", numeric_key: str = "", **_: object
) -> str:
    sq = _polybius(key)
    pos = {ch: (i // 5 + 1) * 10 + (i % 5 + 1) for i, ch in enumerate(sq)}

    def num(ch: str) -> int:
        ch = "I" if ch.upper() == "J" else ch.upper()
        if ch not in pos:
            raise ValueError(f"尼希利斯特：字符 {ch!r} 不在方阵内")
        return pos[ch]

    ks = [num(c) for c in numeric_key if c.isalpha()]
    if not ks:
        raise ValueError("尼希利斯特密码需要数字密钥（至少一个字母）")
    pts = [num(c) for c in text if c.isalpha()]
    return " ".join(str(p + ks[i % len(ks)]) for i, p in enumerate(pts))


def _nihilist_decode(
    text: str, key: str = "", numeric_key: str = "", **_: object
) -> str:
    sq = _polybius(key)
    pos = {ch: (i // 5 + 1) * 10 + (i % 5 + 1) for i, ch in enumerate(sq)}
    ks = [
        pos["I" if c.upper() == "J" else c.upper()]
        for c in numeric_key
        if c.isalpha()
    ]
    if not ks:
        raise ValueError("尼希利斯特密码需要数字密钥（至少一个字母）")
    out = []
    for i, v in enumerate(int(x) for x in re.findall(r"\d+", text)):
        n = v - ks[i % len(ks)]
        if not 11 <= n <= 55 or n % 10 == 0 or n % 10 > 5:
            raise ValueError(f"尼希利斯特：解出的数字 {n} 非法（密钥可能不对）")
        out.append(sq[(n // 10 - 1) * 5 + (n % 10 - 1)])
    return "".join(out)


def _book_encode(text: str, book: str = "", sep: str = " ", **_: object) -> str:
    if not book.strip():
        raise ValueError("书本密码需要提供书本内容")
    words = book.split()
    index: dict[str, tuple[int, int]] = {}
    for wi, w in enumerate(words):
        for ci, ch in enumerate(w):
            index.setdefault(ch.lower(), (wi, ci))
    out = []
    for ch in text:
        k = ch.lower()
        if k not in index:
            raise ValueError(f"书本密码：书中找不到字符 {ch!r}")
        wi, ci = index[k]
        out.append(f"{wi + 1}:{ci + 1}")
    return sep.join(out)


def _book_decode(text: str, book: str = "", sep: str = " ", **_: object) -> str:
    words = book.split()
    if not words:
        raise ValueError("书本密码需要提供书本内容")
    out = []
    for wi, ci in re.findall(r"(\d+)\s*[:：]\s*(\d+)", text):
        w, c = int(wi) - 1, int(ci) - 1
        if not 0 <= w < len(words) or not 0 <= c < len(words[w]):
            raise ValueError(f"书本密码：位置 {wi}:{ci} 超出范围")
        out.append(words[w][c])
    return "".join(out)


# ============================================================ 编码


def _b64_encode(text: str, **_: object) -> str:
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


def _b64_decode(text: str, **_: object) -> str:
    raw = re.sub(r"\s+", "", text)
    bad = _illegal_chars(raw, r"[^A-Za-z0-9+/=]")
    if bad:
        raise ValueError(f"Base64 只接受 A-Z a-z 0-9 + / =，发现非法字符：{bad}")
    raw += "=" * (-len(raw) % 4)  # 补齐 padding
    try:
        data = base64.b64decode(raw, validate=True)
    except ValueError as e:
        raise ValueError(f"不是合法的 Base64：{e}") from None
    return _as_utf8(data, "Base64")


def _b32_encode(text: str, **_: object) -> str:
    return base64.b32encode(text.encode("utf-8")).decode("ascii")


def _b32_decode(text: str, **_: object) -> str:
    raw = re.sub(r"\s+", "", text).upper()
    bad = _illegal_chars(raw, r"[^A-Z2-7=]")
    if bad:
        raise ValueError(f"Base32 只接受 A-Z 2-7 =，发现非法字符：{bad}")
    raw += "=" * (-len(raw) % 8)
    try:
        data = base64.b32decode(raw)
    except ValueError as e:
        raise ValueError(f"不是合法的 Base32：{e}") from None
    return _as_utf8(data, "Base32")


def _b16_encode(text: str, **_: object) -> str:
    return base64.b16encode(text.encode("utf-8")).decode("ascii")


def _b16_decode(text: str, **_: object) -> str:
    raw = re.sub(r"\s+", "", text)
    bad = _illegal_chars(raw, r"[^0-9A-Fa-f]")
    if bad:
        raise ValueError(f"Base16 只接受 0-9 A-F，发现非法字符：{bad}")
    try:
        data = base64.b16decode(raw.upper())
    except ValueError as e:
        raise ValueError(f"不是合法的 Base16：{e}") from None
    return _as_utf8(data, "Base16")


MORSE: dict[str, str] = {
    "A": ".-", "B": "-...", "C": "-.-.", "D": "-..", "E": ".", "F": "..-.",
    "G": "--.", "H": "....", "I": "..", "J": ".---", "K": "-.-", "L": ".-..",
    "M": "--", "N": "-.", "O": "---", "P": ".--.", "Q": "--.-", "R": ".-.",
    "S": "...", "T": "-", "U": "..-", "V": "...-", "W": ".--", "X": "-..-",
    "Y": "-.--", "Z": "--..",
    "0": "-----", "1": ".----", "2": "..---", "3": "...--", "4": "....-",
    "5": ".....", "6": "-....", "7": "--...", "8": "---..", "9": "----.",
    ".": ".-.-.-", ",": "--..--", "?": "..--..", "'": ".----.", "!": "-.-.--",
    "/": "-..-.", "(": "-.--.", ")": "-.--.-", "&": ".-...", ":": "---...",
    ";": "-.-.-.", "=": "-...-", "+": ".-.-.", "-": "-....-", "_": "..--.-",
    '"': ".-..-.", "$": "...-..-", "@": ".--.-.",
}
MORSE_REV = {v: k for k, v in MORSE.items()}

#: 摩斯的字符集模式
MORSE_MODE_ASCII = "标准（仅 ASCII）"
MORSE_MODE_UNICODE = "Unicode（支持中文）"
MORSE_MODES = (MORSE_MODE_ASCII, MORSE_MODE_UNICODE)


def _codepoint_morse(ch: str) -> str:
    """把一个字符的 Unicode 码点写成十六进制，再把每个十六进制位写成摩斯。"""
    return " ".join(MORSE[d] for d in format(ord(ch), "X"))


def _morse_encode(text: str, word_sep: str = "/", mode: str = MORSE_MODE_ASCII,
                  **_: object) -> str:
    """摩斯编码。

    Unicode 模式：每个字符按其码点的十六进制编码，逐位转摩斯，组间用分隔符隔开。
    这样中文也能编码，且完全可逆——代价是输出比标准摩斯长。
    """
    if mode == MORSE_MODE_UNICODE:
        groups = [_codepoint_morse(ch) for ch in text]
        return f" {word_sep} ".join(g for g in groups if g)

    non_ascii = sorted({c for c in text if ord(c) > 127})
    if non_ascii:
        raise ValueError(
            f"标准摩斯只支持 ASCII，遇到非 ASCII 字符：{' '.join(non_ascii[:8])}。"
            f"要编码中文请把「字符集」切到 {MORSE_MODE_UNICODE}"
        )
    out = []
    for word in text.upper().split():
        codes = [MORSE[ch] for ch in word if ch in MORSE]
        if codes:
            out.append(" ".join(codes))
    return f" {word_sep} ".join(out)


def _morse_decode(text: str, word_sep: str = "/", mode: str = MORSE_MODE_ASCII,
                  **_: object) -> str:
    norm = text.replace("·", ".").replace("−", "-").replace("–", "-").strip()

    if mode == MORSE_MODE_UNICODE:
        sep = re.escape(word_sep) if word_sep else r"\s+"
        out = []
        for group in re.split(rf"\s*{sep}\s*", norm):
            digits = "".join(MORSE_REV.get(t, "") for t in group.split() if t)
            if not digits:
                continue
            try:
                out.append(chr(int(digits, 16)))
            except ValueError:
                raise ValueError(
                    f"Unicode 模式下这组不是合法十六进制：{digits}"
                ) from None
        return "".join(out)

    words = re.split(r"(?:\s*/\s*|\s{3,})", norm)
    out = []
    for w in words:
        out.append("".join(MORSE_REV.get(t, "") for t in w.split() if t))
    return " ".join(x for x in out if x)


def _binary_encode(text: str, sep: str = " ", **_: object) -> str:
    return sep.join(f"{b:08b}" for b in text.encode("utf-8"))


def _binary_decode(text: str, sep: str = " ", **_: object) -> str:
    bits = re.sub(r"[^01]", "", text)
    if not bits:
        raise ValueError("没有找到二进制内容")
    if len(bits) % 8:
        raise ValueError(f"二进制长度 {len(bits)} 不是 8 的倍数")
    return bytes(int(bits[i : i + 8], 2) for i in range(0, len(bits), 8)).decode(
        "utf-8", "replace"
    )


def _hex_encode(text: str, sep: str = " ", **_: object) -> str:
    return sep.join(f"{b:02x}" for b in text.encode("utf-8"))


def _hex_decode(text: str, sep: str = " ", **_: object) -> str:
    raw = re.sub(r"[^0-9A-Fa-f]", "", text)
    if len(raw) % 2:
        raise ValueError("十六进制长度为奇数")
    try:
        return bytes.fromhex(raw).decode("utf-8")
    except (ValueError, UnicodeDecodeError) as e:
        raise ValueError(f"不是合法的十六进制：{e}") from None


def _url_encode(text: str, **_: object) -> str:
    return urllib.parse.quote(text, safe="")


def _url_decode(text: str, **_: object) -> str:
    return urllib.parse.unquote(text)


def _html_encode(text: str, **_: object) -> str:
    return html.escape(text, quote=True)


def _html_decode(text: str, **_: object) -> str:
    return html.unescape(text)


# ------------------------------------------------------------ Brainfuck / Ook

BF_CHARS = "><+-.,[]"

OOK_TO_BF: dict[tuple[str, str], str] = {
    ("Ook.", "Ook?"): ">",
    ("Ook?", "Ook."): "<",
    ("Ook.", "Ook."): "+",
    ("Ook!", "Ook!"): "-",
    ("Ook!", "Ook."): ".",
    ("Ook.", "Ook!"): ",",
    ("Ook!", "Ook?"): "[",
    ("Ook?", "Ook!"): "]",
}
BF_TO_OOK = {v: k for k, v in OOK_TO_BF.items()}


def _bf_encode(text: str, **_: object) -> str:
    """把文本编码为 Brainfuck：每字符先清零，再加到对应码值并输出。"""
    return "".join("[-]" + "+" * b + "." for b in text.encode("utf-8"))


def _bf_run(code: str, max_steps: int = 2_000_000) -> str:
    """执行 Brainfuck，返回输出（按 UTF-8 解码）。"""
    prog = [ch for ch in code if ch in BF_CHARS]
    jumps: dict[int, int] = {}
    stack: list[int] = []
    for i, ch in enumerate(prog):
        if ch == "[":
            stack.append(i)
        elif ch == "]":
            if not stack:
                raise ValueError("Brainfuck 括号不匹配")
            j = stack.pop()
            jumps[i], jumps[j] = j, i
    if stack:
        raise ValueError("Brainfuck 括号不匹配")

    tape = bytearray(30000)
    ptr, pc, steps = 0, 0, 0
    out = bytearray()
    while pc < len(prog):
        steps += 1
        if steps > max_steps:
            raise ValueError("Brainfuck 执行步数超限，可能存在死循环")
        ch = prog[pc]
        if ch == ">":
            ptr += 1
            if ptr >= len(tape):
                raise ValueError("Brainfuck 指针越界")
        elif ch == "<":
            ptr -= 1
            if ptr < 0:
                raise ValueError("Brainfuck 指针越界")
        elif ch == "+":
            tape[ptr] = (tape[ptr] + 1) % 256
        elif ch == "-":
            tape[ptr] = (tape[ptr] - 1) % 256
        elif ch == ".":
            out.append(tape[ptr])
        elif ch == "[" and tape[ptr] == 0:
            pc = jumps[pc]
        elif ch == "]" and tape[ptr] != 0:
            pc = jumps[pc]
        pc += 1
    return bytes(out).decode("utf-8", "replace")


def _bf_decode(text: str, **_: object) -> str:
    return _bf_run(text)


def _ook_encode(text: str, **_: object) -> str:
    bf = _bf_encode(text)
    return " ".join(" ".join(BF_TO_OOK[ch]) for ch in bf if ch in BF_TO_OOK)


def _ook_decode(text: str, **_: object) -> str:
    words = re.findall(r"Ook[.!?]", text)
    if len(words) % 2:
        raise ValueError("Ook 词数为奇数，无法配对")
    bf = []
    for i in range(0, len(words), 2):
        pair = (words[i], words[i + 1])
        if pair not in OOK_TO_BF:
            raise ValueError(f"无效的 Ook 组合：{' '.join(pair)}")
        bf.append(OOK_TO_BF[pair])
    return _bf_run("".join(bf))


# ============================================================ 哈希（单向）


def _hash_factory(algo: str) -> Callable[..., str]:
    def run(text: str, **_: object) -> str:
        return hashlib.new(algo, text.encode("utf-8")).hexdigest()

    return run


def _crc32(text: str, **_: object) -> str:
    return f"{zlib.crc32(text.encode('utf-8')) & 0xFFFFFFFF:08x}"


def _no_decode(name: str) -> Callable[..., str]:
    def run(text: str, **_: object) -> str:
        raise ValueError(f"{name} 是单向哈希，无法解码")

    return run


# ============================================================ 其余经典密码


BACON_BITS = {ch: format(i, "05b") for i, ch in enumerate(UPPER)}


def _bacon_encode(text: str, alphabet: str = "ab", **_: object) -> str:
    """培根密码：每字母 5 位，用两组符号表示。"""
    bits = "".join(BACON_BITS[ch] for ch in text.upper() if ch in BACON_BITS)
    if alphabet == "AB":
        return bits.replace("0", "A").replace("1", "B")
    return bits.replace("0", "a").replace("1", "b")


def _bacon_decode(text: str, alphabet: str = "ab", **_: object) -> str:
    bits = "".join(c for c in text if c in "aAbB").lower()
    bits = bits.replace("a", "0").replace("b", "1")
    usable = len(bits) - len(bits) % 5
    return "".join(UPPER[int(bits[i : i + 5], 2)] for i in range(0, usable, 5))


#: 与 26 互质的系数，只有这些取值能让仿射密码可逆
AFFINE_A = tuple(a for a in range(1, 26) if math.gcd(a, 26) == 1)


def _affine_table(a: str, b: str, decrypt: bool) -> dict[str, str]:
    ka = _as_int(a, "系数 a")
    kb = _as_int(b, "系数 b")
    if ka not in AFFINE_A:
        raise ValueError(f"系数 a 必须与 26 互质，可取：{AFFINE_A}")
    if decrypt:
        inv = pow(ka, -1, 26)  # 模逆元
        return {UPPER[i]: UPPER[(inv * (i - kb)) % 26] for i in range(26)}
    return {UPPER[i]: UPPER[(ka * i + kb) % 26] for i in range(26)}


def _affine_encode(text: str, a: str = "5", b: str = "8", **_: object) -> str:
    return _map_letters(text, _affine_table(a, b, False))


def _affine_decode(text: str, a: str = "5", b: str = "8", **_: object) -> str:
    return _map_letters(text, _affine_table(a, b, True))


def _columnar_order(key: str) -> list[int]:
    """按字母顺序给出列的读取次序，同字母时保持原序。"""
    return sorted(range(len(key)), key=lambda i: (key[i], i))


def _columnar_encode(text: str, key: str = "", **_: object) -> str:
    """列置换：按行写入矩阵，按密钥指定的列序读出。"""
    if not key:
        raise ValueError("列置换需要一个密钥单词")
    n = len(key)
    rows = [text[i : i + n] for i in range(0, len(text), n)]
    if rows and len(rows[-1]) < n:
        rows[-1] += " " * (n - len(rows[-1]))  # 末行补空格对齐
    return "".join("".join(r[c] for r in rows) for c in _columnar_order(key))


def _columnar_decode(text: str, key: str = "", **_: object) -> str:
    if not key:
        raise ValueError("列置换需要一个密钥单词")
    n = len(key)
    if len(text) % n:
        raise ValueError(f"密文长度 {len(text)} 不是密钥长度 {n} 的倍数")
    rows_n = len(text) // n
    cols: dict[int, list[str]] = {}
    idx = 0
    for c in _columnar_order(key):
        cols[c] = list(text[idx : idx + rows_n])
        idx += rows_n
    # 补位空格落在末尾，去掉后即为原文
    return "".join(cols[c][r] for r in range(rows_n) for c in range(n)).rstrip()


XOR_KEY_FORMATS = ("文本", "十六进制")


def _xor_key(key: str, key_format: str) -> bytes:
    if not key:
        raise ValueError("异或需要密钥")
    if key_format == "十六进制":
        raw = re.sub(r"[\s:_-]", "", key)
        bad = _illegal_chars(raw, r"[^0-9A-Fa-f]")
        if bad:
            raise ValueError(f"密钥含非十六进制字符：{bad}")
        if len(raw) % 2:
            raise ValueError("密钥的十六进制长度必须是偶数")
        kb = bytes.fromhex(raw)
    else:
        kb = key.encode("utf-8")
    if not kb:
        raise ValueError("密钥不能为空")
    return kb


def _xor_apply(data: bytes, kb: bytes) -> bytes:
    return bytes(b ^ kb[i % len(kb)] for i, b in enumerate(data))


def _xor_encode(text: str, key: str = "", key_format: str = "文本",
                out_encoding: str = "hex", **_: object) -> str:
    """异或（一次一密）：密钥循环使用。密钥够长且随机时是唯一可证明安全的方案。"""
    kb = _xor_key(key, key_format)
    return _encode_bytes(_xor_apply(text.encode("utf-8"), kb), out_encoding)


def _xor_decode(text: str, key: str = "", key_format: str = "文本",
                out_encoding: str = "hex", **_: object) -> str:
    kb = _xor_key(key, key_format)
    return _as_utf8(_xor_apply(_decode_bytes(text, out_encoding), kb), "异或")


B85_VARIANTS = ("b85（RFC 1924）", "a85（Adobe）")


def _b85_encode(text: str, variant: str = B85_VARIANTS[0], **_: object) -> str:
    data = text.encode("utf-8")
    if variant.startswith("a85"):
        return base64.a85encode(data).decode("ascii")
    return base64.b85encode(data).decode("ascii")


def _b85_decode(text: str, variant: str = B85_VARIANTS[0], **_: object) -> str:
    raw = text.strip()
    try:
        if variant.startswith("a85"):
            raw = raw.removeprefix("<~").removesuffix("~>")
            data = base64.a85decode(raw.encode("ascii"))
        else:
            data = base64.b85decode(re.sub(r"\s+", "", raw))
    except (ValueError, UnicodeEncodeError) as e:
        raise ValueError(f"不是合法的 Base85：{e}") from None
    return _as_utf8(data, "Base85")


def _qp_encode(text: str, **_: object) -> str:
    """Quoted-Printable：邮件里表示任意字节的经典方案，每行 76 字符。"""
    return quopri.encodestring(text.encode("utf-8")).decode("ascii")


def _qp_decode(text: str, **_: object) -> str:
    data = quopri.decodestring(text.encode("ascii", "replace"))
    return _as_utf8(data, "Quoted-Printable")


# ============================================================ 注册表

SEP = Param("sep", "分隔符", " ", "text", "元素之间的分隔符")


# --- 替换密码
_register(Codec("caesar", "凯撒密码", "替换密码",
                lambda t, shift="3", **_: _caesar_shift(t, _as_int(shift, "位移")),
                lambda t, shift="3", **_: _caesar_shift(t, -_as_int(shift, "位移")),
                (Param("shift", "位移", "3", "int", "1-25，如 3"),),
                "字母表整体位移，最经典的入门密码"))
_register(Codec("rot13", "ROT13", "替换密码", _rot13, _rot13,
                (), "凯撒位移 13，加密即解密"))
_register(Codec("rot47", "ROT47", "替换密码", _rot47, _rot47,
                (), "对 33-126 的可打印 ASCII 位移 47，能处理数字与符号"))
_register(Codec("atbash", "Atbash", "替换密码", _atbash, _atbash,
                (), "字母表镜像替换：A↔Z、B↔Y"))
_register(Codec("a1z26", "A1Z26", "替换密码",
                _a1z26_encode, _a1z26_decode,
                (SEP,), "字母转序号 A=1…Z=26（丢失大小写与空格）"))
_register(Codec("bacon", "培根密码", "替换密码",
                _bacon_encode, _bacon_decode,
                (Param("alphabet", "符号集", "ab", "choice", "用哪两组符号表示 0/1",
                       ("ab", "AB")),),
                "每字母 5 位，可把密文藏进大小写、字体等任意二元特征里"))

# --- 需密钥
_register(Codec("vigenere", "维吉尼亚密码", "需密钥",
                lambda t, key="", **_: _vigenere(t, key, False),
                lambda t, key="", **_: _vigenere(t, key, True),
                (Param("key", "密钥", "", "text", "至少一个字母"),),
                "多组凯撒叠加，需要密钥"))
_register(Codec("rail_fence", "栅栏密码", "需密钥",
                _rail_fence_encode, _rail_fence_decode,
                (Param("rails", "栏数", "2", "int", "建议 2-10"),),
                "按之字形分栏重排字符"))
_register(Codec("playfair", "Playfair", "需密钥",
                _playfair_encode, _playfair_decode,
                (Param("key", "密钥", "", "text", "用于生成 5×5 方阵"),),
                "双字母组替换，I/J 合并，空格与标点会被丢弃"))
_register(Codec("nihilist", "尼希利斯特密码", "需密钥",
                _nihilist_encode, _nihilist_decode,
                (Param("key", "方阵密钥", "", "text", "生成 Polybius 方阵"),
                 Param("numeric_key", "数字密钥", "", "text", "至少一个字母")),
                "方阵编号后叠加数字密钥，结果为数字串"))
_register(Codec("book_cipher", "书本密码", "需密钥",
                _book_encode, _book_decode,
                (Param("book", "书本内容", "", "text", "整段文本，用空白分词"),
                 SEP),
                "以「词序号:字符序号」定位，需双方持有同一本书"))
_register(Codec("affine", "仿射密码", "需密钥",
                _affine_encode, _affine_decode,
                (Param("a", "系数 a", "5", "text", "必须与 26 互质：1 3 5 7 9 11 15 17 19 21 23 25"),
                 Param("b", "系数 b", "8", "text", "0-25 任意整数")),
                "对字母做 y = a·x + b 的线性变换，凯撒是 a=1 的特例"))
_register(Codec("columnar", "列置换", "需密钥",
                _columnar_encode, _columnar_decode,
                (Param("key", "密钥单词", "", "text", "列按它的字母顺序读出"),),
                "只打乱位置不替换字符，末行补空格，解码时会去掉"))
_register(Codec("xor", "异或 / 一次一密", "需密钥",
                _xor_encode, _xor_decode,
                (Param("key", "密钥", "", "text", "文本或十六进制"),
                 Param("key_format", "密钥格式", "文本", "choice", "", XOR_KEY_FORMATS),
                 Param("out_encoding", "密文格式", "hex", "choice", "", OUT_ENCODINGS)),
                "密钥循环使用。密钥真正随机且不短于明文时，理论上不可破解"))

# --- 编码
_register(Codec("base64", "Base64", "编码", _b64_encode, _b64_decode,
                (), "最常见的编码，常用于隐藏可读文本"))
_register(Codec("base32", "Base32", "编码", _b32_encode, _b32_decode, (), "字母数字大写"))
_register(Codec("base16", "Base16 / Hex", "编码", _b16_encode, _b16_decode, (), "即十六进制"))
_register(Codec("morse", "摩斯电码", "编码", _morse_encode, _morse_decode,
                (Param("word_sep", "词分隔符", "/", "text", "单词/字符组之间的符号"),
                 Param("mode", "字符集", MORSE_MODE_ASCII, "choice",
                       "标准模式只支持 ASCII；中文请选 Unicode",
                       MORSE_MODES)),
                "点划编码。Unicode 模式按码点十六进制编码，中文可用且完全可逆"))
_register(Codec("binary", "二进制", "编码", _binary_encode, _binary_decode, (SEP,),
                "每字节 8 位"))
_register(Codec("hex", "十六进制", "编码", _hex_encode, _hex_decode, (SEP,),
                "每字节两位十六进制"))
_register(Codec("base85", "Base85", "编码", _b85_encode, _b85_decode,
                (Param("variant", "变体", B85_VARIANTS[0], "choice",
                       "RFC 1924 与 Adobe 两套字符集不同", B85_VARIANTS),),
                "比 Base64 更紧凑，Python 源码与 PDF 里常见"))
_register(Codec("quoted_printable", "Quoted-Printable", "编码",
                _qp_encode, _qp_decode,
                (), "邮件中表示任意字节的经典方案，每行 76 字符"))
_register(Codec("url", "URL 编码", "编码", _url_encode, _url_decode, (), "百分号转义"))
_register(Codec("html_entity", "HTML 实体", "编码", _html_encode, _html_decode,
                (), "&amp; &lt; &gt; 等"))
_register(Codec("brainfuck", "Brainfuck", "编码", _bf_encode, _bf_decode,
                (), "极简语言，常被当作编码使用"))
_register(Codec("ook", "Ook!", "编码", _ook_encode, _ook_decode,
                (), "Brainfuck 的猩猩语变体"))

# --- 哈希
for _algo, _label in (("md5", "MD5"), ("sha1", "SHA-1"), ("sha256", "SHA-256"),
                      ("sha512", "SHA-512")):
    _register(Codec(_algo, _label, "哈希",
                    _hash_factory(_algo), _no_decode(_label), (), "单向哈希"))
_register(Codec("crc32", "CRC32", "哈希", _crc32, _no_decode("CRC32"), (), "校验和"))


# ============================================================ 对外接口


def _coerce_params(
    defs: tuple[Param, ...], params: dict[str, object]
) -> dict[str, object]:
    """把 UI 传来的字符串参数转成算法需要的类型。"""
    out: dict[str, object] = {}
    for p in defs:
        raw = params.get(p.name, p.default)
        if p.kind == "int":
            if raw is None or str(raw).strip() == "":
                raw = p.default
            out[p.name] = _as_int(raw, p.label)
        else:
            out[p.name] = p.default if raw is None else raw
    return out


def _coerce(codec: Codec, params: dict[str, object]) -> dict[str, object]:
    return _coerce_params(codec.params, params)


def run_action(method: str, action: str, **params: object) -> str:
    """执行算法附带的操作（例如「生成密钥对」），返回要展示的说明文字。"""
    codec = REGISTRY.get(method)
    if codec is None:
        raise ValueError(f"未知算法：{method!r}")
    for a in codec.actions:
        if a.name == action:
            return a.fn(**_coerce_params(a.params, params))
    raise ValueError(f"{codec.label} 没有名为 {action!r} 的操作")


def encode(text: str, method: str, **params: object) -> str:
    """加密 / 编码。"""
    codec = REGISTRY.get(method)
    if codec is None:
        raise ValueError(f"未知算法：{method!r}")
    if codec.encode is None:
        raise ValueError(f"{codec.label} 不支持编码")
    return codec.encode(text, **_coerce(codec, params))


def decode(text: str, method: str, **params: object) -> str:
    """解密 / 解码。"""
    codec = REGISTRY.get(method)
    if codec is None:
        raise ValueError(f"未知算法：{method!r}")
    if codec.decode is None:
        raise ValueError(f"{codec.label} 是单向哈希，无法解码")
    return codec.decode(text, **_coerce(codec, params))


def detect(text: str) -> list[str]:
    """启发式猜测输入可能是什么编码，按可能性从高到低返回算法标识。"""
    s = text.strip()
    if not s:
        return []
    compact = re.sub(r"\s+", "", s)
    hits: list[str] = []

    if compact and set(compact) <= {"0", "1"} and len(compact) >= 8 and len(compact) % 8 == 0:
        hits.append("binary")
    if re.fullmatch(r"[.\-/\s]+", s) and re.search(r"[.\-]", s):
        hits.append("morse")
    if re.fullmatch(r"[+\-<>.,\[\]\s]+", s) and len(compact) >= 2:
        hits.append("brainfuck")
    if re.fullmatch(r"(Ook[.!?]\s*)+", s):
        hits.append("ook")
    if re.fullmatch(r"[A-Z2-7=\s]+", s) and "=" in s and len(compact) % 8 == 0:
        hits.append("base32")
    if (
        re.fullmatch(r"[A-Za-z0-9+/=\s]+", s)
        and len(compact) % 4 == 0
        and len(compact) >= 8
        and re.search(r"[+/=]", s)
    ):
        hits.append("base64")
    if re.fullmatch(r"[0-9A-Fa-f\s]+", s) and len(compact) >= 4 and len(compact) % 2 == 0:
        hits.append("hex")
    if re.fullmatch(r"[%0-9A-Fa-f]+", s) and "%" in s:
        hits.append("url")
    if re.fullmatch(r"[&\w#;]+", s) and "&" in s and ";" in s:
        hits.append("html_entity")
    if re.fullmatch(r"[\d\s\-_.]+", s) and re.search(r"\d", s):
        hits.append("a1z26")
    return hits


def brute_force(text: str, method: str) -> list[tuple[str, str]]:
    """无密钥暴力枚举。返回 [(说明, 结果), ...]。

    目前支持：凯撒（全 26 位移）、栅栏（全栏数）、ROT13 / ROT47 / Atbash（单一结果）、
    培根（两种符号集）、仿射（全 12 个合法系数 a）。
    """
    if method == "caesar":
        return [(f"位移 {n:>2}", _caesar_shift(text, -n)) for n in range(1, 26)]
    if method == "rail_fence":
        limit = min(len(text), 20)
        return [(f"栏数 {n:>2}", _rail_fence_decode(text, str(n)))
                for n in range(2, limit + 1)]
    if method in ("rot13", "rot47", "atbash"):
        return [(REGISTRY[method].label, decode(text, method))]
    if method == "bacon":
        return [(f"符号集 {a}", _bacon_decode(text, a)) for a in ("ab", "AB")]
    if method == "affine":
        out = []
        for a in AFFINE_A:
            for b in range(26):
                try:
                    out.append((f"a={a:>2} b={b:>2}", _affine_decode(text, str(a), str(b))))
                except ValueError:
                    continue
        return out
    raise ValueError(f"{method!r} 不支持暴力枚举")


# ============================================================ 现代算法注册
# 放在文件末尾：crypto_modern 只依赖 crypto_types，不依赖本模块，
# 因此在这里 import 不会造成循环依赖，同时保证注册表被填充完整。
from src.core import crypto_modern  # noqa: E402,F401

#: 兼容旧接口：所有算法标识。必须在 crypto_modern 导入之后再取，
#: 否则会漏掉现代算法。
CAPABILITIES: tuple[str, ...] = tuple(REGISTRY)

