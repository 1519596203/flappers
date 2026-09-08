# -*- coding: utf-8 -*-
"""
笨鸟先飞 - 素材模块
====================
所有皮肤与地图均用 pygame 绘图 API 程序化生成，零网络依赖。
同时提供可选的在线素材下载（CC0 / 公有领域），下载成功则优先使用。

作者: 元宝
"""

import os
import math
import random
import urllib.request

import pygame

# ---------------------------------------------------------------- 常量

# 预渲染动画帧数
FRAMES = 12

# 皮肤定义: id -> (显示名, 描述)
SKINS = {
    "bird": ("原始笨鸟", "经典的黄色圆胖小鸟"),
    "plane": ("战斗机", "银色机身 + 螺旋桨"),
    "eagle": ("白头海雕", "展翅翱翔的猛禽"),
    "rocket": ("火箭", "尾部喷射火焰"),
    "ufo": ("UFO 飞碟", "来自外星的绿色碟形飞行器"),
    "hero": ("超级英雄", "蓝色战衣 + 红色披风"),
    "bee": ("小蜜蜂", "黄黑条纹 + 高速振翅"),
    "phoenix": ("不死鸟", "燃烧的橙红凤凰"),
}

# 地图定义: id -> (显示名, 描述, 天空顶色, 天空底色, 地面色, 管道主色, 管道高光色)
MAPS = {
    "grassland": ("白天草原", "蓝天白云，绿草如茵",
                  (135, 206, 250), (224, 247, 250), (110, 190, 70),
                  (74, 158, 58), (124, 205, 96)),
    "desert": ("黄昏沙漠", "落日沙丘，仙人掌剪影",
               (255, 140, 60), (255, 215, 130), (222, 184, 110),
               (176, 106, 50), (222, 150, 80)),
    "nightcity": ("夜晚都市", "星空霓虹，城市剪影",
                  (14, 18, 48), (44, 42, 96), (30, 32, 60),
                  (58, 66, 130), (120, 130, 220)),
    "space": ("外太空", "深邃星空，紫色能量管道",
              (4, 4, 20), (24, 10, 48), (18, 12, 38),
              (96, 60, 190), (168, 120, 255)),
    "ocean": ("深海世界", "蓝色深海，气泡与海草",
              (8, 60, 130), (40, 150, 200), (30, 100, 140),
              (40, 130, 150), (110, 210, 220)),
    "snow": ("雪境", "飘雪的雪山之巅",
             (170, 190, 210), (235, 243, 250), (240, 246, 252),
             (130, 175, 205), (200, 230, 250)),
    "cyber": ("赛博朋克", "紫粉霓虹，数据网格",
              (24, 6, 44), (86, 20, 96), (40, 12, 60),
              (200, 40, 140), (80, 240, 240)),
    "volcano": ("火山地带", "岩浆翻涌，黑曜石管道",
                (60, 12, 12), (170, 60, 20), (48, 24, 20),
                (52, 40, 40), (240, 110, 30)),
}

# 地图装饰类型
DECOR_TYPES = {
    "grassland": "cloud",
    "desert": "dune",
    "nightcity": "star",
    "space": "star",
    "ocean": "bubble",
    "snow": "snow",
    "cyber": "grid",
    "volcano": "ember",
}

SKIN_ORDER = list(SKINS.keys())
MAP_ORDER = list(MAPS.keys())


# ---------------------------------------------------------------- 联网素材
# cache 目录：用户可从网上下载精灵图放进这里，自动注册为新皮肤
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

_extra_skins = {}  # 皮肤 id -> 本地图片路径


def discover_extra_skins():
    """扫描 cache 目录下的图片，注册为额外皮肤（id 形如 ext:xxx）。
    下载或手动放入图片后调用即可，不影响内置素材。"""
    _extra_skins.clear()
    # 先清除上一次发现的 ext: 条目，避免残留
    SKIN_ORDER[:] = [k for k in SKIN_ORDER if not k.startswith("ext:")]
    exts = (".png", ".jpg", ".jpeg", ".gif", ".bmp")
    for fn in sorted(os.listdir(CACHE_DIR)):
        low = fn.lower()
        if low.endswith(exts):
            base = os.path.splitext(fn)[0]
            key = "ext:" + base
            name = base.replace("_", " ").replace("-", " ").title()
            SKINS[key] = (name, "下载素材（来自网络）")
            SKIN_ORDER.append(key)
            _extra_skins[key] = os.path.join(CACHE_DIR, fn)


def download_image(url, name=None, timeout=30):
    """从网络下载一张图片到 cache 目录，返回本地路径。
    下载成功会自动注册为新皮肤；失败则抛出 urllib 异常，由调用方处理。"""
    if name is None:
        name = os.path.basename(url.split("?")[0])
        if not os.path.splitext(name)[1]:
            name += ".png"
    if os.path.splitext(name)[1].lower() not in (".png", ".jpg", ".jpeg", ".gif", ".bmp"):
        name += ".png"
    dest = os.path.join(CACHE_DIR, name)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = resp.read()
    with open(dest, "wb") as f:
        f.write(data)
    pygame.image.load(dest)  # 校验是合法图片
    discover_extra_skins()
    return dest


def get_extra_frame(path, scale=1.0):
    img = pygame.image.load(path)  # 加载 PNG/JPG 等；PNG 自带逐像素 alpha
    surf = pygame.transform.smoothscale(img, (SW, SH))
    if scale != 1.0:
        surf = pygame.transform.smoothscale(
            surf, (max(1, int(SW * scale)), max(1, int(SH * scale))))
    return surf


# 启动时自动发现已存在的下载素材
discover_extra_skins()


# ---------------------------------------------------------------- 工具

def _surf(w, h):
    """创建带 alpha 的透明画布"""
    return pygame.Surface((w, h), pygame.SRCALPHA)


def _vgrad(surf, top, bottom, h=None):
    """竖直渐变填充"""
    h = h or surf.get_height()
    w = surf.get_width()
    for y in range(h):
        t = y / max(h - 1, 1)
        c = (
            int(top[0] + (bottom[0] - top[0]) * t),
            int(top[1] + (bottom[1] - top[1]) * t),
            int(top[2] + (bottom[2] - top[2]) * t),
        )
        pygame.draw.line(surf, c, (0, y), (w, y))


def _lerp(a, b, t):
    return (int(a[0] + (b[0] - a[0]) * t),
            int(a[1] + (b[1] - a[1]) * t),
            int(a[2] + (b[2] - a[2]) * t))


# ---------------------------------------------------------------- 皮肤绘制
# 每个函数在 W x H 画布上绘制，phase 为 0~1 动画相位
# 约定画布尺寸 SW x SH

SW, SH = 68, 52


def _draw_bird(s, phase):
    """原始笨鸟"""
    body = (250, 210, 60)
    belly = (255, 240, 170)
    beak = (245, 140, 40)
    wing = (235, 180, 50)

    # 身体
    pygame.draw.ellipse(s, body, (10, 12, 42, 32))
    # 肚皮
    pygame.draw.ellipse(s, belly, (16, 26, 30, 18))
    # 尾巴
    pygame.draw.polygon(s, wing, [(12, 22), (2, 14), (2, 32)])
    # 翅膀（扇动）
    flap = math.sin(phase * math.tau)
    wy = 24 + int(flap * 8)
    pygame.draw.ellipse(s, wing, (16, wy - 4, 22, 13))
    pygame.draw.ellipse(s, (210, 160, 40), (16, wy - 4, 22, 13), 1)
    # 眼睛
    pygame.draw.circle(s, (255, 255, 255), (42, 22), 8)
    pygame.draw.circle(s, (40, 30, 20), (44, 22), 4)
    pygame.draw.circle(s, (255, 255, 255), (46, 20), 2)
    # 喙
    pygame.draw.polygon(s, beak, [(50, 26), (64, 30), (50, 34)])
    pygame.draw.polygon(s, (200, 100, 30), [(50, 30), (64, 30), (50, 34)])


def _draw_plane(s, phase):
    """战斗机"""
    body = (200, 208, 218)
    dark = (140, 150, 165)
    red = (215, 60, 55)

    # 机身
    pygame.draw.ellipse(s, body, (8, 18, 46, 20))
    pygame.draw.ellipse(s, dark, (8, 18, 46, 20), 2)
    # 机头
    pygame.draw.polygon(s, body, [(48, 20), (62, 28), (48, 36)])
    # 尾翼
    pygame.draw.polygon(s, red, [(10, 18), (4, 4), (18, 18)])
    pygame.draw.polygon(s, (170, 40, 38), [(10, 34), (4, 46), (18, 34)])
    # 主翼
    wy = 30 + int(math.sin(phase * math.tau) * 2)
    pygame.draw.polygon(s, (170, 180, 195), [(22, wy), (34, wy + 14), (40, wy)])
    # 驾驶舱
    pygame.draw.ellipse(s, (90, 170, 235), (34, 20, 14, 8))
    pygame.draw.ellipse(s, (200, 240, 255), (36, 21, 7, 4))
    # 螺旋桨（旋转）
    px, py = 8, 28
    a = phase * math.tau
    for k in (0, math.pi / 2):
        dx = math.cos(a + k) * 11
        dy = math.sin(a + k) * 11
        pygame.draw.line(s, (90, 95, 105), (px - dx, py - dy), (px + dx, py + dy), 3)
    pygame.draw.circle(s, (80, 85, 95), (px, py), 3)


def _draw_eagle(s, phase):
    """白头海雕"""
    body = (110, 72, 42)
    head_c = (250, 248, 242)
    beak_c = (250, 190, 60)

    flap = math.sin(phase * math.tau)
    # 双翼（大幅展开）
    for side in (-1, 1):
        wy = 26 + int(flap * 12 * (1 if side > 0 else -1) * 0.5)
        pts = [(34, 26),
               (34 + side * 30, wy - 6),
               (34 + side * 26, wy + 8),
               (34, 34)]
        pygame.draw.polygon(s, body, pts)
        pygame.draw.polygon(s, (80, 52, 30), pts, 1)
        # 翼尖羽毛
        pygame.draw.line(s, (70, 45, 26),
                         (34 + side * 26, wy + 2), (34 + side * 30, wy - 4), 2)
    # 身体
    pygame.draw.ellipse(s, body, (22, 16, 26, 26))
    # 头
    pygame.draw.circle(s, head_c, (48, 20), 10)
    # 喙
    pygame.draw.polygon(s, beak_c, [(56, 18), (68, 22), (56, 26)])
    # 眼
    pygame.draw.circle(s, (30, 25, 20), (50, 18), 3)
    # 尾羽
    pygame.draw.polygon(s, (95, 62, 36), [(20, 24), (4, 30), (20, 36)])


def _draw_rocket(s, phase):
    """火箭"""
    white = (240, 242, 248)
    red = (220, 70, 55)

    # 弹体
    pygame.draw.ellipse(s, white, (8, 16, 44, 22))
    pygame.draw.ellipse(s, (190, 195, 205), (8, 16, 44, 22), 2)
    # 头锥
    pygame.draw.polygon(s, red, [(42, 17), (62, 27), (42, 37)])
    # 舷窗
    pygame.draw.circle(s, (90, 170, 235), (34, 27), 7)
    pygame.draw.circle(s, (190, 230, 255), (32, 25), 3)
    # 尾鳍
    pygame.draw.polygon(s, red, [(12, 24), (2, 14), (14, 30)])
    pygame.draw.polygon(s, red, [(12, 30), (2, 42), (14, 36)])
    # 尾焰（跳动）
    f = 10 + int(abs(math.sin(phase * math.tau * 2)) * 10)
    for i, col in enumerate([(255, 220, 60), (255, 150, 40), (240, 80, 30)]):
        ln = f - i * 5
        if ln <= 2:
            continue
        pygame.draw.polygon(s, col, [
            (12, 26), (12 - ln, 27), (12, 28)])
    pygame.draw.ellipse(s, (255, 235, 120), (2, 22, 12, 10))


def _draw_ufo(s, phase):
    """UFO 飞碟"""
    green = (110, 215, 130)

    # 光晕
    glow_a = 40 + int(abs(math.sin(phase * math.tau)) * 40)
    glow = _surf(SW, SH)
    pygame.draw.ellipse(glow, (140, 255, 180, glow_a), (0, 24, SW, 24))
    s.blit(glow, (0, 0))
    # 穹顶
    pygame.draw.ellipse(s, (150, 230, 245), (22, 8, 26, 22))
    pygame.draw.ellipse(s, (220, 250, 255), (26, 11, 12, 8))
    # 碟身
    pygame.draw.ellipse(s, green, (4, 24, 60, 18))
    pygame.draw.ellipse(s, (80, 175, 100), (4, 24, 60, 18), 2)
    # 底部灯
    for i, x in enumerate(range(14, 56, 10)):
        on = (int(phase * 6) + i) % 3 == 0
        c = (255, 250, 140) if on else (200, 200, 160)
        pygame.draw.circle(s, c, (x, 38), 3)


def _draw_hero(s, phase):
    """超级英雄"""
    blue = (60, 110, 210)
    red = (215, 55, 55)
    skin = (245, 200, 165)

    # 披风（飘动）
    wave = math.sin(phase * math.tau) * 6
    pygame.draw.polygon(s, red, [
        (26, 22), (2, 10 + wave), (0, 30 + wave), (24, 36)])
    pygame.draw.polygon(s, (180, 40, 40), [
        (26, 22), (2, 10 + wave), (8, 20 + wave)])
    # 身体
    pygame.draw.ellipse(s, blue, (16, 16, 30, 26))
    # 胸前标志
    pygame.draw.polygon(s, (250, 210, 60), [(30, 26), (38, 22), (40, 30), (30, 33)])
    # 手臂前伸
    pygame.draw.ellipse(s, blue, (38, 20, 22, 10))
    pygame.draw.circle(s, (245, 200, 165), (60, 25), 6)
    # 头
    pygame.draw.circle(s, skin, (46, 18), 10)
    # 头发
    pygame.draw.arc(s, (40, 30, 30), (36, 8, 20, 18), math.pi, math.tau, 5)
    # 眼
    pygame.draw.circle(s, (30, 30, 40), (49, 17), 2)
    # 腰带
    pygame.draw.rect(s, red, (18, 36, 26, 5))


def _draw_bee(s, phase):
    """小蜜蜂"""
    yellow = (250, 205, 50)
    black = (45, 38, 32)

    # 翅膀（高速振翅）
    for side in (-1, 1):
        wy = 14 + int(abs(math.sin(phase * math.tau * 3)) * 8)
        ell = pygame.Surface((20, 14), pygame.SRCALPHA)
        pygame.draw.ellipse(ell, (230, 245, 255, 170), (0, 0, 20, 14))
        s.blit(ell, (26 + side * 4, wy))
    # 身体（黄黑条纹）
    pygame.draw.ellipse(s, yellow, (10, 20, 40, 24))
    for i, x in enumerate(range(16, 46, 9)):
        pygame.draw.rect(s, black, (x, 20, 5, 24))
    pygame.draw.ellipse(s, (45, 38, 32), (10, 20, 40, 24), 2)
    # 头
    pygame.draw.circle(s, black, (48, 30), 9)
    # 眼
    pygame.draw.circle(s, (255, 255, 255), (50, 28), 3)
    pygame.draw.circle(s, (30, 30, 30), (51, 28), 2)
    # 触角
    for dx in (-1, 1):
        pygame.draw.line(s, black, (50, 22), (52 + dx * 4, 12), 2)
        pygame.draw.circle(s, black, (52 + dx * 4, 11), 2)
    # 尾针
    pygame.draw.polygon(s, black, [(12, 28), (2, 32), (12, 36)])


def _draw_phoenix(s, phase):
    """不死鸟"""
    hot = (255, 170, 40)
    mid = (250, 100, 30)
    core = (255, 230, 90)

    flap = math.sin(phase * math.tau)
    # 火焰双翼
    for side in (-1, 1):
        wy = 26 + int(flap * 10 * side * 0.6)
        pts = [(30, 26), (30 + side * 32, wy - 10),
               (30 + side * 28, wy + 10), (30, 34)]
        pygame.draw.polygon(s, mid, pts)
        pygame.draw.polygon(s, hot, [
            (30, 27), (30 + side * 24, wy - 4), (30 + side * 20, wy + 6)])
    # 身体
    pygame.draw.ellipse(s, mid, (18, 14, 28, 28))
    pygame.draw.ellipse(s, hot, (20, 16, 24, 24))
    pygame.draw.ellipse(s, core, (24, 20, 14, 13))
    # 头
    pygame.draw.circle(s, core, (46, 18), 9)
    pygame.draw.polygon(s, (255, 190, 50), [(53, 16), (66, 21), (53, 24)])
    pygame.draw.circle(s, (120, 40, 20), (48, 16), 2)
    # 火焰长尾
    f = 12 + int(abs(math.sin(phase * math.tau * 2)) * 8)
    for i, col in enumerate([core, hot, mid]):
        ln = f - i * 6
        if ln <= 2:
            continue
        pygame.draw.polygon(s, col, [(18, 26), (18 - ln, 28), (18, 32)])


_SKIN_FUNCS = {
    "bird": _draw_bird,
    "plane": _draw_plane,
    "eagle": _draw_eagle,
    "rocket": _draw_rocket,
    "ufo": _draw_ufo,
    "hero": _draw_hero,
    "bee": _draw_bee,
    "phoenix": _draw_phoenix,
}

_skin_cache = {}


def get_skin_frames(skin_id, scale=1.0):
    """返回预渲染的皮肤动画帧列表（已缩放）"""
    key = (skin_id, round(scale, 2))
    if key in _skin_cache:
        return _skin_cache[key]

    # 下载的外部皮肤
    if skin_id in _extra_skins:
        base = get_extra_frame(_extra_skins[skin_id], scale)
        frames = [base for _ in range(FRAMES)]
        _skin_cache[key] = frames
        return frames

    fn = _SKIN_FUNCS.get(skin_id, _draw_bird)
    frames = []
    for i in range(FRAMES):
        s = _surf(SW, SH)
        fn(s, i / FRAMES)
        if scale != 1.0:
            s = pygame.transform.smoothscale(
                s, (max(1, int(SW * scale)), max(1, int(SH * scale))))
        frames.append(s)
    _skin_cache[key] = frames
    return frames


def get_skin_icon(skin_id, size=(72, 56)):
    """菜单用的静态图标（取动画中间帧）"""
    frames = get_skin_frames(skin_id)
    base = frames[0]
    return pygame.transform.smoothscale(base, size)


# ---------------------------------------------------------------- 地图背景

_bg_cache = {}


def build_background(map_id, w, h):
    """生成地图背景（天空渐变 + 静态装饰），并缓存"""
    key = (map_id, w, h)
    if key in _bg_cache:
        return _bg_cache[key]

    info = MAPS.get(map_id, MAPS["grassland"])
    _, _, top, bottom, ground, _, _ = info
    s = pygame.Surface((w, h))
    _vgrad(s, top, bottom)

    rnd = random.Random(hash(map_id) & 0xFFFF)
    decor = DECOR_TYPES.get(map_id, "cloud")

    if decor == "cloud":
        for _ in range(7):
            x, y = rnd.randint(0, w), rnd.randint(30, h // 2)
            r = rnd.randint(18, 34)
            for dx, dy, rr in ((0, 0, r), (r * 0.8, 4, r * 0.7), (-r * 0.8, 6, r * 0.6)):
                pygame.draw.circle(s, (255, 255, 255), (int(x + dx), int(y + dy)), int(rr))
    elif decor == "dune":
        # 远处沙丘
        for i in range(3):
            base = h // 2 + i * 26
            pts = [(0, base)]
            for x in range(0, w + 40, 40):
                pts.append((x, base - 22 * math.sin(x / 90.0 + i)))
            pts.append((w, h))
            pts.append((0, h))
            c = _lerp((230, 190, 120), (200, 150, 90), i / 2)
            pygame.draw.polygon(s, c, pts)
        # 太阳
        pygame.draw.circle(s, (255, 220, 150), (w - 90, 90), 46)
    elif decor == "star":
        for _ in range(90):
            x, y = rnd.randint(0, w), rnd.randint(0, int(h * 0.75))
            r = rnd.choice([1, 1, 1, 2, 2])
            a = rnd.randint(140, 255)
            pygame.draw.circle(s, (a, a, min(255, a + 20)), (x, y), r)
        if map_id == "nightcity":
            # 月亮
            pygame.draw.circle(s, (250, 246, 220), (w - 90, 80), 34)
            pygame.draw.circle(s, _lerp(bottom, top, 0.4), (w - 76, 70), 30)
            # 城市剪影
            x = 0
            while x < w:
                bw = rnd.randint(38, 74)
                bh = rnd.randint(70, 190)
                pygame.draw.rect(s, (22, 24, 52), (x, h - 120 - bh, bw, bh + 120))
                for wy in range(h - 110 - bh, h - 130, 14):
                    for wx in range(x + 6, x + bw - 6, 12):
                        if rnd.random() < 0.45:
                            pygame.draw.rect(s, (255, 220, 130), (wx, wy, 5, 7))
                x += bw + 4
    elif decor == "bubble":
        for _ in range(40):
            x, y = rnd.randint(0, w), rnd.randint(0, h)
            r = rnd.randint(3, 11)
            pygame.draw.circle(s, (190, 235, 250, 90), (x, y), r, 1)
    elif decor == "snow":
        for _ in range(60):
            x, y = rnd.randint(0, w), rnd.randint(0, h)
            r = rnd.randint(2, 5)
            pygame.draw.circle(s, (255, 255, 255), (x, y), r)
        # 远处雪山
        pts = [(0, h - 130)]
        for x in range(0, w + 60, 60):
            pts.append((x, h - 130 - 70 * abs(math.sin(x / 130.0))))
        pts += [(w, h), (0, h)]
        pygame.draw.polygon(s, (215, 228, 240), pts)
    elif decor == "grid":
        # 透视网格
        horizon = int(h * 0.62)
        for i in range(0, w + 1, 46):
            pygame.draw.line(s, (150, 60, 190), (i, horizon), (i, h), 1)
        y = horizon
        step = 4
        while y < h:
            pygame.draw.line(s, (190, 70, 200), (0, y), (w, y), 1)
            step *= 1.5
            y += step
        # 霓虹太阳
        pygame.draw.circle(s, (255, 90, 180), (w // 2, horizon - 40), 60)
        for r in range(60, 20, -10):
            pygame.draw.circle(s, (60, 20, 90), (w // 2, horizon - 40), r)
    elif decor == "ember":
        for _ in range(45):
            x, y = rnd.randint(0, w), rnd.randint(0, h)
            r = rnd.randint(2, 6)
            c = rnd.choice([(255, 150, 40), (255, 90, 20), (200, 60, 20)])
            pygame.draw.circle(s, c, (x, y), r)
        # 火山剪影
        for vx, vw, vh in ((60, 160, 150), (w - 200, 190, 180)):
            pygame.draw.polygon(s, (42, 26, 24),
                                [(vx, h), (vx + vw // 2, h - vh), (vx + vw, h)])
            pygame.draw.polygon(s, (255, 120, 40),
                                [(vx + vw // 2 - 16, h - vh + 8),
                                 (vx + vw // 2, h - vh - 18),
                                 (vx + vw // 2 + 16, h - vh + 8)])

    _bg_cache[key] = s
    return s


def get_ground(map_id):
    info = MAPS.get(map_id, MAPS["grassland"])
    return info[4]


def get_pipe_colors(map_id):
    info = MAPS.get(map_id, MAPS["grassland"])
    return info[5], info[6]


def draw_pipe(s, map_id, x, y, w, h, is_top, colors=None):
    """绘制管道段落（在 (x,y) 处，宽 w 高 h）

    colors: 可选的 (body_c, hi_c) 覆盖配色，用于换地图时的色彩过渡插值；
            不传则按 map_id 取默认配色。
    """
    body_c, hi_c = colors if colors else get_pipe_colors(map_id)
    pygame.draw.rect(s, body_c, (x, y, w, h))
    # 高光
    pygame.draw.rect(s, hi_c, (x + 4, y, 8, h))
    # 暗部
    pygame.draw.rect(s, tuple(max(0, c - 40) for c in body_c),
                     (x + w - 12, y, 8, h))
    # 边框
    pygame.draw.rect(s, tuple(max(0, c - 70) for c in body_c), (x, y, w, h), 3)

    # 管帽
    cap_h = 26
    cap_w = w + 12
    cap_x = x - 6
    cap_y = (y + h - cap_h) if is_top else y
    pygame.draw.rect(s, body_c, (cap_x, cap_y, cap_w, cap_h))
    pygame.draw.rect(s, hi_c, (cap_x + 4, cap_y + 3, 10, cap_h - 6))
    pygame.draw.rect(s, tuple(max(0, c - 70) for c in body_c),
                     (cap_x, cap_y, cap_w, cap_h), 3)
