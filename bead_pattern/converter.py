"""图片 -> 拼豆网格的核心转换逻辑。

流程：
1. 读图（RGB）
2. 保持原图尺寸（每个像素 = 1 颗豆），仅在超过上限时等比缩小
3. 每个像素在 Lab 色彩空间映射到最接近的标准豆色
4. 可选：用贪心算法在色板中挑选“最能代表本图”的 N 种豆色，
   把相似/模糊颜色统一成最常用的几种色号
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from PIL import Image

from .color import distance_matrix
from .palettes import BeadColor, Palette


@dataclass
class PatternOptions:
    size: int = 200            # 最大边长（超过才等比缩小，图片 ≤ 此值时保持原尺寸）
    width: int = 0             # 固定宽度（格），0=不指定
    height: int = 0            # 固定高度（格），0=不指定
    metric: str = "ciede2000"  # ciede2000 | cie76
    max_colors: int = 0        # 0 = 不限（用满色板）
    dither: bool = False       # Floyd-Steinberg 抖动（默认关闭）


@dataclass
class Pattern:
    width: int
    height: int
    grid: list[list[int]]          # 每格：色板下标
    palette: Palette
    used_indices: list[int] = field(default_factory=list)  # 用到的色板下标
    counts: dict[int, int] = field(default_factory=dict)   # 下标 -> 豆数

    def cell_count(self) -> int:
        return self.width * self.height

    def bead_count(self) -> int:
        return sum(self.counts.values())

    def color_of(self, idx: int) -> BeadColor | None:
        return self.palette.colors[idx] if 0 <= idx < len(self.palette.colors) else None


# ---------------------------------------------------------------------------
# 网格尺寸
# ---------------------------------------------------------------------------
def fit_grid_size(img_w: int, img_h: int, opts: PatternOptions) -> tuple[int, int]:
    if opts.width > 0 and opts.height > 0:
        gw, gh = opts.width, opts.height
    elif opts.width > 0:
        gw = opts.width
        gh = max(1, round(img_h * gw / img_w))
    elif opts.height > 0:
        gh = opts.height
        gw = max(1, round(img_w * gh / img_h))
    else:
        size = max(1, opts.size)
        if img_w >= img_h:
            gw = size
            gh = max(1, round(img_h * size / img_w))
        else:
            gh = size
            gw = max(1, round(img_w * size / img_h))
    return int(gw), int(gh)


# ---------------------------------------------------------------------------
# 读取与降采样
# ---------------------------------------------------------------------------
def load_rgb(path: str) -> np.ndarray:
    """返回 rgb (H,W,3) uint8。"""
    with Image.open(path) as im:
        im = im.convert("RGB")
        return np.asarray(im, dtype=np.uint8)


def downsample(rgb: np.ndarray, gw: int, gh: int) -> np.ndarray:
    """把 RGB 数组等比缩放到 gw x gh，返回 (gh, gw, 3) uint8。"""
    im = Image.fromarray(rgb)
    im = im.resize((gw, gh), Image.LANCZOS)
    return np.asarray(im, dtype=np.uint8)


# ---------------------------------------------------------------------------
# 色号分配（字母/数字/品牌）
# ---------------------------------------------------------------------------
def col_name(n: int) -> str:
    """n(0-based) -> Excel 式列名：0->A, 25->Z, 26->AA。"""
    s = ""
    while n >= 0:
        s = chr(ord("A") + n % 26) + s
        n = n // 26 - 1
    return s


def assign_codes(
    used_indices: list[int], style: str = "letter", palette: Palette | None = None
) -> dict[int, str]:
    """按“使用频率降序”为每个用到的色板下标分配一个短代码。

    style:
      - letter: A, B, C ... Z, AA, AB ...（最像市面图纸的短代码）
      - number: 1, 2, 3 ...
      - brand : 使用色板自带色号（如 P01 / A01 / H01），需传 palette
    """
    codes: dict[int, str] = {}
    for i, idx in enumerate(used_indices):
        if style == "letter":
            codes[idx] = col_name(i)
        elif style == "number":
            codes[idx] = str(i + 1)
        elif style == "brand" and palette is not None:
            codes[idx] = palette.colors[idx].code
        else:
            codes[idx] = str(i + 1)
    return codes


# ---------------------------------------------------------------------------
# 颜色映射 + 自动减色
# ---------------------------------------------------------------------------
def map_to_palette(rgb: np.ndarray, palette: Palette, metric: str) -> np.ndarray:
    """把 (H,W,3) 的每个像素映射到最近色板下标，返回 (H,W) int。"""
    flat = rgb.reshape(-1, 3).astype(np.float64)
    d = distance_matrix(flat, palette.rgb_array(), metric)
    return d.argmin(axis=1).reshape(rgb.shape[:2])


def _dither_assign(rgb: np.ndarray, used: list[int], palette: Palette) -> np.ndarray:
    """Floyd-Steinberg 抖动映射：在 used 色号子集内逐像素量化并把误差扩散到相邻像素。

    返回 (H,W) int 数组（色板下标）。
    误差在 RGB 空间按 7/16、3/16、5/16、1/16 比例扩散到右、左下、下、右下。
    """
    h, w = rgb.shape[:2]
    used_arr = np.array(used, dtype=np.int64)
    used_rgb = palette.rgb_array()[used_arr]  # (K,3)
    work = rgb.astype(np.float64).copy()
    assign = np.full((h, w), 0, dtype=np.int64)
    for y in range(h):
        for x in range(w):
            old = work[y, x]
            d = ((used_rgb - old) ** 2).sum(axis=1)
            k = int(d.argmin())
            idx = int(used_arr[k])
            assign[y, x] = idx
            err = old - used_rgb[k]
            if x + 1 < w:
                work[y, x + 1] += err * (7 / 16)
            if y + 1 < h:
                if x > 0:
                    work[y + 1, x - 1] += err * (3 / 16)
                work[y + 1, x] += err * (5 / 16)
                if x + 1 < w:
                    work[y + 1, x + 1] += err * (1 / 16)
    return assign


def select_optimal_colors(
    rgb: np.ndarray, palette: Palette, max_colors: int, metric: str
) -> list[int]:
    """贪心选取最多 max_colors 种“最能代表本图”的豆色。

    每次加入一个使总色差下降最多的色号，直到数量达标或不再有收益。
    """
    flat = rgb.reshape(-1, 3).astype(np.float64)
    d = distance_matrix(flat, palette.rgb_array(), metric)  # (N, K)
    n, k = d.shape
    chosen: list[int] = []
    best = np.full(n, np.inf)

    # 第一步：选让总距离最小的单色
    first = int(d.sum(axis=0).argmin())
    chosen.append(first)
    best = np.minimum(best, d[:, first])

    while len(chosen) < max_colors:
        gain = np.maximum(0.0, best[:, None] - d).sum(axis=0)  # (K,)
        # 已选的颜色 gain 一定为 0，忽略
        gain[chosen] = -1.0
        nxt = int(gain.argmax())
        if gain[nxt] <= 0:
            break
        chosen.append(nxt)
        best = np.minimum(best, d[:, nxt])
    return chosen


def build_pattern(rgb: np.ndarray, palette: Palette, opts: PatternOptions) -> Pattern:
    """核心入口：rgb (H,W,3) 原图 -> Pattern 网格。

    默认保持原图尺寸（每像素 = 1 颗豆），仅在以下情况缩放：
    - --width / --height 指定了固定网格
    - 图片任一边超过 --size 上限
    """
    img_h, img_w = rgb.shape[:2]

    # 决定是否需要缩放
    if opts.width > 0 or opts.height > 0:
        # 用户指定了固定宽/高 → 强制缩放
        gw, gh = fit_grid_size(img_w, img_h, opts)
        small_rgb = downsample(rgb, gw, gh)
    elif opts.size > 0 and max(img_w, img_h) > opts.size:
        # 图片超过上限 → 等比缩小
        gw, gh = fit_grid_size(img_w, img_h, opts)
        small_rgb = downsample(rgb, gw, gh)
    else:
        # 保持原图尺寸
        gw, gh = img_w, img_h
        small_rgb = rgb

    flat = small_rgb.reshape(-1, 3).astype(np.float64)

    # 选出用到的色号子集
    if opts.max_colors and opts.max_colors < len(palette.colors):
        used = select_optimal_colors(small_rgb, palette, opts.max_colors, opts.metric)
    else:
        d = distance_matrix(flat, palette.rgb_array(), opts.metric)
        assignment = d.argmin(axis=1)
        used = sorted(set(assignment.tolist()))

    # 在子集内映射（可选 Floyd-Steinberg 抖动；默认关闭，开启能更好还原渐变/过渡色）
    if opts.dither:
        assign = _dither_assign(small_rgb, used, palette)
    else:
        used_arr = np.array(used, dtype=np.int64)
        d_sub = distance_matrix(flat, palette.rgb_array()[used_arr], opts.metric)
        assign = used_arr[d_sub.argmin(axis=1)].reshape(gh, gw)

    grid = []
    counts: dict[int, int] = {}
    for y in range(gh):
        row = []
        for x in range(gw):
            c = int(assign[y, x])
            row.append(c)
            counts[c] = counts.get(c, 0) + 1
        grid.append(row)

    # used_indices 按使用频率降序（决定 A/B/C 分配顺序）
    used_indices = sorted(counts.keys(), key=lambda i: (-counts[i], i))
    return Pattern(
        width=gw,
        height=gh,
        grid=grid,
        palette=palette,
        used_indices=used_indices,
        counts=counts,
    )


# 供外部使用的品牌色号分配（需 palette）
def brand_code_of(palette: Palette, idx: int) -> str:
    return palette.colors[idx].code
