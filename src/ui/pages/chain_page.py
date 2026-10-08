"""谜题链 / 叙事地图页。

规划能力：
- 以节点图的形式编排"谜题链"：入口(trailhead) -> 谜题 -> 连接器 -> 下一关
- 每个节点的产出自动成为下一节点的输入，做链路连通性校验
- 难度标定（1-5）与节奏视图，检查整条线的难度曲线
- 试玩清单 / TINAG 一致性审查（沉浸感、游戏外边界）

实现入口：src/core/chain.py + src/core/checklist.py
"""

from src.ui.pages.base import BasePage


class ChainPage(BasePage):
    title = "谜题链"
    description = "叙事地图、节点编排与试玩审查"
