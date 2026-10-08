"""项目 / 线索管理页。

规划能力：
- 新建、打开、保存 ARG 工程（统一存到 data/ 下，JSON 或 SQLite）
- 线索库（clue）与谜题节点（node）的增删改查
- 谜题链概览：当前进度、待验证的节点
- 导入 / 导出工程包，便于协作

实现入口：src/core/store.py
"""

from src.ui.pages.base import BasePage


class ProjectPage(BasePage):
    title = "项目"
    description = "工程管理、线索库与整体进度"
