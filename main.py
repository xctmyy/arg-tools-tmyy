"""arg.xc —— ARG 创作工具箱

程序入口。只做两件事：把项目根加入 import 路径、启动应用。
所有业务逻辑都在 src/ 下，本文件保持极薄。
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.app import ArgToolboxApp  # noqa: E402


def main() -> int:
    """启动 GUI。返回进程退出码。"""
    app = ArgToolboxApp()
    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
