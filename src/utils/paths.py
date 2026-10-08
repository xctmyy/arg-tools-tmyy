"""路径工具。

统一处理：把用户给的相对路径解析到项目根、确保运行期目录存在。
"""

from __future__ import annotations

from pathlib import Path

from src.config.settings import ASSETS_DIR, DATA_DIR, ROOT_DIR


def resolve(path: str | Path) -> Path:
    """相对路径按项目根解析，绝对路径原样返回。"""
    p = Path(path)
    return p if p.is_absolute() else (ROOT_DIR / p)


def ensure_runtime_dirs() -> None:
    """确保运行期目录存在。启动时调用一次即可。"""
    for d in (DATA_DIR, ASSETS_DIR):
        d.mkdir(parents=True, exist_ok=True)


# TODO: 增加 sanitize_filename / unique_path 等辅助函数
