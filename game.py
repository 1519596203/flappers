# -*- coding: utf-8 -*-
"""
笨鸟先飞 (Silly Bird First Fly)
================================
一个 Flappy Bird 风格的 Python 小游戏。
8 种皮肤 × 8 张地图，全部素材程序化生成。

操作:
  菜单    : 鼠标点击 ◀ ▶ 或 左右方向键 / A D   切换皮肤
            鼠标点击 ◀ ▶ 或 上下方向键 / W S   切换地图
            点击「开始游戏」 / 空格  开始
            右侧栏「退出游戏」按钮 / 窗口关闭  退出程序
  游戏中  : 空格 / 上箭头 / 鼠标点击  拍翅上升
             P   暂停
  结束后  : 空格 / 鼠标点击  再来一局
             M    返回菜单
  任意态  : ESC  回到选皮肤菜单（不退出程序）
            每得 10 分自动更换一次地图背景

作者: 元宝
"""

import os
import sys
import json
import random
import math

import pygame

import assets
import soundfx as sfx

# ---------------------------------------------------------------- 配置

# 世界(游戏区)宽度保持 480；窗口额外加右侧 240px 的常驻侧栏
# 用于展示「历史分数 / 排名」，游戏区和玩法逻辑完全不变
WIDTH, HEIGHT = 480, 720
SIDEBAR_W = 240
WIN_W = WIDTH + SIDEBAR_W      # 720
FPS = 60

GRAVITY = 0.55
JUMP_V = -9.2
PIPE_W = 74
PIPE_GAP = 178
PIPE_SPEED = 3.1
PIPE_SPACING = 232
GROUND_H = 96

BIRD_X = 132
BIRD_SCALE = 0.78

SAVE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "save.json")

STATE_MENU = "menu"
STATE_PLAY = "play"
STATE_OVER = "over"


# ---------------------------------------------------------------- 字体

_font_cache = {}


def get_font(size, bold=False):
    key = (size, bold)
    if key in _font_cache:
        return _font_cache[key]
    names = ["Microsoft YaHei", "微软雅黑", "SimHei", "黑体",
             "DengXian", "SimSun", "NSimSun"]
    font = None
    for n in names:
        try:
            f = pygame.font.SysFont(n, size, bold=bold)
            if f is not None:
                font = f
                break
        except Exception:
            continue
    if font is None:
        font = pygame.font.Font(None, size)
    _font_cache[key] = font
    return font


def text(surf, s, size, color, x, y, bold=False, center=False, shadow=None):
    f = get_font(size, bold)
    if shadow:
        sf = f.render(s, True, shadow)
        r = sf.get_rect()
        if center:
            r.center = (x + 2, y + 2)
        else:
            r.topleft = (x + 2, y + 2)
        surf.blit(sf, r)
    img = f.render(s, True, color)
    r = img.get_rect()
    if center:
        r.center = (x, y)
    else:
        r.topleft = (x, y)
    surf.blit(img, r)
    return r


# ---------------------------------------------------------------- 游戏主体

class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("笨鸟先飞 - Silly Bird")
        self.screen = pygame.display.set_mode((WIN_W, HEIGHT))
        self.clock = pygame.time.Clock()

        # 图标
        try:
            ico = assets.get_skin_icon("bird", (32, 32))
            pygame.display.set_icon(ico)
        except Exception:
            pass

        self.skin_idx = 0
        self.map_idx = 0
        assets.discover_extra_skins()  # 载入 cache/ 下已下载的外部皮肤
        self.best = self._load()
        self.state = STATE_MENU
        self.paused = False
        self.frame = 0
        self.map_changed = False   # 本局是否已因「每 10 分换图」切换过背景
        self.music_on = False      # 背景音乐开关
        self.sfx_muted = False     # 一次性音效静音开关
        self.reset()
        sfx.music_start()          # 尝试自动播放背景电子乐（无声卡时静默）
        self.music_on = sfx.music_on()
        self.sfx_muted = sfx.sfx_is_muted()

    # ------------------------------------------------ 存档
    def _load(self):
        try:
            if os.path.exists(SAVE_FILE):
                with open(SAVE_FILE, "r", encoding="utf-8") as f:
                    d = json.load(f)
                    self.history = [int(x) for x in d.get("history", [])]
                    return int(d.get("best", 0))
        except Exception:
            pass
        self.history = []
        return 0

    def _save(self):
        try:
            with open(SAVE_FILE, "w", encoding="utf-8") as f:
                json.dump({"best": self.best, "history": self.history[:100]}, f)
        except Exception:
            pass

    def _record_score(self, score):
        """记录一局的分数到历史，并更新最高分。"""
        self.history.append(score)
        if score > self.best:
            self.best = score
        self._save()

    # ------------------------------------------------ 状态
    @property
    def skin_id(self):
        return assets.SKIN_ORDER[self.skin_idx]

    @property
    def map_id(self):
        return assets.MAP_ORDER[self.map_idx]

    def reset(self):
        self.bird_y = HEIGHT * 0.42
        self.bird_v = 0.0
        self.pipes = []
        self.score = 0
        self.passed = set()
        self.pipe_seq = 0
        self.ground_x = 0
        self.dead_t = 0
        self.anim = 0.0
        self.spawn_x = WIDTH + 80
        self._is_new_record = False     # 本局是否刷新历史最高
        self._start_best = self.best    # 本局开局时的最高纪录（用于判定是否破纪录）
        self._fireworks = []            # 破纪录烟花粒子
        self._mapfade = None            # 换地图的淡入淡出过渡状态
        for i in range(3):
            self._spawn_pipe(WIDTH + 120 + i * PIPE_SPACING)
        self.bg = assets.build_background(self.map_id, WIDTH, HEIGHT)

    # ---------------- 换地图的淡入淡出过渡 ----------------
    MAPFADE_FRAMES = 48   # 过渡时长（帧），48 帧 @60fps ≈ 0.8 秒

    def _start_mapfade(self, old_map_id):
        """记录旧地图的背景/地面/管道色，开启一次交叉淡入过渡。

        注意：必须在 self.bg 已经被替换为新图**之后**调用，因为我们要从缓存里
        重新取旧图作为过渡的「底层」不透明背景。
        """
        self._mapfade = {
            "old_bg": assets.build_background(old_map_id, WIDTH, HEIGHT),  # 旧背景（缓存命中，几乎不耗时）
            "old_ground": assets.get_ground(old_map_id),        # 旧地面色
            "old_pipe": assets.get_pipe_colors(old_map_id),     # 旧管道 (body, hi)
            "t": 0,
            "dur": self.MAPFADE_FRAMES,
        }

    def _mapfade_k(self):
        """返回过渡进度 0.0~1.0；无过渡时返回 1.0（即完全新地图）。"""
        if not self._mapfade:
            return 1.0
        return min(1.0, self._mapfade["t"] / float(self._mapfade["dur"]))

    def _update_mapfade(self):
        if not self._mapfade:
            return
        self._mapfade["t"] += 1
        if self._mapfade["t"] >= self._mapfade["dur"]:
            self._mapfade = None    # 过渡结束，完全切到新地图

    def _cur_ground_color(self):
        """当前地面色（换图过渡期间为新旧线性插值）。"""
        new_c = assets.get_ground(self.map_id)
        if not self._mapfade:
            return new_c
        k = self._mapfade_k()
        old_c = self._mapfade["old_ground"]
        return tuple(int(old_c[i] + (new_c[i] - old_c[i]) * k) for i in range(3))

    def _cur_pipe_colors(self):
        """当前管道配色 (body, hi)，过渡期间线性插值。"""
        new_p = assets.get_pipe_colors(self.map_id)
        if not self._mapfade:
            return new_p
        k = self._mapfade_k()
        old_p = self._mapfade["old_pipe"]
        def mix(a, b):
            return tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3))
        return (mix(old_p[0], new_p[0]), mix(old_p[1], new_p[1]))

    def _spawn_pipe(self, x):
        top_min = 70
        top_max = HEIGHT - GROUND_H - PIPE_GAP - 90
        top_h = random.randint(int(top_min), int(max(top_min + 10, top_max)))
        # id 用单调递增的计数器，绝不复用 —— 否则管道被回收后新 id 会与
        # self.passed 里已记录过的 id 撞车，导致计分永久卡住
        self.pipe_seq += 1
        self.pipes.append({"x": x, "top": top_h, "id": self.pipe_seq})

    # ------------------------------------------------ 事件
    def handle(self):
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return False
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_b:   # 开关背景音乐
                    if self.music_on:
                        sfx.music_stop()
                        self.music_on = False
                    else:
                        sfx.music_start()
                        self.music_on = sfx.music_on()
                elif ev.key == pygame.K_ESCAPE:
                    # ESC 不再退出程序，一律回到选皮肤/选图菜单
                    if self.state != STATE_MENU:
                        self.state = STATE_MENU
                        self.reset()
                    self.paused = False
                elif self.state == STATE_MENU:
                    self._menu_key(ev.key)
                elif self.state == STATE_PLAY:
                    if ev.key in (pygame.K_SPACE, pygame.K_UP, pygame.K_RETURN):
                        self.jump()
                    elif ev.key == pygame.K_p:
                        self.paused = not self.paused
                elif self.state == STATE_OVER:
                    if ev.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_UP):
                        self.state = STATE_PLAY
                        self.reset()
                    elif ev.key == pygame.K_m:
                        self.state = STATE_MENU
                        self.reset()
            if ev.type == pygame.MOUSEBUTTONDOWN:
                mx, my = ev.pos
                # 右侧栏（仅菜单态有退出按钮）
                if mx >= WIDTH:
                    hit_side = self._sidebar_hit(mx, my)
                    if self.state == STATE_MENU and hit_side == "quit":
                        return False
                    continue
                # 角落小按钮（音效/音乐/暂停/菜单）—— 优先级最高，避免误触发跳跃
                hit_corner = self._corner_hit(mx, my)
                if hit_corner == "sfx":
                    self.sfx_muted = sfx.sfx_toggle()
                    continue
                elif hit_corner == "music":
                    if sfx.music_on():
                        sfx.music_stop()
                        self.music_on = False
                    else:
                        sfx.music_start()
                        self.music_on = sfx.music_on()
                    continue
                elif hit_corner == "pause" and self.state == STATE_PLAY:
                    self.paused = not self.paused
                    continue
                elif hit_corner == "menu":
                    # 任意态：返回选皮肤菜单（与 ESC/M 键等效）
                    if self.state != STATE_MENU:
                        self.state = STATE_MENU
                        self.reset()
                        self.paused = False
                    continue
                if self.state == STATE_MENU:
                    hit = self._menu_hit(mx, my)
                    if hit:
                        self._apply_menu_action(hit)
                    else:
                        # 点空白处也直接开始游戏（保留原体验）
                        self.state = STATE_PLAY
                        self.reset()
                elif self.state == STATE_PLAY and not self.paused:
                    self.jump()
                elif self.state == STATE_OVER:
                    self.state = STATE_PLAY
                    self.reset()
        return True

    def _menu_key(self, key):
        n_s = len(assets.SKIN_ORDER)
        n_m = len(assets.MAP_ORDER)
        if key in (pygame.K_LEFT, pygame.K_a):
            self.skin_idx = (self.skin_idx - 1) % n_s
        elif key in (pygame.K_RIGHT, pygame.K_d):
            self.skin_idx = (self.skin_idx + 1) % n_s
        elif key in (pygame.K_UP, pygame.K_w):
            self.map_idx = (self.map_idx - 1) % n_m
        elif key in (pygame.K_DOWN, pygame.K_s):
            self.map_idx = (self.map_idx + 1) % n_m
        elif key in (pygame.K_SPACE, pygame.K_RETURN):
            self.state = STATE_PLAY
            self.reset()
        if key in (pygame.K_UP, pygame.K_DOWN, pygame.K_w, pygame.K_s):
            self.reset()

    # ---------------- 菜单鼠标操作（皮肤 / 地图切换）
    def skin_prev(self):
        self.skin_idx = (self.skin_idx - 1) % len(assets.SKIN_ORDER)

    def skin_next(self):
        self.skin_idx = (self.skin_idx + 1) % len(assets.SKIN_ORDER)

    def map_prev(self):
        self.map_idx = (self.map_idx - 1) % len(assets.MAP_ORDER)
        self.reset()  # 换地图背景立即刷新预览

    def map_next(self):
        self.map_idx = (self.map_idx + 1) % len(assets.MAP_ORDER)
        self.reset()

    # 四个可点击切换按钮的中心坐标（须与 _draw_menu 中绘制的按钮一致）
    def _menu_btn_centers(self):
        sy, my = 150, 336
        return {
            "skin_prev": (62, sy + 74),
            "skin_next": (WIDTH - 62, sy + 74),
            "map_prev": (62, my + 70),
            "map_next": (WIDTH - 62, my + 70),
        }

    def _menu_hit(self, mx, my):
        """命中某个切换按钮则返回动作名；命中开始按钮返回 'start'；否则返回 None"""
        r = 40  # 按钮命中半径，略大于圆形按钮视觉尺寸，方便点击
        for action, (cx, cy) in self._menu_btn_centers().items():
            if (mx - cx) ** 2 + (my - cy) ** 2 <= r * r:
                return action
        # 开始按钮矩形（WIDTH//2-110, 582, 220, 56）
        br = pygame.Rect(WIDTH // 2 - 110, 582, 220, 56)
        if br.collidepoint(mx, my):
            return "start"
        return None

    def _apply_menu_action(self, action):
        if action == "skin_prev":
            self.skin_prev()
        elif action == "skin_next":
            self.skin_next()
        elif action == "map_prev":
            self.map_prev()
        elif action == "map_next":
            self.map_next()
        elif action == "start":
            self.state = STATE_PLAY
            self.reset()

    # 右侧栏退出按钮（菜单和结束态都有）
    def _sidebar_hit(self, mx, my):
        if self.state in (STATE_MENU, STATE_OVER):
            qr = pygame.Rect(WIDTH + 40, HEIGHT - 74, SIDEBAR_W - 80, 52)
            if qr.collidepoint(mx, my):
                return "quit"
        return None

    # ---------------- 左下角小按钮（音效 / 音乐 开关）----------------
    _CORNER_POS = {"sfx": (32, HEIGHT - 32), "music": (84, HEIGHT - 32)}
    # ---------------- 右下角虚拟按钮（仅 PLAY/OVER，手机用）----------------
    _RIGHT_POS = {"pause": (WIDTH - 84, HEIGHT - 32),
                  "menu":  (WIDTH - 32, HEIGHT - 32)}
    _CORNER_R = 18  # 视觉圆半径
    _CORNER_HIT_R = 22  # 命中半径略大，方便点击

    def _corner_hit(self, mx, my):
        """返回被点中的角落按钮名：'sfx' / 'music' / 'pause' / 'menu' / None。
        左下角（音/乐）全状态可点；右下角（暂停/菜单）仅 PLAY/OVER 可见。"""
        all_pos = dict(self._CORNER_POS)
        if self.state in (STATE_PLAY, STATE_OVER):
            all_pos.update(self._RIGHT_POS)
        for name, (cx, cy) in all_pos.items():
            if (mx - cx) ** 2 + (my - cy) ** 2 <= self._CORNER_HIT_R ** 2:
                return name
        return None

    def _draw_corner_buttons(self):
        """左下角两个小圆形按钮：音效开关 + 音乐开关。三态（菜单/游戏中/结束）都可见。"""
        # 取鼠标位置（dummy/无头环境下 mouse 未初始化时退化为 (0,0)）
        try:
            mx, my = pygame.mouse.get_pos()
        except Exception:
            mx, my = -9999, -9999
        # ---- 左下角：音 / 乐（所有状态）----
        for name, (cx, cy) in self._CORNER_POS.items():
            if name == "sfx":
                on = not sfx.sfx_is_muted()
                base = (90, 180, 100) if on else (160, 80, 80)
                label = "音"
            else:  # music
                on = sfx.music_on()
                base = (90, 180, 100) if on else (160, 80, 80)
                label = "乐"
            self._draw_round_button(cx, cy, base, label, mx, my)
        # ---- 右下角：暂停 / 回菜单（仅 PLAY/OVER）----
        if self.state in (STATE_PLAY, STATE_OVER):
            for name, (cx, cy) in self._RIGHT_POS.items():
                if name == "pause":
                    base = (90, 140, 200)               # 蓝色系
                    label = "‖"                          # 暂停符号
                else:  # menu
                    base = (170, 130, 70)                # 橙黄系
                    label = "≡"                          # 菜单符号
                self._draw_round_button(cx, cy, base, label, mx, my)

    def _draw_round_button(self, cx, cy, base, label, mx, my):
        """画一个统一的圆角按钮（半透明底+白描边+中心字+hover 加亮）。"""
        hover = (mx - cx) ** 2 + (my - cy) ** 2 <= self._CORNER_HIT_R ** 2
        col = tuple(min(255, c + 30) for c in base) if hover else base
        s = pygame.Surface((self._CORNER_R * 2 + 4,
                            self._CORNER_R * 2 + 4), pygame.SRCALPHA)
        pygame.draw.circle(s, (*col, 220),
                           (self._CORNER_R + 2, self._CORNER_R + 2),
                           self._CORNER_R)
        self.screen.blit(s, (cx - self._CORNER_R - 2, cy - self._CORNER_R - 2))
        pygame.draw.circle(self.screen, (255, 255, 255),
                           (cx, cy), self._CORNER_R, 2)
        text(self.screen, label, 16, (255, 255, 255), cx, cy,
             bold=True, center=True)

    def jump(self):
        self.bird_v = JUMP_V
        sfx.flap()

    # ------------------------------------------------ 更新
    def update(self):
        self.frame += 1

        # 破纪录烟花的物理更新（over 界面也持续播放）
        if self._fireworks:
            self._update_fireworks()

        # 换地图淡入淡出的推进（放在 state 判断之前，暂停/结束时也能走完）
        self._update_mapfade()

        if self.state != STATE_PLAY or self.paused:
            return

        self.anim += 0.28
        self.bird_v += GRAVITY
        self.bird_y += self.bird_v
        self.ground_x = (self.ground_x - PIPE_SPEED) % 48

        # 管道移动
        for p in self.pipes:
            p["x"] -= PIPE_SPEED

        # 回收 + 生成
        if self.pipes and self.pipes[0]["x"] + PIPE_W < -20:
            self.pipes.pop(0)
        while self.pipes and self.pipes[-1]["x"] < WIDTH + PIPE_SPACING:
            last_x = self.pipes[-1]["x"]
            self._spawn_pipe(last_x + PIPE_SPACING)
            if len(self.pipes) > 6:
                break

        # 计分
        for p in self.pipes:
            if p["id"] not in self.passed and p["x"] + PIPE_W < BIRD_X:
                self.passed.add(p["id"])
                self.score += 1
                sfx.score()
                # 每得 10 分更换一次地图背景（不打断当前一局）
                # 用淡入淡出过渡，避免画面瞬间跳变
                if self.score > 0 and self.score % 10 == 0:
                    old_map_id = self.map_id
                    self.map_idx = (self.map_idx + 1) % len(assets.MAP_ORDER)
                    self.map_changed = True
                    self.bg = assets.build_background(self.map_id, WIDTH, HEIGHT)
                    self._start_mapfade(old_map_id)
                    sfx.levelup()
                if self.score > self.best:
                    self.best = self.score
                    self._save()

        # 碰撞
        bw, bh = int(assets.SW * BIRD_SCALE), int(assets.SH * BIRD_SCALE)
        bx, by = BIRD_X - bw // 2, int(self.bird_y) - bh // 2
        bird_rect = pygame.Rect(bx + 8, by + 8, bw - 16, bh - 16)

        floor_y = HEIGHT - GROUND_H
        if bird_rect.bottom >= floor_y or bird_rect.top <= 0:
            self._die()
            return
        for p in self.pipes:
            top_r = pygame.Rect(int(p["x"]), 0, PIPE_W, int(p["top"]))
            bot_y = p["top"] + PIPE_GAP
            bot_r = pygame.Rect(int(p["x"]), int(bot_y), PIPE_W, HEIGHT - bot_y)
            if bird_rect.colliderect(top_r) or bird_rect.colliderect(bot_r):
                self._die()
                return

    def _die(self):
        self.state = STATE_OVER
        self.dead_t = 0
        # 是否刷新历史纪录（本局分数 > 本局开局前的最高）
        self._is_new_record = self.score > 0 and self.score > self._start_best
        self._record_score(self.score)   # 记录本局分数进历史榜单
        if self._is_new_record:
            self._spawn_fireworks()
            sfx.cheer()
        else:
            sfx.hit()

    # ---------------- 破纪录烟花特效 ----------------
    _FW_COLORS = [(255, 90, 90), (255, 200, 60), (120, 220, 120),
                  (120, 170, 255), (230, 130, 255), (120, 255, 230)]

    def _spawn_fireworks(self):
        """在游戏区随机位置连放几朵礼花弹（先上升后爆开）"""
        self._fireworks = []
        for k in range(4):
            self._fireworks.append({
                "x": random.randint(WIDTH // 2 - 150, WIDTH // 2 + 150),
                "y": HEIGHT * 0.72,          # 从地面附近起升
                "vy": random.uniform(-8.2, -6.2),
                "vx": random.uniform(-0.8, 0.8),
                "phase": "rise",              # rise 上升 -> burst 爆炸
                "burst_at": random.uniform(0.25, 0.45) * HEIGHT,  # 爆点 y
                "parts": [],
                "burst_done": False,
                "delay": k * 9,               # 依次发射
            })

    def _update_fireworks(self):
        # 延迟发射
        for fw in self._fireworks:
            if fw["delay"] > 0:
                fw["delay"] -= 1
                continue
            if not fw["burst_done"]:
                if fw["phase"] == "rise":
                    fw["y"] += fw["vy"]
                    fw["x"] += fw["vx"]
                    fw["vy"] += 0.25           # 轻重力，火箭越升越慢
                    if fw["y"] <= fw["burst_at"] or fw["vy"] > -0.3:
                        # 爆开
                        fw["phase"] = "burst"
                        fw["burst_done"] = True
                        col = random.choice(self._FW_COLORS)
                        n = random.randint(22, 30)
                        for _ in range(n):
                            ang = random.uniform(0, 6.283)
                            spd = random.uniform(1.2, 4.6)
                            fw["parts"].append({
                                "x": fw["x"], "y": fw["y"],
                                "vx": math.cos(ang) * spd,
                                "vy": math.sin(ang) * spd,
                                "life": random.uniform(24, 48),
                                "col": col,
                            })
                else:
                    fw["burst_done"] = True
            # 更新粒子
            dead = []
            for p in fw["parts"]:
                p["x"] += p["vx"]
                p["y"] += p["vy"]
                p["vy"] += 0.12
                p["vx"] *= 0.99
                p["life"] -= 1
                if p["life"] <= 0 or p["y"] > HEIGHT - 20:
                    dead.append(p)
            for p in dead:
                if p in fw["parts"]:
                    fw["parts"].remove(p)
        # 清空已全部熄灭的
        self._fireworks = [f for f in self._fireworks if f["delay"] > 0 or f["parts"] or not f["burst_done"]]

    def _draw_fireworks(self):
        for fw in self._fireworks:
            # 上升段的火箭（带尾迹光点）
            if fw["phase"] == "rise" and fw["delay"] <= 0:
                pygame.draw.circle(self.screen, (255, 255, 255), (int(fw["x"]), int(fw["y"])), 3)
                pygame.draw.circle(self.screen, (200, 200, 255),
                                   (int(fw["x"]), int(fw["y"] + 8)), 2)
            # 爆开的粒子
            for p in fw["parts"]:
                a = min(255, int(255 * (p["life"] / 48)))
                col = (*p["col"], a)
                # 用 alpha surface 画小圆
                ps = pygame.Surface((8, 8), pygame.SRCALPHA)
                pygame.draw.circle(ps, col, (4, 4), 3)
                self.screen.blit(ps, (int(p["x"]) - 4, int(p["y"]) - 4))


    # ------------------------------------------------ 渲染
    def draw(self):
        # 按状态切换窗口宽度：游戏中只有 480（彻底没有右边那块黑框），
        # 菜单/结束态扩到 720（侧栏历史排行 + 退出按钮再次出现）
        target_size = (WIDTH, HEIGHT) if self.state == STATE_PLAY else (WIN_W, HEIGHT)
        if self.screen.get_size() != target_size:
            self.screen = pygame.display.set_mode(target_size)

        # 先把整屏清成黑色，避免上一帧侧栏文字透出来
        self.screen.fill((0, 0, 0))

        # 游戏背景只画 0-480（bg 本身就是 WIDTH 宽，不会越过边界）
        # 换地图时：旧背景铺底(不透明) + 新背景按 alpha 渐显 = 交叉淡入
        if self._mapfade:
            k = self._mapfade_k()
            self.screen.blit(self._mapfade["old_bg"], (0, 0))
            new_a = int(255 * k)
            if new_a > 0:
                prev_a = self.bg.get_alpha()
                self.bg.set_alpha(new_a)
                self.screen.blit(self.bg, (0, 0))
                self.bg.set_alpha(prev_a)
        else:
            self.screen.blit(self.bg, (0, 0))

        if self.state == STATE_MENU:
            self._draw_menu()
        else:
            self._draw_world()
            if self.state == STATE_OVER:
                self._draw_over()
                self._draw_fireworks()   # 破纪录烟花盖在结束层上
            elif self.paused:
                self._draw_pause()

        # 左下角小按钮（音效/音乐开关）—— 永远画在最上层，三态都可点
        self._draw_corner_buttons()

        # 侧栏最后画：仅 MENU/OVER 显示排行榜+退出按钮
        self._draw_sidebar()

        pygame.display.flip()

    # 右侧信息栏：仅菜单/结束态显示；游戏中完全隐藏（窗口此时也只有 480 宽）
    def _draw_sidebar(self):
        # 游戏中：什么都不画 —— 窗口宽度已经是 480，根本不存在右边那块
        if self.state == STATE_PLAY:
            return

        x = WIDTH
        # 侧栏底色（菜单/结束态才铺）
        pygame.draw.rect(self.screen, (16, 18, 30), (x, 0, SIDEBAR_W, HEIGHT))
        pygame.draw.line(self.screen, (60, 70, 95), (x, 0), (x, HEIGHT), 1)

        # 菜单态：完整历史排行 + 退出按钮
        if self.state == STATE_MENU:
            text(self.screen, "历史排行", 20, (255, 225, 120), x + SIDEBAR_W // 2, 34,
                 bold=True, center=True)
            text(self.screen, "HISTORY", 11, (150, 165, 190), x + SIDEBAR_W // 2, 54,
                 center=True)
            self._draw_ranklist(x, ty=84)
            text(self.screen, "每得 10 分自动换地图", 12, (140, 175, 170),
                 x + SIDEBAR_W // 2, HEIGHT - 104, center=True)
            qr = pygame.Rect(x + 40, HEIGHT - 70, SIDEBAR_W - 80, 48)
            hov = qr.collidepoint(*pygame.mouse.get_pos())
            qc = (210, 80, 80) if hov else (150, 55, 55)
            pygame.draw.rect(self.screen, qc, qr, border_radius=24)
            pygame.draw.rect(self.screen, (255, 255, 255), qr, 2, border_radius=24)
            text(self.screen, "退出游戏", 18, (255, 255, 255),
                 x + SIDEBAR_W // 2, HEIGHT - 46, bold=True, center=True)
            return

        # 结束态（OVER）：把本局成绩显示在侧栏，方便玩家一眼看到分数和历史
        if self.state == STATE_OVER:
            text(self.screen, "本局得分", 14, (150, 165, 190),
                 x + SIDEBAR_W // 2, 60, center=True)
            text(self.screen, str(self.score), 44,
                 (255, 200, 120),
                 x + SIDEBAR_W // 2, 96, bold=True, center=True)
            text(self.screen, "历史最高", 12, (120, 132, 155),
                 x + SIDEBAR_W // 2, 158, center=True)
            text(self.screen, str(self.best), 26, (255, 225, 120),
                 x + SIDEBAR_W // 2, 186, bold=True, center=True)
            if self._is_new_record:
                text(self.screen, "新纪录!", 20, (255, 220, 90),
                     x + SIDEBAR_W // 2, 224, bold=True, center=True)
            # 历史排行（前 6 名）
            text(self.screen, "历史排行", 16, (255, 225, 120),
                 x + SIDEBAR_W // 2, 270, bold=True, center=True)
            self._draw_ranklist(x, ty=296)
            # 返回菜单提示
            text(self.screen, "M / ESC  返回菜单", 13, (140, 152, 175),
                 x + SIDEBAR_W // 2, HEIGHT - 60, center=True)
            qr = pygame.Rect(x + 40, HEIGHT - 44, SIDEBAR_W - 80, 36)
            hov = qr.collidepoint(*pygame.mouse.get_pos())
            qc = (170, 70, 70) if hov else (130, 50, 50)
            pygame.draw.rect(self.screen, qc, qr, border_radius=18)
            pygame.draw.rect(self.screen, (255, 255, 255), qr, 2, border_radius=18)
            text(self.screen, "退出游戏", 16, (255, 255, 255),
                 x + SIDEBAR_W // 2, HEIGHT - 26, bold=True, center=True)

    def _draw_ranklist(self, x, ty):
        # 历史前 6 名（可重复记录，标注排名）
        srt = sorted(self.history, reverse=True)[:6]
        row_h = 40
        if not srt:
            text(self.screen, "还没有记录", 15, (140, 150, 170),
                 x + SIDEBAR_W // 2, ty + 40, center=True)
            return
        medals = ("1st", "2nd", "3rd")
        for i, sc in enumerate(srt):
            yy = ty + i * row_h
            if i < 3:
                col = ((255, 215, 90), (210, 210, 220), (200, 150, 90))[i]
                rank = medals[i]
            else:
                col = (170, 180, 200)
                rank = "%d" % (i + 1)
            text(self.screen, rank, 13, col, x + 22, yy, bold=True, center=True)
            # 简单横条
            bar_w = int((SIDEBAR_W - 90) * max(0.18, sc / max(1, srt[0])))
            pygame.draw.rect(self.screen, (40, 52, 80), (x + 52, yy - 8, SIDEBAR_W - 92, 18),
                             border_radius=6)
            pygame.draw.rect(self.screen, col, (x + 52, yy - 8, bar_w, 18), border_radius=6)
            text(self.screen, "%d" % sc, 15, (255, 255, 255), x + SIDEBAR_W - 18, yy,
                 center=True)



    def _draw_world(self):
        # 管道（换图过渡时用插值配色，跟背景一起渐变）
        pipe_colors = self._cur_pipe_colors() if self._mapfade else None
        for p in self.pipes:
            px = int(p["x"])
            assets.draw_pipe(self.screen, self.map_id, px, 0, PIPE_W, int(p["top"]), True,
                             pipe_colors)
            bot_y = int(p["top"] + PIPE_GAP)
            assets.draw_pipe(self.screen, self.map_id, px, bot_y, PIPE_W,
                             HEIGHT - bot_y - GROUND_H, False, pipe_colors)

        # 地面
        self._draw_ground()

        # 鸟
        frames = assets.get_skin_frames(self.skin_id, BIRD_SCALE)
        img = frames[int(self.anim) % len(frames)]
        tilt = max(-28, min(28, -self.bird_v * 3.2))
        rot = pygame.transform.rotate(img, tilt if self.state == STATE_PLAY else 0)
        r = rot.get_rect(center=(BIRD_X, int(self.bird_y)))
        if self.state == STATE_OVER:
            rot = pygame.transform.rotate(img, -70)
            r = rot.get_rect(center=(BIRD_X, int(self.bird_y)))
        self.screen.blit(rot, r)

        # 分数
        text(self.screen, str(self.score), 58, (255, 255, 255),
             WIDTH // 2, 78, bold=True, center=True, shadow=(30, 30, 40))

        # 最高分（小字）
        text(self.screen, "最高 %d" % self.best, 18, (255, 255, 255),
             WIDTH - 12, 16, shadow=(30, 30, 40))

    def _draw_ground(self):
        gy = HEIGHT - GROUND_H
        gc = self._cur_ground_color()      # 换图过渡时为插值色
        pygame.draw.rect(self.screen, gc, (0, gy, WIDTH, GROUND_H))
        # 顶部亮边
        hi = tuple(min(255, c + 45) for c in gc)
        pygame.draw.rect(self.screen, hi, (0, gy, WIDTH, 8))
        # 纹理
        dk = tuple(max(0, c - 35) for c in gc)
        off = int(self.ground_x)
        x = off - 48
        while x < WIDTH + 48:
            pygame.draw.line(self.screen, dk, (x, gy + 10), (x + 22, HEIGHT), 3)
            x += 48

    def _draw_pause(self):
        ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 130))
        self.screen.blit(ov, (0, 0))
        text(self.screen, "已暂停", 46, (255, 255, 255), WIDTH // 2, HEIGHT // 2 - 20,
             bold=True, center=True)
        text(self.screen, "按 P 继续", 22, (220, 220, 230), WIDTH // 2, HEIGHT // 2 + 34,
             center=True)

    def _draw_over(self):
        ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 150))
        self.screen.blit(ov, (0, 0))

        cy = HEIGHT // 2 - 40
        text(self.screen, "撞 机 了", 44, (255, 120, 110), WIDTH // 2, cy - 70,
             bold=True, center=True, shadow=(40, 10, 10))
        text(self.screen, "本局得分", 22, (210, 215, 225), WIDTH // 2, cy - 10, center=True)
        text(self.screen, str(self.score), 72, (255, 230, 90), WIDTH // 2, cy + 46,
             bold=True, center=True, shadow=(50, 40, 10))
        text(self.screen, "最高纪录  %d" % self.best, 24, (255, 255, 255),
             WIDTH // 2, cy + 112, center=True)

        # 破纪录时的庆祝横幅
        if self._is_new_record:
            text(self.screen, "新纪录! 太棒了", 22, (255, 230, 120),
                 WIDTH // 2, cy + 82, bold=True, center=True,
                 shadow=(60, 40, 10))

        text(self.screen, "空格 / 点击  再来一局", 20, (225, 230, 240),
             WIDTH // 2, cy + 176, center=True)
        text(self.screen, "M / ESC  返回菜单选皮肤", 18, (175, 182, 196),
             WIDTH // 2, cy + 208, center=True)

    # ------------------------------------------------ 菜单
    def _draw_menu(self):
        # 半透明遮罩让文字更清晰
        ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 90))
        self.screen.blit(ov, (0, 0))

        text(self.screen, "笨 鸟 先 飞", 46, (255, 235, 120), WIDTH // 2, 62,
             bold=True, center=True, shadow=(50, 30, 10))
        text(self.screen, "SILLY BIRD FIRST FLY", 15, (200, 210, 225),
             WIDTH // 2, 98, center=True)

        # ---- 皮肤选择区
        sy = 150
        self._panel(30, sy, WIDTH - 60, 168)
        text(self.screen, "选择皮肤", 15, (170, 200, 235), WIDTH // 2, sy + 16, center=True)

        sid = self.skin_id
        name, desc = assets.SKINS[sid]
        icon = assets.get_skin_icon(sid, (int(assets.SW * 1.5), int(assets.SH * 1.5)))
        bob = math.sin(self.frame * 0.07) * 5
        self.screen.blit(icon, icon.get_rect(center=(WIDTH // 2, sy + 74 + bob)))

        # 左右切换按钮（鼠标可点击）
        self._nav_btn(62, sy + 74, -1)
        self._nav_btn(WIDTH - 62, sy + 74, 1)

        text(self.screen, name, 26, (255, 255, 255), WIDTH // 2, sy + 126,
             bold=True, center=True)
        text(self.screen, desc, 15, (185, 195, 210), WIDTH // 2, sy + 150, center=True)
        text(self.screen, "%d / %d" % (self.skin_idx + 1, len(assets.SKIN_ORDER)),
             14, (150, 160, 180), WIDTH - 46, sy + 20, center=True)

        # ---- 地图选择区
        my = 336
        self._panel(30, my, WIDTH - 60, 150)
        text(self.screen, "选择地图", 15, (170, 200, 235), WIDTH // 2, my + 16, center=True)

        # 地图缩略图
        tw, th = 128, 76
        tx, ty = WIDTH // 2 - tw // 2, my + 32
        thumb = assets.build_background(self.map_id, tw, th)
        self.screen.blit(thumb, (tx, ty))
        pygame.draw.rect(self.screen, (255, 255, 255), (tx, ty, tw, th), 2)

        # 左右切换按钮（鼠标可点击）
        self._nav_btn(62, my + 70, -1)
        self._nav_btn(WIDTH - 62, my + 70, 1)

        mname, mdesc, *_ = assets.MAPS[self.map_id]
        text(self.screen, mname, 24, (255, 255, 255), WIDTH // 2, my + 118,
             bold=True, center=True)
        text(self.screen, "%d / %d" % (self.map_idx + 1, len(assets.MAP_ORDER)),
             14, (150, 160, 180), WIDTH - 46, my + 20, center=True)

        # ---- 提示
        text(self.screen, "← → / A D  切换皮肤        ↑ ↓ / W S  切换地图",
             15, (190, 200, 216), WIDTH // 2, 522, center=True)
        text(self.screen, "空格 / 点击  拍翅起飞",
             15, (190, 200, 216), WIDTH // 2, 546, center=True)

        # 开始按钮（呼吸效果）
        pulse = 0.5 + 0.5 * math.sin(self.frame * 0.08)
        bc = (int(240 + 15 * pulse), int(190 + 40 * pulse), int(70 + 40 * pulse))
        br = pygame.Rect(WIDTH // 2 - 110, 582, 220, 56)
        pygame.draw.rect(self.screen, bc, br, border_radius=28)
        pygame.draw.rect(self.screen, (255, 255, 255), br, 2, border_radius=28)
        text(self.screen, "空格 开始游戏", 24, (60, 40, 10), WIDTH // 2, 610,
             bold=True, center=True)

        text(self.screen, "最高纪录  %d" % self.best, 20, (255, 240, 160),
             WIDTH // 2, 664, bold=True, center=True, shadow=(40, 30, 10))

    def _panel(self, x, y, w, h):
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        s.fill((18, 22, 38, 165))
        self.screen.blit(s, (x, y))
        pygame.draw.rect(self.screen, (110, 140, 190), (x, y, w, h), 2, border_radius=14)

    def _nav_btn(self, x, y, direction):
        """圆形可点击切换按钮：圆底 + 三角箭头。中心 (x,y)。"""
        mx, my = pygame.mouse.get_pos()
        hover = (mx - x) ** 2 + (my - y) ** 2 <= 38 * 38
        # 圆底
        fill = (70, 110, 175, 235) if hover else (48, 78, 128, 220)
        c = pygame.Surface((80, 80), pygame.SRCALPHA)
        pygame.draw.circle(c, fill, (40, 40), 34)
        pygame.draw.circle(c, (210, 225, 245) if hover else (150, 180, 220),
                           (40, 40), 34, 3)
        self.screen.blit(c, (x - 40, y - 40))
        # 三角箭头（用深色在圆底上更清晰）
        d = direction
        col = (255, 255, 255)
        pts = [(x + d * 10, y - 15), (x + d * 10, y + 15), (x - d * 7, y)]
        pygame.draw.polygon(self.screen, col, pts)

    # ------------------------------------------------ 主循环
    def run(self):
        alive = True
        while alive:
            alive = self.handle()
            self.update()
            self.draw()
            self.clock.tick(FPS)
        pygame.quit()


def main():
    g = Game()
    g.run()


if __name__ == "__main__":
    main()
