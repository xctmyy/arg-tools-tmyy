"""core.crypto_modern 的单元测试。

没装 cryptography 时整组跳过，不会让测试变红。
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.core import crypto, crypto_modern  # noqa: E402

KEY16 = "00112233445566778899aabbccddeeff"
KEY32 = "00112233445566778899aabbccddeeff00112233445566778899aabbccddeeff"
IV16 = "0102030405060708090a0b0c0d0e0f10"
NONCE16 = "000102030405060708090a0b0c0d0e0f"
NONCE12 = "000102030405060708090a0b"

needs_lib = unittest.skipUnless(crypto_modern.HAVE_CRYPTOGRAPHY, "需要 cryptography 库")


@needs_lib
class TestSymmetric(unittest.TestCase):
    TEXT = "ARG 谜题：中文与符号 @#$ 都要能往返"

    def _round_trip(self, method: str, **params: object) -> None:
        ct = crypto.encode(self.TEXT, method, **params)
        self.assertEqual(crypto.decode(ct, method, **params), self.TEXT)

    def test_aes_gcm_password(self) -> None:
        self._round_trip("aes_gcm", password="hunter2")

    def test_aes_gcm_is_randomised(self) -> None:
        """每次加密盐与 nonce 都不同，相同明文不能得到相同密文。"""
        a = crypto.encode(self.TEXT, "aes_gcm", password="p")
        b = crypto.encode(self.TEXT, "aes_gcm", password="p")
        self.assertNotEqual(a, b)

    def test_aes_gcm_wrong_password(self) -> None:
        ct = crypto.encode(self.TEXT, "aes_gcm", password="right")
        with self.assertRaises(ValueError) as ctx:
            crypto.decode(ct, "aes_gcm", password="wrong")
        self.assertIn("口令不对", str(ctx.exception))

    def test_aes_gcm_iterations_read_from_header(self) -> None:
        """迭代次数写在密文头部，解码不受参数影响——参数只在加密时生效。"""
        ct = crypto.encode(self.TEXT, "aes_gcm", password="p", iterations="5000")
        self.assertEqual(
            crypto.decode(ct, "aes_gcm", password="p", iterations="200000"), self.TEXT
        )

    def test_aes_gcm_rejects_foreign_ciphertext(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            crypto.decode("aGVsbG8gd29ybGQ=", "aes_gcm", password="p")
        self.assertIn("AES-GCM", str(ctx.exception))

    def test_aes_cbc(self) -> None:
        self._round_trip("aes_cbc", key=KEY32, iv=IV16)

    def test_aes_cbc_wrong_iv(self) -> None:
        ct = crypto.encode(self.TEXT, "aes_cbc", key=KEY32, iv=IV16)
        with self.assertRaises(ValueError):
            crypto.decode(ct, "aes_cbc", key=KEY32, iv="ff" * 16)

    def test_aes_ecb(self) -> None:
        self._round_trip("aes_ecb", key=KEY32)

    def test_aes_ecb_is_deterministic(self) -> None:
        """ECB 没有 IV，相同明文必然得到相同密文——这正是它的弱点。"""
        a = crypto.encode("A" * 32, "aes_ecb", key=KEY32)
        b = crypto.encode("A" * 32, "aes_ecb", key=KEY32)
        self.assertEqual(a, b)

    def test_chacha20(self) -> None:
        self._round_trip("chacha20", key=KEY32, nonce=NONCE16)

    def test_chacha20_poly1305(self) -> None:
        self._round_trip("chacha20_poly1305", key=KEY32, nonce=NONCE12)

    def test_chacha20_poly1305_detects_tampering(self) -> None:
        ct = crypto.encode(self.TEXT, "chacha20_poly1305", key=KEY32, nonce=NONCE12)
        broken = ("A" if ct[0] != "A" else "B") + ct[1:]
        with self.assertRaises(ValueError):
            crypto.decode(broken, "chacha20_poly1305", key=KEY32, nonce=NONCE12)

    def test_hex_and_base32_output(self) -> None:
        for how in ("hex", "base32"):
            self._round_trip("aes_ecb", key=KEY32, out_encoding=how)

    def test_aes_128_key_accepted(self) -> None:
        self._round_trip("aes_ecb", key=KEY16)


@needs_lib
class TestKeyErrors(unittest.TestCase):
    def test_key_wrong_length(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            crypto.encode("x", "aes_ecb", key="0011")
        self.assertIn("长度应为", str(ctx.exception))

    def test_chacha20_requires_16_byte_nonce(self) -> None:
        """cryptography 的 ChaCha20 是 Bernstein 变体，nonce 必须 16 字节。"""
        with self.assertRaises(ValueError) as ctx:
            crypto.encode("x", "chacha20", key=KEY32, nonce=NONCE12)
        self.assertIn("Nonce", str(ctx.exception))

    def test_chacha20_poly1305_requires_12_byte_nonce(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            crypto.encode("x", "chacha20_poly1305", key=KEY32, nonce=NONCE16)
        self.assertIn("Nonce", str(ctx.exception))

    def test_non_hex_key_gives_chinese_error(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            crypto.encode("x", "aes_ecb", key="zz" * 16)
        self.assertIn("非十六进制", str(ctx.exception))

    def test_empty_password(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            crypto.encode("x", "aes_gcm", password="")
        self.assertIn("口令", str(ctx.exception))


@needs_lib
class TestAsymmetric(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls._tmp.name)
        cls.rsa_dir = cls.root / "rsa"
        cls.ecc_dir = cls.root / "ecc"
        crypto.run_action("rsa", "keygen", outdir=str(cls.rsa_dir), bits="2048")
        crypto.run_action(
            "ecc", "keygen", outdir=str(cls.ecc_dir), curve="secp256r1 (P-256)"
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def test_keygen_writes_pem_pair(self) -> None:
        for d in (self.rsa_dir, self.ecc_dir):
            self.assertTrue((d / "private.pem").is_file())
            self.assertTrue((d / "public.pem").is_file())
            self.assertIn("PRIVATE KEY", (d / "private.pem").read_text("utf-8"))

    def test_rsa_round_trip(self) -> None:
        text = "短消息才能直接交给 RSA"
        ct = crypto.encode(text, "rsa", pubkey=str(self.rsa_dir / "public.pem"))
        self.assertEqual(
            crypto.decode(ct, "rsa", privkey=str(self.rsa_dir / "private.pem")), text
        )

    def test_rsa_pkcs1v15_round_trip(self) -> None:
        ct = crypto.encode("hi", "rsa", pubkey=str(self.rsa_dir / "public.pem"),
                           padding_mode="PKCS1v15")
        self.assertEqual(
            crypto.decode(ct, "rsa", privkey=str(self.rsa_dir / "private.pem"),
                          padding_mode="PKCS1v15"),
            "hi",
        )

    def test_rsa_payload_too_long_explains_workaround(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            crypto.encode("A" * 500, "rsa", pubkey=str(self.rsa_dir / "public.pem"))
        msg = str(ctx.exception)
        self.assertIn("只能加密", msg)
        self.assertIn("AES", msg)  # 提示改用混合加密

    def test_rsa_wrong_private_key(self) -> None:
        ct = crypto.encode("hi", "rsa", pubkey=str(self.rsa_dir / "public.pem"))
        with self.assertRaises(ValueError):
            crypto.decode(ct, "rsa", privkey=str(self.ecc_dir / "private.pem"))

    def test_private_key_file_usable_as_public(self) -> None:
        """误把私钥文件填进公钥栏时，自动取其中的公钥部分。"""
        ct = crypto.encode("hi", "rsa", pubkey=str(self.rsa_dir / "private.pem"))
        self.assertEqual(
            crypto.decode(ct, "rsa", privkey=str(self.rsa_dir / "private.pem")), "hi"
        )

    def test_ecc_ecies_round_trip(self) -> None:
        text = "ECIES 加密中文也没问题：你好，世界"
        ct = crypto.encode(text, "ecc", pubkey=str(self.ecc_dir / "public.pem"))
        self.assertEqual(
            crypto.decode(ct, "ecc", privkey=str(self.ecc_dir / "private.pem")), text
        )

    def test_ecc_is_randomised(self) -> None:
        """ECIES 每次用临时密钥，相同明文密文不同。"""
        a = crypto.encode("hi", "ecc", pubkey=str(self.ecc_dir / "public.pem"))
        b = crypto.encode("hi", "ecc", pubkey=str(self.ecc_dir / "public.pem"))
        self.assertNotEqual(a, b)

    def test_missing_key_file(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            crypto.encode("x", "rsa", pubkey=str(self.root / "nope.pem"))
        self.assertIn("不存在", str(ctx.exception))

    def test_cross_type_key_rejected(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            crypto.encode("x", "ecc", pubkey=str(self.rsa_dir / "public.pem"))
        self.assertIn("EC 公钥", str(ctx.exception))

    def test_keygen_requires_outdir(self) -> None:
        with self.assertRaises(ValueError):
            crypto.run_action("rsa", "keygen", outdir="")

    def test_keygen_rejects_bad_bits(self) -> None:
        with self.assertRaises(ValueError):
            crypto.run_action("rsa", "keygen", outdir=str(self.root / "x"), bits="1024")

    def test_encrypted_private_key_needs_password(self) -> None:
        d = self.root / "rsa_enc"
        crypto.run_action("rsa", "keygen", outdir=str(d), bits="2048", password="pw")
        ct = crypto.encode("hi", "rsa", pubkey=str(d / "public.pem"))
        self.assertEqual(crypto.decode(ct, "rsa", privkey=str(d / "private.pem"),
                                       password="pw"), "hi")
        with self.assertRaises(ValueError) as ctx:
            crypto.decode(ct, "rsa", privkey=str(d / "private.pem"))
        self.assertIn("口令", str(ctx.exception))


@needs_lib
class TestActions(unittest.TestCase):
    def test_unknown_action(self) -> None:
        with self.assertRaises(ValueError):
            crypto.run_action("rsa", "no_such_action")

    def test_unknown_method(self) -> None:
        with self.assertRaises(ValueError):
            crypto.run_action("nope", "keygen")

    def test_only_asymmetric_has_actions(self) -> None:
        with_actions = {c.name for c in crypto.available() if c.actions}
        self.assertEqual(with_actions, {"rsa", "ecc"})


class TestMissingDependency(unittest.TestCase):
    """没装 cryptography 时的降级行为。

    这组测试**不**跳过——降级路径本身就是要保证的东西。
    放在子进程里跑，用 import 拦截模拟依赖缺失，避免污染当前进程的模块缓存。
    """

    def _run_blocked(self, body: str) -> subprocess.CompletedProcess:
        code = (
            "import sys, builtins\n"
            "real = builtins.__import__\n"
            "def blocker(name, *a, **k):\n"
            "    if name.split('.')[0] == 'cryptography':\n"
            "        raise ImportError('blocked for test')\n"
            "    return real(name, *a, **k)\n"
            "builtins.__import__ = blocker\n"
            f"sys.path.insert(0, r'{ROOT}')\n"
            "from src.core import crypto, crypto_modern\n"
            f"{body}"
        )
        return subprocess.run(
            [sys.executable, "-c", code], capture_output=True, text=True
        )

    def test_module_still_imports(self) -> None:
        """缺依赖时模块必须能导入——否则整个应用都起不来。"""
        proc = self._run_blocked(
            "assert crypto_modern.HAVE_CRYPTOGRAPHY is False\n"
            f"assert len(crypto.REGISTRY) == {len(crypto.REGISTRY)}\n"
            "print('OK')\n"
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("OK", proc.stdout)

    def test_curves_stored_as_names_not_classes(self) -> None:
        """曲线必须存类名字符串。

        直接存 `ec.SECP256R1` 会在模块级求值，缺依赖时抛 NameError，
        连累整个 crypto 模块导入失败。这是踩过的坑。
        """
        proc = self._run_blocked(
            "bad = [k for k, v in crypto_modern.CURVES.items() "
            "if not isinstance(v, str)]\n"
            "assert not bad, bad\n"
            "print('OK')\n"
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("OK", proc.stdout)

    def test_calling_modern_algorithm_gives_actionable_error(self) -> None:
        proc = self._run_blocked(
            "try:\n"
            "    crypto.encode('x', 'aes_gcm', password='p')\n"
            "except ValueError as e:\n"
            "    assert 'cryptography' in str(e), e\n"
            "else:\n"
            "    raise AssertionError('应当报错')\n"
            "try:\n"
            "    crypto.run_action('ecc', 'keygen', outdir='x')\n"
            "except ValueError as e:\n"
            "    assert 'cryptography' in str(e), e\n"
            "else:\n"
            "    raise AssertionError('应当报错')\n"
            "print('OK')\n"
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("OK", proc.stdout)

    def test_classical_algorithms_unaffected(self) -> None:
        proc = self._run_blocked(
            "assert crypto.encode('HELLO', 'caesar', shift='3') == 'KHOOR'\n"
            "assert crypto.encode('中', 'morse', "
            "mode=crypto.MORSE_MODE_UNICODE)\n"
            "print('OK')\n"
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("OK", proc.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
