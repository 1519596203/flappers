# -*- coding: utf-8 -*-
"""
笨鸟先飞 - 素材下载器
========================
把网上的精灵图下载到 cache/ 目录，游戏会自动把它们注册成新皮肤。

用法:
    python download_packs.py            # 下载内置的 CC0 开源精灵包
    python download_packs.py <URL>      # 下载指定图片并自动命名
    python download_packs.py <URL> 名字  # 指定保存文件名

注意:
    - 图片只要是常见格式（png/jpg/gif/bmp）即可，会自动缩放到皮肤尺寸
    - 推荐 CC0 / 公有领域素材站: kenney.nl、opengameart.org、craftpix.net
    - 下载失败不影响内置的 8 个程序化皮肤
"""

import os
import sys

import assets

# 内置开源精灵包（来自 Flappy Bird 克隆常用素材，MIT 许可，可自由使用）
REPO = "https://raw.githubusercontent.com/samuelcust/flappy-bird-assets/master/sprites"
SOURCES = [
    (f"{REPO}/yellowbird-midflap.png", "yellowbird.png"),
    (f"{REPO}/redbird-midflap.png", "redbird.png"),
    (f"{REPO}/bluebird-midflap.png", "bluebird.png"),
]


def main():
    args = sys.argv[1:]
    jobs = []

    if not args:
        jobs = list(SOURCES)
        print("== 下载内置开源精灵包 ==")
    elif len(args) == 1:
        jobs = [(args[0], None)]
        print("== 下载指定链接 ==")
    else:
        jobs = [(args[0], args[1])]
        print("== 下载指定链接（自定义文件名）==")

    ok, fail = 0, 0
    for url, name in jobs:
        try:
            dest = assets.download_image(url, name)
            print(f"  [OK] {os.path.basename(dest)}")
            ok += 1
        except Exception as e:
            print(f"  [失败] {url}\n        原因: {e}")
            fail += 1

    print(f"\n完成: 成功 {ok} 个, 失败 {fail} 个")
    print(f"缓存目录: {assets.CACHE_DIR}")
    if ok:
        print("重新启动游戏即可在选择皮肤里看到新下载的皮肤。")


if __name__ == "__main__":
    main()
