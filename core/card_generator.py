"""
卡片生成器模块
实现各类修仙游戏卡片的生成
"""

from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
from typing import Optional, Dict, Any, List
import io
import urllib.request
from .image_generator import ImageGenerator
from .background_generator import BackgroundGenerator
from .image_config import ImageConfig, get_global_config


class CardGenerator(ImageGenerator):
    """修仙卡片生成器"""

    def __init__(self, assets_dir: Optional[Path] = None, config: Optional[ImageConfig] = None):
        super().__init__(assets_dir)

        # 初始化背景生成器
        self.bg_generator = BackgroundGenerator(assets_dir)

        # 加载配置
        self.config = config if config else get_global_config()

    def _get_qq_avatar(self, qq_id: str, size: int = 100) -> Optional[Image.Image]:
        """
        获取QQ头像

        Args:
            qq_id: QQ号
            size: 头像大小

        Returns:
            PIL Image对象，获取失败返回None
        """
        try:
            # QQ头像API
            url = f"https://q1.qlogo.cn/g?b=qq&nk={qq_id}&s=640"

            # 下载头像
            with urllib.request.urlopen(url, timeout=5) as response:
                avatar_data = response.read()
                avatar = Image.open(io.BytesIO(avatar_data))
                avatar = avatar.convert('RGBA')
                avatar = avatar.resize((size, size), Image.Resampling.LANCZOS)
                return avatar
        except Exception as e:
            print(f"[CardGenerator] 获取QQ头像失败: {e}")
            return None

    def _create_circular_avatar(self, avatar: Image.Image) -> Image.Image:
        """
        创建圆形头像

        Args:
            avatar: 原始头像

        Returns:
            圆形头像
        """
        size = avatar.size[0]

        # 创建圆形遮罩
        mask = Image.new('L', (size, size), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse((0, 0, size, size), fill=255)

        # 应用遮罩
        output = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        output.paste(avatar, (0, 0))
        output.putalpha(mask)

        return output

    def generate_player_card(self, player_data: Dict[str, Any]) -> Image.Image:
        """
        生成角色属性卡片

        Args:
            player_data: 玩家数据字典
                {
                    'name': str,        # 角色名称
                    'user_id': str,     # 用户ID (QQ号)
                    'realm': str,       # 境界
                    'realm_level': int, # 小等级
                    'cultivation': int, # 当前修为
                    'max_cultivation': int, # 升级所需修为
                    'hp': int,          # 当前生命值
                    'max_hp': int,      # 最大生命值
                    'mp': int,          # 当前法力值
                    'max_mp': int,      # 最大法力值
                    'attack': int,      # 攻击力
                    'defense': int,     # 防御力
                    'spirit_root': str, # 灵根类型
                    'spirit_root_quality': str, # 灵根品质
                }

        Returns:
            PIL Image对象
        """
        # 卡片尺寸 - 调整为更适合QQ显示的尺寸
        width, height = 800, 650
        padding = 40
        content_padding = 50  # 内容区域内边距

        # 创建简洁的渐变背景
        image = Image.new('RGBA', (width, height), self.colors['bg_main'])
        draw = ImageDraw.Draw(image)

        # 绘制渐变背景（从深蓝到浅紫）
        for y in range(height):
            ratio = y / height
            r = int(26 + (67 - 26) * ratio)
            g = int(32 + (56 - 32) * ratio)
            b = int(44 + (202 - 44) * ratio)
            draw.line([(0, y), (width, y)], fill=(r, g, b))

        # 绘制半透明卡片背景
        card_overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        card_draw = ImageDraw.Draw(card_overlay)
        self.draw_rounded_rectangle(
            card_draw,
            (padding, padding, width - padding, height - padding),
            radius=20,
            fill=(30, 41, 59, 230),  # 半透明背景
            outline=self.colors['border_highlight'],
            width=3
        )
        image = Image.alpha_composite(image, card_overlay)
        draw = ImageDraw.Draw(image)

        # 获取QQ头像
        avatar_size = 120
        user_id = player_data.get('user_id', '')
        avatar = None
        if user_id:
            avatar = self._get_qq_avatar(user_id, avatar_size)
            if avatar:
                avatar = self._create_circular_avatar(avatar)

        # 头像区域
        avatar_x = content_padding
        avatar_y = content_padding

        if avatar:
            # 绘制头像边框
            border_width = 4
            self.draw_rounded_rectangle(
                draw,
                (avatar_x - border_width, avatar_y - border_width,
                 avatar_x + avatar_size + border_width, avatar_y + avatar_size + border_width),
                radius=avatar_size // 2 + border_width,
                fill=None,
                outline=self.colors['border_highlight'],
                width=border_width
            )
            # 粘贴头像
            image.paste(avatar, (avatar_x, avatar_y), avatar)

        # 文字区域起始X坐标
        text_start_x = content_padding + avatar_size + 30 if avatar else content_padding

        # 格式化数字函数
        def format_number(n):
            if n >= 1_000_000_000:
                return f"{n/1_000_000_000:.1f}B"
            elif n >= 1_000_000:
                return f"{n/1_000_000:.1f}M"
            elif n >= 1_000:
                return f"{n/1_000:.1f}K"
            else:
                return str(int(n))

        # 绘制角色名称 - 大幅增大字体
        name = player_data.get('name', '未知')
        y = content_padding
        draw.text(
            (text_start_x, y),
            name,
            font=self.get_font(64),  # 48 -> 64
            fill=self.colors['text_accent']
        )
        y += 80

        # 绘制境界信息 - 大幅增大字体
        realm = player_data.get('realm', '凡人')
        realm_level = player_data.get('realm_level', 1)
        realm_level_map = {1: '初期', 2: '中期', 3: '后期', 4: '大圆满'}
        realm_level_name = realm_level_map.get(realm_level, f'{realm_level}级')

        draw.text(
            (text_start_x, y),
            f"{realm} · {realm_level_name}",
            font=self.get_font(40),  # 32 -> 40
            fill=self.colors['text_primary']
        )
        y += 60

        # 绘制灵根信息 - 大幅增大字体
        spirit_root = player_data.get('spirit_root', '无')
        spirit_root_quality = player_data.get('spirit_root_quality', '凡品')
        quality_color = self.get_quality_color(spirit_root_quality)

        draw.text(
            (content_padding, y),
            f"{spirit_root}灵根 · {spirit_root_quality}",
            font=self.get_font(36),  # 28 -> 36
            fill=quality_color
        )
        y += 70

        # 绘制分隔线
        draw.line(
            [(content_padding, y), (width - content_padding, y)],
            fill=self.colors['border_default'],
            width=2
        )
        y += 30

        # 绘制修为进度条 - 增大字体
        cultivation = player_data.get('cultivation', 0)
        max_cultivation = player_data.get('max_cultivation', 1000)
        progress = cultivation / max_cultivation if max_cultivation > 0 else 0
        progress_percent = progress * 100

        draw.text(
            (content_padding, y),
            "修为进度",
            font=self.get_font(32),  # 24 -> 32
            fill=self.colors['text_secondary']
        )
        y += 45

        # 进度条 - 增大高度
        bar_width = width - content_padding * 2
        bar_height = 40  # 30 -> 40
        self.draw_progress_bar(
            draw,
            (content_padding, y),
            width=bar_width,
            height=bar_height,
            progress=progress,
            fill_color=self.colors['exp_color'],
            radius=10
        )

        # 在进度条上显示文字 - 增大字体
        progress_text = f"{format_number(cultivation)} / {format_number(max_cultivation)}  ({progress_percent:.1f}%)"
        draw.text(
            (width // 2, y + bar_height // 2),
            progress_text,
            font=self.get_font(28),  # 20 -> 28
            fill=(255, 255, 255),
            anchor='mm'
        )
        y += bar_height + 50

        # 属性信息（两列布局）- 大幅增大字体
        hp = player_data.get('hp', 100)
        max_hp = player_data.get('max_hp', 100)
        mp = player_data.get('mp', 100)
        max_mp = player_data.get('max_mp', 100)
        attack = player_data.get('attack', 0)
        defense = player_data.get('defense', 0)
        spirit_stone = player_data.get('spirit_stone', 0)

        left_x = content_padding
        right_x = width // 2 + 30
        line_height = 50  # 调整行高

        # 第一行：生命值和法力值
        draw.text(
            (left_x, y),
            f"生命  {format_number(hp)} / {format_number(max_hp)}",
            font=self.get_font(28),  # 调整字体大小
            fill=self.colors['hp_color']
        )
        draw.text(
            (right_x, y),
            f"法力  {format_number(mp)} / {format_number(max_mp)}",
            font=self.get_font(28),
            fill=self.colors['mp_color']
        )
        y += line_height

        # 第二行：攻击力和防御力
        draw.text(
            (left_x, y),
            f"攻击力  {format_number(attack)}",
            font=self.get_font(28),
            fill=self.colors['text_primary']
        )
        draw.text(
            (right_x, y),
            f"防御力  {format_number(defense)}",
            font=self.get_font(28),
            fill=self.colors['text_primary']
        )
        y += line_height

        # 第三行：灵石数量（居中显示）
        draw.text(
            (width // 2, y),
            f"💎 灵石  {format_number(spirit_stone)}",
            font=self.get_font(28),
            fill=(255, 215, 0),  # 金色
            anchor='mt'
        )

        return image

    def generate_cultivation_card(self, cultivation_data: Dict[str, Any]) -> Image.Image:
        """
        生成修炼结果卡片

        Args:
            cultivation_data: 修炼数据
                {
                    'player_name': str,
                    'cultivation_gained': int,
                    'total_cultivation': int,
                    'can_breakthrough': bool,
                    'next_realm': str,
                    'required_cultivation': int,
                    'sect_bonus_rate': float,
                }

        Returns:
            PIL Image对象
        """
        # 卡片尺寸
        width, height = 500, 300
        padding = 30

        # 生成背景
        if self.config.get('enable_background', True):
            theme = self.config.get_theme_for_card('cultivation')
            direction = self.config.get('gradient_direction', 'radial')
            add_effects = self.config.get('enable_effects', True)

            image = self.bg_generator.generate_themed_background(
                width, height, theme, direction, add_effects
            )
            if image.mode != 'RGBA':
                image = image.convert('RGBA')
        else:
            image = Image.new('RGBA', (width, height), self.colors['bg_main'])

        draw = ImageDraw.Draw(image)

        # 绘制卡片背景
        self.draw_rounded_rectangle(
            draw,
            (padding, padding, width - padding, height - padding),
            radius=15,
            fill=self.colors['bg_card'],
            outline=self.colors['border_default'],
            width=2
        )

        y = padding + 20

        # 标题
        draw.text(
            (width // 2, y),
            "✨ 修炼完成",
            font=self.get_font(28),
            fill=self.colors['text_accent'],
            anchor='mt'
        )
        y += 50

        # 修为增加
        cultivation_gained = cultivation_data.get('cultivation_gained', 0)
        draw.text(
            (width // 2, y),
            f"+{cultivation_gained} 修为",
            font=self.get_font(32),
            fill=self.colors['exp_color'],
            anchor='mt'
        )
        y += 50

        # 当前修为
        total_cultivation = cultivation_data.get('total_cultivation', 0)
        draw.text(
            (width // 2, y),
            f"当前修为：{total_cultivation}",
            font=self.get_font(18),
            fill=self.colors['text_secondary'],
            anchor='mt'
        )
        y += 40

        # 宗门加成
        sect_bonus_rate = cultivation_data.get('sect_bonus_rate', 0)
        if sect_bonus_rate > 0:
            draw.text(
                (width // 2, y),
                f"🏛️ 宗门加成：+{sect_bonus_rate * 100:.0f}%",
                font=self.get_font(16),
                fill=self.colors['text_primary'],
                anchor='mt'
            )
            y += 35

        # 突破提示
        can_breakthrough = cultivation_data.get('can_breakthrough', False)
        if can_breakthrough:
            next_realm = cultivation_data.get('next_realm', '未知境界')
            required = cultivation_data.get('required_cultivation', 0)

            draw.text(
                (width // 2, y),
                f"⚡ 可突破至 {next_realm}",
                font=self.get_font(20),
                fill=self.colors['quality_epic'],
                anchor='mt'
            )
            y += 30

            draw.text(
                (width // 2, y),
                f"需要修为：{required}",
                font=self.get_font(16),
                fill=self.colors['text_secondary'],
                anchor='mt'
            )

        return image

    def generate_equipment_card(self, equipment_data: Dict[str, Any]) -> Image.Image:
        """
        生成装备展示卡片

        Args:
            equipment_data: 装备数据
                {
                    'name': str,
                    'type': str,
                    'quality': str,
                    'level': int,
                    'enhance_level': int,
                    'attributes': Dict[str, int],
                }

        Returns:
            PIL Image对象
        """
        # 卡片尺寸
        width, height = 450, 350
        padding = 30

        # 生成背景
        if self.config.get('enable_background', True):
            theme = self.config.get_theme_for_card('equipment')
            direction = self.config.get('gradient_direction', 'radial')
            add_effects = self.config.get('enable_effects', True)

            image = self.bg_generator.generate_themed_background(
                width, height, theme, direction, add_effects
            )
            if image.mode != 'RGBA':
                image = image.convert('RGBA')
        else:
            image = Image.new('RGBA', (width, height), self.colors['bg_main'])

        draw = ImageDraw.Draw(image)

        # 获取品质颜色
        quality = equipment_data.get('quality', '凡品')
        quality_color = self.get_quality_color(quality)

        # 绘制卡片背景
        self.draw_rounded_rectangle(
            draw,
            (padding, padding, width - padding, height - padding),
            radius=15,
            fill=self.colors['bg_card'],
            outline=quality_color,
            width=3
        )

        y = padding + 20

        # 装备名称
        name = equipment_data.get('name', '未知装备')
        enhance_level = equipment_data.get('enhance_level', 0)
        display_name = f"{name} +{enhance_level}" if enhance_level > 0 else name

        draw.text(
            (width // 2, y),
            display_name,
            font=self.get_font(24),
            fill=quality_color,
            anchor='mt'
        )
        y += 40

        # 装备类型和品质
        equip_type = equipment_data.get('type', '未知')
        type_map = {'weapon': '⚔️ 武器', 'armor': '🛡️ 护甲', 'accessory': '💎 饰品'}
        type_display = type_map.get(equip_type, equip_type)

        draw.text(
            (width // 2, y),
            f"{type_display} · {quality}",
            font=self.get_font(18),
            fill=self.colors['text_secondary'],
            anchor='mt'
        )
        y += 40

        # 装备等级
        level = equipment_data.get('level', 1)
        draw.text(
            (width // 2, y),
            f"等级：{level}",
            font=self.get_font(16),
            fill=self.colors['text_secondary'],
            anchor='mt'
        )
        y += 35

        # 属性列表
        attributes = equipment_data.get('attributes', {})
        if attributes:
            draw.text(
                (padding + 20, y),
                "属性：",
                font=self.get_font(18),
                fill=self.colors['text_primary']
            )
            y += 30

            attr_map = {
                'attack': '⚔️ 攻击力',
                'defense': '🛡️ 防御力',
                'hp_bonus': '❤️ 生命值',
                'mp_bonus': '💙 法力值',
                'crit_rate': '🎯 暴击率',
                'dodge': '💨 闪避',
            }

            for attr_key, attr_value in attributes.items():
                attr_name = attr_map.get(attr_key, attr_key)
                draw.text(
                    (padding + 40, y),
                    f"{attr_name}：+{attr_value}",
                    font=self.get_font(16),
                    fill=self.colors['text_primary']
                )
                y += 28

        return image

    def generate_combat_result_card(self, combat_data: Dict[str, Any]) -> Image.Image:
        """
        生成战斗结果卡片

        Args:
            combat_data: 战斗数据
                {
                    'winner_name': str,
                    'loser_name': str,
                    'winner_hp': int,
                    'winner_max_hp': int,
                    'rounds': int,
                    'rewards': Dict[str, int],
                }

        Returns:
            PIL Image对象
        """
        # 卡片尺寸
        width, height = 550, 400
        padding = 30

        # 生成背景
        if self.config.get('enable_background', True):
            theme = self.config.get_theme_for_card('combat')
            direction = self.config.get('gradient_direction', 'radial')
            add_effects = self.config.get('enable_effects', True)

            image = self.bg_generator.generate_themed_background(
                width, height, theme, direction, add_effects
            )
            if image.mode != 'RGBA':
                image = image.convert('RGBA')
        else:
            image = Image.new('RGBA', (width, height), self.colors['bg_main'])

        draw = ImageDraw.Draw(image)

        # 绘制卡片背景
        self.draw_rounded_rectangle(
            draw,
            (padding, padding, width - padding, height - padding),
            radius=15,
            fill=self.colors['bg_card'],
            outline=self.colors['quality_epic'],
            width=2
        )

        y = padding + 20

        # 标题
        draw.text(
            (width // 2, y),
            "⚔️ 战斗结果",
            font=self.get_font(32),
            fill=self.colors['text_accent'],
            anchor='mt'
        )
        y += 60

        # 胜利者
        winner_name = combat_data.get('winner_name', '未知')
        draw.text(
            (width // 2, y),
            f"🎉 {winner_name} 获胜！",
            font=self.get_font(28),
            fill=self.colors['quality_epic'],
            anchor='mt'
        )
        y += 50

        # 对战信息
        loser_name = combat_data.get('loser_name', '未知')
        draw.text(
            (width // 2, y),
            f"VS {loser_name}",
            font=self.get_font(20),
            fill=self.colors['text_secondary'],
            anchor='mt'
        )
        y += 40

        # 回合数
        rounds = combat_data.get('rounds', 0)
        draw.text(
            (width // 2, y),
            f"战斗回合：{rounds}",
            font=self.get_font(16),
            fill=self.colors['text_secondary'],
            anchor='mt'
        )
        y += 35

        # 剩余生命值
        winner_hp = combat_data.get('winner_hp', 100)
        winner_max_hp = combat_data.get('winner_max_hp', 100)
        hp_percent = (winner_hp / winner_max_hp) * 100 if winner_max_hp > 0 else 0

        draw.text(
            (width // 2, y),
            f"剩余生命：{winner_hp}/{winner_max_hp} ({hp_percent:.1f}%)",
            font=self.get_font(16),
            fill=self.colors['hp_color'],
            anchor='mt'
        )
        y += 40

        # 奖励
        rewards = combat_data.get('rewards', {})
        if rewards:
            draw.text(
                (width // 2, y),
                "🎁 战斗奖励",
                font=self.get_font(20),
                fill=self.colors['text_primary'],
                anchor='mt'
            )
            y += 35

            if 'spirit_stone' in rewards:
                draw.text(
                    (width // 2, y),
                    f"💎 灵石 +{rewards['spirit_stone']}",
                    font=self.get_font(18),
                    fill=self.colors['text_primary'],
                    anchor='mt'
                )
                y += 30

            if 'exp' in rewards:
                draw.text(
                    (width // 2, y),
                    f"⭐ 经验 +{rewards['exp']}",
                    font=self.get_font(18),
                    fill=self.colors['text_primary'],
                    anchor='mt'
                )

        return image
