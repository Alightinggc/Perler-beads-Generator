"""颜色空间转换与色差计算。

- srgb_to_lab：sRGB(0-255) -> CIELAB (D65 白点)
- ciede2000_matrix / cie76_matrix：批量计算 (P, K) 距离矩阵
所有函数基于 numpy 向量化，适合网格像素 x 色板的批量最近色匹配。
"""

from __future__ import annotations

import numpy as np

# D65 白点
_WHITE_X, _WHITE_Y, _WHITE_Z = 0.95047, 1.0, 1.08883
_EPS = 216.0 / 24389.0   # (6/29)^3
_KAPPA = 24389.0 / 27.0  # 29^3/27


def srgb_to_lab(rgb: np.ndarray) -> np.ndarray:
    """rgb: (..., 3) uint8 或 float(0-255) -> lab: (..., 3) float"""
    rgb = np.asarray(rgb, dtype=np.float64) / 255.0

    def linearize(c: np.ndarray) -> np.ndarray:
        return np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)

    r, g, b = linearize(rgb[..., 0]), linearize(rgb[..., 1]), linearize(rgb[..., 2])
    x = 0.4124564 * r + 0.3575761 * g + 0.1804375 * b
    y = 0.2126729 * r + 0.7151522 * g + 0.0721750 * b
    z = 0.0193339 * r + 0.1191920 * g + 0.9503041 * b

    def f(t: np.ndarray) -> np.ndarray:
        return np.where(t > _EPS, np.cbrt(t), (t * _KAPPA + 16.0) / 116.0)

    fx, fy, fz = f(x / _WHITE_X), f(y / _WHITE_Y), f(z / _WHITE_Z)
    l = 116.0 * fy - 16.0
    a = 500.0 * (fx - fy)
    b = 200.0 * (fy - fz)
    return np.stack([l, a, b], axis=-1)


def ciede2000_matrix(lab_p: np.ndarray, lab_k: np.ndarray) -> np.ndarray:
    """批量 CIEDE2000 色差矩阵。

    lab_p: (P, 3) 像素 Lab；lab_k: (K, 3) 色板 Lab。
    返回 (P, K)。
    """
    L1 = lab_p[:, None, 0]
    a1 = lab_p[:, None, 1]
    b1 = lab_p[:, None, 2]
    L2 = lab_k[None, :, 0]
    a2 = lab_k[None, :, 1]
    b2 = lab_k[None, :, 2]

    C1 = np.sqrt(a1 ** 2 + b1 ** 2)
    C2 = np.sqrt(a2 ** 2 + b2 ** 2)
    Cbar = (C1 + C2) / 2.0
    c7 = Cbar ** 7
    G = 0.5 * (1.0 - np.sqrt(c7 / (c7 + 25.0 ** 7)))

    a1p = (1.0 + G) * a1
    a2p = (1.0 + G) * a2
    C1p = np.sqrt(a1p ** 2 + b1 ** 2)
    C2p = np.sqrt(a2p ** 2 + b2 ** 2)
    h1p = np.degrees(np.arctan2(b1, a1p)) % 360.0
    h2p = np.degrees(np.arctan2(b2, a2p)) % 360.0

    dLp = L2 - L1
    dCp = C2p - C1p

    hdiff = h2p - h1p
    dhp = np.where(
        C1p * C2p == 0.0,
        0.0,
        np.where(
            np.abs(hdiff) <= 180.0,
            hdiff,
            np.where(hdiff > 180.0, hdiff - 360.0, hdiff + 360.0),
        ),
    )
    dHp = 2.0 * np.sqrt(C1p * C2p) * np.sin(np.radians(dhp) / 2.0)

    Lbarp = (L1 + L2) / 2.0
    Cbarp = (C1p + C2p) / 2.0
    hsum = h1p + h2p
    hbarp = np.where(
        C1p * C2p == 0.0,
        hsum,
        np.where(
            np.abs(h1p - h2p) <= 180.0,
            hsum / 2.0,
            np.where(hsum < 360.0, (hsum + 360.0) / 2.0, (hsum - 360.0) / 2.0),
        ),
    )

    T = (
        1.0
        - 0.17 * np.cos(np.radians(hbarp - 30.0))
        + 0.24 * np.cos(np.radians(2.0 * hbarp))
        + 0.32 * np.cos(np.radians(3.0 * hbarp + 6.0))
        - 0.20 * np.cos(np.radians(4.0 * hbarp - 63.0))
    )
    dtheta = 30.0 * np.exp(-(((hbarp - 275.0) / 25.0) ** 2))
    cbar7 = Cbarp ** 7
    RC = 2.0 * np.sqrt(cbar7 / (cbar7 + 25.0 ** 7))
    SL = 1.0 + 0.015 * (Lbarp - 50.0) ** 2 / np.sqrt(20.0 + (Lbarp - 50.0) ** 2)
    SC = 1.0 + 0.045 * Cbarp
    SH = 1.0 + 0.015 * Cbarp * T
    RT = -np.sin(np.radians(2.0 * dtheta)) * RC

    dsc = dCp / SC
    dsh = dHp / SH
    return np.sqrt((dLp / SL) ** 2 + dsc ** 2 + dsh ** 2 + RT * dsc * dsh)


def cie76_matrix(lab_p: np.ndarray, lab_k: np.ndarray) -> np.ndarray:
    """CIELAB 欧氏距离矩阵 (P, K)，速度更快、精度稍低。"""
    diff = lab_p[:, None, :] - lab_k[None, :, :]
    return np.sqrt((diff ** 2).sum(axis=-1))


METRICS = {
    "ciede2000": ciede2000_matrix,
    "cie76": cie76_matrix,
}


def distance_matrix(rgb_p: np.ndarray, rgb_k: np.ndarray, metric: str = "ciede2000") -> np.ndarray:
    """rgb_p: (P,3), rgb_k: (K,3) -> 距离矩阵 (P, K)。"""
    fn = METRICS.get(metric)
    if fn is None:
        raise ValueError(f"未知色差度量 '{metric}'，可选: {', '.join(METRICS)}")
    lab_p = srgb_to_lab(rgb_p)
    lab_k = srgb_to_lab(rgb_k)
    return fn(lab_p, lab_k)
