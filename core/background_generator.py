"""
背景图片生成器模块
支持渐变背景、纹理叠加、装饰元素等功能
"""

from PIL import Image, ImageDraw, ImageFilter
from pathlib import Path
from typing import Optional, Tuple, List
import math


class BackgroundGenerator:
    """背景图片生成器"""

    def __init__(self, assets_dir: Optional[Path] = None):
        """
        初始化背景生成器

        Args:
            assets_dir: 素材目录路径
        """
        if assets_dir is None:
            assets_dir = Path(__file__).parent.parent / "assets"

        self.assets_dir = assets_dir
        self.textures_dir = assets_dir / "textures"
        self.decorations_dir = assets_dir / "decorations"

        # 创建必要的目录
        self.textures_dir.mkdir(parents=True, exist_ok=True)
        self.decorations_dir.mkdir(parents=True, exist_ok=True)

        # 修仙主题配色方案
        self.themes = {
            'xiuxian': {  # 修仙主题
                'colors': [(26, 32, 44), (67, 56, 202), (139, 92, 246), (255, 215, 0)],
                'name': '修仙紫金'
            },
            'alchemy': {  # 炼丹主题
                'colors': [(120, 40, 31), (220, 38, 38), (251, 146, 60), (255, 215, 0)],
                'name': '炼丹火焰'
            },
            'combat': {  # 战斗主题
                'colors': [(17, 24, 39), (127, 29, 29), (220, 38, 38), (255, 0, 0)],
                'name': '战斗血红'
            },
            'sect': {  # 宗门主题
                'colors': [(15, 23, 42), (30, 58, 138), (96, 165, 250), (255, 255, 255)],
                'name': '宗门青云'
            },
            'cultivation': {  # 修炼主题
                'colors': [(22, 30, 46), (49, 46, 129), (109, 40, 217), (168, 85, 247)],
                'name': '修炼紫气'
            },
            'nature': {  # 自然主题
                'colors': [(20, 83, 45), (22, 101, 52), (34, 197, 94), (134, 239, 172)],
                'name': '自然翠绿'
            },
            'treasure': {  # 宝物主题
                'colors': [(71, 85, 105), (168, 85, 247), (251, 191, 36), (255, 223, 0)],
                'name': '宝物金辉'
            },
        }

    def generate_gradient(
        self,
        width: int,
        height: int,
        colors: List[Tuple[int, int, int]],
        direction: str = 'vertical',
        smooth: bool = True
    ) -> Image.Image:
        """
        生成渐变背景

        Args:
            width: 图片宽度
            height: 图片高度
            colors: 颜色列表，至少2种颜色
            direction: 渐变方向 'vertical'(垂直) / 'horizontal'(水平) / 'radial'(径向) / 'diagonal'(对角)
            smooth: 是否使用平滑渐变

        Returns:
            PIL Image对象
        """
        if len(colors) < 2:
            raise ValueError("至少需要2种颜色")

        image = Image.new('RGB', (width, height))
        draw = ImageDraw.Draw(image)

        if direction == 'vertical':
            return self._generate_linear_gradient(image, colors, 'vertical', smooth)
        elif direction == 'horizontal':
            return self._generate_linear_gradient(image, colors, 'horizontal', smooth)
        elif direction == 'diagonal':
            return self._generate_diagonal_gradient(image, colors, smooth)
        elif direction == 'radial':
            return self._generate_radial_gradient(image, colors, smooth)
        else:
            raise ValueError(f"不支持的渐变方向: {direction}")

    def _generate_linear_gradient(
        self,
        image: Image.Image,
        colors: List[Tuple[int, int, int]],
        direction: str,
        smooth: bool
    ) -> Image.Image:
        """生成线性渐变"""
        width, height = image.size
        draw = ImageDraw.Draw(image)

        # 确定渐变的步数
        steps = height if direction == 'vertical' else width
        num_segments = len(colors) - 1

        for i in range(steps):
            # 计算当前位置在哪个颜色段
            progress = i / (steps - 1)  # 0.0 到 1.0
            segment_progress = progress * num_segments
            segment_index = min(int(segment_progress), num_segments - 1)
            local_progress = segment_progress - segment_index

            # 在两个颜色之间插值
            color1 = colors[segment_index]
            color2 = colors[segment_index + 1]

            if smooth:
                # 使用平滑插值（ease-in-out）
                local_progress = self._smooth_step(local_progress)

            r = int(color1[0] + (color2[0] - color1[0]) * local_progress)
            g = int(color1[1] + (color2[1] - color1[1]) * local_progress)
            b = int(color1[2] + (color2[2] - color1[2]) * local_progress)

            if direction == 'vertical':
                draw.line([(0, i), (width, i)], fill=(r, g, b))
            else:
                draw.line([(i, 0), (i, height)], fill=(r, g, b))

        return image

    def _generate_diagonal_gradient(
        self,
        image: Image.Image,
        colors: List[Tuple[int, int, int]],
        smooth: bool
    ) -> Image.Image:
        """生成对角线渐变"""
        width, height = image.size
        pixels = image.load()

        # 对角线最大距离
        max_distance = math.sqrt(width ** 2 + height ** 2)
        num_segments = len(colors) - 1

        for y in range(height):
            for x in range(width):
                # 计算点到左上角的距离
                distance = math.sqrt(x ** 2 + y ** 2)
                progress = distance / max_distance

                segment_progress = progress * num_segments
                segment_index = min(int(segment_progress), num_segments - 1)
                local_progress = segment_progress - segment_index

                color1 = colors[segment_index]
                color2 = colors[segment_index + 1]

                if smooth:
                    local_progress = self._smooth_step(local_progress)

                r = int(color1[0] + (color2[0] - color1[0]) * local_progress)
                g = int(color1[1] + (color2[1] - color1[1]) * local_progress)
                b = int(color1[2] + (color2[2] - color1[2]) * local_progress)

                pixels[x, y] = (r, g, b)

        return image

    def _generate_radial_gradient(
        self,
        image: Image.Image,
        colors: List[Tuple[int, int, int]],
        smooth: bool,
        center: Optional[Tuple[int, int]] = None
    ) -> Image.Image:
        """生成径向渐变"""
        width, height = image.size
        pixels = image.load()

        # 默认中心点
        if center is None:
            center = (width // 2, height // 2)

        # 最大半径
        max_radius = math.sqrt(
            max(center[0], width - center[0]) ** 2 +
            max(center[1], height - center[1]) ** 2
        )
        num_segments = len(colors) - 1

        for y in range(height):
            for x in range(width):
                # 计算点到中心的距离
                distance = math.sqrt((x - center[0]) ** 2 + (y - center[1]) ** 2)
                progress = min(distance / max_radius, 1.0)

                segment_progress = progress * num_segments
                segment_index = min(int(segment_progress), num_segments - 1)
                local_progress = segment_progress - segment_index

                color1 = colors[segment_index]
                color2 = colors[segment_index + 1]

                if smooth:
                    local_progress = self._smooth_step(local_progress)

                r = int(color1[0] + (color2[0] - color1[0]) * local_progress)
                g = int(color1[1] + (color2[1] - color1[1]) * local_progress)
                b = int(color1[2] + (color2[2] - color1[2]) * local_progress)

                pixels[x, y] = (r, g, b)

        return image

    def _smooth_step(self, t: float) -> float:
        """
        平滑插值函数（ease-in-out）

        Args:
            t: 输入值 (0.0-1.0)

        Returns:
            平滑后的值 (0.0-1.0)
        """
        return t * t * (3.0 - 2.0 * t)

    def add_texture(
        self,
        base_image: Image.Image,
        texture_path: Optional[Path] = None,
        opacity: float = 0.3,
        blend_mode: str = 'normal'
    ) -> Image.Image:
        """
        添加纹理叠加

        Args:
            base_image: 基础图片
            texture_path: 纹理图片路径（如果为None则生成简单噪点纹理）
            opacity: 纹理透明度 (0.0-1.0)
            blend_mode: 混合模式 'normal' / 'multiply' / 'screen'

        Returns:
            叠加纹理后的图片
        """
        width, height = base_image.size

        # 如果没有提供纹理路径，生成简单的噪点纹理
        if texture_path is None or not texture_path.exists():
            texture = self._generate_noise_texture(width, height)
        else:
            # 加载并调整纹理大小
            texture = Image.open(texture_path).convert('RGBA')
            texture = texture.resize((width, height), Image.Resampling.LANCZOS)

        # 调整透明度
        if texture.mode != 'RGBA':
            texture = texture.convert('RGBA')

        # 创建alpha通道
        alpha = texture.split()[3] if len(texture.split()) == 4 else Image.new('L', (width, height), 255)
        alpha = alpha.point(lambda p: int(p * opacity))

        # 转换base_image为RGBA
        if base_image.mode != 'RGBA':
            base_image = base_image.convert('RGBA')

        # 应用混合模式
        result = base_image.copy()
        texture.putalpha(alpha)
        result.paste(texture, (0, 0), texture)

        return result

    def _generate_noise_texture(self, width: int, height: int, intensity: int = 20) -> Image.Image:
        """
        生成简单的噪点纹理

        Args:
            width: 宽度
            height: 高度
            intensity: 噪点强度 (0-255)

        Returns:
            噪点纹理图片
        """
        import random

        texture = Image.new('RGBA', (width, height), (128, 128, 128, 0))
        pixels = texture.load()

        for y in range(0, height, 2):  # 每隔2个像素采样，提高性能
            for x in range(0, width, 2):
                noise = random.randint(-intensity, intensity)
                gray = 128 + noise
                gray = max(0, min(255, gray))
                pixels[x, y] = (gray, gray, gray, 50)

        return texture

    def add_glow_effect(
        self,
        base_image: Image.Image,
        glow_color: Tuple[int, int, int] = (255, 215, 0),
        intensity: float = 0.3,
        blur_radius: int = 30
    ) -> Image.Image:
        """
        添加光晕效果

        Args:
            base_image: 基础图片
            glow_color: 光晕颜色
            intensity: 光晕强度 (0.0-1.0)
            blur_radius: 模糊半径

        Returns:
            添加光晕后的图片
        """
        width, height = base_image.size

        # 创建光晕层
        glow_layer = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(glow_layer)

        # 在中心绘制渐变光晕
        center_x, center_y = width // 2, height // 2
        for i in range(blur_radius, 0, -2):
            alpha = int((i / blur_radius) * 255 * intensity)
            draw.ellipse(
                [center_x - i, center_y - i, center_x + i, center_y + i],
                fill=(*glow_color, alpha)
            )

        # 应用高斯模糊
        glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=blur_radius // 2))

        # 合并图层
        if base_image.mode != 'RGBA':
            base_image = base_image.convert('RGBA')

        result = Image.alpha_composite(base_image, glow_layer)
        return result

    def add_particles(
        self,
        base_image: Image.Image,
        particle_count: int = 50,
        particle_color: Tuple[int, int, int] = (255, 255, 255),
        particle_size_range: Tuple[int, int] = (1, 4),
        opacity_range: Tuple[int, int] = (50, 200)
    ) -> Image.Image:
        """
        添加粒子效果（灵气光点）

        Args:
            base_image: 基础图片
            particle_count: 粒子数量
            particle_color: 粒子颜色
            particle_size_range: 粒子大小范围 (min, max)
            opacity_range: 不透明度范围 (min, max)

        Returns:
            添加粒子后的图片
        """
        import random

        width, height = base_image.size

        if base_image.mode != 'RGBA':
            base_image = base_image.convert('RGBA')

        # 创建粒子层
        particle_layer = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(particle_layer)

        for _ in range(particle_count):
            x = random.randint(0, width)
            y = random.randint(0, height)
            size = random.randint(*particle_size_range)
            opacity = random.randint(*opacity_range)

            # 绘制粒子（小圆点）
            draw.ellipse(
                [x - size, y - size, x + size, y + size],
                fill=(*particle_color, opacity)
            )

            # 添加光晕
            if size > 2:
                glow_size = size + 2
                draw.ellipse(
                    [x - glow_size, y - glow_size, x + glow_size, y + glow_size],
                    fill=(*particle_color, opacity // 3)
                )

        # 合并图层
        result = Image.alpha_composite(base_image, particle_layer)
        return result

    def generate_themed_background(
        self,
        width: int,
        height: int,
        theme: str = 'xiuxian',
        direction: str = 'radial',
        add_effects: bool = True
    ) -> Image.Image:
        """
        生成主题背景（一站式方法）

        Args:
            width: 宽度
            height: 高度
            theme: 主题名称 ('xiuxian', 'alchemy', 'combat', 'sect', 'cultivation', 'nature', 'treasure')
            direction: 渐变方向
            add_effects: 是否添加特效（纹理、粒子等）

        Returns:
            完整的主题背景图片
        """
        if theme not in self.themes:
            theme = 'xiuxian'

        theme_config = self.themes[theme]
        colors = theme_config['colors']

        # 1. 生成渐变背景
        background = self.generate_gradient(width, height, colors, direction, smooth=True)

        if add_effects:
            # 2. 添加纹理
            background = self.add_texture(background, opacity=0.15)

            # 3. 根据主题添加特定效果
            if theme in ['xiuxian', 'cultivation', 'sect']:
                # 修仙类主题：添加紫金色光晕和粒子
                background = self.add_glow_effect(
                    background,
                    glow_color=(168, 85, 247),  # 紫色
                    intensity=0.2,
                    blur_radius=40
                )
                background = self.add_particles(
                    background,
                    particle_count=40,
                    particle_color=(255, 215, 0),  # 金色
                    particle_size_range=(1, 3),
                    opacity_range=(100, 180)
                )

            elif theme == 'alchemy':
                # 炼丹主题：火焰色光晕
                background = self.add_glow_effect(
                    background,
                    glow_color=(251, 146, 60),  # 橙色
                    intensity=0.3,
                    blur_radius=50
                )
                background = self.add_particles(
                    background,
                    particle_count=30,
                    particle_color=(255, 100, 0),  # 火焰色
                    particle_size_range=(2, 5),
                    opacity_range=(120, 200)
                )

            elif theme == 'combat':
                # 战斗主题：红色光晕和能量粒子
                background = self.add_glow_effect(
                    background,
                    glow_color=(220, 38, 38),  # 红色
                    intensity=0.25,
                    blur_radius=35
                )
                background = self.add_particles(
                    background,
                    particle_count=60,
                    particle_color=(255, 0, 0),  # 红色
                    particle_size_range=(1, 4),
                    opacity_range=(100, 200)
                )

            elif theme == 'nature':
                # 自然主题：绿色光晕
                background = self.add_glow_effect(
                    background,
                    glow_color=(34, 197, 94),  # 绿色
                    intensity=0.2,
                    blur_radius=40
                )
                background = self.add_particles(
                    background,
                    particle_count=35,
                    particle_color=(134, 239, 172),  # 浅绿
                    particle_size_range=(1, 3),
                    opacity_range=(80, 150)
                )

            elif theme == 'treasure':
                # 宝物主题：金色光晕和闪光粒子
                background = self.add_glow_effect(
                    background,
                    glow_color=(255, 215, 0),  # 金色
                    intensity=0.35,
                    blur_radius=45
                )
                background = self.add_particles(
                    background,
                    particle_count=50,
                    particle_color=(255, 223, 0),  # 金色
                    particle_size_range=(2, 5),
                    opacity_range=(150, 255)
                )

        return background

    def get_available_themes(self) -> List[str]:
        """
        获取可用的主题列表

        Returns:
            主题名称列表
        """
        return list(self.themes.keys())

    def get_theme_info(self, theme: str) -> dict:
        """
        获取主题信息

        Args:
            theme: 主题名称

        Returns:
            主题配置字典
        """
        return self.themes.get(theme, self.themes['xiuxian'])
