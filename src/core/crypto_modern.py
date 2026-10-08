"""现代密码算法：AES / ChaCha20 / RSA / ECC。

依赖 `cryptography`（pyca）。**不自己实现任何密码原语**——手搓 AES 或椭圆曲线
是自找麻烦，正确性和侧信道都保证不了。

依赖缺失时不会崩：算法照常出现在列表里，调用时才提示去装库，便于用户发现问题。

设计说明
--------
现代算法产出的是**二进制**密文，放进文本框必须先转成文本。因此每个算法都有
一个「密文格式」参数（base64 / hex / base32），默认 base64。

对称算法的密钥来源分两类：
    - 口令派生（PBKDF2）—— 适合人记，`aes_gcm`
    - 原始密钥（十六进制）—— 适合谜题给定密钥，`aes_cbc` / `aes_ecb` / `chacha20*`

非对称算法用 PEM 密钥文件，密钥生成是「动作」而不是编码方向。
"""

from __future__ import annotations

import os
from pathlib import Path

from src.core.crypto_types import (
    OUT_ENCODINGS,
    Action,
    Codec,
    Param,
    as_int,
    decode_bytes,
    encode_bytes,
    hex_to_bytes,
    register,
)

# ============================================================ 依赖探测

try:
    from cryptography.exceptions import InvalidTag
    from cryptography.hazmat.primitives import hashes, padding as sym_padding, serialization
    from cryptography.hazmat.primitives.asymmetric import ec, padding as asym_padding, rsa
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM, ChaCha20Poly1305
    from cryptography.hazmat.primitives.kdf.hkdf import HKDF
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

    HAVE_CRYPTOGRAPHY = True
except ImportError:  # pragma: no cover —— 只在没装库时走到
    HAVE_CRYPTOGRAPHY = False


def _ensure() -> None:
    if not HAVE_CRYPTOGRAPHY:
        raise ValueError(
            "现代密码算法需要 cryptography 库，请先安装：pip install cryptography"
        )


# ============================================================ 通用

#: AES-GCM 密文的头部魔数，用于识别格式并给出更好的报错
_GCM_MAGIC = b"AXG1"
_GCM_HEADER = len(_GCM_MAGIC) + 4 + 16 + 12  # magic + 迭代次数 + salt + nonce

OUT_PARAM = Param("out_encoding", "密文格式", "base64", "choice",
                  "密文的文本表示方式", OUT_ENCODINGS)


def _utf8(data: bytes, what: str = "明文") -> str:
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as e:
        raise ValueError(f"解出的{what}不是 UTF-8 文本：{e}") from None


# ------------------------------------------------------------ 对称：口令派生

def _derive(password: str, salt: bytes, iterations: int) -> bytes:
    if not password:
        raise ValueError("请填写口令")
    return PBKDF2HMAC(
        algorithm=hashes.SHA256(), length=32, salt=salt, iterations=iterations
    ).derive(password.encode("utf-8"))


def _aes_gcm_encode(text: str, password: str = "", iterations: str = "200000",
                    out_encoding: str = "base64", **_: object) -> str:
    """AES-256-GCM，密钥由口令经 PBKDF2 派生。头部自带迭代次数，解密不必重填。"""
    _ensure()
    rounds = as_int(iterations, "迭代次数")
    if rounds < 1000:
        raise ValueError("迭代次数至少 1000")

    salt = os.urandom(16)
    nonce = os.urandom(12)
    key = _derive(password, salt, rounds)
    body = AESGCM(key).encrypt(nonce, text.encode("utf-8"), None)
    header = _GCM_MAGIC + rounds.to_bytes(4, "big") + salt + nonce
    return encode_bytes(header + body, out_encoding)


def _aes_gcm_decode(text: str, password: str = "", iterations: str = "200000",
                    out_encoding: str = "base64", **_: object) -> str:
    _ensure()
    raw = decode_bytes(text, out_encoding)
    if len(raw) < _GCM_HEADER + 16:
        raise ValueError("密文太短，不是本工具生成的 AES-GCM 密文")
    if raw[:4] != _GCM_MAGIC:
        raise ValueError("密文头部不对，不是本工具生成的 AES-GCM 密文")

    rounds = int.from_bytes(raw[4:8], "big")
    salt = raw[8:24]
    nonce = raw[24:36]
    body = raw[36:]
    key = _derive(password, salt, rounds)
    try:
        return _utf8(AESGCM(key).decrypt(nonce, body, None))
    except InvalidTag:
        raise ValueError("解密失败：口令不对，或密文被改动过") from None


# ------------------------------------------------------------ 对称：原始密钥

def _aes_cbc_encode(text: str, key: str = "", iv: str = "",
                    out_encoding: str = "base64", **_: object) -> str:
    _ensure()
    kb = hex_to_bytes(key, "密钥", (16, 24, 32))
    ivb = hex_to_bytes(iv, "初始向量 IV", (16,))
    padder = sym_padding.PKCS7(128).padder()
    data = padder.update(text.encode("utf-8")) + padder.finalize()
    enc = Cipher(algorithms.AES(kb), modes.CBC(ivb)).encryptor()
    return encode_bytes(enc.update(data) + enc.finalize(), out_encoding)


def _aes_cbc_decode(text: str, key: str = "", iv: str = "",
                    out_encoding: str = "base64", **_: object) -> str:
    _ensure()
    kb = hex_to_bytes(key, "密钥", (16, 24, 32))
    ivb = hex_to_bytes(iv, "初始向量 IV", (16,))
    raw = decode_bytes(text, out_encoding)
    if len(raw) % 16:
        raise ValueError(f"密文长度 {len(raw)} 不是 16 的倍数，不像 AES-CBC 密文")
    dec = Cipher(algorithms.AES(kb), modes.CBC(ivb)).decryptor()
    data = dec.update(raw) + dec.finalize()
    unpadder = sym_padding.PKCS7(128).unpadder()
    try:
        data = unpadder.update(data) + unpadder.finalize()
    except ValueError:
        raise ValueError("去填充失败：密钥或 IV 不对") from None
    return _utf8(data)


def _aes_ecb_encode(text: str, key: str = "", out_encoding: str = "base64",
                    **_: object) -> str:
    _ensure()
    kb = hex_to_bytes(key, "密钥", (16, 24, 32))
    padder = sym_padding.PKCS7(128).padder()
    data = padder.update(text.encode("utf-8")) + padder.finalize()
    enc = Cipher(algorithms.AES(kb), modes.ECB()).encryptor()
    return encode_bytes(enc.update(data) + enc.finalize(), out_encoding)


def _aes_ecb_decode(text: str, key: str = "", out_encoding: str = "base64",
                    **_: object) -> str:
    _ensure()
    kb = hex_to_bytes(key, "密钥", (16, 24, 32))
    raw = decode_bytes(text, out_encoding)
    if len(raw) % 16:
        raise ValueError(f"密文长度 {len(raw)} 不是 16 的倍数，不像 AES-ECB 密文")
    dec = Cipher(algorithms.AES(kb), modes.ECB()).decryptor()
    data = dec.update(raw) + dec.finalize()
    padder = sym_padding.PKCS7(128).unpadder()
    try:
        data = padder.update(data) + padder.finalize()
    except ValueError:
        raise ValueError("去填充失败：密钥不对") from None
    return _utf8(data)


def _chacha20_encode(text: str, key: str = "", nonce: str = "",
                     out_encoding: str = "base64", **_: object) -> str:
    """ChaCha20 流密码。

    注意：cryptography 库实现的是 Bernstein 原始变体，**nonce 必须是 16 字节**。
    RFC 8439 的 12 字节 nonce 请用 ChaCha20-Poly1305。
    """
    _ensure()
    kb = hex_to_bytes(key, "密钥", (32,))
    nb = hex_to_bytes(nonce, "Nonce", (16,))
    enc = Cipher(algorithms.ChaCha20(kb, nb), mode=None).encryptor()
    return encode_bytes(enc.update(text.encode("utf-8")), out_encoding)


def _chacha20_decode(text: str, key: str = "", nonce: str = "",
                     out_encoding: str = "base64", **_: object) -> str:
    _ensure()
    kb = hex_to_bytes(key, "密钥", (32,))
    nb = hex_to_bytes(nonce, "Nonce", (16,))
    raw = decode_bytes(text, out_encoding)
    dec = Cipher(algorithms.ChaCha20(kb, nb), mode=None).decryptor()
    return _utf8(dec.update(raw))


def _cc20p_encode(text: str, key: str = "", nonce: str = "",
                  out_encoding: str = "base64", **_: object) -> str:
    """ChaCha20-Poly1305（RFC 8439），12 字节 nonce，带认证。"""
    _ensure()
    kb = hex_to_bytes(key, "密钥", (32,))
    nb = hex_to_bytes(nonce, "Nonce", (12,))
    return encode_bytes(
        ChaCha20Poly1305(kb).encrypt(nb, text.encode("utf-8"), None), out_encoding
    )


def _cc20p_decode(text: str, key: str = "", nonce: str = "",
                  out_encoding: str = "base64", **_: object) -> str:
    _ensure()
    kb = hex_to_bytes(key, "密钥", (32,))
    nb = hex_to_bytes(nonce, "Nonce", (12,))
    raw = decode_bytes(text, out_encoding)
    try:
        return _utf8(ChaCha20Poly1305(kb).decrypt(nb, raw, None))
    except InvalidTag:
        raise ValueError("解密失败：密钥或 Nonce 不对，或密文被改动过") from None


# ------------------------------------------------------------ 非对称：密钥文件

def _load_public_key(path: str):
    """加载 PEM 公钥。若给的是私钥文件，自动取其公钥部分。"""
    p = Path(path or "")
    if not p.is_file():
        raise ValueError(f"公钥文件不存在：{path}")
    data = p.read_bytes()
    try:
        return serialization.load_pem_public_key(data)
    except Exception:  # noqa: BLE001 —— 退一步试试是不是私钥文件
        try:
            return serialization.load_pem_private_key(data, password=None).public_key()
        except Exception as e:
            raise ValueError(f"无法解析公钥文件（需 PEM 格式）：{e}") from None


def _load_private_key(path: str, password: str = ""):
    p = Path(path or "")
    if not p.is_file():
        raise ValueError(f"私钥文件不存在：{path}")
    pw = password.encode("utf-8") if password else None
    try:
        return serialization.load_pem_private_key(p.read_bytes(), password=pw)
    except TypeError:
        raise ValueError("私钥已加密，请填写口令") from None
    except Exception as e:
        raise ValueError(f"无法解析私钥文件（需 PEM 格式）：{e}") from None


# ------------------------------------------------------------ RSA

_RSA_PADDINGS = ("OAEP-SHA256", "PKCS1v15")


def _rsa_padding(mode: str):
    if mode == "PKCS1v15":
        return asym_padding.PKCS1v15()
    return asym_padding.OAEP(
        mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
        algorithm=hashes.SHA256(),
        label=None,
    )


def _rsa_capacity(key_size_bits: int, mode: str) -> int:
    """该填充方式下单次能加密的最大字节数。"""
    if mode == "PKCS1v15":
        return key_size_bits // 8 - 11
    return key_size_bits // 8 - 2 * 32 - 2  # OAEP-SHA256


def _rsa_encode(text: str, pubkey: str = "", padding_mode: str = "OAEP-SHA256",
                out_encoding: str = "base64", **_: object) -> str:
    _ensure()
    key = _load_public_key(pubkey)
    if not isinstance(key, rsa.RSAPublicKey):
        raise ValueError("这个公钥不是 RSA 公钥")
    data = text.encode("utf-8")
    limit = _rsa_capacity(key.key_size, padding_mode)
    if len(data) > limit:
        raise ValueError(
            f"RSA 单次只能加密 {limit} 字节，当前 {len(data)} 字节。"
            "长文本请先用 AES 加密，再用 RSA 加密那把 AES 密钥"
        )
    return encode_bytes(key.encrypt(data, _rsa_padding(padding_mode)), out_encoding)


def _rsa_decode(text: str, privkey: str = "", password: str = "",
                padding_mode: str = "OAEP-SHA256", out_encoding: str = "base64",
                **_: object) -> str:
    _ensure()
    key = _load_private_key(privkey, password)
    if not isinstance(key, rsa.RSAPrivateKey):
        raise ValueError("这个私钥不是 RSA 私钥")
    raw = decode_bytes(text, out_encoding)
    try:
        return _utf8(key.decrypt(raw, _rsa_padding(padding_mode)))
    except ValueError:
        raise ValueError("解密失败：私钥不对、填充方式不对，或密文被改动过") from None


def _rsa_keygen(outdir: str = "", bits: str = "2048", password: str = "",
                **_: object) -> str:
    """生成 RSA 密钥对，写 private.pem / public.pem。"""
    _ensure()
    if not outdir:
        raise ValueError("请选择输出目录")
    size = as_int(bits, "密钥长度")
    if size not in (2048, 3072, 4096):
        raise ValueError("密钥长度只支持 2048 / 3072 / 4096")

    key = rsa.generate_private_key(public_exponent=65537, key_size=size)
    enc = (
        serialization.BestAvailableEncryption(password.encode("utf-8"))
        if password
        else serialization.NoEncryption()
    )
    priv = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        enc,
    )
    pub = key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return _write_keypair(outdir, priv, pub, f"RSA-{size}")


def _write_keypair(outdir: str, priv: bytes, pub: bytes, label: str) -> str:
    root = Path(outdir)
    try:
        root.mkdir(parents=True, exist_ok=True)
        (root / "private.pem").write_bytes(priv)
        (root / "public.pem").write_bytes(pub)
    except OSError as e:
        raise ValueError(f"写文件失败：{e}") from None
    return f"已生成 {label} 密钥对：{root / 'private.pem'} 与 {root / 'public.pem'}"


# ------------------------------------------------------------ ECC / ECIES

#: 曲线名 -> cryptography 里的类名。
#: 这里存**名字字符串**而不是类对象：没装 cryptography 时 `ec` 根本不存在，
#: 模块级直接引用会让 import 失败，进而拖垮整个应用。
CURVES: dict[str, str] = {
    "secp256r1 (P-256)": "SECP256R1",
    "secp384r1 (P-384)": "SECP384R1",
    "secp521r1 (P-521)": "SECP521R1",
}

#: ECIES 中由共享密钥派生 AES 密钥时用的 info，防止跨用途复用
_ECIES_INFO = b"arg.xc/ecies/v1"


def _ecies_key(shared: bytes) -> bytes:
    return HKDF(
        algorithm=hashes.SHA256(), length=32, salt=None, info=_ECIES_INFO
    ).derive(shared)


def _ecc_encode(text: str, pubkey: str = "", out_encoding: str = "base64",
                **_: object) -> str:
    """ECIES：临时 EC 密钥 + ECDH 共享密钥 + HKDF + AES-GCM。

    ECC 本身不定义加密方案（ECIES 是组合出来的），这里采用业界通行的组合。
    """
    _ensure()
    key = _load_public_key(pubkey)
    if not isinstance(key, ec.EllipticCurvePublicKey):
        raise ValueError("这个公钥不是 EC 公钥")

    eph = ec.generate_private_key(key.curve)
    nonce = os.urandom(12)
    body = AESGCM(_ecies_key(eph.exchange(ec.ECDH(), key))).encrypt(
        nonce, text.encode("utf-8"), None
    )
    point = eph.public_key().public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.CompressedPoint
    )
    header = len(point).to_bytes(2, "big") + point + nonce
    return encode_bytes(header + body, out_encoding)


def _ecc_decode(text: str, privkey: str = "", password: str = "",
                out_encoding: str = "base64", **_: object) -> str:
    _ensure()
    key = _load_private_key(privkey, password)
    if not isinstance(key, ec.EllipticCurvePrivateKey):
        raise ValueError("这个私钥不是 EC 私钥")

    raw = decode_bytes(text, out_encoding)
    if len(raw) < 2 + 12 + 16:
        raise ValueError("密文太短，不是本工具生成的 ECIES 密文")
    n = int.from_bytes(raw[:2], "big")
    if len(raw) < 2 + n + 12:
        raise ValueError("密文长度不对，不是本工具生成的 ECIES 密文")
    try:
        eph_pub = ec.EllipticCurvePublicKey.from_encoded_point(key.curve, raw[2 : 2 + n])
    except ValueError as e:
        raise ValueError(f"临时公钥解析失败：{e}") from None

    nonce = raw[2 + n : 2 + n + 12]
    body = raw[2 + n + 12 :]
    try:
        return _utf8(
            AESGCM(_ecies_key(key.exchange(ec.ECDH(), eph_pub))).decrypt(
                nonce, body, None
            )
        )
    except InvalidTag:
        raise ValueError("解密失败：私钥不对，或密文被改动过") from None


def _ecc_keygen(outdir: str = "", curve: str = "secp256r1 (P-256)",
                password: str = "", **_: object) -> str:
    _ensure()
    if not outdir:
        raise ValueError("请选择输出目录")
    curve_attr = CURVES.get(curve)
    if curve_attr is None:
        raise ValueError(f"不支持的曲线：{curve}")

    key = ec.generate_private_key(getattr(ec, curve_attr)())
    enc = (
        serialization.BestAvailableEncryption(password.encode("utf-8"))
        if password
        else serialization.NoEncryption()
    )
    priv = key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, enc
    )
    pub = key.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    return _write_keypair(outdir, priv, pub, f"ECC {curve}")


# ============================================================ 注册

_PW = Param("password", "口令", "", "password", "用于派生密钥，务必记牢")
_ITER = Param("iterations", "迭代次数", "200000", "int", "越大越安全也越慢")

register(Codec(
    "aes_gcm", "AES-256-GCM", "现代密码",
    _aes_gcm_encode, _aes_gcm_decode,
    (_PW, _ITER, OUT_PARAM),
    "口令派生密钥的认证加密，推荐默认使用。密文自带盐与迭代次数",
))

_AES_KEY = Param("key", "密钥（hex）", "", "text", "16 / 24 / 32 字节，如 32 个字符=16 字节")
register(Codec(
    "aes_cbc", "AES-CBC", "现代密码",
    _aes_cbc_encode, _aes_cbc_decode,
    (_AES_KEY, Param("iv", "初始向量 IV（hex）", "", "text", "16 字节，32 个十六进制字符"),
     OUT_PARAM),
    "密钥与 IV 都是十六进制。IV 必须随机且每次不同，否则会泄露明文规律",
))
register(Codec(
    "aes_ecb", "AES-ECB", "现代密码",
    _aes_ecb_encode, _aes_ecb_decode,
    (_AES_KEY, OUT_PARAM),
    "无 IV 的旧模式，相同明文块会得到相同密文块（ECB 企鹅）。仅用于复现谜题",
))

_CHACHA_KEY = Param("key", "密钥（hex）", "", "text", "32 字节，64 个十六进制字符")
register(Codec(
    "chacha20", "ChaCha20", "现代密码",
    _chacha20_encode, _chacha20_decode,
    (_CHACHA_KEY, Param("nonce", "Nonce（hex）", "", "text", "16 字节，32 个十六进制字符"),
     OUT_PARAM),
    "流密码。注意本实现用 16 字节 nonce；RFC 8439 的 12 字节 nonce 请用 ChaCha20-Poly1305",
))
register(Codec(
    "chacha20_poly1305", "ChaCha20-Poly1305", "现代密码",
    _cc20p_encode, _cc20p_decode,
    (_CHACHA_KEY, Param("nonce", "Nonce（hex）", "", "text", "12 字节，24 个十六进制字符"),
     OUT_PARAM),
    "RFC 8439 认证加密，Google 在 TLS 中主推的方案",
))

_RSA_PUB = Param("pubkey", "公钥文件", "", "keyfile", "PEM 格式，加密时使用")
_RSA_PRIV = Param("privkey", "私钥文件", "", "keyfile", "PEM 格式，解密时使用")
_RSA_PAD = Param("padding_mode", "填充方式", "OAEP-SHA256", "choice",
                 "PKCS1v15 是旧方案，仅为兼容谜题保留", _RSA_PADDINGS)
register(Codec(
    "rsa", "RSA", "现代密码",
    _rsa_encode, _rsa_decode,
    (_RSA_PUB, _RSA_PRIV, Param("password", "私钥口令", "", "password", "私钥未加密则留空"),
     _RSA_PAD, OUT_PARAM),
    "公钥加密、私钥解密。单次可加密的字节数受密钥长度限制，长文本请配合 AES 使用",
    actions=(Action(
        "keygen", "生成 RSA 密钥对", _rsa_keygen,
        (Param("outdir", "输出目录", "", "dir", "写入 private.pem / public.pem"),
         Param("bits", "密钥长度", "2048", "choice", "", ("2048", "3072", "4096")),
         Param("password", "私钥口令", "", "password", "留空则不加密私钥")),
        "生成后请把公钥给玩家、私钥自己留好",
    ),),
))

_ECC_CURVES = tuple(CURVES)
register(Codec(
    "ecc", "ECC / ECIES", "现代密码",
    _ecc_encode, _ecc_decode,
    (_RSA_PUB, _RSA_PRIV, Param("password", "私钥口令", "", "password", "私钥未加密则留空"),
     OUT_PARAM),
    "ECIES：临时密钥 ECDH + HKDF + AES-GCM。ECC 本身只定义密钥与签名，加密方案是组合出来的",
    actions=(Action(
        "keygen", "生成 ECC 密钥对", _ecc_keygen,
        (Param("outdir", "输出目录", "", "dir", "写入 private.pem / public.pem"),
         Param("curve", "曲线", _ECC_CURVES[0], "choice", "", _ECC_CURVES),
         Param("password", "私钥口令", "", "password", "留空则不加密私钥")),
        "曲线越短越快，P-256 已足够日常使用",
    ),),
))
