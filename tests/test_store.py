"""core.store 的单元测试。

运行：
    python -m unittest tests.test_store -v
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.core import store  # noqa: E402


class TestProjectLifecycle(unittest.TestCase):
    """每个测试用独立子目录保证隔离。

    注意：这里按「每个测试类」建临时目录，而不是每个测试方法。
    原因是在某些 Windows 环境下 TemporaryDirectory.cleanup() 单次要 1 秒以上
    （删除目录被安全软件/沙箱拦截），逐个方法清理会把测试拖慢几十倍。
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def setUp(self) -> None:
        self.base = Path(self._tmp.name) / self._testMethodName
        self.base.mkdir(parents=True, exist_ok=True)

    def test_create_writes_files(self) -> None:
        root = self.base / "demo"
        p = store.Project.create("演示工程", root, author="tmyy", description="desc")

        self.assertTrue((root / store.PROJECT_FILE).is_file())
        self.assertTrue((root / store.CLUES_FILE).is_file())
        self.assertTrue((root / store.CHAIN_FILE).is_file())
        self.assertTrue((root / store.ASSETS_DIR).is_dir())
        self.assertTrue(store.Project.is_project(root))
        self.assertEqual(p.name, "演示工程")

    def test_save_and_reopen_round_trip(self) -> None:
        root = self.base / "rt"
        p = store.Project.create("往返测试", root, author="a")
        c1 = p.add_clue(title="第一条", content="内容1", source="discord",
                        tags=["音频", "频谱"])
        p.add_clue(title="第二条", content="内容2", tags=["音频"])
        p.save()

        again = store.Project.open(root)
        self.assertEqual(again.name, "往返测试")
        self.assertEqual(again.author, "a")
        self.assertEqual(len(again.clues), 2)

        got = again.get_clue(c1.id)
        self.assertIsNotNone(got)
        assert got is not None
        self.assertEqual(got.title, "第一条")
        self.assertEqual(got.tags, ["音频", "频谱"])
        self.assertEqual(got.source, "discord")

    def test_create_rejects_existing_project(self) -> None:
        root = self.base / "dup"
        store.Project.create("one", root)
        with self.assertRaises(store.ProjectError):
            store.Project.create("two", root)

    def test_create_rejects_non_empty_dir(self) -> None:
        root = self.base / "busy"
        root.mkdir()
        (root / "随便.txt").write_text("x", encoding="utf-8")
        with self.assertRaises(store.ProjectError):
            store.Project.create("x", root)

    def test_open_missing_raises(self) -> None:
        with self.assertRaises(store.ProjectError):
            store.Project.open(self.base / "not-here")

    def test_is_project_false_for_plain_dir(self) -> None:
        plain = self.base / "plain"
        plain.mkdir()
        self.assertFalse(store.Project.is_project(plain))


class TestClueOperations(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def setUp(self) -> None:
        self.root = Path(self._tmp.name) / self._testMethodName / "proj"
        self.p = store.Project.create("线索测试", self.root)
        self.a = self.p.add_clue(title="凯撒密文", content="KHOOR",
                                 source="邮件", tags=["密码"])
        self.b = self.p.add_clue(title="频谱图", content="screenshot.png",
                                 source="B站", tags=["音频", "图像"])

    def test_ids_are_unique(self) -> None:
        self.assertNotEqual(self.a.id, self.b.id)

    def test_find_by_keyword(self) -> None:
        self.assertEqual([c.id for c in self.p.find_clues("KHOOR")], [self.a.id])
        self.assertEqual([c.id for c in self.p.find_clues("频谱")], [self.b.id])

    def test_find_by_tag(self) -> None:
        self.assertEqual([c.id for c in self.p.find_clues(tag="音频")], [self.b.id])
        self.assertEqual(len(self.p.find_clues()), 2)

    def test_keyword_and_tag_combined(self) -> None:
        self.assertEqual(self.p.find_clues("KHOOR", tag="音频"), [])

    def test_update_clue(self) -> None:
        self.assertTrue(self.p.update_clue(self.a.id, title="改过了", tags=["密码", "凯撒"]))
        got = self.p.get_clue(self.a.id)
        assert got is not None
        self.assertEqual(got.title, "改过了")
        self.assertEqual(got.tags, ["密码", "凯撒"])

    def test_update_unknown_field_raises(self) -> None:
        with self.assertRaises(store.ProjectError):
            self.p.update_clue(self.a.id, nope=1)

    def test_update_missing_returns_false(self) -> None:
        self.assertFalse(self.p.update_clue("nosuchid", title="x"))

    def test_remove_clue(self) -> None:
        self.assertTrue(self.p.remove_clue(self.a.id))
        self.assertIsNone(self.p.get_clue(self.a.id))
        self.assertFalse(self.p.remove_clue(self.a.id))

    def test_all_tags_sorted_by_frequency(self) -> None:
        self.p.add_clue(title="再来一条", tags=["音频"])
        self.assertEqual(self.p.all_tags()[0], "音频")

    def test_changes_persist_after_save(self) -> None:
        self.p.update_clue(self.a.id, content="明文是 HELLO")
        self.p.remove_clue(self.b.id)
        self.p.save()

        again = store.Project.open(self.root)
        self.assertEqual(len(again.clues), 1)
        got = again.get_clue(self.a.id)
        assert got is not None
        self.assertEqual(got.content, "明文是 HELLO")


if __name__ == "__main__":
    unittest.main(verbosity=2)
