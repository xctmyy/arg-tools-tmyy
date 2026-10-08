"""应用装配层。

职责：读取配置 -> 设置外观主题 -> 创建并运行主窗口。
不承载任何业务逻辑，方便后续替换 UI 框架或做无界面（CLI）模式。
"""

from __future__ import annotations

from src.config.settings import (
    APP_NAME,
    WINDOW_MIN_SIZE,
    WINDOW_SIZE,
    AppSettings,
    load_settings,
    save_settings,
)
from src.ui.main_window import MainWindow
from src.utils.logger import get_logger

log = get_logger(__name__)


class ArgToolboxApp:
    """应用门面。"""

    def __init__(self, settings: AppSettings | None = None) -> None:
        self.settings = settings or load_settings()
        self.window: MainWindow | None = None

    def run(self) -> None:
        log.info("启动 %s", APP_NAME)
        self.window = MainWindow(
            title=APP_NAME,
            size=WINDOW_SIZE,
            min_size=WINDOW_MIN_SIZE,
            settings=self.settings,
        )
        self.window.mainloop()
        save_settings(self.settings)
        log.info("%s 已退出", APP_NAME)
