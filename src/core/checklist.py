"""试玩与设计审查清单。

规划：把"一个好 ARG 该有的东西"变成可勾选项，逐条自查。

分组（对应 doc/ARG工具调研.md 第 6 节）：
    narrative   叙事与沉浸感：TINAG、游戏外边界、角色一致性
    puzzle      谜题质量：难度曲线、线索冗余、无死胡同
    platform    平台与分发：入口可达、跨平台衔接、账号准备
    operation   运营：玩家社区、进度追踪、应急预案
    legal       合规：隐私、版权、伦理红线

统一对外接口（待实现）：
    load_checklist(group) -> list[Item]
    run_audit(project) -> AuditReport
"""

from __future__ import annotations

from dataclasses import dataclass

GROUPS: tuple[str, ...] = ("narrative", "puzzle", "platform", "operation", "legal")


@dataclass
class Item:
    """一条审查项。"""

    group: str
    text: str
    passed: bool = False
    note: str = ""


def load_checklist(group: str) -> list[Item]:
    """加载某一分组的清单项。"""
    raise NotImplementedError("load_checklist 尚未实现")


def run_audit(project: object) -> dict:
    """对工程跑一遍全量审查，返回分组结果。"""
    raise NotImplementedError("run_audit 尚未实现")
