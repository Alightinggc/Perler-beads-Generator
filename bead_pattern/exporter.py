"""导出：色号清单 CSV、网格代码 CSV。"""

from __future__ import annotations

import csv

from .converter import Pattern


def save_legend_csv(path: str, pattern: Pattern, codes: dict[int, str]) -> None:
    """导出颜色用量清单：code, brand_code, name, name_en, hex, count。"""
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["code", "brand_code", "name", "name_en", "hex", "count"])
        for idx in sorted(pattern.counts.keys(), key=lambda i: codes.get(i, "")):
            color = pattern.color_of(idx)
            w.writerow([
                codes.get(idx, ""),
                color.code,
                color.name,
                color.name_en,
                color.hex,
                pattern.counts[idx],
            ])


def save_grid_csv(path: str, pattern: Pattern, codes: dict[int, str]) -> None:
    """导出网格（行列=图纸坐标，单元格=字符代码）。"""
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        for y in range(pattern.height):
            row = []
            for x in range(pattern.width):
                idx = pattern.grid[y][x]
                row.append(codes.get(idx, ""))
            w.writerow(row)


def summary_text(pattern: Pattern, codes: dict[int, str]) -> str:
    """打印用的人读摘要。"""
    lines = [
        f"图纸尺寸: {pattern.width} x {pattern.height} 格",
        f"有效豆数: {pattern.bead_count()} 颗",
        f"用色数量: {len(pattern.counts)} 种",
    ]
    for idx in sorted(pattern.counts.keys(), key=lambda i: codes.get(i, "")):
        color = pattern.color_of(idx)
        lines.append(f"  {codes.get(idx, ''):<4} {color.code:<5} {color.name:<8} {color.hex}  x{pattern.counts[idx]}")
    return "\n".join(lines)
