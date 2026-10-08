"""ui.async_task 的单元测试。

`TaskRunner` 只需要宿主提供 `after(ms, fn)`，所以用一个假控件就能在没有
显示器、没有 Tk 的环境下完整驱动它。
"""

from __future__ import annotations

import sys
import threading
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ui.async_task import TaskRunner  # noqa: E402


class FakeWidget:
    """收集 after 回调，由测试手动驱动（模拟 Tk 主循环）。"""

    def __init__(self) -> None:
        self.pending: list = []

    def after(self, ms: int, fn) -> None:
        self.pending.append(fn)


def drive(widget: FakeWidget, until, timeout: float = 5.0) -> None:
    """反复执行排队的回调，直到 until() 为真或超时。"""
    deadline = time.time() + timeout
    while not until() and time.time() < deadline:
        if widget.pending:
            widget.pending.pop(0)()
        else:
            time.sleep(0.002)
    assert until(), "等待超时：回调始终没把结果送回来"


class TestTaskRunner(unittest.TestCase):
    def test_success_delivers_result(self) -> None:
        widget = FakeWidget()
        runner = TaskRunner(widget)
        got: list = []

        self.assertTrue(runner.run(lambda: 6 * 7, on_done=got.append))
        self.assertTrue(runner.busy)
        drive(widget, lambda: bool(got))

        self.assertEqual(got, [42])
        self.assertFalse(runner.busy)

    def test_error_goes_to_on_error(self) -> None:
        widget = FakeWidget()
        runner = TaskRunner(widget)
        errors: list = []

        def boom() -> str:
            raise ValueError("算不动了")

        runner.run(boom, on_done=lambda _r: None, on_error=errors.append)
        drive(widget, lambda: bool(errors))

        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], ValueError)
        self.assertEqual(str(errors[0]), "算不动了")
        self.assertFalse(runner.busy)

    def test_error_without_handler_does_not_crash(self) -> None:
        """没给 on_error 时只记日志，不能把主线程带崩。"""
        widget = FakeWidget()
        runner = TaskRunner(widget)

        runner.run(lambda: 1 / 0, on_done=lambda _r: None)
        drive(widget, lambda: not runner.busy)
        self.assertFalse(runner.busy)

    def test_second_run_rejected_while_busy(self) -> None:
        widget = FakeWidget()
        runner = TaskRunner(widget)
        gate = threading.Event()
        done: list = []

        self.assertTrue(runner.run(lambda: gate.wait(2), on_done=done.append))
        # 第一个任务还卡在 gate 上，第二次提交必须被拒
        self.assertFalse(runner.run(lambda: "第二个", on_done=done.append))

        gate.set()
        drive(widget, lambda: bool(done))
        self.assertEqual(len(done), 1)

    def test_runs_off_the_calling_thread(self) -> None:
        """核心保证：fn 不在调用者线程里执行，否则起不到解冻界面的作用。"""
        widget = FakeWidget()
        runner = TaskRunner(widget)
        caller = threading.get_ident()
        seen: list = []

        runner.run(lambda: seen.append(threading.get_ident()) or "ok",
                   on_done=lambda _r: None)
        drive(widget, lambda: bool(seen))

        self.assertNotEqual(seen[0], caller)

    def test_callback_runs_on_the_driving_thread(self) -> None:
        """回调必须在主线程（这里由 drive 模拟）执行，才能安全碰控件。"""
        widget = FakeWidget()
        runner = TaskRunner(widget)
        caller = threading.get_ident()
        seen: list = []

        runner.run(lambda: "ok", on_done=lambda _r: seen.append(threading.get_ident()))
        drive(widget, lambda: bool(seen))

        self.assertEqual(seen[0], caller)


if __name__ == "__main__":
    unittest.main(verbosity=2)
