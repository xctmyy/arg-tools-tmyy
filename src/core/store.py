"""工程数据持久化。

一个 ARG 工程 = 一个目录，结构：

    <工程根>/
        project.json     元信息（名称、作者、简介、时间）
        clues.json       线索库
        chain.json       谜题链结构（对应 core.chain）
        assets/          该工程的素材

对外接口
--------
    Project.create(name, root, ...) -> Project
    Project.open(root) -> Project
    Project.save() -> None
    Project.add_clue(...) / update_clue(...) / remove_clue(...)
    Project.find_clues(keyword=..., tag=...) -> list[Clue]
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

PROJECT_FILE = "project.json"
CLUES_FILE = "clues.json"
CHAIN_FILE = "chain.json"
ASSETS_DIR = "assets"

#: 工程文件格式版本，将来结构变更时用于迁移
FORMAT_VERSION = 1


class ProjectError(Exception):
    """工程读写相关的错误。"""


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _new_id() -> str:
    return uuid.uuid4().hex[:8]


def _write_json(path: Path, payload: object) -> None:
    """原子写：先写临时文件再替换，避免中途失败损坏工程。"""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    tmp.replace(path)


def _read_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ProjectError(f"缺少文件：{path}") from None
    except json.JSONDecodeError as e:
        raise ProjectError(f"{path.name} 不是合法 JSON：{e}") from None


# ============================================================ 线索


@dataclass
class Clue:
    """一条线索。"""

    id: str = field(default_factory=_new_id)
    title: str = ""
    content: str = ""
    #: 来源：哪个平台 / 哪个文件 / 哪次对话
    source: str = ""
    tags: list[str] = field(default_factory=list)
    #: 关联的谜题节点 id（对应 core.chain.Node.id），可为空
    node_id: str = ""
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Clue":
        known = {f for f in cls.__dataclass_fields__}  # 忽略多余的旧字段
        return cls(**{k: v for k, v in data.items() if k in known})

    def matches(self, keyword: str, tag: str = "") -> bool:
        """关键词匹配标题 / 正文 / 来源 / 标签。"""
        if tag and tag not in self.tags:
            return False
        if not keyword:
            return True
        k = keyword.lower()
        haystack = " ".join([self.title, self.content, self.source, *self.tags])
        return k in haystack.lower()


# ============================================================ 工程


@dataclass
class Project:
    """一个 ARG 工程。"""

    name: str = "未命名工程"
    author: str = ""
    description: str = ""
    root: Path | None = None
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    clues: list[Clue] = field(default_factory=list)
    #: 是否已落盘（新建但尚未 save 的工程为 False）
    _saved: bool = False

    # ---------------------------------------------------------- 生命周期
    @classmethod
    def create(
        cls,
        name: str,
        root: str | Path,
        author: str = "",
        description: str = "",
    ) -> "Project":
        """新建工程并立即落盘。目标目录已存在且非空时报错。"""
        root = Path(root)
        if (root / PROJECT_FILE).exists():
            raise ProjectError(f"目录中已存在工程：{root}")
        if root.exists() and any(root.iterdir()):
            raise ProjectError(f"目录非空，请换一个位置：{root}")

        project = cls(name=name or "未命名工程", author=author,
                      description=description, root=root)
        project.save()
        return project

    @classmethod
    def open(cls, root: str | Path) -> "Project":
        """打开已有工程。"""
        root = Path(root)
        meta = _read_json(root / PROJECT_FILE)
        if not isinstance(meta, dict):
            raise ProjectError(f"{PROJECT_FILE} 内容不是对象")

        project = cls(
            name=meta.get("name", "未命名工程"),
            author=meta.get("author", ""),
            description=meta.get("description", ""),
            root=root,
            created_at=meta.get("created_at", _now()),
            updated_at=meta.get("updated_at", _now()),
        )

        clues_path = root / CLUES_FILE
        if clues_path.exists():
            data = _read_json(clues_path)
            raw = data.get("clues", []) if isinstance(data, dict) else []
            project.clues = [Clue.from_dict(c) for c in raw if isinstance(c, dict)]

        project._saved = True
        return project

    @classmethod
    def is_project(cls, root: str | Path) -> bool:
        """判断目录是否是一个工程根。"""
        return (Path(root) / PROJECT_FILE).is_file()

    def save(self) -> None:
        """写回全部工程文件。"""
        if self.root is None:
            raise ProjectError("工程尚未关联目录，无法保存")
        self.root.mkdir(parents=True, exist_ok=True)
        self.assets_dir.mkdir(parents=True, exist_ok=True)
        self.updated_at = _now()

        _write_json(
            self.root / PROJECT_FILE,
            {
                "format_version": FORMAT_VERSION,
                "name": self.name,
                "author": self.author,
                "description": self.description,
                "created_at": self.created_at,
                "updated_at": self.updated_at,
            },
        )
        _write_json(
            self.root / CLUES_FILE,
            {"clues": [c.to_dict() for c in self.clues]},
        )
        chain_path = self.root / CHAIN_FILE
        if not chain_path.exists():
            _write_json(chain_path, {"name": "未命名线路", "nodes": [], "links": []})

        self._saved = True

    @property
    def assets_dir(self) -> Path:
        if self.root is None:
            raise ProjectError("工程尚未关联目录")
        return self.root / ASSETS_DIR

    # ---------------------------------------------------------- 线索操作
    def add_clue(
        self,
        title: str = "",
        content: str = "",
        source: str = "",
        tags: list[str] | None = None,
        node_id: str = "",
    ) -> Clue:
        """新增一条线索（不自动落盘，由调用方决定何时 save）。"""
        clue = Clue(
            title=title,
            content=content,
            source=source,
            tags=[t.strip() for t in (tags or []) if t.strip()],
            node_id=node_id,
        )
        self.clues.append(clue)
        return clue

    def get_clue(self, clue_id: str) -> Clue | None:
        return next((c for c in self.clues if c.id == clue_id), None)

    def update_clue(self, clue_id: str, **fields: object) -> bool:
        """按字段更新线索。返回是否找到。"""
        clue = self.get_clue(clue_id)
        if clue is None:
            return False
        allowed = {"title", "content", "source", "tags", "node_id"}
        for k, v in fields.items():
            if k not in allowed:
                raise ProjectError(f"线索不支持修改字段：{k}")
            setattr(clue, k, v)
        return True

    def remove_clue(self, clue_id: str) -> bool:
        """删除线索。返回是否删掉了东西。"""
        before = len(self.clues)
        self.clues = [c for c in self.clues if c.id != clue_id]
        return len(self.clues) < before

    def find_clues(self, keyword: str = "", tag: str = "") -> list[Clue]:
        """按关键词 / 标签筛选。两者都为空时返回全部。"""
        return [c for c in self.clues if c.matches(keyword, tag)]

    def all_tags(self) -> list[str]:
        """全部标签，按出现次数降序。"""
        counts: dict[str, int] = {}
        for c in self.clues:
            for t in c.tags:
                counts[t] = counts.get(t, 0) + 1
        return sorted(counts, key=lambda t: (-counts[t], t))
