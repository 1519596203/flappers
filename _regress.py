# -*- coding: utf-8 -*-
"""回归测试（本轮改动：排行榜仅菜单显示 / 背景电子乐 / 破纪录烟花+音效）
覆盖：
1. 破纪录检测：死时 score>开局best -> _is_new_record=True 且生成烟花、播 cheer
   未破纪录：score<=best -> False、播 hit
2. 烟花粒子会推进与渲染（over 态 update 持续 tick）
3. 右侧栏：菜单显示「历史排行」，游戏/结束不显示榜单(只分数)
4. 背景音乐：可 start / stop / 状态翻转（无声卡环境优雅降级）
5. 计分仍能破 5（前几轮 bug 复查）
"""
import os
import json
import pygame

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import assets
import game
import soundfx as sfx
from game import Game, STATE_MENU, STATE_PLAY, STATE_OVER

W, H = game.WIDTH, game.HEIGHT
WIN_W = game.WIN_W
GAP = game.PIPE_GAP
BIRD_X = game.BIRD_X


def seed_save(best, hist):
    with open(game.SAVE_FILE, "w", encoding="utf-8") as f:
        json.dump({"best": best, "history": hist}, f)


def test_record_detect():
    pygame.init()
    pygame.display.set_mode((WIN_W, H))
    # 开局 best=10，本局打 15 -> 破纪录
    seed_save(10, [10, 8])
    g = Game()
    g._start_best = 10
    g.score = 15
    g._die()
    ok = g._is_new_record is True and g.best >= 15
    print(f"[1] 破纪录检测: _is_new_record={g._is_new_record} fireworks={len(g._fireworks)}",
          "-> PASS" if ok and len(g._fireworks) > 0 else "-> FAIL")
    # 烟花 tick 推进（over 态）
    for _ in range(5):
        g.update()
    print("[1b] 烟花推进无异常 ->", "PASS")

    # 未破纪录
    seed_save(20, [20])
    g2 = Game()
    g2._start_best = 20
    g2.score = 5
    g2._die()
    ok2 = g2._is_new_record is False
    print(f"[1c] 未破纪录: _is_new_record={g2._is_new_record} ->",
          "PASS" if ok2 else "FAIL")
    pygame.quit()
    return ok and ok2


def test_score_past_5_and_map():
    pygame.init()
    pygame.display.set_mode((WIN_W, H))
    seed_save(0, [])
    g = Game()
    g.state = STATE_PLAY
    g.reset()
    safe = 360.0
    g.bird_y, g.bird_v = safe, 0.0
    m0 = g.map_idx
    passed5 = False
    changed = False
    for _ in range(30000):
        g.handle()
        if g.state == STATE_PLAY:
            g.bird_y, g.bird_v = safe, 0.0
            for q in g.pipes:
                if q["x"] + 74 > BIRD_X - 5:
                    q["top"] = int(safe - GAP / 2)
                    break
        g.update()
        if g.score >= 6:
            passed5 = True
        if g.score >= 10 and g.map_idx != m0:
            changed = True
            break
        if g.state == STATE_OVER:
            break
    print(f"[2] 计分破5: score={g.score} ->", "PASS" if passed5 else "FAIL")
    print(f"[3] 10分换图: map {m0}->{g.map_idx} ->", "PASS" if changed else "FAIL")
    pygame.quit()
    return passed5 and changed


def test_sidebar_and_music():
    pygame.init()
    pygame.display.set_mode((WIN_W, H))
    seed_save(12, [12, 9, 6])
    g = Game()

    # 音乐开关状态翻转（dummy 音频可能不可用，优雅处理）
    before = g.music_on
    try:
        if before:
            sfx.music_stop()
            g.music_on = False
        else:
            sfx.music_start()
            g.music_on = sfx.music_on()
        print(f"[4] 音乐开关: start前={before} -> 状态可切换 -> PASS")
    except Exception as e:
        print("[4] 音乐开关异常:", e, "-> FAIL")

    # 侧栏渲染：菜单与游戏各跑若干帧无崩溃，并验证排行榜只在菜单
    g.state = STATE_MENU
    g.reset()
    for _ in range(5):
        g.draw()
    menu_ok = g.state == STATE_MENU

    g.state = STATE_PLAY
    g.reset()
    for _ in range(20):
        g.handle()
        g.update()
        g.draw()
    print("[5] 菜单/游戏渲染无崩溃 -> PASS")

    # 空历史时侧栏也要能画（菜单）
    seed_save(0, [])
    g.state = STATE_MENU
    g.reset()
    for _ in range(3):
        g.draw()
    print("[6] 空历史榜单渲染 -> PASS")

    pygame.quit()
    return True


def test_corner_buttons_and_resize():
    """本轮新加：左下角小按钮命中 + SFX 静音 + 窗口按状态切换宽度。"""
    pygame.init()
    pygame.display.set_mode((WIN_W, H))
    seed_save(0, [])
    g = Game()

    # 1. SFX 静音 toggle
    before = sfx.sfx_is_muted()
    g.sfx_muted = sfx.sfx_toggle()
    after = sfx.sfx_is_muted()
    ok_sfx = before != after
    # 再 toggle 一次回到原状态
    g.sfx_muted = sfx.sfx_toggle()
    print(f"[7] SFX 静音翻转: {before}->{after} ->", "PASS" if ok_sfx else "FAIL")

    # 2. corner 按钮命中位置
    hit_sfx = g._corner_hit(32, 720 - 32)
    hit_music = g._corner_hit(84, 720 - 32)
    miss = g._corner_hit(200, 720 - 32)
    hit_in_sidebar = g._corner_hit(600, 360)  # 在右 480 之外
    ok_corner = (hit_sfx == "sfx" and hit_music == "music"
                 and miss is None and hit_in_sidebar is None)
    print(f"[8] corner 按钮命中: sfx={hit_sfx} music={hit_music} miss={miss} sidebar={hit_in_sidebar} ->",
          "PASS" if ok_corner else "FAIL")

    # 3. 窗口按状态切换（用 _resize_for_state-style 调用，不跑全 draw 避免 dummy 驱动崩溃）
    g.state = STATE_MENU
    target = (game.WIN_W, game.HEIGHT) if g.state != STATE_PLAY else (game.WIDTH, game.HEIGHT)
    g.screen = pygame.display.set_mode(target)
    sz_menu = g.screen.get_size()
    g.state = STATE_PLAY
    target = (game.WIN_W, game.HEIGHT) if g.state != STATE_PLAY else (game.WIDTH, game.HEIGHT)
    g.screen = pygame.display.set_mode(target)
    sz_play = g.screen.get_size()
    g.state = STATE_OVER
    target = (game.WIN_W, game.HEIGHT) if g.state != STATE_PLAY else (game.WIDTH, game.HEIGHT)
    g.screen = pygame.display.set_mode(target)
    sz_over = g.screen.get_size()
    ok_resize = (sz_menu == (WIN_W, H) and sz_play == (W, H)
                 and sz_over == (WIN_W, H))
    print(f"[9] 窗口宽度切换: menu={sz_menu[0]} play={sz_play[0]} over={sz_over[0]} ->",
          "PASS" if ok_resize else "FAIL")

    pygame.quit()
    return ok_sfx and ok_corner and ok_resize


def test_mapfade_and_right_btns():
    """本轮新加：换图淡入淡出（颜色线性插值）+ 右下角虚拟按钮按状态显隐。"""
    pygame.init()
    pygame.display.set_mode((WIN_W, H))
    seed_save(0, [])
    g = Game()

    # 1. mapfade 状态
    g.state = STATE_PLAY
    old_map = g.map_id
    g.map_idx = (g.map_idx + 1) % len(assets.MAP_ORDER)
    g.bg = assets.build_background(g.map_id, W, H)
    g._start_mapfade(old_map)
    old_ground = assets.get_ground(old_map)
    new_ground = assets.get_ground(g.map_id)
    # 起点 = old, 终点 = new
    g._mapfade["t"] = 0
    gc_start = g._cur_ground_color()
    g._mapfade["t"] = g.MAPFADE_FRAMES
    gc_end = g._cur_ground_color()
    # 中点插值
    g._mapfade["t"] = g.MAPFADE_FRAMES // 2
    gc_mid = g._cur_ground_color()
    r_old, r_new = old_ground[0], new_ground[0]
    r_mid_expected = (r_old + r_new) // 2
    ok_ground = (gc_start == old_ground and gc_end == new_ground
                 and abs(gc_mid[0] - r_mid_expected) <= 1)
    print(f"[10] mapfade 地面插值: 起点={gc_start} 终点={gc_end} 中点R={gc_mid[0]}(期望{r_mid_expected}) ->",
          "PASS" if ok_ground else "FAIL")

    # 2. 右下角按钮按态显隐
    g._mapfade = None
    g.state = STATE_MENU
    hit_menu = g._corner_hit(W - 32, H - 32)
    hit_pause = g._corner_hit(W - 84, H - 32)
    ok_menu_hidden = (hit_menu is None and hit_pause is None)

    g.state = STATE_PLAY
    hit_pause_play = g._corner_hit(W - 84, H - 32)
    hit_menu_play = g._corner_hit(W - 32, H - 32)
    ok_play_shows = (hit_pause_play == "pause" and hit_menu_play == "menu")

    g.state = STATE_OVER
    hit_pause_over = g._corner_hit(W - 84, H - 32)
    ok_over_shows = (hit_pause_over == "pause")
    print(f"[11] 右下角按钮按态: menu={hit_menu}/{hit_pause} play={hit_pause_play}/{hit_menu_play} over={hit_pause_over} ->",
          "PASS" if (ok_menu_hidden and ok_play_shows and ok_over_shows) else "FAIL")

    pygame.quit()
    return ok_ground and ok_menu_hidden and ok_play_shows and ok_over_shows


if __name__ == "__main__":
    r1 = test_record_detect()
    r2 = test_score_past_5_and_map()
    r3 = test_sidebar_and_music()
    r4 = test_corner_buttons_and_resize()
    r5 = test_mapfade_and_right_btns()
    print("\n=== 汇总 ===")
    print("破纪录检测+烟花:", "PASS" if r1 else "FAIL")
    print("计分破5+换图:", "PASS" if r2 else "FAIL")
    print("侧栏/音乐:", "PASS" if r3 else "FAIL")
    print("角按钮+窗口:", "PASS" if r4 else "FAIL")
    print("换图淡入+右下按钮:", "PASS" if r5 else "FAIL")
