"""core.crypto 的单元测试。

运行：
    python -m unittest tests.test_crypto -v
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.core import crypto  # noqa: E402


class TestRoundTrip(unittest.TestCase):
    """编解码往返一致性：decode(encode(x)) == x。"""

    def _check(self, method: str, text: str, **params: object) -> None:
        enc = crypto.encode(text, method, **params)
        dec = crypto.decode(enc, method, **params)
        self.assertEqual(dec, text, f"{method} 往返失败：{text!r} -> {enc!r} -> {dec!r}")

    def test_substitution(self) -> None:
        self._check("caesar", "Hello, World!", shift="7")
        self._check("rot13", "Attack at dawn")
        self._check("atbash", "Hello World")
        # A1Z26 只保留字母、统一大写，故用大写纯字母测往返
        self._check("a1z26", "HELLO", sep="-")

    def test_a1z26_is_lossy_by_design(self) -> None:
        """A1Z26 丢失大小写与空格——这是算法本身的性质，不是 bug。"""
        self.assertEqual(crypto.decode(crypto.encode("Hi there", "a1z26"), "a1z26"),
                         "HITHERE")

    def test_keyed(self) -> None:
        self._check("vigenere", "AttackAtDawn", key="LEMON")
        self._check("rail_fence", "WEAREDISCOVEREDFLEEATONCE", rails="3")
        # Playfair 会丢弃空格与标点，且 I/J 合并，故用纯字母测试
        self._check("playfair", "HELLOWORLD", key="MONARCHY")
        self._check("nihilist", "HELLO", key="ZEBRAS", numeric_key="KEY")
        book = "the quick brown fox jumps over the lazy dog"
        self._check("book_cipher", "hello", book=book, sep=" ")

    def test_encoding(self) -> None:
        for method in ("base64", "base32", "base16", "url", "html_entity",
                       "brainfuck", "ook"):
            self._check(method, "Hello, 世界! 123")
        self._check("morse", "SOS HELP", word_sep="/")
        self._check("binary", "Hi 你好", sep=" ")
        self._check("hex", "Hi 你好", sep=" ")


class TestKnownVectors(unittest.TestCase):
    """已知向量，防止实现悄悄跑偏。"""

    def test_caesar(self) -> None:
        self.assertEqual(crypto.encode("HELLO", "caesar", shift="3"), "KHOOR")
        self.assertEqual(crypto.decode("KHOOR", "caesar", shift="3"), "HELLO")

    def test_rot13(self) -> None:
        self.assertEqual(crypto.encode("Hello", "rot13"), "Uryyb")

    def test_atbash(self) -> None:
        self.assertEqual(crypto.encode("abc", "atbash"), "zyx")

    def test_a1z26(self) -> None:
        self.assertEqual(crypto.encode("ABC", "a1z26", sep="-"), "1-2-3")
        self.assertEqual(crypto.decode("1-2-3", "a1z26"), "ABC")

    def test_vigenere(self) -> None:
        # 经典教科书向量：ATTACKATDAWN + LEMON -> LXFOPVEFRNHR
        self.assertEqual(
            crypto.encode("ATTACKATDAWN", "vigenere", key="LEMON"),
            "LXFOPVEFRNHR",
        )

    def test_base_family(self) -> None:
        self.assertEqual(crypto.encode("hello", "base64"), "aGVsbG8=")
        self.assertEqual(crypto.encode("hello", "base32"), "NBSWY3DP")
        self.assertEqual(crypto.encode("hello", "base16"), "68656C6C6F")
        self.assertEqual(crypto.decode("aGVsbG8=", "base64"), "hello")

    def test_morse(self) -> None:
        self.assertEqual(crypto.encode("SOS", "morse"), "... --- ...")
        self.assertEqual(crypto.decode("... --- ...", "morse"), "SOS")

    def test_binary_hex(self) -> None:
        self.assertEqual(crypto.encode("Hi", "binary"), "01001000 01101001")
        self.assertEqual(crypto.decode("01001000 01101001", "binary"), "Hi")
        self.assertEqual(crypto.encode("Hi", "hex"), "48 69")

    def test_hashes(self) -> None:
        self.assertEqual(
            crypto.encode("abc", "md5"), "900150983cd24fb0d6963f7d28e17f72"
        )
        self.assertEqual(
            crypto.encode("abc", "sha256"),
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
        )
        self.assertEqual(crypto.encode("abc", "crc32"), "352441c2")


class TestBehavior(unittest.TestCase):
    def test_hash_is_one_way(self) -> None:
        with self.assertRaises(ValueError):
            crypto.decode("900150983cd24fb0d6963f7d28e17f72", "md5")

    def test_unknown_method(self) -> None:
        with self.assertRaises(ValueError):
            crypto.encode("x", "no_such_codec")

    def test_missing_key(self) -> None:
        with self.assertRaises(ValueError):
            crypto.encode("HELLO", "vigenere", key="")

    def test_bad_int_param(self) -> None:
        with self.assertRaises(ValueError):
            crypto.encode("HELLO", "caesar", shift="abc")

    def test_registry_completeness(self) -> None:
        """注册表里每个算法都能被 available() 列出，且分组合法。"""
        listed = crypto.available()
        self.assertEqual(len(listed), len(crypto.REGISTRY))
        for c in listed:
            self.assertIn(c.group, crypto.GROUPS)
            self.assertTrue(c.label)

    def test_capabilities_backward_compatible(self) -> None:
        for name in ("caesar", "base64", "morse", "md5", "crc32"):
            self.assertIn(name, crypto.CAPABILITIES)


class TestDetect(unittest.TestCase):
    def test_detects_common(self) -> None:
        self.assertIn("binary", crypto.detect("01001000 01101001"))
        self.assertIn("base64", crypto.detect("aGVsbG8="))
        self.assertIn("morse", crypto.detect("... --- ..."))
        self.assertIn("hex", crypto.detect("68656c6c6f"))

    def test_empty(self) -> None:
        self.assertEqual(crypto.detect("   "), [])


class TestBruteForce(unittest.TestCase):
    def test_caesar_bruteforce_finds_plaintext(self) -> None:
        results = crypto.brute_force("KHOOR", "caesar")
        self.assertEqual(len(results), 25)
        self.assertIn("HELLO", [text for _, text in results])

    def test_rail_bruteforce_round_trips(self) -> None:
        cipher = crypto.encode("WEAREDISCOVEREDFLEEATONCE", "rail_fence", rails="3")
        results = crypto.brute_force(cipher, "rail_fence")
        self.assertIn("WEAREDISCOVEREDFLEEATONCE", [text for _, text in results])

    def test_unsupported(self) -> None:
        with self.assertRaises(ValueError):
            crypto.brute_force("x", "base64")


class TestFriendlyErrors(unittest.TestCase):
    """错误信息要能直接给用户看，不能把标准库的英文原文透出去。

    背景：base64.b64decode 遇到非 ASCII 输入时抛的是普通 ValueError
    （"string argument should contain only ASCII characters"）。
    它虽然和 binascii.Error 同属 ValueError 家族，但反过来不成立——
    只捕获 binascii.Error 会让这条英文消息漏到界面上。
    """

    def _message(self, text: str, method: str) -> str:
        with self.assertRaises(ValueError) as ctx:
            crypto.decode(text, method)
        return str(ctx.exception)

    def test_base64_non_ascii_input(self) -> None:
        msg = self._message("这不是base64!!!", "base64")
        self.assertIn("Base64", msg)
        self.assertNotIn("only ASCII", msg)
        self.assertNotIn("string argument", msg)

    def test_base64_illegal_chars(self) -> None:
        self.assertIn("非法字符", self._message("###", "base64"))

    def test_base32_non_ascii_input(self) -> None:
        msg = self._message("中文输入", "base32")
        self.assertIn("Base32", msg)
        self.assertNotIn("only ASCII", msg)

    def test_base16_illegal_chars(self) -> None:
        msg = self._message("zz!!", "base16")
        self.assertIn("Base16", msg)
        self.assertNotIn("only ASCII", msg)

    def test_valid_input_still_decodes(self) -> None:
        self.assertEqual(crypto.decode("aGVsbG8=", "base64"), "hello")
        self.assertEqual(crypto.decode("NBSWY3DP", "base32"), "hello")
        self.assertEqual(crypto.decode("68656C6C6F", "base16"), "hello")

    def test_lowercase_base32_accepted(self) -> None:
        self.assertEqual(crypto.decode("nbswy3dp", "base32"), "hello")


if __name__ == "__main__":
    unittest.main(verbosity=2)
