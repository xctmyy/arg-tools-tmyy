"""隐写 工具页。

规划能力：
- 图像：LSB 隐写嵌入 / 提取、通道分离与图层查看、EXIF 元数据读写
- 音频：频谱图生成与查看、倒放、DTMF 音解码
- 视频：关键帧提取、字幕轨检查
- 文本：零宽字符、Unicode 同形字、HTML 注释

实现入口：src/core/stego.py
"""

from src.ui.pages.base import BasePage


class StegoPage(BasePage):
    title = "隐写"
    description = "图像 / 音频 / 文本中的信息隐藏与提取"

    planned = (
        "图像：LSB 最低有效位嵌入与提取",
        "图像：色彩通道分离、图层查看",
        "图像：EXIF 等元数据读写",
        "音频：频谱图生成与查看（把图藏进声音里）",
        "音频：倒放、DTMF 双音多频解码",
        "视频：关键帧提取、字幕轨检查",
        "文本：零宽字符、Unicode 同形字、HTML 注释",
    )
