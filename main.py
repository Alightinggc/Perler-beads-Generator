#!/usr/bin/env python3
"""拼豆图纸转换器 - 命令行入口。

示例：
  python main.py 照片.png                          # 基础转换（保持原尺寸）
  python main.py 照片.png --max-colors 24 --coords  # 24色+坐标
  python main.py 照片.png --size 29 --max-colors 12 # 限制最多 29×29，最多 12 色
  python main.py --demo                             # 生成示例图并转换
  python main.py --pick                             # 弹窗选图

详细说明见 README.md。
"""

from __future__ import annotations

import argparse
import os
import sys


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="拼豆图纸转换器",
        description="把一张图片转换成带字符色号的拼豆图纸（Perler Bead Pattern）。",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("input", nargs="?", help="输入图片路径（PNG/JPG/WebP 等）")
    p.add_argument("-o", "--output", help="输出图纸 PNG 路径（默认 <输入名>_pattern.png）")

    # 网格
    g = p.add_argument_group("网格尺寸")
    g.add_argument("--size", type=int, default=200, help="最大边长上限（超过才等比缩小；图片本身 ≤ 此值则保持原尺寸，每像素 = 1 颗豆）")
    g.add_argument("--width", type=int, default=0, help="固定宽度（格），0=自动")
    g.add_argument("--height", type=int, default=0, help="固定高度（格），0=自动")

    # 颜色
    g = p.add_argument_group("颜色映射")
    g.add_argument("--palette", default="perler",
                   help="内置色板: perler / artkal / hama / mard（MARD 291色，色号如 H5、F11）")
    g.add_argument("--palette-file", help="自定义色板 CSV（code,name,hex[,name_en]）")
    g.add_argument("--metric", default="ciede2000", choices=["ciede2000", "cie76"],
                   help="色差度量：ciede2000 更准，cie76 更快")
    g.add_argument("--max-colors", type=int, default=0,
                   help="最多用几种豆色（0=不限）。会贪心挑选最能代表本图的色号，自动合并相似颜色")
    g.add_argument("--dither", dest="dither", action="store_true", default=False,
                   help="开启Floyd-Steinberg抖动（默认关闭；开启能更好还原渐变/过渡色）")

    # 标注
    g = p.add_argument_group("字符标注")
    g.add_argument("--label-style", default="letter", choices=["letter", "number", "brand"],
                   help="单元格字符代码：letter=A,B,C... / number=1,2,3... / brand=品牌色号")
    g.add_argument("--cell", type=int, default=24, help="每格像素大小（越大代码越清晰）")
    g.add_argument("--no-grid-lines", action="store_true", help="不画网格线")
    g.add_argument("--coords", action="store_true", help="显示行列坐标（A、B、C... 与 1、2、3...）")
    g.add_argument("--no-legend", action="store_true", help="不输出底部色号图例")
    g.add_argument("--title", default="", help="图纸顶部标题文字")
    g.add_argument("--bead-look", action="store_true", help="给豆子加内阴影，模拟实物观感")
    g.add_argument("--lang", default="zh", choices=["zh", "en", "both"],
                   help="图例颜色名称语言")

    # 输出
    g = p.add_argument_group("输出文件")
    g.add_argument("--no-colors-csv", action="store_true", help="不导出颜色清单 CSV")
    g.add_argument("--no-grid-csv", action="store_true", help="不导出网格代码 CSV")

    # 工具
    g = p.add_argument_group("其他")
    g.add_argument("--demo", action="store_true", help="生成一张示例图片并转换")
    g.add_argument("--pick", action="store_true", help="弹出文件选择框选择图片")
    g.add_argument("--out-dir", default="output", help="输出目录（默认 output/，自动创建）")
    return p

def _make_demo_image(path: str, size: tuple[int, int] = (160, 160)) -> None:
    """生成一张彩色演示图片（用于 --demo），含多种颜色便于观察转换/减色效果。"""
    from PIL import Image, ImageDraw

    img = Image.new("RGB", size, "white")
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, size[0] - 1, size[1] - 1], fill=(245, 245, 245))

    cx, cy = size[0] // 2, size[1] // 2
    r = size[0] * 0.30
    # 黄色圆脸
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 214, 0))
    # 眼睛
    er = r * 0.13
    d.ellipse([cx - r * 0.42 - er, cy - r * 0.25 - er, cx - r * 0.42 + er, cy - r * 0.25 + er],
              fill=(40, 40, 40))
    d.ellipse([cx + r * 0.42 - er, cy - r * 0.25 - er, cx + r * 0.42 + er, cy - r * 0.25 + er],
              fill=(40, 40, 40))
    # 微笑
    d.arc([cx - r * 0.55, cy - r * 0.35, cx + r * 0.55, cy + r * 0.55],
          start=20, end=160, fill=(40, 40, 40), width=max(3, int(r * 0.09)))
    # 腮红
    br = r * 0.18
    d.ellipse([cx - r * 0.7, cy + r * 0.15, cx - r * 0.7 + 2 * br, cy + r * 0.15 + 2 * br],
              fill=(255, 120, 130))
    d.ellipse([cx + r * 0.7 - 2 * br, cy + r * 0.15, cx + r * 0.7, cy + r * 0.15 + 2 * br],
              fill=(255, 120, 130))

    img.save(path)


def _pick_file() -> str:
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()
    path = filedialog.askopenfilename(
        title="选择要转换的图片",
        filetypes=[("图片", "*.png *.jpg *.jpeg *.bmp *.webp *.gif"), ("所有文件", "*.*")],
    )
    root.destroy()
    return path


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    # 是否由用户显式指定了 --out-dir（否则默认按输入文件名建同名子文件夹）
    explicit_outdir = args.out_dir != "output"

    if args.demo:
        demo_dir = os.path.abspath(os.path.join(args.out_dir, "_demo"))
        os.makedirs(demo_dir, exist_ok=True)
        demo_input = os.path.join(demo_dir, "_demo_input.png")
        if not os.path.exists(demo_input):
            _make_demo_image(demo_input)
        args.input = demo_input
        if not args.output:
            args.output = os.path.join(demo_dir, "_demo_pattern.png")
        out_dir = demo_dir
    elif args.pick and not args.input:
        args.input = _pick_file()
        if not args.input:
            print("未选择文件，退出。")
            return 1

    if not args.input:
        build_parser().print_help()
        print("\n错误：请提供输入图片路径，或使用 --pick / --demo。")
        return 1
    if not os.path.exists(args.input):
        print(f"错误：找不到输入文件 {args.input}")
        return 1

    # 输出目录：未显式指定 --out-dir 时，输出到 output/原文件名_品牌_最大颜色数/ 子文件夹
    # （同名文件夹自动加 (1)(2)...，每个转换批次独立文件夹，互不覆盖）
    stem = os.path.splitext(os.path.basename(args.input))[0]
    if explicit_outdir:
        out_dir = os.path.abspath(args.out_dir)
    else:
        base = os.path.join(args.out_dir, f"{stem}_{args.palette}_{args.max_colors}")
        out_dir = os.path.abspath(base)
        n = 0
        while os.path.isdir(out_dir):
            n += 1
            out_dir = os.path.abspath(f"{base} ({n})")
    os.makedirs(out_dir, exist_ok=True)

    # 色板
    from bead_pattern.palettes import load_palette, load_palette_csv

    if args.palette_file:
        palette = load_palette_csv(args.palette_file)
    else:
        palette = load_palette(args.palette)

    # 转换
    from bead_pattern.converter import (
        PatternOptions,
        assign_codes,
        build_pattern,
        load_rgb,
    )
    from bead_pattern.exporter import (
        save_grid_csv,
        save_legend_csv,
        summary_text,
    )
    from bead_pattern.renderer import RenderOptions, render_pattern

    opts = PatternOptions(
        size=args.size,
        width=args.width,
        height=args.height,
        metric=args.metric,
        max_colors=args.max_colors,
        dither=args.dither,
    )

    print(f"读取图片: {args.input}")
    rgb = load_rgb(args.input)
    print(f"原图尺寸: {rgb.shape[1]} x {rgb.shape[0]}  使用色板: {palette.name}（{len(palette.colors)}色）")
    pattern = build_pattern(rgb, palette, opts)
    codes = assign_codes(pattern.used_indices, args.label_style, palette)

    print()
    print(summary_text(pattern, codes))
    print()

    # 输出文件名（默认格式：原文件名_品牌_最大颜色数_pattern.png）
    if args.output:
        out_png = args.output
    else:
        # 同名文件自动加 (1)(2)...，避免覆盖
        base_name = os.path.join(out_dir, f"{stem}_{args.palette}_{args.max_colors}")
        out_png = f"{base_name}_pattern.png"
        n = 0
        while os.path.exists(out_png):
            n += 1
            out_png = f"{base_name} ({n})_pattern.png"
    out_csv = f"{os.path.splitext(out_png)[0]}_colors.csv"
    out_grid = f"{os.path.splitext(out_png)[0]}_grid.csv"

    r_opts = RenderOptions(
        cell=args.cell,
        grid_lines=not args.no_grid_lines,
        coords=args.coords,
        legend=not args.no_legend,
        title=args.title,
        bead_look=args.bead_look,
        text_lang=args.lang,
    )
    img = render_pattern(pattern, codes, r_opts)
    img.save(out_png)
    print(f"图纸已保存: {out_png}（{img.width} x {img.height} px）")

    if not args.no_colors_csv:
        save_legend_csv(out_csv, pattern, codes)
        print(f"颜色清单已保存: {out_csv}")
    if not args.no_grid_csv:
        save_grid_csv(out_grid, pattern, codes)
        print(f"网格代码已保存: {out_grid}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
