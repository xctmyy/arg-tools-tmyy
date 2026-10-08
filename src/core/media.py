"""多媒体加工。

统一对外接口（待实现）：
    convert(src, dst, **params) -> Path
    extract_frames(video, out_dir, **params) -> list[Path]
    qrcode_generate(text, out_path, **params) -> Path
    qrcode_read(image) -> str
"""

from __future__ import annotations

from pathlib import Path

CAPABILITIES: tuple[str, ...] = (
    "audio_trim", "audio_reverse", "audio_speed", "audio_convert",
    "image_resize", "image_crop", "image_convert", "image_watermark",
    "video_frames", "video_clip", "video_convert",
    "qrcode_generate", "qrcode_read",
)


def convert(src: Path, dst: Path, **params: object) -> Path:
    """通用格式 / 参数转换。"""
    raise NotImplementedError("convert 尚未实现")


def extract_frames(video: Path, out_dir: Path, **params: object) -> list[Path]:
    """从视频抽帧。"""
    raise NotImplementedError("extract_frames 尚未实现")


def qrcode_generate(text: str, out_path: Path, **params: object) -> Path:
    """生成二维码。"""
    raise NotImplementedError("qrcode_generate 尚未实现")


def qrcode_read(image: Path) -> str:
    """识别二维码。"""
    raise NotImplementedError("qrcode_read 尚未实现")
