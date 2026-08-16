#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""拼豆图纸「精简版」打包入口。

把图片拖到生成的 exe 上（或命令行传图片路径），按精简版默认参数批量转换：
palette=mard / label=brand / max-colors=24 / cell=30 / 显示坐标 / 不导出 CSV。
"""
import os
import sys


def _app_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def _default_args() -> list[str]:
    return [
        "--palette", "mard",
        "--label-style", "brand",
        "--max-colors", "24",
        "--cell", "30",
        "--coords",
        "--no-colors-csv",
        "--no-grid-csv",
    ]


def main() -> int:
    os.chdir(_app_dir())

    import main as main_mod

    files = [a for a in sys.argv[1:] if os.path.isfile(a)]
    if not files:
        print("请把图片文件拖到本程序图标上，或用命令行传入图片路径。")
        print("示例: 拼豆图纸精简版.exe 图片.png")
        return 1

    for f in files:
        print()
        print("=" * 60)
        print("处理: %s" % os.path.basename(f))
        print("=" * 60)
        try:
            main_mod.main([f] + _default_args())
        except Exception as e:  # noqa: BLE001
            print("处理失败: %s" % e)
    return 0


if __name__ == "__main__":
    try:
        rc = main()
    except Exception as e:  # noqa: BLE001
        print("发生错误: %s" % e)
        rc = 1
    input("全部完成，按回车键关闭...")
    sys.exit(rc)
