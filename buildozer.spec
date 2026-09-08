# -*- coding: utf-8 -*-
# buildozer 配置文件（python-for-android 打包 pygame 游戏为 Android APK）
# 用法：buildozer android debug    （生成 bin/sillybird-1.0-debug.apk）

[app]
# 应用名（显示在桌面）
title = 笨鸟先飞
source.dir = .
# 包名（必须全英文小写，dot 分隔；最终包名 = package.domain.package.name）
package.name = sillybird
package.domain = com.workbuddy

# 主入口（必须和当前目录的 main.py 对应）
source.filename = main.py
source.main = main.py

# 打包时包含的文件类型 + 排除的垃圾（cache 是下载/合成的运行时产物）
source.include_exts = py,png,jpg,kv,atlas,json,wav,mp3
source.exclude_patterns = cache/*,.git/*,.github/*,tests/*,_regress.py,download_packs.py,make_shortcut.py,launch.bat,start.bat,icon.ico,*.lnk,preview_*.png,*.md,__pycache__/*,*.pyc

# 版本
version = 1.0
version.code = 1

# 关键依赖：python3 + pygame（p4a 走 SDL2 bootstrap）
# pygame 必须是 2.1.3+ 才稳定支持 Android；kivy 是 p4a SDL2 bootstrap 的强制依赖
requirements = python3==3.11.6, pygame==2.5.2, kivy==2.3.0

# 屏幕方向（全屏竖屏，跟原版 480x720 比例一致）
orientation = portrait
fullscreen = 1
android.presplash_color = #1a1d2e

# 权限：纯单机游戏，不需要网络
android.permissions =

# 最低 API 21 (Android 5.0)，编译 API 33
android.api = 33
android.minapi = 21
android.accept_sdk_license = True
android.private_mode = True

# 启动画面（可用 ICO 或 PNG；先省略，避免依赖额外资源）
# android.presplash.lottie = ...
# icon.filename = %(source.dir)s/icon.png

# 不打 logcat 刷屏
log_level = 2

[buildozer]
# 加快二次构建：p4a 用 ~/.gradle 缓存
android.gradle_dependencies = 

# 调试模式：APK 包含 Python 解释器源码；发布版应该用 release
# (这里先给 debug，方便快速验证；正式发布用 android release)
