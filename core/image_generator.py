"""
图片生成器模块
用于生成修仙插件的各类图形化界面卡片
"""

from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import io
from typing import Optional, Tuple, Dict, List
from datetime import datetime


class ImageGenerator:
    """图片生成器基础类"""

    def __init__(self, assets_dir: Optional[Path] = None):
        """
        初始化图片生成器

        Args:
            assets_dir: 素材目录路径
        """
        if assets_dir is None:
            assets_dir = Path(__file__).parent.parent / "assets"

        self.assets_dir = assets_dir
        self.fonts_dir = assets_dir / "fonts"
        self.images_dir = assets_dir / "images"
        self.output_dir = assets_dir / "output"

        # 创建必要的目录
        self.assets_dir.mkdir(exist_ok=True)
        self.fonts_dir.mkdir(exist_ok=True)
        self.images_dir.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)

        # 颜色方案（修仙风格）
        self.colors = {
            # 背景色
            'bg_main': (26, 32, 44),          # 深蓝灰
            'bg_secondary': (45, 55, 72),     # 中蓝灰
            'bg_card': (30, 41, 59),          # 卡片背景

            # 文字色
            'text_primary': (237, 242, 247),  # 主文字（亮白）
            'text_secondary': (160, 174, 192), # 次要文字（灰白）
            'text_accent': (255, 215, 0),      # 强调文字（金色）

            # 品质颜色
            'quality_common': (156, 163, 175),    # 凡品（灰）
            'quality_uncommon': (96, 165, 250),   # 灵品（蓝）
            'quality_rare': (168, 85, 247),       # 宝品（紫）
            'quality_epic': (251, 191, 36),       # 仙品（金）
            'quality_legendary': (239, 68, 68),   # 神品（红）
            'quality_mythic': (255, 0, 255),      # 道品（粉）

            # 元素颜色
            'element_gold': (255, 215, 0),    # 金
            'element_wood': (34, 197, 94),    # 木
            'element_water': (59, 130, 246),  # 水
            'element_fire': (239, 68, 68),    # 火
            'element_earth': (161, 98, 7),    # 土

            # 状态颜色
            'hp_color': (239, 68, 68),        # 生命值（红）
            'mp_color': (59, 130, 246),       # 法力值（蓝）
            'exp_color': (251, 191, 36),      # 经验值（金）

            # 进度条
            'progress_bg': (55, 65, 81),      # 进度条背景
            'progress_fill': (139, 92, 246),  # 进度条填充（紫）

            # 边框
            'border_default': (75, 85, 99),   # 默认边框
            'border_highlight': (168, 85, 247), # 高亮边框
        }

        # 尝试加载字体
        self._load_fonts()

    def _load_fonts(self):
        """加载字体文件"""
        # 打印调试信息
        print(f"[FontLoader] 字体目录: {self.fonts_dir}")
        print(f"[FontLoader] 字体目录是否存在: {self.fonts_dir.exists()}")

        # 字体搜索路径（优先使用项目内字体）
        font_paths = [
            # 1. 项目字体目录（优先级最高）
            self.fonts_dir / "NotoSansCJK-Regular.ttc",      # Noto Sans CJK（推荐）
            self.fonts_dir / "SourceHanSansCN-Regular.otf",  # 思源黑体
            self.fonts_dir / "SimHei.ttf",                   # 黑体

            # 2. Linux 系统字体
            "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",  # 文泉驿正黑
            "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc", # 文泉驿微米黑
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",  # Noto Sans CJK
            "/usr/share/fonts/truetype/arphic/uming.ttc",    # AR PL UMing
            "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",  # Droid Sans Fallback

            # 3. macOS 系统字体
            "/System/Library/Fonts/PingFang.ttc",            # 苹方
            "/System/Library/Fonts/STHeiti Light.ttc",       # 华文黑体

            # 4. Windows 系统字体
            "C:\\Windows\\Fonts\\msyh.ttc",                  # 微软雅黑
            "C:\\Windows\\Fonts\\simhei.ttf",                # 黑体
            "C:\\Windows\\Fonts\\simsun.ttc",                # 宋体
        ]

        # 检查哪些字体文件存在
        print("[FontLoader] 检查字体文件...")
        for i, fp in enumerate(font_paths[:5], 1):  # 只检查前5个
            exists = Path(fp).exists()
            status = "✓" if exists else "✗"
            print(f"  [{status}] {fp}")
            if exists and i <= 3:  # 项目字体
                try:
                    size = Path(fp).stat().st_size / (1024 * 1024)
                    print(f"      大小: {size:.1f} MB")
                except:
                    pass

        self.fonts = {}
        self.font_path_used = None
        self.font_missing_warning = False

        # 尝试加载字体 - 增加更大的字体尺寸
        for size in [12, 14, 16, 18, 20, 24, 28, 32, 36, 40, 48, 56, 64, 72, 80]:
            font_loaded = False
            for font_path in font_paths:
                try:
                    font_path_obj = Path(font_path)
                    if font_path_obj.exists():
                        # 尝试加载字体
                        self.fonts[size] = ImageFont.truetype(str(font_path_obj.absolute()), size)

                        if self.font_path_used is None:
                            self.font_path_used = str(font_path_obj.absolute())
                            # 判断是否使用了项目内字体
                            if str(self.fonts_dir) in str(font_path):
                                print(f"\n[FontLoader] ✅ 成功加载项目字体!")
                                print(f"             路径: {font_path_obj.absolute()}")
                            else:
                                print(f"\n[FontLoader] ℹ️  使用系统字体: {font_path_obj.absolute()}")
                        font_loaded = True
                        break
                except Exception as e:
                    if self.font_path_used is None:  # 只在第一次打印错误
                        print(f"  [!] 加载失败: {font_path} - {e}")
                    continue

            if not font_loaded:
                # 使用PIL默认字体（不支持中文，但至少能显示）
                self.fonts[size] = ImageFont.load_default()

                if not self.font_missing_warning:
                    self.font_missing_warning = True
                    self.font_path_used = "PIL默认字体（不支持中文）"
                    print("\n" + "!" * 70)
                    print("⚠️  警告：未找到任何中文字体！")
                    print("!" * 70)
                    print(f"字体目录: {self.fonts_dir}")
                    print("中文将显示为方块。")
                    print()
                    print("解决方法:")
                    print(f"1. 运行: python3 {self.fonts_dir / 'download_fonts.py'}")
                    print("2. 或安装系统字体: sudo apt install fonts-noto-cjk")
                    print("!" * 70 + "\n")

    def get_font(self, size: int = 16) -> ImageFont.FreeTypeFont:
        """
        获取指定大小的字体

        Args:
            size: 字体大小

        Returns:
            字体对象
        """
        return self.fonts.get(size, self.fonts.get(16, ImageFont.load_default()))

    def draw_rounded_rectangle(
        self,
        draw: ImageDraw.ImageDraw,
        xy: Tuple[int, int, int, int],
        radius: int = 10,
        fill: Optional[Tuple[int, int, int]] = None,
        outline: Optional[Tuple[int, int, int]] = None,
        width: int = 1
    ):
        """
        绘制圆角矩形

        Args:
            draw: ImageDraw对象
            xy: 坐标 (x1, y1, x2, y2)
            radius: 圆角半径
            fill: 填充颜色
            outline: 边框颜色
            width: 边框宽度
        """
        x1, y1, x2, y2 = xy

        # 绘制四个圆角
        draw.pieslice([x1, y1, x1 + radius * 2, y1 + radius * 2], 180, 270, fill=fill, outline=outline, width=width)
        draw.pieslice([x2 - radius * 2, y1, x2, y1 + radius * 2], 270, 360, fill=fill, outline=outline, width=width)
        draw.pieslice([x1, y2 - radius * 2, x1 + radius * 2, y2], 90, 180, fill=fill, outline=outline, width=width)
        draw.pieslice([x2 - radius * 2, y2 - radius * 2, x2, y2], 0, 90, fill=fill, outline=outline, width=width)

        # 绘制矩形部分
        draw.rectangle([x1 + radius, y1, x2 - radius, y2], fill=fill, outline=outline, width=0)
        draw.rectangle([x1, y1 + radius, x2, y2 - radius], fill=fill, outline=outline, width=0)

        # 绘制边框
        if outline and width > 0:
            draw.line([x1 + radius, y1, x2 - radius, y1], fill=outline, width=width)
            draw.line([x1 + radius, y2, x2 - radius, y2], fill=outline, width=width)
            draw.line([x1, y1 + radius, x1, y2 - radius], fill=outline, width=width)
            draw.line([x2, y1 + radius, x2, y2 - radius], fill=outline, width=width)

    def draw_progress_bar(
        self,
        draw: ImageDraw.ImageDraw,
        xy: Tuple[int, int],
        width: int,
        height: int,
        progress: float,
        bg_color: Optional[Tuple[int, int, int]] = None,
        fill_color: Optional[Tuple[int, int, int]] = None,
        border_color: Optional[Tuple[int, int, int]] = None,
        radius: int = 5
    ):
        """
        绘制进度条

        Args:
            draw: ImageDraw对象
            xy: 左上角坐标 (x, y)
            width: 进度条宽度
            height: 进度条高度
            progress: 进度值 (0.0-1.0)
            bg_color: 背景颜色
            fill_color: 填充颜色
            border_color: 边框颜色
            radius: 圆角半径
        """
        x, y = xy
        progress = max(0.0, min(1.0, progress))

        if bg_color is None:
            bg_color = self.colors['progress_bg']
        if fill_color is None:
            fill_color = self.colors['progress_fill']
        if border_color is None:
            border_color = self.colors['border_default']

        # 绘制背景
        self.draw_rounded_rectangle(
            draw,
            (x, y, x + width, y + height),
            radius=radius,
            fill=bg_color,
            outline=border_color,
            width=1
        )

        # 绘制进度
        if progress > 0:
            fill_width = int(width * progress)
            self.draw_rounded_rectangle(
                draw,
                (x, y, x + fill_width, y + height),
                radius=radius,
                fill=fill_color,
                outline=None,
                width=0
            )

    def get_quality_color(self, quality: str) -> Tuple[int, int, int]:
        """
        根据品质获取颜色

        Args:
            quality: 品质名称（支持装备品质和灵根品质）

        Returns:
            RGB颜色元组
        """
        quality_map = {
            # 装备品质
            '凡品': 'quality_common',
            '灵品': 'quality_uncommon',
            '宝品': 'quality_rare',
            '仙品': 'quality_epic',
            '神品': 'quality_legendary',
            '道品': 'quality_mythic',
            '混沌品': 'quality_mythic',
            # 灵根品质
            '废灵根': 'quality_common',
            '杂灵根': 'quality_uncommon',
            '双灵根': 'quality_rare',
            '单灵根': 'quality_epic',
            '变异灵根': 'quality_legendary',
            '天灵根': 'quality_mythic',
        }
        color_key = quality_map.get(quality, 'quality_common')
        return self.colors[color_key]

    def get_element_color(self, element: str) -> Tuple[int, int, int]:
        """
        根据元素获取颜色

        Args:
            element: 元素名称

        Returns:
            RGB颜色元组
        """
        element_map = {
            '金': 'element_gold',
            '木': 'element_wood',
            '水': 'element_water',
            '火': 'element_fire',
            '土': 'element_earth',
        }
        color_key = element_map.get(element, 'text_primary')
        return self.colors[color_key]

    def save_image(self, image: Image.Image, filename: str) -> Path:
        """
        保存图片

        Args:
            image: PIL Image对象
            filename: 文件名

        Returns:
            保存的文件路径
        """
        filepath = self.output_dir / filename
        image.save(filepath, 'PNG')
        return filepath

    def image_to_bytes(self, image: Image.Image, format: str = 'PNG') -> bytes:
        """
        将图片转换为字节数据

        Args:
            image: PIL Image对象
            format: 图片格式

        Returns:
            字节数据
        """
        buffer = io.BytesIO()
        image.save(buffer, format=format)
        return buffer.getvalue()
