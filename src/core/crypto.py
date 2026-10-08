"""密码与编码算法实现。

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
import re
import string
import urllib.parse
import zlib
from dataclasses import dataclass
from typing import Callable

# ============================================================ 数据结构


@dataclass(frozen=True)
class Param:
    """算法的一个参数。UI 据此生成输入控件。"""

    name: str
    label: str
    default: str = ""
    kind: str = "text"  # text | int
    hint: str = ""


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

    @property
    def reversible(self) -> bool:
        """是否可逆（有解码方向）。哈希类不可逆。"""
        return self.decode is not None


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


def _as_int(value: object, label: str) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        raise ValueError(f"参数「{label}」需要整数，收到 {value!r}") from None


def _illegal_chars(raw: str, pattern: str) -> str:
    """找出不合法字符，用于给出比标准库更清楚的中文报错。

    标准库在遇到非 ASCII 输入时抛的是英文 `ValueError`
    （"string argument should contain only ASCII characters"），
    直接透给用户很难懂，所以先自己检查一遍字符集。
    """
    bad = sorted(set(re.findall(pattern, raw)))
    return " ".join(bad[:8])


def _as_utf8(data: bytes, label: str) -> str:
    """把解出的字节按 UTF-8 转文本，失败时给出可读的提示。"""
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as e:
        raise ValueError(f"{label} 解出的字节不是 UTF-8 文本：{e}") from None


# ============================================================ 替换密码


def _rot13(text: str, **_: object) -> str:
    return _caesar_shift(text, 13)


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


def _morse_encode(text: str, word_sep: str = "/", **_: object) -> str:
    out = []
    for word in text.upper().split():
        codes = [MORSE[ch] for ch in word if ch in MORSE]
        if codes:
            out.append(" ".join(codes))
    return f" {word_sep} ".join(out)


def _morse_decode(text: str, word_sep: str = "/", **_: object) -> str:
    norm = text.replace("·", ".").replace("−", "-").replace("–", "-")
    words = re.split(r"(?:\s*/\s*|\s{3,})", norm.strip())
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


# ============================================================ 注册表

SEP = Param("sep", "分隔符", " ", "text", "元素之间的分隔符")

REGISTRY: dict[str, Codec] = {}


def _register(codec: Codec) -> None:
    REGISTRY[codec.name] = codec


# --- 替换密码
_register(Codec("caesar", "凯撒密码", "替换密码",
                lambda t, shift="3", **_: _caesar_shift(t, _as_int(shift, "位移")),
                lambda t, shift="3", **_: _caesar_shift(t, -_as_int(shift, "位移")),
                (Param("shift", "位移", "3", "int", "1-25，如 3"),),
                "字母表整体位移，最经典的入门密码"))
_register(Codec("rot13", "ROT13", "替换密码", _rot13, _rot13,
                (), "凯撒位移 13，加密即解密"))
_register(Codec("atbash", "Atbash", "替换密码", _atbash, _atbash,
                (), "字母表镜像替换：A↔Z、B↔Y"))
_register(Codec("a1z26", "A1Z26", "替换密码",
                _a1z26_encode, _a1z26_decode,
                (SEP,), "字母转序号 A=1…Z=26（丢失大小写与空格）"))

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

# --- 编码
_register(Codec("base64", "Base64", "编码", _b64_encode, _b64_decode,
                (), "最常见的编码，常用于隐藏可读文本"))
_register(Codec("base32", "Base32", "编码", _b32_encode, _b32_decode, (), "字母数字大写"))
_register(Codec("base16", "Base16 / Hex", "编码", _b16_encode, _b16_decode, (), "即十六进制"))
_register(Codec("morse", "摩斯电码", "编码", _morse_encode, _morse_decode,
                (Param("word_sep", "词分隔符", "/", "text", "单词之间的符号"),),
                "点划编码，字母间用空格"))
_register(Codec("binary", "二进制", "编码", _binary_encode, _binary_decode, (SEP,),
                "每字节 8 位"))
_register(Codec("hex", "十六进制", "编码", _hex_encode, _hex_decode, (SEP,),
                "每字节两位十六进制"))
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

#: 兼容旧接口：所有算法标识
CAPABILITIES: tuple[str, ...] = tuple(REGISTRY)

#: 分组顺序（UI 用）
GROUPS: tuple[str, ...] = ("替换密码", "需密钥", "编码", "哈希")


# ============================================================ 对外接口


def available() -> list[Codec]:
    """按分组顺序返回全部算法。"""
    return [c for g in GROUPS for c in REGISTRY.values() if c.group == g]


def _coerce(codec: Codec, params: dict[str, object]) -> dict[str, object]:
    """把 UI 传来的字符串参数转成算法需要的类型。"""
    out: dict[str, object] = {}
    for p in codec.params:
        raw = params.get(p.name, p.default)
        if p.kind == "int":
            if raw is None or str(raw).strip() == "":
                raw = p.default
            out[p.name] = _as_int(raw, p.label)
        else:
            out[p.name] = p.default if raw is None else raw
    return out


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

    目前支持：凯撒（全 26 位移）、栅栏（全栏数）、ROT13 / Atbash（单一结果）。
    """
    if method == "caesar":
        return [(f"位移 {n:>2}", _caesar_shift(text, -n)) for n in range(1, 26)]
    if method == "rail_fence":
        limit = min(len(text), 20)
        return [(f"栏数 {n:>2}", _rail_fence_decode(text, str(n)))
                for n in range(2, limit + 1)]
    if method in ("rot13", "atbash"):
        return [(REGISTRY[method].label, decode(text, method))]
    raise ValueError(f"{method!r} 不支持暴力枚举")
