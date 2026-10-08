"""统一日志入口。

用法：
    from src.utils.logger import get_logger
    log = get_logger(__name__)
    log.info("...")
"""

from __future__ import annotations

import logging

_CONFIGURED = False


def get_logger(name: str = "arg.xc") -> logging.Logger:
    """返回带统一格式的 logger。首次调用时完成 root 配置。"""
    global _CONFIGURED
    if not _CONFIGURED:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%H:%M:%S",
        )
        _CONFIGURED = True
    return logging.getLogger(name)
