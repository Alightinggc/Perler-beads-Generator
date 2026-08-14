#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""像素画缩小工具 —— 自动把“大像素格”的像素画图片缩回单像素风格。

背景
----
很多像素画图片并不是“一个逻辑像素 = 1 个屏幕像素”，而是截图 / 放大保存的：
一个像素格在图片里往往占着 20×20、50×50 … 个真实像素。
这种图直接拿去拼豆转换（或观察颜色代码）时，图纸会巨大、每格看不清。

本程序会自动检测每个“像素格”占多大（块大小 block size），
再用 最近邻插值 / 块主色聚合 把它缩回单像素风格，不破坏原图的像素分布。

用法示例
--------
  python shrink_pixel_art.py 图.png                  # 自动检测并缩小（默认输出到 output_/）
  python shrink_pixel_art.py 图.png --out-dir out    # 输出到指定目录
  python shrink_pixel_art.py 图.png --block 20       # 手动指定每格 20 像素
  python shrink_pixel_art.py 图.png --block 20x10    # 每格宽 20、高 10
  python shrink_pixel_art.py 图.png --scale 0.1      # 手动指定缩小到 10%
  python shrink_pixel_art.py 图.png --info           # 只检测并打印信息，不保存
  python shrink_pixel_art.py 图.png --autocrop       # 先裁掉四周空白/边框
  python shrink_pixel_art.py 图.png --nearest        # 强制用纯最近邻缩放
  python shrink_pixel_art.py 图片目录                # 批量处理目录内所有图片
  python shrink_pixel_art.py "*.png"                 # 按通配符批量处理
  python shrink_pixel_art.py --pick                  # 弹窗选择图片

原理简介
--------
1. 自动检测块大小（两种方法互相验证）：
   a. 边界间隔众数：扫描每一行/列，找出“颜色突变点”之间的间距，
      出现最多的间距就是块大小（因为像素画里每个像素格内部颜色一致）。
   b. 重建误差：把图片缩小到 1/k 再用最近邻放大回原尺寸，
      和原图逐像素对比；当 k 正好等于真实块大小时误差趋近 0。
2. 缩小：自动模式下，块内颜色干净时用纯最近邻插值；
   块内有噪点（JPEG 压缩 / 网格线 / 抗锯齿）时把每个 k×k 块取“众数颜色”
   作为代表色（永远保留块内真实存在的颜色，绝不产生混合色），
   每个逻辑像素只保留一种干净颜色，不破坏原图的像素分布。
3. 偏移对齐：如果像素画在图片里不是从 (0,0) 对齐（有位置偏移 / 起点不对齐），
   会通过“像素格边界位置 mod 块大小”的众数估算起始偏移并裁掉对齐，
   再缩小，保证每个格取到的颜色正确。
4. 报告“重建一致性”：把缩小结果放大回原尺寸，统计与原图一致的像素比例，
   用来量化“没有破坏像素分布”。
"""

from __future__ import annotations

import argparse
import glob
import os
import re
import sys
from collections import Counter

import numpy as np
from PIL import Image, ImageFilter

Image.MAX_IMAGE_PIXELS = None  # 允许超大尺寸图片

DEFAULT_MAX_BLOCK = 64  # 自动检测时的最大候选块大小
COLOR_TOL = 35          # “两种颜色不同”判定阈值：RGB 三通道差之和超过它视为不同
ERR_TOL = 0.03          # 重建不一致比例低于该值，认为块大小正确
ANALYSIS_MAX_SIDE = 2048  # 检测用图片的最大边长（超大图先缩到该尺寸再检测，提速）
# 默认输出目录：脚本所在文件夹下的 output_
DEFAULT_OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output_")


# ---------------------------------------------------------------------------
# 基础工具
# ---------------------------------------------------------------------------

def load_image(path: str) -> Image.Image:
    """读取图片。带异常提示。"""
    img = Image.open(path)
    img.load()
    return img


def _has_alpha(img: Image.Image) -> bool:
    return img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info)


def to_rgba(img: Image.Image) -> Image.Image:
    return img.convert("RGBA")


def to_rgb(img: Image.Image) -> Image.Image:
    return img.convert("RGB")


def rgb_array(img: Image.Image) -> np.ndarray:
    """返回 int16 的 (H, W, 3) RGB 数组（int16 防止差值计算溢出）。"""
    return np.asarray(to_rgb(img), dtype=np.int16)


def analysis_image(img: Image.Image) -> Image.Image:
    """用于块大小检测的图片：超大图先按最近邻缩到 ANALYSIS_MAX_SIDE 内。
    块内纯色在最近邻缩放后仍是纯色，不影响检测结果。"""
    W, H = img.size
    if max(W, H) <= ANALYSIS_MAX_SIDE:
        return img
    r = ANALYSIS_MAX_SIDE / max(W, H)
    return img.resize((max(1, round(W * r)), max(1, round(H * r))), Image.Resampling.NEAREST)


# ---------------------------------------------------------------------------
# 1. 自动检测块大小
# ---------------------------------------------------------------------------

def _edge_maps(img: Image.Image, tol: int = COLOR_TOL) -> tuple[np.ndarray, np.ndarray]:
    """返回 (dx, dy) 边界布尔矩阵：
    - dx: (H, W-1)，行扫描的“垂直边界”（左右相邻像素颜色差 > tol）；
    - dy: (H-1, W)，列扫描的“水平边界”。
    先做 3×3 中值滤波去噪：JPEG/抗锯齿的块内噪点被抹平，硬边缘得以保留。
    """
    denoised = np.asarray(to_rgb(img).filter(ImageFilter.MedianFilter(3)), dtype=np.int16)
    dx = np.abs(np.diff(denoised, axis=1)).sum(axis=2) > tol  # (H, W-1) 垂直边界
    dy = np.abs(np.diff(denoised, axis=0)).sum(axis=2) > tol  # (H-1, W) 水平边界
    return dx, dy


def _offset_from_edges(edge_map: np.ndarray, k: int) -> int:
    """从边界位置估算像素格起始偏移：边界位置 mod 块大小的众数。

    像素画中块边界位于 偏移 + n×块大小 处，因此 (边界位置 mod 块大小) 的
    众数就是像素格相对图片左上角的起始偏移（0 表示恰好从 (0,0) 对齐）。
    """
    if k <= 1:
        return 0
    rows, cols = np.nonzero(edge_map)
    if rows.size == 0:
        return 0
    positions = cols + 1  # 边界位置（1 基）
    counts = np.bincount(positions % k, minlength=k)
    return int(np.argmax(counts))


def interval_mode_xy(img: Image.Image, max_block: int, tol: int = COLOR_TOL) -> tuple[int, int, float, float]:
    """扫描每一行/列的颜色突变点，统计相邻突变点间距的“众数”。

    水平方向（每行左右扫描）得到“块宽”cx，垂直方向（每列上下扫描）得到“块高”cy。
    同时返回众数在全部间距中的占比 conf（越高说明边界越规则、越可信）。
    检测不到返回 (1, 1, 0.0, 0.0)。
    """
    dx, dy = _edge_maps(img, tol)

    def _mode(edges: np.ndarray) -> tuple[int, float]:
        # edges: (N, M) 布尔，每行一条扫描线，True 表示该处有颜色边界
        counter: dict[int, int] = {}
        total = 0
        for row in edges:
            idx = np.flatnonzero(row) + 1  # 边界位置（1 基）
            if idx.size >= 2:
                for g in np.diff(idx).tolist():
                    # 只统计合理范围的间距；间距 1 通常是噪声/网格线，跳过
                    if 2 <= g <= max_block:
                        counter[g] = counter.get(g, 0) + 1
                        total += 1
        if not counter:
            return 1, 0.0
        best = max(counter, key=counter.get)  # 出现最多的间距 = 块大小
        return best, (counter[best] / total if total else 0.0)

    cx, conf_x = _mode(dx)     # 水平扫描 → 块宽
    cy, conf_y = _mode(dy.T)   # 垂直扫描 → 块高
    return cx, cy, conf_x, conf_y


def reconstruction_mismatch(img: Image.Image, kx: int, ky: int, tol: int = COLOR_TOL) -> float:
    """重建误差：把图缩小到 1/kx × 1/ky，再用最近邻放大回原尺寸，
    统计与原图不一致的像素比例。块大小正确时该值趋近 0。"""
    W, H = img.size
    tw, th = max(1, round(W / kx)), max(1, round(H / ky))
    if (tw, th) == (W, H):
        return 0.0
    a = rgb_array(img)
    small = to_rgb(img).resize((tw, th), Image.Resampling.NEAREST)
    recon = small.resize((W, H), Image.Resampling.NEAREST)
    b = np.asarray(recon, dtype=np.int16)
    diff = np.abs(a - b).sum(axis=2) > tol
    return float(diff.mean())


def _aligned_mismatch(a: np.ndarray, dx: int, dy: int, kx: int, ky: int,
                      tol: int = COLOR_TOL) -> float:
    """对齐后的重建误差：把图裁掉起始偏移 (dx, dy) 使其与 kx×ky 网格对齐，
    再缩小到 1/kx × 1/ky 并放大回原尺寸逐像素对比。偏移正确时该值趋近 0。"""
    if dx >= a.shape[1] or dy >= a.shape[0]:
        return 1.0
    sub = a[dy:, dx:]  # (H-dy, W-dx, 3) int16
    H, W, _ = sub.shape
    tw, th = max(1, round(W / kx)), max(1, round(H / ky))
    if (tw, th) == (W, H):
        return 0.0
    sub_img = Image.fromarray(sub.astype(np.uint8), "RGB")
    small = sub_img.resize((tw, th), Image.Resampling.NEAREST)
    recon = small.resize((W, H), Image.Resampling.NEAREST)
    b = np.asarray(recon, dtype=np.int16)
    diff = np.abs(sub - b).sum(axis=2) > tol
    return float(diff.mean())


def align_image(img: Image.Image, kx: int, ky: int, tol: int = COLOR_TOL) -> tuple[Image.Image, int, int]:
    """估算并裁掉像素格起始偏移，返回 (对齐后图片, 水平偏移, 垂直偏移)。

    用于手动指定块大小（--block）时也能自动对齐有位置偏移的像素画。
    """
    if kx <= 1 or ky <= 1:
        return img, 0, 0
    dx_edges, dy_edges = _edge_maps(img, tol)
    dx = _offset_from_edges(dx_edges, kx)
    dy = _offset_from_edges(dy_edges.T, ky)
    W, H = img.size
    dx, dy = min(dx, W - 1), min(dy, H - 1)
    if not (dx or dy):
        return img, 0, 0
    return img.crop((dx, dy, W, H)), dx, dy


def detect_block_size(img: Image.Image,
                      max_block: int = DEFAULT_MAX_BLOCK,
                      err_tol: float = ERR_TOL,
                      tol: int = COLOR_TOL,
                      trust_tol: float = 0.70) -> tuple[int, dict]:
    """自动检测“每个像素格占多大”和“起始偏移”。返回 (块大小 k, 诊断信息 dict)。

    判据（互相验证）：
    - 对每个候选 k，先用边界位置 mod k 的众数估算起始偏移 (dx, dy)，
      再计算“对齐后重建误差”（裁掉偏移缩小到 1/k 放大回原尺寸的不一致比例）；
      “可信度” = 1 - 对齐后重建误差 ≈ 块内主色占比。
      * 干净像素画（含位置偏移）：真实 k 处可信度 ≈ 1.0；
      * JPEG/网格线噪声图：真实 k 处可信度仍明显高于 0.70（主色占多数）；
      * 单像素风格图：任何 k 处可信度都低（块内颜色杂乱）→ 判为 k=1。
    取“可信度 ≥ trust_tol 的最大 k”作为块大小（k 的约数也会可信，取最大即真实块）。
    内部在 ANALYSIS_MAX_SIDE 内的小图上做误差扫描，再把结果换算回原图，
    保证大图也能快速检测。
    """
    W, H = img.size
    a_img = analysis_image(img)
    aW, aH = a_img.size

    lim = min(max_block, min(aW, aH) // 2)
    if lim < 2:
        return 1, {"reason": "图片太小，无法检测"}

    a_arr = rgb_array(a_img)
    dx_edges, dy_edges = _edge_maps(a_img, tol)

    # a) 对每个候选 k：先估算起始偏移，再算“对齐后”的重建误差
    errs: dict[int, float] = {}
    offsets: dict[int, tuple[int, int]] = {}
    for k in range(2, lim + 1):
        dx = _offset_from_edges(dx_edges, k)
        dy = _offset_from_edges(dy_edges.T, k)
        offsets[k] = (dx, dy)
        errs[k] = _aligned_mismatch(a_arr, dx, dy, k, k, tol)

    # b) 边界间隔众数（同样在检测小图上，仅用于报告/参考）
    cx, cy, conf_x, conf_y = interval_mode_xy(a_img, max_block, tol)

    # c) 决策：取“对齐后可信度 ≥ trust_tol”的最大 k
    trusted = [k for k, e in errs.items() if (1.0 - e) >= trust_tol]
    k_small = max(trusted) if trusted else 1

    # 换算回原图尺寸的块大小与起始偏移
    k_orig = max(1, round(k_small * W / aW))
    if k_small > 1:
        dx_s, dy_s = offsets[k_small]
        dx_orig = round(dx_s * W / aW)
        dy_orig = round(dy_s * H / aH)
    else:
        dx_orig = dy_orig = 0
    info = {
        "errs": errs,
        "cx": cx,
        "cy": cy,
        "conf_x": conf_x,
        "conf_y": conf_y,
        "trusted_max": k_small,
        "analysis_size": (aW, aH),
        "k_small": k_small,
        "dx": dx_orig,       # 原图坐标的像素格起始偏移（水平）
        "dy": dy_orig,       # 原图坐标的像素格起始偏移（垂直）
        "raw_size": (W, H),  # 对齐前（autocrop 后）的尺寸
    }
    return k_orig, info


# ---------------------------------------------------------------------------
# 1b. 网格线检测（处理块大小非整数 / 局部变化 / 相邻同色合并）
# ---------------------------------------------------------------------------

GRID_PEAK_MIN_H = 0.10  # 边界分数局部极大值的阈值（该列有多少比例的行有边界）


def _boundary_scores(img: Image.Image, tol: int = COLOR_TOL) -> tuple[np.ndarray, np.ndarray]:
    """返回 (列边界分数, 行边界分数)。

    列边界分数 col_score[i] = 第 i 列位置上有“垂直颜色边界”的行比例；
    像素格的真实分界列处接近 1，块内部接近 0。先做 3×3 中值滤波去噪。
    """
    denoised = np.asarray(to_rgb(img).filter(ImageFilter.MedianFilter(3)), dtype=np.int16)
    dx = (np.abs(np.diff(denoised, axis=1)).sum(axis=2) > tol)  # (H, W-1) 垂直边界
    dy = (np.abs(np.diff(denoised, axis=0)).sum(axis=2) > tol)  # (H-1, W) 水平边界
    col_score = dx.mean(axis=0)  # (W-1,)
    row_score = dy.mean(axis=1)  # (H-1,)
    return col_score, row_score


def _find_peaks(score: np.ndarray, min_h: float = GRID_PEAK_MIN_H) -> list[int]:
    """找分数曲线的局部极大值，作为像素格分界（网格线）候选位置。"""
    n = len(score)
    return [i for i in range(1, n - 1)
            if score[i] >= score[i - 1] and score[i] > score[i + 1] and score[i] >= min_h]


def _estimate_period(pts: list[int]) -> int:
    """从峰值位置估算“一个逻辑像素”的周期（块大小）。"""
    if len(pts) < 2:
        return 1
    gaps = np.diff(pts)
    gaps = gaps[gaps >= 2]
    if gaps.size == 0:
        return 1
    counts = Counter(gaps.tolist())
    k, c = counts.most_common(1)[0]
    if c / gaps.size < 0.4:
        k = int(np.median(gaps))
    return max(1, k)


def _median_period(pts: list[int]) -> float | None:
    """峰值间距的中位数 = 一个逻辑像素的平均宽度。"""
    if len(pts) < 2:
        return None
    gaps = np.diff(pts)
    gaps = gaps[gaps >= 2]
    if gaps.size == 0:
        return None
    return float(np.median(gaps))


def uniform_grid_aligned(pts: list[int], size: int, max_block: int) -> list[int] | None:
    """生成对齐像素画的均匀网格线（首条 0，末条 size）。

    - 块大小 = 峰值间距中位数取整（一个逻辑像素的宽度）；
    - 格数 n = round(尺寸/块大小)；
    - 网格线 = 0, size/n, 2×size/n, …（从图左/上缘 0 开始均匀切分）。

    注：峰值仅用于估计块大小；网格边界不从峰值吸附——实测截图/缩放过的
    像素画中，边界检测峰值常有 1~4px 系统性偏移，吸附反而导致错位。
    """
    step_f = _median_period(pts)
    if not step_f:
        return None
    step = max(1, round(step_f))
    if not (2 <= step <= max_block):
        return None
    # 平均格宽过小（<4px）说明不是“大像素格”像素画（可能是单像素图/照片），
    # 返回 None 让调用方回退到块大小法（能正确判为“无需缩小”）
    if step < 4:
        return None
    n = max(1, round(size / step))
    return [round(i * size / n) for i in range(n + 1)]


def make_grid_from_peaks(pts: list[int], k: float, limit: int) -> list[int]:
    """以峰值为锚点、按周期 k 生成完整网格线（含图左/上缘 0 与右/下缘 limit）。

    每条峰值位置向两侧扩展 ±n×k（k 可为非整数，位置取整），合并去重得到完整网格。
    这样既能精确定位非整数块（如 51.5px）的边界，也能把相邻同色导致
    边界极弱、峰值漏检的那条边界按周期补回来。
    """
    import math

    lines = {0, limit}
    for p in pts:
        n0 = math.floor((0.0 - p) / k)
        n1 = math.ceil((limit - 0.0 - p) / k)
        for n in range(n0, n1 + 1):
            pos = p + n * k
            if 0 < pos < limit:
                lines.add(int(round(pos)))
    return sorted(lines)


def detect_pixel_grid(img: Image.Image, max_block: int = DEFAULT_MAX_BLOCK,
                      tol: int = COLOR_TOL) -> dict | None:
    """网格线检测：直接定位每个逻辑像素的边界（不假设整数块大小）。

    返回 dict：{col_lines, row_lines, k_col, k_row, cols, rows, offset_x, offset_y}
    检测不到足够边界时返回 None（调用方回退到块大小法）。
    """
    a_img = analysis_image(img)
    aW, aH = a_img.size
    col_s, row_s = _boundary_scores(a_img, tol)
    col_pts = _find_peaks(col_s)
    row_pts = _find_peaks(row_s)
    if len(col_pts) < 2 or len(row_pts) < 2:
        return None
    # 网格线：step=峰值间距取整，offset=峰值 mod step 的众数（对齐相位）
    col_lines = uniform_grid_aligned(col_pts, aW, max_block)
    row_lines = uniform_grid_aligned(row_pts, aH, max_block)
    if not col_lines or not row_lines or len(col_lines) < 2 or len(row_lines) < 2:
        return None
    # 换算回原图坐标（末条保留为图宽/图高）
    W, H = img.size
    sx, sy = W / aW, H / aH
    col_lines = sorted(set(min(max(round(c * sx), 0), W) for c in col_lines))
    row_lines = sorted(set(min(max(round(r * sy), 0), H) for r in row_lines))
    return {
        "col_lines": col_lines,
        "row_lines": row_lines,
        "k_col": _median_period(col_pts) or 0,
        "k_row": _median_period(row_pts) or 0,
        "cols": len(col_lines) - 1,
        "rows": len(row_lines) - 1,
    }


# ---------------------------------------------------------------------------
# 2. 缩小
# ---------------------------------------------------------------------------

def downscale_nearest(img: Image.Image, tw: int, th: int) -> Image.Image:
    """纯最近邻插值缩小。不引入新颜色，完美保留像素画风格。"""
    rgba = to_rgba(img)
    return rgba.resize((tw, th), Image.Resampling.NEAREST)


def block_mode_downscale(img: Image.Image, kx: int, ky: int,
                         tw: int | None = None, th: int | None = None,
                         batch_rows: int = 64) -> Image.Image:
    """块主色聚合：把图片按 kx×ky 切块，每块取“主色簇的平均色”作为代表色。

    - 取块内颜色量化后出现最多的“簇”，再对簇内像素取平均：
      抗 JPEG 压缩 / 抗锯齿噪声，代表色贴近真实内容色，绝不产生混合色，
      从而不破坏原图的像素分布。
    - 目标格数 tw/th 缺省时按 ceil 计算；传入时（与主流程一致）以传入为准。
    - 按行分批处理，避免超大图占用过多内存；图片尺寸不能整除块大小时，
      边缘块用复制填充的方式补全（不丢内容）。
    """
    import math

    rgba = to_rgba(img)
    arr = np.asarray(rgba, dtype=np.int16)  # (H, W, 4)
    H, W, C = arr.shape
    if th is None:
        th = max(1, math.ceil(H / ky))
    if tw is None:
        tw = max(1, math.ceil(W / kx))
    out = np.empty((th, tw, C), dtype=np.uint8)

    for y0 in range(0, th, batch_rows):
        y1 = min(th, y0 + batch_rows)
        a = arr[y0 * ky:y1 * ky, :tw * kx]
        # 行/列补齐到 (y1-y0)*ky × tw*kx（边缘复制填充，保证 reshape 正确）
        # 注意：目标尺寸按 round 计算时 tw*kx 可能小于原图宽，先裁剪列；
        # 不足时（ceil 计算）再填充
        need_h = (y1 - y0) * ky - a.shape[0]
        need_w = tw * kx - a.shape[1]
        if need_h > 0 or need_w > 0:
            a = np.pad(a, ((0, max(0, need_h)), (0, max(0, need_w)), (0, 0)), mode="edge")
        # 切块：reshape 成 (行块数, ky, 列块数, kx, C) 再转成 (行块数, 列块数, ky*kx, C)
        b = a.reshape(y1 - y0, ky, tw, kx, C).transpose(0, 2, 1, 3, 4) \
              .reshape(y1 - y0, tw, ky * kx, C)
        out[y0:y1] = _mode_of_blocks(b)  # 每块取主色簇

    return Image.fromarray(out, "RGBA")


def _mode_of_blocks(b: np.ndarray, quant_bits: int = 3) -> np.ndarray:
    """b: (R, C, N, 4) int16 —— 对每个 kx×ky 块求主色。

    - 快速路径：块内所有像素完全相同，直接取该色（干净像素画绝大多数块如此）；
    - 慢路径（混合块）：把颜色量化到 quant_bits 位/通道 找“主色簇”
      （抗 JPEG 噪点：噪声变体会落入同一簇），再对簇内像素取平均得到代表色。
      透明像素占多数的块输出全透明。
    """
    R, C, N, _ = b.shape
    res = np.empty((R, C, 4), dtype=np.uint8)

    # 快速路径：整块同色
    first = b[..., 0, :]                                        # (R, C, 4)
    same = np.all(b == first[..., None, :], axis=(2, 3))       # (R, C)
    res[same] = first[same].astype(np.uint8)

    # 慢路径：混合块逐块求主色簇
    ys, xs = np.nonzero(~same)
    for i, j in zip(ys.tolist(), xs.tolist()):
        res[i, j] = _mode_of_block(b[i, j], quant_bits)
    return res


def _mode_of_block(block: np.ndarray, quant_bits: int = 3) -> np.ndarray:
    """单块主色：block: (h, w, 4) int16 → 主色簇平均色 (4,) uint8。

    透明像素占多数的块输出全透明。
    """
    vals = block.reshape(-1, 4)
    opaque = vals[..., 3] >= 128
    if not opaque.any():
        return np.array([0, 0, 0, 0], dtype=np.uint8)
    rgb = vals[opaque, :3].astype(np.int64)
    shift = 8 - quant_bits
    q = (rgb >> shift) & ((1 << quant_bits) - 1)
    enc = (q[..., 0] << (2 * quant_bits)) | (q[..., 1] << quant_bits) | q[..., 2]
    counts = np.bincount(enc)
    cluster = int(np.argmax(counts))
    mask = enc == cluster
    avg = np.rint(rgb[mask].mean(axis=0)).astype(np.uint8)
    return np.concatenate([avg, [255]])


def grid_mode_downscale(img: Image.Image, col_lines: list[int],
                        row_lines: list[int]) -> Image.Image:
    """网格线重建：按检测到的网格线把图片切成逻辑像素格，每格取主色。

    网格线首条即内容起点（之前的偏移区会被自动裁掉），末条补图宽/图高，
    因此相邻两条网格线之间恰好是一个逻辑像素。
    """
    rgba = np.asarray(to_rgba(img), dtype=np.int16)
    H, W, _ = rgba.shape
    xs = sorted(set([W] + [min(max(int(c), 0), W) for c in col_lines]))
    ys = sorted(set([H] + [min(max(int(r), 0), H) for r in row_lines]))
    out = np.empty((len(ys) - 1, len(xs) - 1, 4), dtype=np.uint8)
    for i in range(len(ys) - 1):
        y0, y1 = ys[i], ys[i + 1]
        if y1 <= y0:
            continue
        for j in range(len(xs) - 1):
            x0, x1 = xs[j], xs[j + 1]
            if x1 <= x0:
                continue
            out[i, j] = _mode_of_block(rgba[y0:y1, x0:x1])
    return Image.fromarray(out, "RGBA")


# ---------------------------------------------------------------------------
# 3. 其他处理
# ---------------------------------------------------------------------------

def autocrop(img: Image.Image, margin: int = 2, tol: int = 20) -> Image.Image:
    """自动裁掉四周的纯色空白/边框（背景色取四角的公共色）。"""
    arr = rgb_array(img)
    H, W, _ = arr.shape
    corners = [arr[0, 0], arr[0, -1], arr[-1, 0], arr[-1, -1]]
    bg = np.median(corners, axis=0)
    mask = np.abs(arr - bg).sum(axis=2) > tol
    rows = mask.any(axis=1)
    cols = mask.any(axis=0)
    if not rows.any():
        return img  # 整图都是背景色
    ys = np.flatnonzero(rows)
    xs = np.flatnonzero(cols)
    y0, y1 = int(ys.min()), int(ys.max())
    x0, x1 = int(xs.min()), int(xs.max())
    x0, y0 = max(0, x0 - margin), max(0, y0 - margin)
    x1, y1 = min(W - 1, x1 + margin), min(H - 1, y1 + margin)
    return img.crop((x0, y0, x1 + 1, y1 + 1))


def consistency_ratio(img: Image.Image, small: Image.Image, tol: int = COLOR_TOL) -> float:
    """重建一致性：把缩小结果放大回原尺寸，与原图一致的像素比例。
    用于量化“没有破坏像素分布”。"""
    W, H = img.size
    a = rgb_array(img)
    recon = to_rgb(small).resize((W, H), Image.Resampling.NEAREST)
    b = np.asarray(recon, dtype=np.int16)
    diff = np.abs(a - b).sum(axis=2) > tol
    return 1.0 - float(diff.mean())


def unique_color_count(img: Image.Image) -> int:
    """缩小结果中的唯一颜色数（忽略透明）。"""
    rgba = to_rgba(img)
    arr = np.asarray(rgba)
    alpha = arr[..., 3]
    opaque = arr[alpha >= 128][..., :3]
    if opaque.size == 0:
        return 0
    return int(np.unique(opaque.reshape(-1, 3), axis=0).shape[0])


def save_image(img: Image.Image, path: str) -> None:
    """保存图片：全不透明时存成 RGB（文件更小）。"""
    if img.mode == "RGBA":
        alpha = img.getchannel("A")
        if alpha.getextrema()[0] == 255:
            img = img.convert("RGB")
    img.save(path)


def unique_path(path: str) -> str:
    """若文件已存在，自动追加 (1)、(2)… 避免覆盖。"""
    if not os.path.exists(path):
        return path
    stem, ext = os.path.splitext(path)
    i = 1
    while True:
        cand = f"{stem} ({i}){ext}"
        if not os.path.exists(cand):
            return cand
        i += 1


def expand_inputs(path: str) -> list[str]:
    """把输入参数展开成文件列表：支持文件 / 目录 / 通配符。"""
    if any(ch in path for ch in "*?["):
        return sorted(glob.glob(path))
    if os.path.isdir(path):
        exts = {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".gif", ".tif", ".tiff", ".jfif"}
        return sorted(
            os.path.join(path, f)
            for f in os.listdir(path)
            if os.path.splitext(f)[1].lower() in exts
            and os.path.isfile(os.path.join(path, f))
        )
    return [path]


def parse_block(s: str) -> tuple[int, int]:
    """解析 --block 参数：'20' → (20,20)；'20x10' / '20,10' → (20,10)。"""
    m = re.match(r"^\s*(\d+)\s*(?:[xX,，]\s*(\d+))?\s*$", s)
    if not m:
        raise ValueError(f"无法解析 --block 值: {s!r}（请用 20 或 20x10）")
    kx = int(m.group(1))
    ky = int(m.group(2)) if m.group(2) else kx
    if kx < 1 or ky < 1:
        raise ValueError("--block 必须为正整数")
    return kx, ky


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def process_file(in_path: str, args: argparse.Namespace) -> tuple[str, dict] | None:
    """处理单个图片文件，返回 (输出路径, 报告信息)。失败返回 None。"""
    img = load_image(in_path)
    if args.autocrop:
        img = autocrop(img, margin=args.autocrop_margin)

    W, H = img.size
    raw_W, raw_H = W, H   # 偏移对齐前的尺寸（用于报告）
    kx = ky = 0
    det_info = None

    # —— 自动检测主路径：网格线重建 ——
    # 直接定位每个逻辑像素的边界（处理非整数块大小、相邻同色合并、JPEG 噪点）
    if not args.block and not args.scale:
        grid = detect_pixel_grid(img, max_block=args.max_block)
        if grid is not None:
            small = grid_mode_downscale(img, grid["col_lines"], grid["row_lines"])
            tw, th = small.size
            det_info = grid
            if args.quantize and args.quantize > 0 and (tw, th) != (W, H):
                q = small.quantize(args.quantize, method=Image.Quantize.FASTOCTREE) \
                    if "A" in small.getbands() \
                    else small.quantize(args.quantize, method=Image.Quantize.MEDIANCUT)
                small = q.convert("RGBA")
            rep = _report_info(in_path, img, raw_W, raw_H, kx, ky, tw, th, small, "", args, det_info)
            if args.info:
                return None, rep
            out_dir = args.out_dir or os.path.dirname(os.path.abspath(in_path))
            os.makedirs(out_dir, exist_ok=True)
            stem = os.path.splitext(os.path.basename(in_path))[0]
            out_path = unique_path(os.path.join(out_dir, f"{stem}_{tw}x{th}.png"))
            save_image(small, out_path)
            return out_path, rep

    # —— 其余路径：手动 block / scale / 网格检测失败回退到块大小法 ——
    use_mode = False  # auto 模式下是否需要用块主色聚合去噪
    if args.block:
        kx, ky = parse_block(args.block)
        # 手动指定块大小，但也自动对齐像素格起始偏移
        img, dx, dy = align_image(img, kx, ky)
        W, H = img.size
        det_info = {"manual": True, "dx": dx, "dy": dy}
        tw, th = max(1, round(W / kx)), max(1, round(H / ky))
    elif args.scale:
        tw, th = max(1, round(W * args.scale)), max(1, round(H * args.scale))
    else:
        k, det_info = detect_block_size(img, max_block=args.max_block)
        kx = ky = k
        if k > 1:
            dx, dy = det_info.get("dx", 0), det_info.get("dy", 0)
            if dx or dy:
                # 裁掉起始偏移，让像素格与网格对齐后再缩小
                img = img.crop((dx, dy, W, H))
                W, H = img.size
            tw, th = max(1, round(W / k)), max(1, round(H / k))
            # auto 模式：块内颜色干净（重建误差小）用最近邻；
            # 块内有噪点（网格线/JPEG，重建误差大）用块主色聚合去噪
            use_mode = det_info["errs"].get(det_info["k_small"], 1.0) >= ERR_TOL
        else:
            tw, th = W, H

    # 缩小
    if (tw, th) == (W, H) and not args.scale and not args.block:
        small = img  # 本身就是单像素风格，无需缩小
    elif args.method == "nearest":
        small = downscale_nearest(img, tw, th)
    elif args.method == "mode":
        # 块主色聚合需要块大小；--scale 模式没有块概念，退化为最近邻
        small = block_mode_downscale(img, kx, ky, tw, th) if kx > 1 \
            else downscale_nearest(img, tw, th)
    else:  # auto
        small = block_mode_downscale(img, kx, ky, tw, th) if use_mode and kx > 1 \
            else downscale_nearest(img, tw, th)

    # 可选：颜色量化（把相似颜色合并成有限几种，便于观察颜色代码）
    if args.quantize and args.quantize > 0 and (tw, th) != (W, H):
        if "A" in small.getbands():
            q = small.quantize(args.quantize, method=Image.Quantize.FASTOCTREE)
        else:
            q = small.quantize(args.quantize, method=Image.Quantize.MEDIANCUT)
        small = q.convert("RGBA")

    note = "图片本身就是单像素风格，无需缩小" \
        if (tw, th) == (W, H) and not args.scale and not args.block else ""

    rep = _report_info(in_path, img, raw_W, raw_H, kx, ky, tw, th, small, note, args, det_info)
    if args.info:
        return None, rep

    # 保存
    out_dir = args.out_dir or os.path.dirname(os.path.abspath(in_path))
    os.makedirs(out_dir, exist_ok=True)
    stem = os.path.splitext(os.path.basename(in_path))[0]
    out_path = unique_path(os.path.join(out_dir, f"{stem}_{tw}x{th}.png"))
    save_image(small, out_path)
    return out_path, rep


def _report_info(in_path, img, W, H, kx, ky, tw, th, small, note, args, det_info) -> dict:
    """收集报告信息（供打印 / 返回）。"""
    r = {
        "input": in_path,
        "src": (W, H),
        "dst": (tw, th),
        "kx": kx,
        "ky": ky,
        "note": note,
        "method": args.method,
        "autocrop": args.autocrop,
        "det_info": det_info,
        "consistency": None,
        "colors": None,
    }
    if note:
        r["consistency"] = 1.0
        r["colors"] = unique_color_count(img)
    else:
        r["consistency"] = consistency_ratio(img, small)
        r["colors"] = unique_color_count(small)
    return r


def print_report(r: dict) -> None:
    """打印单个文件的结果报告。"""
    W, H = r["src"]
    tw, th = r["dst"]
    det = r["det_info"]
    print("-" * 56)
    print(f"输入文件:  {r['input']}")
    print(f"原图尺寸:  {W} x {H} 像素")
    if det is not None:
        if "col_lines" in det:
            # 网格线重建（自动检测主路径）
            print(f"像素格:    自动检测 = 平均 {det.get('k_col', 0):.1f} x {det.get('k_row', 0):.1f} px"
                  f"  (网格 {det['cols']} x {det['rows']})")
        elif det.get("manual"):
            print(f"块大小:    手动指定 = {r['kx']} x {r['ky']} 像素")
        else:
            print(f"块大小:    自动检测 = {r['kx']} x {r['ky']} 像素"
                  f"  (边界众数 {det.get('cx', '-')}/{det.get('cy', '-')},"
                  f" 最大可信块 {det.get('trusted_max', '-')})")
        dx, dy = det.get("dx", 0), det.get("dy", 0)
        if dx or dy:
            print(f"对齐偏移:  水平 {dx}、垂直 {dy} 像素（已自动对齐）")
    elif r["kx"] > 1:
        print(f"块大小:    手动指定 = {r['kx']} x {r['ky']} 像素")
    else:
        print("块大小:    按缩放比例")
    print(f"目标尺寸:  {tw} x {th} 格")
    if r["src"] != r["dst"]:
        print(f"缩小率:    {W / tw:.2f} 倍")
    if r["colors"] is not None:
        print(f"唯一颜色:  {r['colors']} 种")
    if r["consistency"] is not None:
        print(f"重建一致性: {r['consistency'] * 100:.1f}%   (缩小后放大回原尺寸的像素一致比例)")
    if r["note"]:
        print(f"提示:      {r['note']}")


def _pick_file() -> str:
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()
    path = filedialog.askopenfilename(
        title="选择要缩小的图片",
        filetypes=[("图片", "*.png *.jpg *.jpeg *.bmp *.webp *.gif"), ("所有文件", "*.*")],
    )
    root.destroy()
    return path


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="shrink_pixel_art",
        description="自动把大像素格的像素画图片缩回单像素风格（不破坏像素分布）。",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("inputs", nargs="*", help="图片文件 / 目录 / 通配符（可多个）")
    p.add_argument("-o", "--out-dir", default=DEFAULT_OUT_DIR,
                   help="输出目录（默认 output_/，自动创建）")
    p.add_argument("--block", help="手动指定每格像素数，如 20 或 20x10（默认自动检测）")
    p.add_argument("--scale", type=float, help="手动指定缩放比例，如 0.1 表示缩小到十分之一")
    p.add_argument("--max-block", type=int, default=DEFAULT_MAX_BLOCK,
                   help="自动检测时允许的最大候选块大小")
    p.add_argument("--method", choices=["auto", "nearest", "mode"], default="auto",
                   help="缩小方式：auto 自动（干净时用最近邻，块内有噪点时用块主色）"
                        "/ nearest 纯最近邻 / mode 块主色聚合（每块取主色簇）")
    p.add_argument("--nearest", action="store_true", help="等价于 --method nearest")
    p.add_argument("--quantize", type=int, default=0,
                   help="把缩小结果量化到 N 种颜色（默认 0=不量化）。"
                        "适合 JPEG/抗锯齿图，让颜色代码更容易观察")
    p.add_argument("--autocrop", action="store_true", help="先自动裁掉四周纯色空白/边框")
    p.add_argument("--autocrop-margin", type=int, default=2, help="裁剪时四周保留的边距")
    p.add_argument("--info", action="store_true", help="只检测并打印信息，不保存图片")
    p.add_argument("--pick", action="store_true", help="弹出文件选择框选择图片")
    p.add_argument("-q", "--quiet", action="store_true", help="不打印报告")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.nearest:
        args.method = "nearest"

    if args.scale is not None and (args.scale <= 0 or args.scale > 1):
        print("--scale 必须是 (0, 1] 之间的正数。", file=sys.stderr)
        return 2

    inputs = list(args.inputs)
    if args.pick and not inputs:
        picked = _pick_file()
        if picked:
            inputs = [picked]
        else:
            print("未选择文件，退出。")
            return 1
    if not inputs:
        build_parser().print_help()
        return 1

    files: list[str] = []
    for raw in inputs:
        files.extend(expand_inputs(raw))
    files = [f for f in files if os.path.isfile(f)]

    if not files:
        print("没有找到任何图片文件。", file=sys.stderr)
        return 1

    ok = 0
    for f in files:
        try:
            out_path, rep = process_file(f, args)
        except Exception as e:  # noqa: BLE001 - 逐个文件容错，不中断批量
            print(f"处理失败: {f}  ({e})", file=sys.stderr)
            continue
        ok += 1
        if not args.quiet:
            print_report(rep)
            if out_path:
                print(f"输出文件:  {out_path}")
    print("-" * 56)
    print(f"完成：成功 {ok} 个，共 {len(files)} 个。")
    return 0 if ok == len(files) else 1


if __name__ == "__main__":
    sys.exit(main())
