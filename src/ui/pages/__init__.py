"""功能页面包。

新增页面三步：
  1. 在本目录新建 xxx_page.py，定义继承 BasePage 的类；
  2. 在下面 import 并登记进 PAGES；
  3. 完成。主窗口会自动生成导航按钮与内容区。
"""

from __future__ import annotations

from src.ui.pages.analysis_page import AnalysisPage
from src.ui.pages.base import BasePage
from src.ui.pages.chain_page import ChainPage
from src.ui.pages.crypto_page import CryptoPage
from src.ui.pages.media_page import MediaPage
from src.ui.pages.project_page import ProjectPage
from src.ui.pages.stego_page import StegoPage

# 顺序即侧边栏顺序
PAGES: dict[str, BasePage] = {
    "project": ProjectPage(),
    "crypto": CryptoPage(),
    "stego": StegoPage(),
    "media": MediaPage(),
    "analysis": AnalysisPage(),
    "chain": ChainPage(),
}

__all__ = ["PAGES", "BasePage"]
