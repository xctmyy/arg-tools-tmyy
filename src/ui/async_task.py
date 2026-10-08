"""后台任务：把耗时运算挪出 UI 线程。

为什么需要
----------
Tk 的主循环负责重绘与响应事件。任何耗时操作（大文本编解码、Brainfuck 解释、
图像处理）直接在主线程跑，界面就会卡住甚至被系统判定为"无响应"。

线程安全铁律
------------
**绝对不能在工作线程里碰任何控件。** Tk 不是线程安全的，跨线程调用控件
会导致随机崩溃或死锁。本模块的做法是：

    工作线程  只负责算 -> 把结果塞进队列
    主线程    用 widget.after() 轮询队列 -> 拿到结果后才回调

用法
----
    self._tasks = TaskRunner(self)

    self._tasks.run(
        lambda: crypto.encode(text, method, **params),   # 纯函数，不碰控件
        on_done=self._show_result,
        on_error=self._show_error,
    )

注意 `fn` 用到的所有数据都要在**主线程里先取好**（比如先把输入框内容读成
字符串），闭包里不要出现控件对象。
"""

from __future__ import annotations

import queue
import threading
from typing import Any, Callable

from src.utils.logger import get_logger

log = get_logger(__name__)

#: 轮询间隔（毫秒）。25ms 约 40fps，人眼无感，CPU 占用可忽略。
POLL_MS = 25


class TaskRunner:
    """串行执行后台任务：同一时刻只允许一个任务在跑。

    串行的理由：这类运算本身是用户触发的短任务，并发跑多个既没必要，
    也会让"结果该写到哪个框"变得含糊。
    """

    def __init__(self, widget: Any) -> None:
        """widget 只需提供 `after(ms, fn)` 方法，通常是某个控件或窗口。"""
        self._widget = widget
        self._busy = False

    @property
    def busy(self) -> bool:
        """是否有任务正在执行。"""
        return self._busy

    def run(
        self,
        fn: Callable[[], Any],
        on_done: Callable[[Any], None],
        on_error: Callable[[Exception], None] | None = None,
        poll_ms: int = POLL_MS,
    ) -> bool:
        """在后台线程执行 `fn`，完成后在主线程回调。

        `fn` 必须是纯计算，不得读写任何控件。
        返回 False 表示已有任务在执行，本次未启动。
        """
        if self._busy:
            return False
        self._busy = True

        box: queue.Queue[tuple[bool, Any]] = queue.Queue(maxsize=1)

        def worker() -> None:
            try:
                box.put((True, fn()))
            except Exception as e:  # noqa: BLE001 —— 异常要原样带回主线程处理
                box.put((False, e))

        threading.Thread(target=worker, daemon=True).start()

        def poll() -> None:
            try:
                ok, payload = box.get_nowait()
            except queue.Empty:
                # 还没算完，下一拍再看
                self._widget.after(poll_ms, poll)
                return

            self._busy = False
            if ok:
                on_done(payload)
            elif on_error is not None:
                on_error(payload)
            else:
                log.error("后台任务失败：%r", payload)

        self._widget.after(poll_ms, poll)
        return True
