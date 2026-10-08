"""config.settings 的单元测试：默认值、序列化往返、容错、最近工程维护。"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import settings as S  # noqa: E402


class TestDefaults(unittest.TestCase):
    def test_defaults(self) -> None:
        s = S.AppSettings()
        self.assertEqual(s.appearance, S.AppearanceMode.DARK)
        self.assertEqual(s.theme, S.ColorTheme.BLUE)
        self.assertEqual(s.recent_projects, [])
        self.assertIsNone(s.last_opened_project)
        self.assertTrue(s.ai_panel_open)


class TestSerialisation(unittest.TestCase):
    def test_round_trip(self) -> None:
        s = S.AppSettings(
            appearance=S.AppearanceMode.LIGHT,
            theme=S.ColorTheme.GREEN,
            recent_projects=["/a", "/b"],
            last_opened_project="/a",
            ai_panel_open=False,
        )
        again = S.AppSettings.from_dict(s.to_dict())
        self.assertEqual(again.appearance, S.AppearanceMode.LIGHT)
        self.assertEqual(again.theme, S.ColorTheme.GREEN)
        self.assertEqual(again.recent_projects, ["/a", "/b"])
        self.assertEqual(again.last_opened_project, "/a")
        self.assertFalse(again.ai_panel_open)

    def test_to_dict_is_json_serialisable(self) -> None:
        json.dumps(S.AppSettings().to_dict())

    def test_missing_keys_fall_back_to_defaults(self) -> None:
        s = S.AppSettings.from_dict({})
        self.assertEqual(s.appearance, S.AppearanceMode.DARK)
        self.assertEqual(s.theme, S.ColorTheme.BLUE)
        self.assertEqual(s.recent_projects, [])
        self.assertTrue(s.ai_panel_open)

    def test_garbage_values_are_tolerated(self) -> None:
        s = S.AppSettings.from_dict({
            "appearance": "不存在的模式",
            "theme": 12345,
            "recent_projects": "这不是列表",
            "ai_panel_open": None,
        })
        self.assertEqual(s.appearance, S.AppearanceMode.DARK)
        self.assertEqual(s.theme, S.ColorTheme.BLUE)
        self.assertEqual(s.recent_projects, [])
        # 值为 None 应当回落到默认的「展开」，而不是当成 False
        self.assertTrue(s.ai_panel_open)

    def test_explicit_false_is_kept(self) -> None:
        self.assertFalse(S.AppSettings.from_dict({"ai_panel_open": False}).ai_panel_open)


class TestTouchRecent(unittest.TestCase):
    def test_inserts_at_front(self) -> None:
        s = S.AppSettings()
        s.touch_recent("/a")
        s.touch_recent("/b")
        self.assertEqual(s.recent_projects, ["/b", "/a"])
        self.assertEqual(s.last_opened_project, "/b")

    def test_deduplicates(self) -> None:
        s = S.AppSettings()
        s.touch_recent("/a")
        s.touch_recent("/b")
        s.touch_recent("/a")
        self.assertEqual(s.recent_projects, ["/a", "/b"])

    def test_caps_length(self) -> None:
        s = S.AppSettings()
        for i in range(S.AppSettings.MAX_RECENT + 5):
            s.touch_recent(f"/p{i}")
        self.assertEqual(len(s.recent_projects), S.AppSettings.MAX_RECENT)
        self.assertEqual(s.recent_projects[0], f"/p{S.AppSettings.MAX_RECENT + 4}")

    def test_accepts_path_object(self) -> None:
        s = S.AppSettings()
        s.touch_recent(Path("/tmp/x"))
        self.assertEqual(s.recent_projects, [str(Path("/tmp/x"))])


class TestLoadSave(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._orig = S.SETTINGS_FILE
        S.SETTINGS_FILE = Path(self._tmp.name) / "settings.json"

    def tearDown(self) -> None:
        S.SETTINGS_FILE = self._orig
        self._tmp.cleanup()

    def test_load_missing_file_returns_defaults(self) -> None:
        s = S.load_settings()
        self.assertEqual(s.appearance, S.AppearanceMode.DARK)
        self.assertTrue(s.ai_panel_open)

    def test_save_then_load(self) -> None:
        S.save_settings(S.AppSettings(ai_panel_open=False,
                                      recent_projects=["/x"],
                                      appearance=S.AppearanceMode.LIGHT))
        again = S.load_settings()
        self.assertFalse(again.ai_panel_open)
        self.assertEqual(again.recent_projects, ["/x"])
        self.assertEqual(again.appearance, S.AppearanceMode.LIGHT)

    def test_load_corrupt_file_returns_defaults(self) -> None:
        S.SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        S.SETTINGS_FILE.write_text("{ 这不是 JSON", encoding="utf-8")
        self.assertEqual(S.load_settings().appearance, S.AppearanceMode.DARK)

    def test_save_is_atomic_leaves_no_tmp(self) -> None:
        S.save_settings(S.AppSettings())
        leftovers = list(S.SETTINGS_FILE.parent.glob("*.tmp"))
        self.assertEqual(leftovers, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
