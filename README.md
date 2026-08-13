# 拼豆图纸转换器

把一张图片自动转换成**带字符色号的拼豆图纸**：图片按网格放大成一颗颗豆，每颗豆都标上字符代码，底部附带色号图例。适合 Perler / Artkal / Hama 等拼豆制作。

## 快速开始

### 最简单：拖拽图片到 bat 文件

直接把图片拖到 **`拼豆图纸精简版.bat`** 上，自动生成图纸，完成后会看到统计信息。
可以一次拖多张图片，无需调节参数，适合懒人。

### 调节参数版本：`拼豆图纸参数自选.bat`

双击 **`拼豆图纸参数自选.bat`** 会弹出菜单（菜单由 `interactive.py` 实现，UTF-8 中文（cmd有点问题啊），转换前可以逐项调节参数，无需改代码：

- **[1] 品牌/色板**：`mard`(291色) / `perler`(95色) / `artkal`(30色) / `hama`(28色)
- **[2] 图例语言**：`zh` 中文 / `en` English / `both` 双语
- **[3] 色号标注**：`brand` 品牌色号(如 H5/F11) / `letter` ABC / `number` 123
- **[4] 最多用色**：0(不限) / 8 / 12 / 16 / 24 / 36
- **[5] 每格大小**：20 / 24 / 28 / 30 / 36 px
- **[6] 显示坐标**、**[7] 网格线**、**[8] 立体豆感**：开/关切换
- **[9] 图纸标题**、**[A] 背景色**、**[B] 底板尺寸(宽×高)**：手动输入

设置好后按 **S** 开始转换，可选「输入图片路径（可拖拽）」「弹出文件选择框」；按 **D** 直接生成示例图体验。

把图片拖到 `拼豆图纸参数自选.bat` 图标上，会**先进入菜单**并显示「已选文件」，你可以先调节参数，再按 **S** 选择「用已选文件转换」——不会直接用默认参数乱转。

> 说明：`拼豆图纸参数自选.bat` 只是入口（纯 ASCII），真正的交互菜单在 `interactive.py`（UTF-8），因此任何编辑器/终端打开都不会乱码。

### 命令行
```bash
# 安装依赖（只需一次）
pip install -r requirements.txt

# 转换一张图片
python main.py 照片.png

# 带坐标、限制 24 色
python main.py 照片.png --max-colors 24 --coords

# 生成示例体验
python main.py --demo

# 弹出文件选择框
python main.py --pick
```

输出文件（默认每个输入图片生成一个**与图片同名**的子文件夹，如 `output/照片/`）：

| 文件 | 说明 |
|------|------|
| `<名>_pattern.png` | 拼豆图纸 |
| `<名>_colors.csv` | 颜色用量清单 |
| `<名>_grid.csv` | 网格代码表 |

> 每个输入图片的所有结果都放在 `output/<图片名>/` 同名文件夹内，方便按图片归档。
> 显式指定 `--out-dir`（或 `--output`）时则输出到你指定的位置。

## 常用参数

### 网格尺寸
```bash
--size 200          # 最大边长上限（超过才等比缩小，默认 200。图片本身 ≤ 200 则保持原尺寸）
--width 80          # 固定宽度（格），指定后强制缩放
--height 60         # 固定高度（格）
```

### 颜色处理（核心：自动统一相似/模糊颜色）
```bash
--max-colors 24     # 最多只用 24 种颜色：贪心挑选最能代表本图的色号，把相似的颜色自动合并
--palette perler    # 色板：perler(95色) / artkal(30色) / hama(28色)
--palette-file 我的色板.csv   # 自定义色板（code,name,hex[,name_en]）
--metric ciede2000  # 色差度量：ciede2000 更养眼（推荐）/ cie76 更快
--bg-hex '#FFFFFF'  # 把该颜色当背景（空格不填豆）
--auto-bg           # 自动把图片四周主色识别为背景
--bg-tol 6          # 背景匹配容差
```

透明像素（alpha < 128）会自动当作空格，不填豆。

### 字符标注与出图
```bash
--label-style letter   # 单元格代码：letter=A,B,C...(推荐) / number=1,2,3... / brand=P01,A01,H01
--cell 24              # 每格像素大小（越大代码越清晰；brand 风格建议 >=28）
--coords               # 显示行列坐标（类似 Excel）
--no-grid-lines        # 不画网格线
--no-legend            # 不要底部色号图例
--title "我的图纸"      # 顶部标题
--bead-look            # 给豆子加内阴影，更接近实物观感
--lang zh              # 图例名称语言：zh / en / both
```

### 输出
```bash
--out-dir output       # 输出目录（默认 output/，自动创建）
--no-colors-csv        # 不导出颜色清单
--no-grid-csv          # 不导出网格代码
```

## 工作原理

1. **保持原尺寸**：默认不做缩放，每个像素 = 1 颗豆。仅在图片某边超过 `--size` 上限时才等比缩小（防止超大图渲崩）。
2. **颜色映射**：把每格颜色转成 CIELAB，用 **CIEDE2000** 色差找最近的标准豆色（比直接 RGB 距离更符合人眼）。
3. **自动减色**：`--max-colors N` 时，用贪心算法从色板中挑选 N 种"最能代表本图"的豆色，再统一映射 —— 相似、模糊的颜色自动归并到最常用的色号。
4. **像素放大**：每颗豆渲染为 `--cell`×`--cell` 像素大方格，中心标字符代码（按明暗自动黑/白字保证对比度），底部生成色号图例与颗数统计。

## 色板说明

| 色板 | 来源 | 说明 |
|------|------|------|
| `perler` | Perler 官方色板（开源仓库转写） | 95 色，含中英文名，推荐 |
| `artkal` | Artkal 预览色板 | 30 色（A01–A30） |
| `hama` | Hama 预览色板 | 28 色（H01–H28） |
| `mard` | **MARD（麦德）官方 291 色** | 国内拼豆品牌，色号如 `A1`、`H5`、`F11`、`ZG5`，完整映射表已导出在 `output/MARD.csv` |

## MARD 色号用法

```bash
# 用 MARD 色板 + 品牌色号标注（单元格显示 H5、F11 这种色号）
python main.py 照片.png --palette mard --label-style brand --cell 30 --max-colors 24
```

配套说明：
- `output/MARD色号映射表.csv`：完整 291 色（code / 名称 / HEX / RGB），可直接对照备料
- `bead_pattern/data/mard.json`：色号 → HEX 原始数据
- MARD 系列：A黄橙(26)、B绿(32)、C蓝青(29)、D紫(26)、E粉(24)、F红(25)、G棕(21)、H棕(23)、M黑白灰(15)、P粉(23)、Q特殊(5)、R红(28)、T特殊(1)、Y黄(5)、ZG荧光(8)

## 示例命令

```bash
# 基础用法：保持原图尺寸，每个像素 = 1 颗豆
python main.py 皮卡丘.png --max-colors 24 --coords

# 加坐标、限制 24 色（会自动合并相近颜色）
python main.py 头像.png --coords --max-colors 24 --cell 22

# 品牌色号标注（cell 建议放大些）
python main.py 图标.png --label-style brand --cell 30

# 指定固定底板尺寸（如 29×29 小底板）
python main.py 图标.png --width 29 --height 29 --max-colors 12

# 去掉白色背景
python main.py logo.png --bg-hex '#FFFFFF' --max-colors 16
```

## 项目结构

```
dot/
├── main.py                 # 命令行入口
├── requirements.txt        # numpy + Pillow
├── README.md
└── bead_pattern/
    ├── palettes.py         # Perler/Artkal/Hama 色板 + 自定义 CSV 加载
    ├── color.py            # sRGB→Lab、CIEDE2000/CIE76 色差
    ├── converter.py        # 缩放、映射、贪心减色、背景处理
    ├── renderer.py         # 图纸渲染（网格+代码+坐标+图例）
    └── exporter.py         # 颜色清单 / 网格代码 CSV 导出
```
