#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把四个工具打包成独立 exe（PyInstaller onefile）。

用法:
    python packaging/build_exe.py
    （或双击 packaging/build_exe.bat，会自动先装 PyInstaller）

产物在 dist/ 目录，无需 Python / numpy / Pillow 即可直接运行。
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable
SEP = ";" if os.name == "nt" else ":"
DIST = os.path.join(ROOT, "dist")
WORK = os.path.join(ROOT, "build")
SPEC = os.path.join(ROOT, "packaging")


def data(src_rel: str, dst_rel: str) -> str:
    return os.path.join(ROOT, src_rel) + SEP + dst_rel


MARD = data(os.path.join("bead_pattern", "data", "mard.json"), os.path.join("bead_pattern", "data"))
WEB = data("web", "web")

# (最终中文名, 构建用英文名, 入口脚本, 附加数据, 隐藏导入)
TARGETS = [
    ("拼豆图纸精简版", "bead_lite", "packaging/entry_lite.py", [MARD], ["main"]),
    ("拼豆图纸参数自选", "bead_menu", "interactive.py", [MARD], ["main"]),
    ("拼豆图纸网页版", "bead_web", "webui.py", [MARD, WEB], ["main"]),
    ("像素画缩小", "pixel_shrink", "shrink_pixel_art.py", [], []),
]


def build_one(final_name: str, build_name: str, entry: str, datas: list[str], hidden: list[str]) -> str:
    cmd = [
        PY, "-m", "PyInstaller",
        "--noconfirm", "--clean",
        "--onefile", "--console",
        "--name", build_name,
        "--paths", ROOT,
        "--distpath", DIST,
        "--workpath", WORK,
        "--specpath", SPEC,
    ]
    for d in datas:
        cmd += ["--add-data", d]
    for h in hidden:
        cmd += ["--hidden-import", h]
    cmd.append(os.path.join(ROOT, entry))

    print()
    print("=" * 72)
    print("构建: %s  (入口 %s)" % (final_name, entry))
    print("=" * 72)
    subprocess.run(cmd, cwd=ROOT, check=True)

    ext = ".exe" if os.name == "nt" else ""
    built = os.path.join(DIST, build_name + ext)
    final = os.path.join(DIST, final_name + ext)
    if os.path.exists(final):
        os.remove(final)
    os.rename(built, final)
    print("完成 -> %s" % final)
    return final


def main() -> int:
    os.makedirs(DIST, exist_ok=True)
    for final_name, build_name, entry, datas, hidden in TARGETS:
        build_one(final_name, build_name, entry, datas, hidden)
    print()
    print("全部完成，产物在: %s" % DIST)
    return 0


if __name__ == "__main__":
    sys.exit(main())
