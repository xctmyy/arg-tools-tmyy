"""谜题链 / 叙事地图。

核心模型（待实现）：

    Node     一个谜题节点：类型、难度、输入、输出、所在平台
    Link     连接器：上一个节点的 output 即下一个节点的 input
    Chain    整条线路：校验连通性、检测断点与死循环、输出难度曲线

规划接口：
    Chain.validate() -> list[str]          # 返回问题列表
    Chain.difficulty_curve() -> list[int]  # 难度曲线
    Chain.export_dot(path) -> Path         # 导出为图，便于可视化
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Node:
    """一个谜题节点。"""

    id: str
    title: str = ""
    #: 载体类型：text / image / audio / video / file / website / offline
    carrier: str = "text"
    #: 隐藏 / 加密手法标识，对应 crypto.CAPABILITIES 或 stego.CAPABILITIES
    method: str = ""
    #: 难度 1-5
    difficulty: int = 1
    #: 本节点产出的内容（作为下一节点的输入）
    output: str = ""
    #: 承载平台：discord / telegram / youtube / website / phone ...
    platform: str = ""


@dataclass
class Chain:
    """一条谜题链。"""

    name: str = "未命名线路"
    nodes: list[Node] = field(default_factory=list)
    #: (from_node_id, to_node_id)
    links: list[tuple[str, str]] = field(default_factory=list)

    def validate(self) -> list[str]:
        """检查连通性、孤立节点、输出/输入是否对得上。"""
        raise NotImplementedError("Chain.validate 尚未实现")

    def difficulty_curve(self) -> list[int]:
        """按链路顺序返回难度序列。"""
        raise NotImplementedError("Chain.difficulty_curve 尚未实现")
