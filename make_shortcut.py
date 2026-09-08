# -*- coding: utf-8 -*-
"""
为「笨鸟先飞」生成桌面快捷方式（纯 Python 写 .lnk，无需管理员、无需 COM）。
用法:  python make_shortcut.py
会把快捷方式放到当前用户的桌面。
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
NAME = "笨鸟先飞"


def find_pythonw():
    """优先用当前解释器同目录的 pythonw（通常就是带 pygame 的虚拟环境）。"""
    cand = []
    if sys.executable:
        cand.append(os.path.join(os.path.dirname(sys.executable), "pythonw.exe"))
    for p in os.environ.get("PATH", "").split(os.pathsep):
        if p:
            cand.append(os.path.join(p, "pythonw.exe"))
    for c in cand:
        if os.path.exists(c):
            return os.path.abspath(c)
    if sys.executable and os.path.exists(sys.executable):
        return os.path.abspath(sys.executable)
    return "pythonw.exe"


TARGET = find_pythonw()
SCRIPT = os.path.join(HERE, "game.py")
WORKDIR = HERE
ICON = os.path.join(HERE, "icon.ico")


def wstr(s):
    data = s.encode("utf-16-le")
    return struct.pack("<H", len(data) // 2) + data + b"\x00\x00"


def build():
    flags = 0x0001 | 0x0002 | 0x0004 | 0x0010 | 0x0020 | 0x0040 | 0x0080
    out = bytearray()
    out += struct.pack("<I", 0x4C)
    out += bytes.fromhex("0114020000000000c000000000000046")
    out += struct.pack("<I", flags)
    out += struct.pack("<I", 0x20)
    out += struct.pack("<Q", 0) * 3
    out += struct.pack("<I", 0)
    out += struct.pack("<i", 0)
    out += struct.pack("<I", 1)
    out += struct.pack("<H", 0)
    out += struct.pack("<H", 0)
    out += struct.pack("<I", 0) * 2

    idlist = b"\x00\x00"
    out += struct.pack("<H", len(idlist)) + idlist

    tb = TARGET.encode("latin-1")
    li = bytearray()
    li += struct.pack("<I", 0)
    li += struct.pack("<I", 28)
    li += struct.pack("<I", 1)
    li += struct.pack("<I", 28)
    li += struct.pack("<I", 44)
    li += struct.pack("<I", 0)
    li += struct.pack("<I", 44 + len(tb) + 1)
    li += struct.pack("<I", 16)
    li += struct.pack("<I", 3)
    li += struct.pack("<I", 0)
    li += struct.pack("<I", 16)
    li += tb + b"\x00"
    li += b"\x00"
    struct.pack_into("<I", li, 0, len(li))
    out += bytes(li)

    out += wstr(NAME)
    out += wstr(WORKDIR)
    out += wstr(SCRIPT)
    out += wstr(ICON)
    out += struct.pack("<I", 0)
    return bytes(out)


def main():
    desktop = os.path.join(os.environ.get("USERPROFILE", ""), "Desktop")
    os.makedirs(desktop, exist_ok=True)
    path = os.path.join(desktop, NAME + ".lnk")
    with open(path, "wb") as f:
        f.write(build())
    print("已生成桌面快捷方式:")
    print("  ", path)
    print("目标程序:", TARGET)
    if not os.path.exists(TARGET):
        print("  [警告] 目标 Python 不存在，请先安装 Python + pygame 或运行本项目自带的虚拟环境。")


if __name__ == "__main__":
    main()
