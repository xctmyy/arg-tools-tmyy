"""密码 / 编码 工具页。

规划能力：
- 经典替换密码：凯撒、ROT13、Atbash、维吉尼亚、栅栏、A1Z26、Playfair、书本密码
- 编码：Base16/32/64、摩斯、二进制、十六进制、Brainfuck / Ook
- 哈希：MD5、SHA 家族、CRC
- 自动识别：对输入串猜测可能的编码类型
- 双层联动：上层密文 -> 下层明文实时预览

实现入口：src/core/crypto.py
"""

from src.ui.pages.base import BasePage


class CryptoPage(BasePage):
    title = "密码 / 编码"
    description = "替换密码、Base/摩斯编码与哈希计算"
