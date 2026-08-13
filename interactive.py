#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""拼豆图纸 - 交互式参数调节面板（Python 版）。

用法：
  双击 拼豆图纸-交互版.bat  -> 打开交互菜单
  拖图片到 bat 图标           -> 用默认参数直接转换
"""
import os
import shlex
import subprocess
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
MAIN = os.path.join(BASE, "main.py")

# 固定工作目录为脚本所在目录，确保相对路径(如 output/)始终正确
os.chdir(BASE)

P = {
    "palette": "mard",
    "lang": "zh",
    "label": "brand",
    "max_colors": 24,
    "cell": 30,
    "coords": True,
    "grid": True,
    "bead": False,
    "title": "",
    "bg_hex": "",
    "width": 0,
    "height": 0,
}

PALETTE_NOTE = {
    "mard": "MARD 291色(国内拼豆,色号如H5/F11)",
    "perler": "Perler 95色(经典)",
    "artkal": "Artkal 30色(A01-A30)",
    "hama": "Hama 28色(H01-H28)",
}

# 拖拽到 bat 图标时接收的待处理文件（进入菜单后由用户先调参数再转换）
PENDING_FILES = []


def clear():
    os.system("cls" if os.name == "nt" else "clear")


def build_args():
    a = [
        "--palette", P["palette"],
        "--label-style", P["label"],
        "--max-colors", str(P["max_colors"]),
        "--cell", str(P["cell"]),
        "--lang", P["lang"],
    ]
    if P["coords"]:
        a.append("--coords")
    if not P["grid"]:
        a.append("--no-grid-lines")
    if P["bead"]:
        a.append("--bead-look")
    if P["title"]:
        a += ["--title", P["title"]]
    if P["bg_hex"]:
        a += ["--bg-hex", P["bg_hex"]]
    if P["width"]:
        a += ["--width", str(P["width"])]
    if P["height"]:
        a += ["--height", str(P["height"])]
    return a


def run_converter(files=None, pick=False, demo=False):
    # main.py 一次只处理一个输入文件，所以逐个调用
    if demo:
        targets = ["--demo"]
    elif pick:
        targets = ["--pick"]
    else:
        targets = list(files) if files else []
    for t in targets:
        cmd = [sys.executable, MAIN, t] + build_args()
        print()
        print("执行: python main.py %s" % " ".join(cmd[2:]))
        print("-" * 60)
        subprocess.run(cmd)
        print("-" * 60)
    input("按回车键继续...")


def ask(choices, prompt):
    while True:
        c = input(prompt).strip().lower()
        if c in choices:
            return c
        print("  输入无效，请重新输入。")


def show_menu():
    clear()
    print("=" * 60)
    print("  拼豆图纸转换器 - 参数调节面板")
    print("=" * 60)
    print()
    if PENDING_FILES:
        names = "、".join(os.path.basename(f) for f in PENDING_FILES[:3])
        if len(PENDING_FILES) > 3:
            names += " ... 共%d张" % len(PENDING_FILES)
        print("  ★ 已选文件：%s" % names)
        print("    （按 S 开始转换，或继续调节参数）")
        print()
    print("  [1] 品牌/色板 : %s" % P["palette"])
    print("      %s" % PALETTE_NOTE.get(P["palette"], ""))
    print("  [2] 图例语言 : %s   （zh=中文 / en=English / both=双语）" % P["lang"])
    print("  [3] 色号标注 : %s   （brand=品牌色号 / letter=ABC / number=123）" % P["label"])
    print("  [4] 最多用色 : %s   （0=不限；常用 12/24/36）" % P["max_colors"])
    print("  [5] 每格大小 : %s px  （越大色号越清晰，brand 建议 28+）" % P["cell"])
    print("  [6] 显示坐标 : %s   （开 / 关）" % ("开" if P["coords"] else "关"))
    print("  [7] 网格线   : %s   （显示 / 隐藏）" % ("显示" if P["grid"] else "隐藏"))
    print("  [8] 立体豆感 : %s   （开 / 关）" % ("开" if P["bead"] else "关"))
    print("  [9] 图纸标题 : %s   （空=无标题）" % (P["title"] or "(无)"))
    print("  [A] 背景色   : %s   （如 #FFFFFF，空=不处理）" % (P["bg_hex"] or "(不处理)"))
    print("  [B] 底板尺寸 : %s x %s  （0=自动）" % (P["width"] or 0, P["height"] or 0))
    print()
    print("  " + "-" * 58)
    print("  [S] 开始转换    [D] 生成示例图    [0] 退出")
    print("=" * 60)


def set_palette():
    clear()
    print("选择品牌/色板：")
    print("  [1] mard   - MARD（麦德）官方 291 色，国内拼豆，色号如 H5 / F11")
    print("  [2] perler - Perler 官方 95 色（经典）")
    print("  [3] artkal - Artkal 30 色（A01-A30）")
    print("  [4] hama   - Hama 28 色（H01-H28）")
    c = ask("1234", "请选择：")
    P["palette"] = {"1": "mard", "2": "perler", "3": "artkal", "4": "hama"}[c]


def set_lang():
    clear()
    print("选择图例颜色名称语言：")
    print("  [1] zh   - 中文")
    print("  [2] en   - English")
    print("  [3] both - 中英双语")
    c = ask("123", "请选择：")
    P["lang"] = {"1": "zh", "2": "en", "3": "both"}[c]


def set_label():
    clear()
    print("选择单元格字符代码风格：")
    print("  [1] letter - A、B、C...")
    print("  [2] number - 1、2、3...")
    print("  [3] brand  - 品牌色号（如 H5 / F11），需搭配品牌色板")
    c = ask("123", "请选择：")
    P["label"] = {"1": "letter", "2": "number", "3": "brand"}[c]


def set_maxcolors():
    clear()
    print("选择最多使用几种豆色（相似颜色会自动合并）：")
    print("  [1] 0   - 不限")
    print("  [2] 8   - 极简")
    print("  [3] 12  - 精简")
    print("  [4] 16  - 适中")
    print("  [5] 24  - 丰富（推荐）")
    print("  [6] 36  - 细腻")
    c = ask("123456", "请选择：")
    P["max_colors"] = int({"1": "0", "2": "8", "3": "12", "4": "16", "5": "24", "6": "36"}[c])


def set_cell():
    clear()
    print("选择每格像素大小（越大色号越清晰，图纸也越大）：")
    print("  [1] 20   [2] 24   [3] 28   [4] 30   [5] 36")
    print("  （brand 品牌色号建议 28 以上）")
    c = ask("12345", "请选择：")
    P["cell"] = int({"1": "20", "2": "24", "3": "28", "4": "30", "5": "36"}[c])


def set_title():
    clear()
    t = input("请输入图纸顶部标题（直接回车 = 无标题）：").strip()
    P["title"] = t


def set_bg():
    clear()
    print("把指定颜色当作背景（空格不填豆）。示例：#FFFFFF（白）、#000000（黑）")
    t = input("请输入背景色HEX（直接回车 = 不处理）：").strip()
    P["bg_hex"] = t


def set_size():
    clear()
    print("当前底板尺寸: %s x %s （0=自动）" % (P["width"] or 0, P["height"] or 0))
    print("例如小底板 29 x 29；直接回车则保持 0（自动）。")
    w = input("固定宽度（格），回车=自动: ").strip()
    h = input("固定高度（格），回车=自动: ").strip()
    P["width"] = int(w) if w.isdigit() else 0
    P["height"] = int(h) if h.isdigit() else 0


def convert_menu():
    while True:
        clear()
        print("=" * 60)
        print("  选择输入方式")
        print("=" * 60)
        if PENDING_FILES:
            print("  已选文件（%d 张）：" % len(PENDING_FILES))
            for f in PENDING_FILES:
                print("    - %s" % os.path.basename(f))
            print()
            print("  [1] 用已选文件转换（可先回主菜单调参数）")
            print("  [2] 重新选择文件（清空已选）")
            print("  [3] 返回主菜单")
            print("=" * 60)
            c = ask("123", "请选择：")
            if c == "3":
                return
            if c == "1":
                run_converter(files=list(PENDING_FILES))
                continue
            PENDING_FILES.clear()
            continue
        print("  [1] 输入图片路径（可把一张或多张图片拖进窗口）")
        print("  [2] 弹出文件选择框（推荐，支持中文/带空格路径）")
        print("  [3] 返回主菜单")
        print("=" * 60)
        c = ask("123", "请选择：")
        if c == "3":
            return
        if c == "2":
            run_converter(pick=True)
            continue
        print()
        print("请把图片文件拖进此窗口后回车；也可以直接输入完整路径。")
        print("（一次可拖多张，多个文件用空格隔开）")
        text = input().strip()
        if not text:
            print("未输入任何路径，返回菜单。")
            input("按回车键继续...")
            continue
        try:
            files = shlex.split(text)
        except ValueError:
            files = text.split()
        files = [f for f in files if os.path.isfile(f)]
        if not files:
            print("未输入有效路径，返回菜单。")
            input("按回车键继续...")
            continue
        run_converter(files=files)


def main_menu_loop():
    while True:
        show_menu()
        c = ask("0123456789absd", "请选择要调节的参数：")
        if c == "0":
            print("再见！")
            return
        if c == "s":
            convert_menu()
        elif c == "d":
            run_converter(demo=True)
        elif c == "1":
            set_palette()
        elif c == "2":
            set_lang()
        elif c == "3":
            set_label()
        elif c == "4":
            set_maxcolors()
        elif c == "5":
            set_cell()
        elif c == "6":
            P["coords"] = not P["coords"]
        elif c == "7":
            P["grid"] = not P["grid"]
        elif c == "8":
            P["bead"] = not P["bead"]
        elif c == "9":
            set_title()
        elif c == "a":
            set_bg()
        elif c == "b":
            set_size()


def main():
    global PENDING_FILES
    # 拖入到 bat 图标上的文件先进菜单，由用户先调参数再转换（不直接转换）
    PENDING_FILES = [a for a in sys.argv[1:] if os.path.isfile(a)]
    main_menu_loop()


if __name__ == "__main__":
    main()
