"""文件与网络分析页。

规划能力：
- 文件：十六进制查看、文件类型识别、嵌套压缩包 / 附加数据提取（类 binwalk）
- 元数据：EXIF、PDF / Office 属性
- 网络：URL / 域名信息查询、网页历史快照、HTTP 请求调试
- 文本：字符串提取、编码嗅探

实现入口：src/core/analysis.py
"""

from src.ui.pages.base import BasePage


class AnalysisPage(BasePage):
    title = "文件 / 网络"
    description = "二进制分析、元数据提取与网络线索查询"
