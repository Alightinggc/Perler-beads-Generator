# 拼豆图纸转换器

把一张图片自动转换成**带字符色号的拼豆图纸**：图片按网格放大成一颗颗豆，每颗豆都标上字符代码，底部附带色号图例。适合 Perler / Artkal / Hama 等拼豆制作。



## 快速开始：使用release版的exe文件
可以直接将图片拖拽至**`拼豆图纸精简版`**或**`拼豆图纸参数自选`**进行快速生成。
也可以使用**`拼豆图纸网页版`**的可视化ui来生成。


### 最简单：拖拽图片到 exe 文件

直接把图片拖到 **`拼豆图纸精简版.exe`** 上，自动生成图纸，完成后会看到统计信息。
可以一次拖多张图片，无需调节参数，适合懒人。

### 调节参数版本：`拼豆图纸参数自选.exe`

双击 **`拼豆图纸参数自选.exe`** 会弹出菜单（菜单由 `interactive.py` 实现，转换前可以逐项调节参数：

- **[1] 品牌/色板**：`mard`(291色) / `perler`(95色) / `artkal`(30色) / `hama`(28色)
- **[2] 色号标注**：`brand` 品牌色号(如 H5/F11) / `letter` ABC / `number` 123
- **[3] 最多用色**：0(不限) / 8 / 12 / 16 / 24 / 36
- **[4] 每格大小**：20 / 24 / 28 / 30 / 36 px
- **[5] 显示坐标**、**[6] 网格线**、**[7] 立体豆感**、**[8] 抖动处理(Floyd-Steinberg)**：开/关切换
- **[9] 图纸标题**、**[A] 底板尺寸(宽×高)**：手动输入

设置好后按 **S** 开始转换，可选「输入图片路径（可拖拽）」「弹出文件选择框」；按 **D** 直接生成示例图体验。

把图片拖到 `拼豆图纸参数自选.exe` 图标上，会**先进入菜单**并显示「已选文件」，你可以先调节参数，再按 **S** 选择「用已选文件转换」——不会直接用默认参数乱转。

### 网页版界面（推荐）：`拼豆图纸网页版.exe`

双击 **`拼豆图纸网页版.exe`**（或命令行 `python webui.py`），会自动打开浏览器，呈现一个现代化的网页界面：

- **拖拽选图**：把一张或多张图片拖进上传区（或点击选择），列表即时显示缩略图
- **参数面板**：品牌/色板、色号标注、最多用色、每格大小、最大边长、图例语言、底板尺寸、图纸标题，以及显示坐标 / 网格线 / 立体豆感 / 抖动处理等开关
- **图纸预览**：转换完成后在页面内直接预览生成的图纸，一键下载颜色清单/网格表，或“打开文件夹”定位成品
- **本地运行**：所有转换都在本机完成，图片不上传任何外部服务器

**注意** 不要关闭cmd页面

> 说明：网页界面由 `webui.py`（本地 HTTP 服务）+ `web/index.html` 实现，**零额外依赖**（仅需 numpy + Pillow）。关闭服务 = 关闭运行 exe 弹出的那个命令行窗口（或按 Ctrl+C）。

## 命令行
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

输出文件（默认每个输入图片生成一个**与图片名+品牌+最大颜色数同名**的子文件夹，如 `output/chicken_mard_24/`）：

| 文件 | 说明 |
|------|------|
| `<名>_<品牌>_<最大颜色数>_pattern.png` | 拼豆图纸 |
| `<名>_<品牌>_<最大颜色数>_colors.csv` | 颜色用量清单 |
| `<名>_<品牌>_<最大颜色数>_grid.csv` | 网格代码表 |

> 文件名和文件夹名依次为：原文件名 + 品牌（如 mard/perler）+ 最大颜色数（如 24），用下划线隔开。
> 示例：文件夹 `output/chicken_mard_24/` 内为 `chicken_mard_24_pattern.png`
> 每个输入图片的所有结果都放在 `output/<图片名>_<品牌>_<最大颜色数>/` 同名文件夹内，方便按图片归档。
> **同名不覆盖**：如果已存在同名的输出文件夹，会自动新建 `(1)`、`(2)`… 的独立文件夹（如 `output/chicken_mard_24 (1)/`），文件夹内文件名保持干净；每次转换都是独立一批，互不覆盖。
> 显式指定 `--out-dir`（或 `--output`）时则输出到你指定的位置。

## 配套工具：先把大图缩回单像素（`shrink_pixel_art.py`）

如果你的图片是**截图 / 放大保存**的像素画（一个像素格在图片里占了很多像素），
直接转换会让图纸巨大、看不清颜色。先用这个小工具**自动检测每个像素格占多大**，
再缩回单像素风格，且不破坏原图的像素分布。核心采用**网格线检测**：
扫描每一列/行找出像素格的真实边界，自动适配非整数块大小、局部缩放差异、
相邻同色合并与 JPEG 噪点，比简单的“全局块大小 + 最近邻”缩放准得多：

程序会自动寻找最小的像素方格进行压缩，所以请保证你的截图/保存图片画面上只有你要转换的像素画
能力有限，没有办法做出更好的效果。
推荐放入长宽接近的图片。

```bash
# 自动检测并缩小（默认输出到 output_ 文件夹，命名 <名>_<宽>x<高>.png）
python shrink_pixel_art.py 截图.png

# 手动指定每格像素数（如截图里一格占 20 像素）
python shrink_pixel_art.py 截图.png --block 20

# JPEG/抗锯齿图：缩小后再把颜色量化成 12 种，方便看色号
python shrink_pixel_art.py 截图.jpg --quantize 12

# 先裁掉四周白边/边框再缩小
python shrink_pixel_art.py 截图.png --autocrop

# 只检测并打印信息，不保存
python shrink_pixel_art.py 截图.png --info

# 批量处理整个目录 / 通配符
python shrink_pixel_art.py 图片目录
python shrink_pixel_art.py "*.png"
```

技术栈：`numpy` + `Pillow`（自动块大小检测 + 最近邻插值 / 块主色聚合）。
用法与原理详见该文件顶部注释。

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
--dither               # 开启Floyd-Steinberg抖动（默认关闭；开启能更好还原渐变/过渡色）
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
```

## 项目结构

```
dot/
├── main.py                 # 命令行入口
├── interactive.py          # cmd 文本菜单
├── webui.py                # 网页版界面本地服务器
├── web/index.html          # 网页版界面（HTML+CSS+JS）
├── requirements.txt        # numpy + Pillow
├── README.md
└── bead_pattern/
    ├── palettes.py         # Perler/Artkal/Hama 色板 + 自定义 CSV 加载
    ├── color.py            # sRGB→Lab、CIEDE2000/CIE76 色差
    ├── converter.py        # 缩放、映射、贪心减色、背景处理
    ├── renderer.py         # 图纸渲染（网格+代码+坐标+图例）
    └── exporter.py         # 颜色清单 / 网格代码 CSV 导出
```
