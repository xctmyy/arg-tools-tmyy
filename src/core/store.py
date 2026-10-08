"""工程数据持久化。

规划：一个 ARG 工程 = 一个目录（或单个 .argx 包），包含
    project.json     元信息（名称、作者、简介、时间线）
    clues.json       线索库
    chain.json       谜题链结构（对应 core.chain）
    assets/          该工程的素材

统一对外接口（待实现）：
    Project.create(name, path) -> Project
    Project.open(path) -> Project
    Project.save() -> None
    Project.add_clue(...) / remove_clue(...)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

PROJECT_FILE = "project.json"


@dataclass
class Project:
    """一个 ARG 工程。"""

    name: str = "未命名工程"
    author: str = ""
    description: str = ""
    root: Path | None = None
    clues: list[dict] = field(default_factory=list)

    @classmethod
    def create(cls, name: str, root: Path) -> "Project":
        raise NotImplementedError("Project.create 尚未实现")

    @classmethod
    def open(cls, root: Path) -> "Project":
        raise NotImplementedError("Project.open 尚未实现")

    def save(self) -> None:
        raise NotImplementedError("Project.save 尚未实现")
