# -*- coding: utf-8 -*-
"""
程序化音效模块（零素材、零第三方依赖）
========================================
用 Python 内置 array 直接合成 WAV 波形，写进 cache/sfx/ 下的临时文件，
再用 pygame.mixer.Sound 加载播放：
  flap    -> 拍翅（短促上扫音）
  score   -> 过管得分（清脆双音）
  levelup -> 每 10 分换图（上行琶音）
  hit     -> 撞机（低沉撞击）

如果音频设备不可用（无声卡 / 无头环境），静默降级为空操作，绝不抛异常。
作者: 元宝
"""

import os
import math
import array
import wave
import random

import pygame

# 采样率 / 采样格式
SR = 22050
DUR_SEC = 0.35          # 每种音效最长时长（内部再各自截短）

_CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache", "sfx")
_ready = False
_sounds = {}
_sfx_muted = False       # 一次性音效（拍翅/得分/换图/撞机/欢呼）静音开关


# ---------------------------------------------------------------- 波形合成
def _tone_wav(name, dur):
    """按名称生成对应 PCM (16bit 单声道) array"""
    n = int(SR * dur)
    step = 1.0 / SR
    buf = array.array("h")

    if name == "flap":
        # 500 -> 900 Hz 上扫
        for i in range(n):
            t = i * step
            freq = 500 + 400 * (t / 0.09)
            v = math.sin(2 * math.pi * freq * t) * 0.9
            v += 0.25 * math.copysign(1.0, math.sin(2 * math.pi * 2000 * t))
            env = 1.0 if t < 0.06 else max(0.0, 1.0 - (t - 0.06) / 0.03)
            buf.append(int(max(-1, min(1, v * env)) * 0.45 * 32767))

    elif name == "score":
        # E6(1318) -> A6(1760)，两短音
        for i in range(n):
            t = i * step
            freq = 1318.5 if t < 0.06 else 1760.0
            v = math.sin(2 * math.pi * freq * t) * 0.8
            env = 1.0 if t < 0.055 else max(0.0, 1.0 - (t - 0.055) / 0.03)
            buf.append(int(max(-1, min(1, v * env)) * 0.5 * 32767))

    elif name == "levelup":
        # 上行琶音 C5-E5-G5-C6
        notes = [523.25, 659.25, 783.99, 1046.5]
        seg_dur = 0.055
        for i in range(n):
            t = i * step
            seg = int(t / seg_dur)
            seg = min(seg, 3)
            freq = notes[seg]
            tt = t - seg * seg_dur
            v = math.sin(2 * math.pi * freq * t) * 0.8
            v += 0.25 * math.sin(2 * math.pi * 2 * freq * t)
            env = min(1.0, tt / 0.005) * max(0.0, 1.0 - max(0, tt - 0.035) / 0.02)
            buf.append(int(max(-1, min(1, v * env)) * 0.5 * 32767))

    elif name == "hit":
        # 低频下滑 + 噪声爆裂
        rnd = _noise(n)
        for i in range(n):
            t = i * step
            freq = max(60.0, 300.0 - 1300.0 * t)
            tone = math.sin(2 * math.pi * freq * t) * 0.9
            v = tone * math.exp(-7 * t) + 0.3 * rnd[i] * math.exp(-14 * t)
            buf.append(int(max(-1, min(1, v)) * 0.7 * 32767))

    elif name == "cheer":
        # 破纪录小号式上行琶音 C-E-G-C-E + 高音收尾，欢快
        seq = [523.25, 659.25, 783.99, 1046.5, 1318.5, 1568.0]
        npts = len(seq)
        dur_each = 0.09
        for i in range(n):
            t = i * step
            k = min(int(t / dur_each), npts - 1)
            freq = seq[k]
            tt = t - k * dur_each
            v = math.sin(2 * math.pi * freq * t) * 0.9
            v += 0.4 * math.sin(4 * math.pi * freq * t)   # 带金属感的方波泛音
            env = min(1.0, tt / 0.008) * max(0.0, 1.0 - max(0, tt - 0.06) / 0.03)
            buf.append(int(max(-1, min(1, v * env)) * 0.6 * 32767))
    else:
        return None
    return buf


def _noise(n):
    # 确定性伪随机噪声（无需 random 高频开销亦可接受）
    rnd = array.array("f")
    x = 12345.0
    for _ in range(n):
        x = (x * 1103515245 + 12345) % 2147483648
        rnd.append((x / 2147483647.0) * 2.0 - 1.0)
    return rnd


def _wav_to_file(buf, path):
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(buf.tobytes())


# ---------------------------------------------------------------- 初始化
def _init():
    global _ready
    if _ready:
        return
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=SR, size=-16, channels=1)
        # 生成本地 wav（若尚未生成）
        os.makedirs(_CACHE, exist_ok=True)
        durs = {"flap": 0.10, "score": 0.13, "levelup": 0.24, "hit": 0.25,
                "cheer": 0.60}
        for name, dur in durs.items():
            path = os.path.join(_CACHE, name + ".wav")
            if not os.path.exists(path):
                buf = _tone_wav(name, dur)
                if buf:
                    _wav_to_file(buf, path)
            if os.path.exists(path):
                s = pygame.mixer.Sound(path)
                s.set_volume(0.6)
                _sounds[name] = s
        _ready = bool(_sounds)
    except Exception:
        _ready = False


def _play(name):
    if _sfx_muted:
        return
    _init()
    if not _ready:
        return
    snd = _sounds.get(name)
    if snd:
        try:
            snd.play()
        except Exception:
            pass


def sfx_set_muted(muted):
    """设置一次性音效静音（flap/score/levelup/hit/cheer）。"""
    global _sfx_muted
    _sfx_muted = bool(muted)


def sfx_is_muted():
    """返回一次性音效是否静音。"""
    return _sfx_muted


def sfx_toggle():
    """切换一次性音效静音状态，返回新的状态（True=已静音）。"""
    global _sfx_muted
    _sfx_muted = not _sfx_muted
    return _sfx_muted


def flap():
    _play("flap")


def score():
    _play("score")


def levelup():
    _play("levelup")


def hit():
    _play("hit")


def cheer():
    _play("cheer")


# ================================================================
# 背景电子音乐（程序化合成，循环播放）
# ================================================================
_bg_path = os.path.join(_CACHE, "bgm.wav")
_music_on = False
_TEMPO = 0.145          # 每拍秒数（~ 138 BPM）


def _gen_bgm():
    """合成一段约 8 小节、欢快的电子循环（方波主旋律 + 三角波低音）。"""
    if os.path.exists(_bg_path) and os.path.getsize(_bg_path) > 0:
        return
    # 音名 -> 频率
    A4 = 440.0
    def nf(semi):
        return A4 * (2 ** (semi / 12.0))
    # 用半音相对 A4 定义音（C 大调为主，明快）
    # 主旋律音型（每步一拍，含休止 0）
    mel = [0, 0, 4, 7, 12, 7, 4, 0,
           2, 0, 5, 9, 14, 9, 5, 0,
           3, 0, 7, 11, 16, 11, 7, 0,
           2, 0, 7, 11, 15, 11, 7, 0]
    bass = [ -12,-12, -12,-12, -10,-10,-10,-10,
            -8,-8,  -5,-5, -7,-7,-7,-7,
            -12,-12,-12,-12, -10,-10,-10,-10,
            -8,-8,-5,-5, -7,-7,-7,-7]  # 与主旋律配合的根音
    beat = _TEMPO
    total = int(32 * beat * SR)     # 32 步
    out = array.array("h")
    rnd = random.Random(99)

    for i in range(total):
        t = i / SR
        step = int(t // beat)
        st = step % 32
        # ---- 主旋律（方波 + 轻微衰减）----
        m = mel[st]
        seg_t = t - step * beat
        if m != 0:
            f = nf(m)
            # 方波：只含奇数谐波，用叠加近似
            v = math.sin(2*math.pi*f*seg_t)
            # 加第二次泛音让音色更亮
            v += 0.4*math.sin(4*math.pi*f*seg_t)
            v += 0.2*math.sin(6*math.pi*f*seg_t)
            env = 0.9 if seg_t < 0.09 else 0.7
            val = v * env * 0.28
        else:
            val = 0.0
        # ---- 低音（三角波，简单）----
        b = bass[st]
        bf = nf(b)
        seg_b = t - step * beat
        # 三角波近似
        p = (seg_b * bf) % 1.0
        bv = 4 * abs(p - 0.5) - 1
        val += bv * 0.22 * (0.9 if seg_b < 0.6 else 0.5)
        # ---- 轻快节奏：每拍后半一个 HiHat(噪声短促)----
        if 0.10 < seg_t < 0.13:
            val += (rnd.uniform(-1,1)) * 0.10
        # ---- 结尾避免爆音----
        out.append(int(max(-1, min(1, val)) * 0.55 * 32767))
    _wav_to_file(out, _bg_path)


def music_start():
    """开始循环播放背景电子乐（幂等）。"""
    global _music_on
    if not _init_mixer_only():
        return
    if _music_on:
        return
    try:
        _gen_bgm()
        if not pygame.mixer.music.get_busy():
            pygame.mixer.music.load(_bg_path)
            pygame.mixer.music.play(-1)
        _music_on = True
    except Exception:
        _music_on = False


def music_stop():
    global _music_on
    try:
        pygame.mixer.music.stop()
    except Exception:
        pass
    _music_on = False


def music_on():
    return _music_on


def _init_mixer_only():
    """只初始化 mixer（不生成一次性音效），供音乐用。"""
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=SR, size=-16, channels=1)
        return True
    except Exception:
        return False

