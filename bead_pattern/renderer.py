"""把 Pattern 网格渲染成带字符代码的拼豆图纸 PNG。

布局（自上而下）：
  [可选标题条]
  [列坐标头 1 2 3 ...]（可选）
  [行坐标头 A B C ... + 网格单元格（每个格 = 1 颗豆，中心标字符代码）]
  [色号图例：色块 + 代码 + 名称 + 颗数]
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from PIL import Image, ImageDraw, ImageFont

from .converter import Pattern, col_name

_FONT_DIRS = [
    "C:/Windows/Fonts",
    "/System/Library/Fonts",
    "/usr/share/fonts/truetype/dejavu",
    "/Library/Fonts",
]


@dataclass
class RenderOptions:
    cell: int = 24                 # 每格像素
    grid_lines: bool = True        # 画网格线
    coords: bool = False           # 行列坐标
    legend: bool = True            # 底部色号图例
    title: str = ""                # 顶部标题
    bead_look: bool = False        # 模拟豆子的内阴影
    text_lang: str = "zh"          # 图例名称语言 zh / en / both
    bg_color: tuple[int, int, int] = (255, 255, 255)  # 画布底色
    empty_color: tuple[int, int, int] = (230, 230, 230)  # 空格底色
    margin: int = 8
    header_frac: float = 0.72      # 坐标头宽度/高度相对 cell


# ---------------------------------------------------------------------------
# 字体
# ---------------------------------------------------------------------------
_FONT_CACHE: dict[str, ImageFont.FreeTypeFont | ImageFont.ImageFont] = {}


def _find_font_file(name: str) -> str | None:
    for d in _FONT_DIRS:
        p = os.path.join(d, name)
        if os.path.exists(p):
            return p
    return None


def _latin_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """单元格字符代码字体（等宽/拉丁）。"""
    key = f"latin:{size}"
    if key not in _FONT_CACHE:
        path = _find_font_file("arial.ttf") or _find_font_file("consola.ttf") or _find_font_file("DejaVuSans.ttf")
        _FONT_CACHE[key] = ImageFont.truetype(path, size) if path else ImageFont.load_default()
    return _FONT_CACHE[key]


def _cjk_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """图例文字字体（含中文）。"""
    key = f"cjk:{size}"
    if key not in _FONT_CACHE:
        path = (
            _find_font_file("msyh.ttc")
            or _find_font_file("simhei.ttf")
            or _find_font_file("simsun.ttc")
            or _find_font_file("arial.ttf")
        )
        _FONT_CACHE[key] = ImageFont.truetype(path, size) if path else ImageFont.load_default()
    return _FONT_CACHE[key]


def _text_color(rgb: tuple[int, int, int]) -> tuple[int, int, int]:
    lum = 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]
    return (20, 20, 20) if lum > 150 else (255, 255, 255)


def _fit_font(draw: ImageDraw.ImageDraw, text: str, max_w: int, max_h: int) -> ImageFont.FreeTypeFont:
    """在 max_w x max_h 内尽量大的字体。"""
    size = int(max_h * 0.62)
    while size > 6:
        f = _latin_font(size)
        w = draw.textlength(text, font=f)
        if w <= max_w and size <= max_h:
            return f
        size -= 1
    return _latin_font(max(6, size))


def _centered_text(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    text: str,
    font,
    fill,
):
    x0, y0, x1, y1 = box
    tw = draw.textlength(text, font=font)
    # 用 textbbox 计算真实高度
    bbox = draw.textbbox((0, 0), text, font=font)
    th = bbox[3] - bbox[1]
    tx = x0 + (x1 - x0 - tw) / 2
    ty = y0 + (y1 - y0 - th) / 2 - bbox[1]
    draw.text((tx, ty), text, font=font, fill=fill)


# ---------------------------------------------------------------------------
# 主渲染
# ---------------------------------------------------------------------------
def render_pattern(
    pattern: Pattern,
    codes: dict[int, str],
    opts: RenderOptions,
) -> Image.Image:
    gw, gh = pattern.width, pattern.height
    cell = max(4, opts.cell)
    margin = opts.margin

    # 坐标头尺寸
    hdr = int(cell * opts.header_frac) if opts.coords else 0
    hdr = max(hdr, 0)

    # 顶部标题条
    title_h = 0
    if opts.title:
        title_h = int(cell * 0.9)

    grid_w = gw * cell + (gw + 1) * (1 if opts.grid_lines else 0)
    grid_h = gh * cell + (gh + 1) * (1 if opts.grid_lines else 0)

    # ---- 先绘制网格主体，用于确定图例宽度 ----
    body_w = hdr + grid_w
    body_h = hdr + grid_h
    grid_x0 = margin + hdr
    grid_y0 = margin + title_h + hdr

    # 图例
    legend_h = 0
    legend_items = _legend_items(pattern, codes, opts.text_lang)
    if opts.legend and legend_items:
        legend_h, legend_w = _measure_legend(legend_items, body_w + margin * 2, cell, opts)
    else:
        legend_w = 0

    canvas_w = max(body_w + margin * 2, legend_w + margin * 2)
    canvas_h = margin + title_h + hdr + grid_h + margin + legend_h + margin

    img = Image.new("RGB", (canvas_w, canvas_h), opts.bg_color)
    draw = ImageDraw.Draw(img)

    # 标题
    if opts.title:
        f = _cjk_font(int(title_h * 0.6))
        draw.text((margin, margin + (title_h - f.size) / 2), opts.title, font=f, fill=(40, 40, 40))

    # 坐标头
    if opts.coords:
        draw.rectangle([margin, grid_y0 - hdr, margin + hdr - 1, grid_y0 - 1], fill=(40, 40, 40))
        fcol = _latin_font(int(hdr * 0.6))
        for x in range(gw):
            x0 = grid_x0 + x * (cell + 1) if opts.grid_lines else grid_x0 + x * cell
            x1 = x0 + cell
            draw.rectangle([x0, grid_y0 - hdr, x1, grid_y0 - 1], fill=(40, 40, 40))
            _centered_text(draw, (x0, grid_y0 - hdr, x1, grid_y0), str(x + 1), fcol, (255, 255, 255))
        frow = _cjk_font(int(hdr * 0.6))
        for y in range(gh):
            y0 = grid_y0 + y * (cell + 1) if opts.grid_lines else grid_y0 + y * cell
            y1 = y0 + cell
            draw.rectangle([margin, y0, margin + hdr - 1, y1], fill=(40, 40, 40))
            _centered_text(draw, (margin, y0, margin + hdr - 1, y1), col_name(y), frow, (255, 255, 255))

    # 网格单元格
    for y in range(gh):
        for x in range(gw):
            y0 = grid_y0 + y * (cell + 1) if opts.grid_lines else grid_y0 + y * cell
            x0 = grid_x0 + x * (cell + 1) if opts.grid_lines else grid_x0 + x * cell
            y1, x1 = y0 + cell, x0 + cell
            idx = pattern.grid[y][x]
            if idx < 0:
                draw.rectangle([x0, y0, x1 - 1, y1 - 1], fill=opts.empty_color)
                if opts.grid_lines:
                    draw.rectangle([x0, y0, x1 - 1, y1 - 1], outline=(120, 120, 120))
                continue

            color = pattern.color_of(idx).rgb
            draw.rectangle([x0, y0, x1 - 1, y1 - 1], fill=color)

            if opts.bead_look:
                # 模拟豆子：右侧/底部加一圈深色内描边
                dark = tuple(max(0, c - 55) for c in color)
                draw.rectangle([x1 - 4, y0 + 1, x1 - 1, y1 - 1], fill=dark)
                draw.rectangle([x0 + 1, y1 - 4, x1 - 1, y1 - 1], fill=dark)

            if opts.grid_lines:
                draw.rectangle([x0, y0, x1 - 1, y1 - 1], outline=(60, 60, 60))

            # 字符代码
            label = codes.get(idx, "")
            if label:
                font = _fit_font(draw, label, cell - 4, cell - 4)
                _centered_text(draw, (x0 + 1, y0 + 1, x1 - 1, y1 - 1), label, font, _text_color(color))

    # 图例
    if opts.legend and legend_items:
        _draw_legend(img, draw, legend_items, margin, grid_y0 + grid_h + margin, cell, opts, body_w + margin * 2)

    return img


# ---------------------------------------------------------------------------
# 图例
# ---------------------------------------------------------------------------
def _legend_items(pattern: Pattern, codes: dict[int, str], text_lang: str):
    """返回按代码排序的 [(code, color, name_text, count)]。"""
    items = []
    for idx in sorted(pattern.counts.keys(), key=lambda i: codes.get(i, "")):
        color = pattern.color_of(idx)
        code = codes.get(idx, "")
        if text_lang == "en":
            name = color.name_en or color.name
        elif text_lang == "both":
            name = f"{color.name} {color.name_en}".strip()
        else:
            name = color.name
        items.append((code, color.rgb, name, pattern.counts[idx]))
    return items


def _measure_legend(items, max_w: int, cell: int, opts: RenderOptions) -> tuple[int, int]:
    """估算图例高度/宽度（先画一遍测量）。"""
    dummy = Image.new("RGB", (1, 1))
    dd = ImageDraw.Draw(dummy)
    swatch = cell
    f = _cjk_font(max(10, int(cell * 0.55)))
    pad = 10
    item_w = 0
    for code, rgb, name, cnt in items:
        text = f"{code}  {name}  x{cnt}"
        w = swatch + pad + dd.textlength(text, font=f)
        item_w = max(item_w, w)
    item_w = int(item_w) + pad * 2

    avail_w = max(max_w, item_w)
    cols = max(1, avail_w // item_w)
    rows = (len(items) + cols - 1) // cols
    row_h = cell + 8
    title_h = int(cell * 1.2)
    total_h = int(title_h + rows * row_h + pad)
    total_w = int(cols * item_w)
    return total_h, total_w


def _draw_legend(img, draw, items, margin, y_top, cell, opts, max_w: int):
    swatch = cell
    pad = 10
    f = _cjk_font(max(10, int(cell * 0.55)))
    ftitle = _cjk_font(int(cell * 0.7))

    # 先测量最宽项，确定列数
    item_w = 0
    for code, rgb, name, cnt in items:
        text = f"{code}  {name}  x{cnt}"
        w = swatch + pad + draw.textlength(text, font=f)
        item_w = max(item_w, w)
    item_w = int(item_w) + pad * 2

    avail_w = img.width - margin * 2
    cols = max(1, avail_w // item_w)
    # 背景
    draw.rectangle([margin, y_top, img.width - margin, y_top + _measure_legend(items, avail_w, cell, opts)[0] - 1],
                   fill=(245, 245, 245))
    draw.text((margin + pad, y_top + 2), "色号图例 Color Legend", font=ftitle, fill=(40, 40, 40))

    row_h = cell + 8
    for i, (code, rgb, name, cnt) in enumerate(items):
        col = i % cols
        row = i // cols
        x = margin + pad + col * item_w
        y = y_top + int(cell * 1.2) + row * row_h
        draw.rectangle([x, y, x + swatch - 1, y + swatch - 1], fill=rgb, outline=(80, 80, 80))
        text = f"{code}  {name}  x{cnt}"
        draw.text((x + swatch + pad, y + 1), text, font=f, fill=(40, 40, 40))
