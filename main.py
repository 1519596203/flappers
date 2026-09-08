# -*- coding: utf-8 -*-
"""
笨鸟先飞 - Android 打包入口
============================
把当前目录加入 sys.path（buildozer/p4a 打包后脚本不在标准 site-packages 里），
然后调用 game.Game().run() 启动游戏。
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

# Android 上没有鼠标光标，禁掉；桌面端仍保留（hover 高亮用）
if "ANDROID_APP_PATH" in os.environ or os.path.exists("/sdcard"):
    try:
        os.environ.setdefault("SDL_HIDDEN_CURSOR", "1")
    except Exception:
        pass

import game  # noqa: E402


def main():
    g = game.Game()
    g.run()


if __name__ == "__main__":
    main()
