"""
卡片生成器模块
实现各类修仙游戏卡片的生成
"""

from PIL import Image, ImageDraw
from pathlib import Path
from typing import Optional, Dict, Any, List
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

    def generate_player_card(self, player_data: Dict[str, Any]) -> Image.Image:
        """
        生成角色属性卡片

        Args:
            player_data: 玩家数据字典
                {
                    'name': str,        # 角色名称
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
        # 卡片尺寸 - 增大以容纳更多信息
        width, height = 650, 480
        padding = 30

        # 生成背景
        if self.config.get('enable_background', True):
            theme = self.config.get_theme_for_card('player')
            direction = self.config.get('gradient_direction', 'radial')
            add_effects = self.config.get('enable_effects', True)

            image = self.bg_generator.generate_themed_background(
                width, height, theme, direction, add_effects
            )
            # 转换为RGBA以便后续处理
            if image.mode != 'RGBA':
                image = image.convert('RGBA')
        else:
            # 使用纯色背景
            image = Image.new('RGBA', (width, height), self.colors['bg_main'])

        draw = ImageDraw.Draw(image)

        # 绘制卡片背景
        self.draw_rounded_rectangle(
            draw,
            (padding, padding, width - padding, height - padding),
            radius=15,
            fill=self.colors['bg_card'],
            outline=self.colors['border_highlight'],
            width=2
        )

        # 当前Y坐标
        y = padding + 15

        # 绘制标题：角色名称
        name = player_data.get('name', '未知')
        draw.text(
            (width // 2, y),
            f"【 {name} 】",
            font=self.get_font(32),
            fill=self.colors['text_accent'],
            anchor='mt'
        )
        y += 48

        # 绘制境界信息
        realm = player_data.get('realm', '凡人')
        realm_level = player_data.get('realm_level', 1)
        realm_level_map = {1: '初期', 2: '中期', 3: '后期', 4: '大圆满'}
        realm_level_name = realm_level_map.get(realm_level, f'{realm_level}级')

        draw.text(
            (width // 2, y),
            f"⚡ {realm} · {realm_level_name}",
            font=self.get_font(24),
            fill=self.colors['text_primary'],
            anchor='mt'
        )
        y += 45

        # 绘制灵根信息（提前显示，因为很重要）
        spirit_root = player_data.get('spirit_root', '无')
        spirit_root_quality = player_data.get('spirit_root_quality', '凡品')
        quality_color = self.get_quality_color(spirit_root_quality)

        spirit_root_text = f"🌟 {spirit_root}灵根 · {spirit_root_quality}"
        draw.text(
            (width // 2, y),
            spirit_root_text,
            font=self.get_font(18),
            fill=quality_color,
            anchor='mt'
        )
        y += 40

        # 绘制修为进度条
        cultivation = player_data.get('cultivation', 0)
        max_cultivation = player_data.get('max_cultivation', 1000)
        progress = cultivation / max_cultivation if max_cultivation > 0 else 0
        progress_percent = progress * 100

        # 格式化数字（如果很大就用K/M/B）
        def format_number(n):
            if n >= 1_000_000_000:
                return f"{n/1_000_000_000:.1f}B"
            elif n >= 1_000_000:
                return f"{n/1_000_000:.1f}M"
            elif n >= 1_000:
                return f"{n/1_000:.1f}K"
            else:
                return str(n)

        cultivation_text = f"修为: {format_number(cultivation)} / {format_number(max_cultivation)} ({progress_percent:.1f}%)"
        draw.text(
            (padding + 20, y),
            cultivation_text,
            font=self.get_font(16),
            fill=self.colors['text_secondary']
        )
        y += 25

        self.draw_progress_bar(
            draw,
            (padding + 20, y),
            width=width - padding * 2 - 40,
            height=22,
            progress=progress,
            fill_color=self.colors['exp_color']
        )
        y += 35

        # 绘制生命值和法力值（两列显示）
        hp = player_data.get('hp', 100)
        max_hp = player_data.get('max_hp', 100)
        mp = player_data.get('mp', 100)
        max_mp = player_data.get('max_mp', 100)

        left_x = padding + 20
        right_x = width // 2 + 20

        # 生命值（左列）
        hp_text = f"❤️  生命: {format_number(hp)} / {format_number(max_hp)}"
        draw.text(
            (left_x, y),
            hp_text,
            font=self.get_font(17),
            fill=self.colors['hp_color']
        )

        # 法力值（右列）
        mp_text = f"💙  法力: {format_number(mp)} / {format_number(max_mp)}"
        draw.text(
            (right_x, y),
            mp_text,
            font=self.get_font(17),
            fill=self.colors['mp_color']
        )
        y += 35

        # 绘制攻击和防御（两列显示）
        attack = player_data.get('attack', 0)
        defense = player_data.get('defense', 0)

        # 攻击力（左列）
        attack_text = f"⚔️  攻击力: {format_number(attack)}"
        draw.text(
            (left_x, y),
            attack_text,
            font=self.get_font(17),
            fill=self.colors['text_primary']
        )

        # 防御力（右列）
        defense_text = f"🛡️  防御力: {format_number(defense)}"
        draw.text(
            (right_x, y),
            defense_text,
            font=self.get_font(17),
            fill=self.colors['text_primary']
        )
        y += 40

        # 绘制装饰性分隔线
        line_y = height - padding - 25
        draw.line(
            [(padding + 20, line_y), (width - padding - 20, line_y)],
            fill=self.colors['border_default'],
            width=1
        )

        # 底部提示文字
        footer_text = "✨ 修仙之路，道阻且长 ✨"
        draw.text(
            (width // 2, height - padding - 10),
            footer_text,
            font=self.get_font(14),
            fill=self.colors['text_secondary'],
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
