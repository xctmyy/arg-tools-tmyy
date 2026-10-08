"""隐写（steganography）实现。

统一对外接口（待实现）：
    hide(carrier, payload, method, **params) -> Path     # 把信息藏进载体
    extract(carrier, method, **params) -> bytes | str    # 从载体中取出信息
"""

from __future__ import annotations

from pathlib import Path

#: 支持（规划中）的隐写方式
CAPABILITIES: tuple[str, ...] = (
    "lsb_image",        # 图像最低有效位
    "channel_split",    # 通道 / 图层分离
    "exif",             # 元数据写入
    "spectrogram",      # 音频频谱图
    "dtmf",             # 双音多频
    "zero_width",       # 零宽字符
    "unicode_homoglyph",
)


def hide(carrier: Path, payload: bytes | str, method: str, **params: object) -> Path:
    """把 payload 藏进 carrier，返回产物路径。"""
    raise NotImplementedError(f"hide: {method!r} 尚未实现")


def extract(carrier: Path, method: str, **params: object) -> bytes | str:
    """从 carrier 中提取隐藏信息。"""
    raise NotImplementedError(f"extract: {method!r} 尚未实现")
