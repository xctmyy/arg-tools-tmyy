"""文件与网络分析。

统一对外接口（待实现）：
    hexdump(path, offset, length) -> str
    sniff_type(path) -> str                      # 文件类型识别（魔术字节）
    carve(path, out_dir) -> list[Path]           # 提取嵌套 / 附加数据
    read_metadata(path) -> dict
    whois(domain) -> dict
    wayback(url, timestamp) -> str
    http_request(url, method, **params) -> dict
"""

from __future__ import annotations

from pathlib import Path

CAPABILITIES: tuple[str, ...] = (
    "hexdump", "sniff_type", "carve", "strings",
    "read_metadata", "whois", "wayback", "http_request",
)


def hexdump(path: Path, offset: int = 0, length: int = 512) -> str:
    """以十六进制 + ASCII 形式查看文件片段。"""
    raise NotImplementedError("hexdump 尚未实现")


def sniff_type(path: Path) -> str:
    """根据魔术字节判断真实文件类型。"""
    raise NotImplementedError("sniff_type 尚未实现")


def carve(path: Path, out_dir: Path) -> list[Path]:
    """从文件中提取被嵌入的其它文件（类 binwalk）。"""
    raise NotImplementedError("carve 尚未实现")


def read_metadata(path: Path) -> dict:
    """读取 EXIF / PDF / Office 等元数据。"""
    raise NotImplementedError("read_metadata 尚未实现")


def whois(domain: str) -> dict:
    """域名注册信息查询。"""
    raise NotImplementedError("whois 尚未实现")


def wayback(url: str, timestamp: str | None = None) -> str:
    """获取网页历史快照地址。"""
    raise NotImplementedError("wayback 尚未实现")
