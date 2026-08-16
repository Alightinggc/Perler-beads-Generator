"""拼豆标准色板数据。

数据来源：
- perler：基于开源仓库 Gyros007/Perler-Color-Coverter-and-Counter 的 Perler 官方色板
  （BGR -> RGB 转换），95 色，含中英文名。色号为本项目自编号 P01~P95。
- artkal：基于 tuxknight/pixel-beads 的 Artkal 预览色板（A01~A30，Material 色系近似值）。
- hama  ：基于 tuxknight/pixel-beads 的 Hama 预览色板（H01~H28）。

注意：所有 RGB 均为“屏幕近似值”，实际购买请以官方色卡/实物为准。
自定义更精确的色板可通过 --palette-file 传入 CSV：
    code,name,hex
    A01,白色,#FFFFFF
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field


@dataclass(frozen=True)
class BeadColor:
    code: str        # 色号，如 P01 / A01 / H01
    name: str        # 名称（中文优先）
    rgb: tuple[int, int, int]
    name_en: str = ""

    @property
    def hex(self) -> str:
        return "#%02X%02X%02X" % self.rgb


@dataclass
class Palette:
    name: str
    brand: str
    colors: list[BeadColor] = field(default_factory=list)

    def by_code(self) -> dict[str, BeadColor]:
        return {c.code: c for c in self.colors}

    def rgb_array(self):
        import numpy as np

        return np.array([c.rgb for c in self.colors], dtype=np.float64)


# ---------------------------------------------------------------------------
# Perler 95 色（真实色板，BGR -> RGB 已转换）
# 格式: (code, 英文名, 中文名, R, G, B)
# ---------------------------------------------------------------------------
_PERLER_RAW: list[tuple[str, str, str, int, int, int]] = [
    ("P01", "White",              "白",        247, 247, 242),
    ("P02", "Light Grey",         "浅灰",      190, 195, 191),
    ("P03", "Grey",               "灰",        150, 152, 156),
    ("P04", "Pewter",             "锡灰",      147, 161, 159),
    ("P05", "Charcoal",           "炭灰",      84, 95, 95),
    ("P06", "Dark Grey",          "深灰",      86, 87, 92),
    ("P07", "Black",              "黑",        52, 50, 52),
    ("P08", "Toasted Marshmallow", "烤棉花糖", 241, 229, 216),
    ("P09", "Sand",               "沙色",      234, 196, 159),
    ("P10", "Fawn",               "浅褐",      215, 176, 135),
    ("P11", "Tan",                "茶褐",      207, 168, 137),
    ("P12", "Rust",               "锈红",      160, 78, 63),
    ("P13", "Cranapple",          "蔓越莓红",  136, 64, 79),
    ("P14", "Light Brown",        "浅棕",      164, 123, 71),
    ("P15", "Gingerbread",        "姜饼棕",    126, 84, 70),
    ("P16", "Brown",              "棕色",      108, 82, 77),
    ("P17", "Creme",              "奶油",      237, 231, 186),
    ("P18", "Pastel Yellow",      "淡黄",      250, 238, 141),
    ("P19", "Yellow",             "黄",        249, 215, 55),
    ("P20", "Cheddar",            "切达黄",    255, 182, 78),
    ("P21", "Orange",             "橙",        255, 128, 62),
    ("P22", "Butterscotch",       "太妃糖",    225, 154, 82),
    ("P23", "Honey",              "蜂蜜",      218, 140, 44),
    ("P24", "Hot Coral",          "热珊瑚",    255, 97, 88),
    ("P25", "Salmon",             "三文鱼",    255, 119, 127),
    ("P26", "Blush",              "腮红粉",    255, 158, 141),
    ("P27", "Flamingo",           "火烈鸟粉",  255, 181, 190),
    ("P28", "Peach",              "桃色",      252, 198, 184),
    ("P29", "Light Pink",         "浅粉",      245, 192, 213),
    ("P30", "Bubblegum",          "泡泡糖粉",  225, 109, 157),
    ("P31", "Pink",               "粉",        230, 87, 148),
    ("P32", "Magenta",            "品红",      243, 70, 118),
    ("P33", "Fruit Punch",        "果酒红",    218, 48, 89),
    ("P34", "Red",                "红",        196, 58, 68),
    ("P35", "Cherry",             "樱桃红",    173, 51, 69),
    ("P36", "Raspberry",          "覆盆子红",  173, 60, 108),
    ("P37", "Plum",               "梅紫",      178, 95, 170),
    ("P38", "Lavender",           "薰衣草",    180, 166, 211),
    ("P39", "Pastel Lavender",    "淡紫",      149, 130, 187),
    ("P40", "Purple",             "紫",        111, 84, 147),
    ("P41", "Blueberry Cream",    "蓝莓奶油",  135, 167, 225),
    ("P42", "Periwinkle Blue",    "长春花蓝",  108, 136, 191),
    ("P43", "Robin's Egg",        "知更鸟蛋蓝", 180, 217, 223),
    ("P44", "Pastel Blue",        "淡蓝",      99, 169, 214),
    ("P45", "Light Blue",         "浅蓝",      39, 138, 203),
    ("P46", "Cobalt",             "钴蓝",      0, 102, 179),
    ("P47", "Dark Blue",          "深蓝",      43, 48, 124),
    ("P48", "Midnight",           "午夜蓝",    22, 40, 70),
    ("P49", "Toothpaste",         "薄荷蓝",    176, 232, 213),
    ("P50", "Turquoise",          "松石绿",    0, 143, 204),
    ("P51", "Light Green",        "浅绿",      56, 199, 175),
    ("P52", "Parrot Green",       "鹦鹉绿",    0, 150, 138),
    ("P53", "Pastel Green",       "淡绿",      115, 213, 148),
    ("P54", "Kiwi Lime",          "奇异果青柠", 119, 202, 74),
    ("P55", "Bright Green",       "亮绿",      84, 177, 96),
    ("P56", "Shamrock",           "三叶草绿",  0, 150, 84),
    ("P57", "Dark Green",         "深绿",      16, 131, 85),
    ("P58", "Prickly Pear",       "仙人掌果绿", 203, 215, 53),
    ("P59", "Evergreen",          "常青绿",    60, 97, 79),
    ("P60", "Thistle",            "蓟紫",      153, 152, 175),
    ("P61", "Slime",              "荧光绿",    196, 206, 31),
    ("P62", "Mulberry",           "桑葚紫",    109, 59, 104),
    ("P63", "Fuchsia",            "紫红",      221, 83, 177),
    ("P64", "Orange Cream",       "橙奶油",    255, 179, 145),
    ("P65", "Dark Spruce",        "云杉绿",    38, 74, 84),
    ("P66", "Denim",              "牛仔蓝",    78, 115, 153),
    ("P67", "Sage",               "鼠尾草绿",  155, 189, 141),
    ("P68", "Slate Blue",         "灰蓝",      114, 133, 145),
    ("P69", "Sherbert",           "雪芭橙",    225, 238, 125),
    ("P70", "Fern",               "蕨绿",      123, 151, 48),
    ("P71", "Olive",              "橄榄绿",    115, 117, 62),
    ("P72", "Mist",               "雾蓝",      156, 185, 199),
    ("P73", "Sky",                "天蓝",      84, 205, 227),
    ("P74", "Lagoon",             "泻湖绿",    0, 171, 178),
    ("P75", "Apricot",            "杏色",      255, 169, 103),
    ("P76", "Orchid",             "兰花紫",    181, 108, 153),
    ("P77", "Spice",              "香料橙",    227, 92, 68),
    ("P78", "Tomato",             "番茄红",    234, 66, 66),
    ("P79", "Teal",               "青蓝",      54, 141, 151),
    ("P80", "Rose",               "玫瑰粉",    210, 93, 114),
    ("P81", "Cotton Candy",       "棉花糖粉",  244, 121, 176),
    ("P82", "Eggplant",           "茄子紫",    111, 50, 85),
    ("P83", "Grape",              "葡萄紫",    80, 59, 156),
    ("P84", "Tangerine",          "橘橙",      253, 89, 24),
    ("P85", "Iris",               "鸢尾紫",    78, 86, 163),
    ("P86", "Forest",             "森林绿",    0, 93, 87),
    ("P87", "Sour Apple",         "青苹果绿",  163, 222, 111),
    ("P88", "Mint",               "薄荷",      179, 238, 213),
    ("P89", "Stone",              "石头灰",    162, 152, 146),
    ("P90", "Cocoa",              "可可棕",    80, 69, 70),
    ("P91", "Caribbean Sea",      "加勒比海蓝", 0, 185, 158),
    ("P92", "Twilight Plum",      "暮色梅紫",  157, 117, 148),
    ("P93", "Frosted Lilac",      "霜紫",      208, 192, 202),
]


# ---------------------------------------------------------------------------
# Artkal 30 色 / Hama 28 色（预览级近似色板，来自 palettes.ts）
# ---------------------------------------------------------------------------
_ARTKAL_RAW: list[tuple[str, str, int, int, int]] = [
    ("A01", "白",     255, 255, 255), ("A02", "米白",   245, 240, 225),
    ("A03", "浅黄",   255, 241, 118), ("A04", "黄",     253, 216, 53),
    ("A05", "橙",     255, 152, 0),   ("A06", "红",     244, 67, 54),
    ("A07", "深红",   211, 47, 47),   ("A08", "粉",     244, 143, 177),
    ("A09", "紫",     156, 39, 176),  ("A10", "蓝",     33, 150, 243),
    ("A11", "深蓝",   21, 101, 192),  ("A12", "青",     0, 188, 212),
    ("A13", "绿",     76, 175, 80),   ("A14", "深绿",   46, 125, 50),
    ("A15", "棕",     121, 85, 72),   ("A16", "深棕",   78, 52, 46),
    ("A17", "浅灰",   189, 189, 189), ("A18", "深灰",   97, 97, 97),
    ("A19", "黑",     33, 33, 33),    ("A20", "薰衣草", 179, 157, 219),
    ("A21", "珊瑚",   255, 138, 128), ("A22", "薄荷",   165, 214, 167),
    ("A23", "湖蓝",   77, 208, 225),  ("A24", "玫瑰",   233, 30, 99),
    ("A25", "金",     255, 193, 7),   ("A26", "象牙",   255, 248, 225),
    ("A27", "灰紫",   126, 87, 194),  ("A28", "天蓝",   129, 212, 250),
    ("A29", "草绿",   139, 195, 74),  ("A30", "栗色",   136, 14, 79),
]

_HAMA_RAW: list[tuple[str, str, int, int, int]] = [
    ("H01", "白",     255, 255, 255), ("H02", "浅黄",   255, 245, 157),
    ("H03", "黄",     255, 235, 59),  ("H04", "橙",     255, 152, 0),
    ("H05", "红",     244, 67, 54),   ("H06", "深红",   198, 40, 40),
    ("H07", "粉",     248, 187, 208), ("H08", "紫",     156, 39, 176),
    ("H09", "浅蓝",   144, 202, 249), ("H10", "蓝",     30, 136, 229),
    ("H11", "深蓝",   13, 71, 161),   ("H12", "青",     0, 172, 193),
    ("H13", "浅绿",   165, 214, 167), ("H14", "绿",     67, 160, 71),
    ("H15", "深绿",   27, 94, 32),    ("H16", "橄榄",   130, 119, 23),
    ("H17", "浅棕",   188, 170, 164), ("H18", "棕",     121, 85, 72),
    ("H19", "深棕",   78, 52, 46),    ("H20", "浅灰",   224, 224, 224),
    ("H21", "灰",     158, 158, 158), ("H22", "深灰",   97, 97, 97),
    ("H23", "黑",     33, 33, 33),    ("H24", "丁香",   206, 147, 216),
    ("H25", "珊瑚",   239, 154, 154), ("H26", "薄荷",   200, 230, 201),
    ("H27", "沙色",   215, 204, 200), ("H28", "锡色",   120, 144, 156),
]


def _build_perler() -> Palette:
    colors = [
        BeadColor(code, zh, (r, g, b), name_en=en)
        for code, en, zh, r, g, b in _PERLER_RAW
    ]
    return Palette(name="Perler 官方色板（95色）", brand="perler", colors=colors)


def _build_artkal() -> Palette:
    colors = [BeadColor(code, name, (r, g, b)) for code, name, r, g, b in _ARTKAL_RAW]
    return Palette(name="Artkal 预览色板（30色）", brand="artkal", colors=colors)


def _build_hama() -> Palette:
    colors = [BeadColor(code, name, (r, g, b)) for code, name, r, g, b in _HAMA_RAW]
    return Palette(name="Hama 预览色板（28色）", brand="hama", colors=colors)


# ---------------------------------------------------------------------------
# MARD 291 色（国内拼豆品牌马尔德，色号如 H5、F11）
# 数据来自开源仓库 a31521424/pixel-to-beads 的 src/mard-color.json
# ---------------------------------------------------------------------------
_MARD_DATA = "data/mard.json"
_MARD_FAMILIES = {
    "A": "黄橙", "B": "绿", "C": "蓝青", "D": "紫", "E": "粉",
    "F": "红", "G": "棕", "H": "棕", "M": "黑白灰", "P": "粉",
    "Q": "特殊", "R": "红", "T": "特殊", "Y": "黄", "ZG": "荧光",
}


def load_mard() -> Palette:
    """从项目内 data/mard.json 加载 MARD 291 色。"""
    import json
    import os
    import re
    import sys

    if getattr(sys, "frozen", False):
        # PyInstaller 打包后数据文件被解压到 _MEIPASS 下
        base = os.path.join(getattr(sys, "_MEIPASS", ""), "bead_pattern")
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base, _MARD_DATA)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    colors: list[BeadColor] = []
    for code, hex_val in data.items():
        h = hex_val.lstrip("#")
        rgb = (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
        m = re.match(r"([A-Z]+)", code)
        family = _MARD_FAMILIES.get(m.group(1) if m else "", "其他")
        colors.append(BeadColor(code, f"{family}系{code}", rgb, name_en=code))

    return Palette(name=f"MARD 官方色板（{len(colors)}色）", brand="mard", colors=colors)


def builtin_palettes() -> dict[str, Palette]:
    return {
        "perler": _build_perler(),
        "artkal": _build_artkal(),
        "hama": _build_hama(),
        "mard": load_mard(),
    }


def load_palette(name: str) -> Palette:
    """按名称加载内置色板，未知名称抛出 KeyError。"""
    palettes = builtin_palettes()
    if name not in palettes:
        raise KeyError(
            f"未知色板 '{name}'，可选: {', '.join(sorted(palettes))} "
            "或使用 --palette-file 指定自定义 CSV。"
        )
    return palettes[name]


def load_palette_csv(path: str, name: str | None = None) -> Palette:
    """从 CSV 加载自定义色板。

    CSV 表头: code,name,hex （hex 形如 #RRGGBB），可选的第四列 name_en。
    """
    colors: list[BeadColor] = []
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if header is None:
            raise ValueError(f"色板 CSV 为空: {path}")
        cols = {h.strip().lower(): i for i, h in enumerate(header)}
        for raw in reader:
            if not raw or not raw[0].strip():
                continue
            code = raw[cols["code"]].strip()
            name = raw[cols["name"]].strip()
            hex_val = raw[cols["hex"]].strip().lstrip("#")
            r, g, b = int(hex_val[0:2], 16), int(hex_val[2:4], 16), int(hex_val[4:6], 16)
            en = raw[cols["name_en"]].strip() if "name_en" in cols and len(raw) > cols["name_en"] else ""
            colors.append(BeadColor(code, name, (r, g, b), name_en=en))
    if not colors:
        raise ValueError(f"色板 CSV 中没有有效颜色: {path}")
    brand = name or "custom"
    return Palette(name=f"自定义色板（{len(colors)}色）", brand=brand, colors=colors)
