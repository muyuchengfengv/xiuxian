"""
消息格式化工具
提供美观的信息展示功能
"""

from typing import List, Dict, Any
from ..models.player_model import Player
from ..models.equipment_model import Equipment
from .constants import REALM_LEVEL_NAMES, SPIRIT_ROOTS


class MessageFormatter:
    """消息格式化类"""

    @staticmethod
    def format_player_info(player: Player) -> str:
        """
        格式化玩家信息显示

        Args:
            player: 玩家对象

        Returns:
            格式化后的玩家信息字符串
        """
        from .constants import get_realm_level_name
        realm_level_name = get_realm_level_name(player.realm, player.realm_level)
        full_realm = f"{player.realm}{realm_level_name}"

        # 计算属性总和
        total_attributes = (
            player.constitution +
            player.spiritual_power +
            player.comprehension +
            player.luck +
            player.root_bone
        )

        lines = [
            "╔" + "═" * 38 + "╗",
            f"║ 【修仙信息】{player.name}".ljust(40 - len(player.name.encode('gbk')) + len(player.name)) + "║",
            "╠" + "═" * 38 + "╣",
            f"║ 境界：{full_realm}".ljust(40 - len(full_realm.encode('gbk')) + len(full_realm)) + "║",
            f"║ 修为：{player.cultivation}".ljust(40 - len(str(player.cultivation))) + "║",
            "╠" + "─" * 38 + "╣",
            f"║ 生命值：{player.hp}/{player.max_hp}".ljust(40 - len(str(player.hp)) - len(str(player.max_hp))) + "║",
            f"║ 法力值：{player.mp}/{player.max_mp}".ljust(40 - len(str(player.mp)) - len(str(player.max_mp))) + "║",
            f"║ 攻击力：{player.attack}".ljust(40 - len(str(player.attack))) + "║",
            f"║ 防御力：{player.defense}".ljust(40 - len(str(player.defense))) + "║",
            "╠" + "─" * 38 + "╣",
            f"║ 体质：{player.constitution}  灵力：{player.spiritual_power}  悟性：{player.comprehension}".ljust(
                40 - len(str(player.constitution)) - len(str(player.spiritual_power)) - len(str(player.comprehension))
            ) + "║",
            f"║ 幸运：{player.luck}  根骨：{player.root_bone}  总计：{total_attributes}".ljust(
                40 - len(str(player.luck)) - len(str(player.root_bone)) - len(str(total_attributes))
            ) + "║",
            "╠" + "─" * 38 + "╣",
            f"║ 灵石：{player.spirit_stone}".ljust(40 - len(str(player.spirit_stone))) + "║",
            f"║ 位置：{player.current_location}".ljust(40 - len(player.current_location.encode('gbk')) + len(player.current_location)) + "║",
            "╚" + "═" * 38 + "╝"
        ]

        return "\n".join(lines)

    @staticmethod
    def format_spirit_root_info(player: Player) -> str:
        """
        格式化灵根信息显示

        Args:
            player: 玩家对象

        Returns:
            格式化后的灵根信息字符串
        """
        if not player.spirit_root_type or not player.spirit_root_quality:
            return "尚未检测灵根，请使用 /修仙 开始修仙之路"

        spirit_type = player.spirit_root_type
        spirit_quality = player.spirit_root_quality
        spirit_value = player.spirit_root_value
        spirit_purity = player.spirit_root_purity

        # 获取灵根配置
        root_config = SPIRIT_ROOTS.get(spirit_type, {})

        lines = [
            "╔" + "═" * 38 + "╗",
            "║ 【灵根信息】".ljust(42) + "║",
            "╠" + "═" * 38 + "╣",
            f"║ 类型：{spirit_type}系灵根".ljust(40 - len(spirit_type.encode('gbk')) + len(spirit_type)) + "║",
            f"║ 品质：{spirit_quality}（{root_config.get('type', '未知')}）".ljust(
                40 - len(spirit_quality.encode('gbk')) + len(spirit_quality) - len(root_config.get('type', '未知').encode('gbk')) + len(root_config.get('type', '未知'))
            ) + "║",
            f"║ 纯度：{spirit_purity}%".ljust(40 - len(str(spirit_purity))) + "║",
            f"║ 灵根值：{spirit_value}/100".ljust(40 - len(str(spirit_value))) + "║",
            "╠" + "─" * 38 + "╣",
            "║ 【属性加成】".ljust(42) + "║",
        ]

        # 添加修为加成
        cult_bonus = root_config.get('cultivation_bonus', 0)
        lines.append(f"║ - 修为获取：+{int(cult_bonus * 100)}%".ljust(40 - len(str(int(cult_bonus * 100)))) + "║")

        # 添加技能加成
        skill_bonus = root_config.get('skill_bonus', 0)
        lines.append(f"║ - {spirit_type}系法术威力：+{int(skill_bonus * 100)}%".ljust(
            40 - len(spirit_type.encode('gbk')) + len(spirit_type) - len(str(int(skill_bonus * 100)))
        ) + "║")

        # 添加职业加成
        profession_bonus = root_config.get('profession_bonus', {})
        if profession_bonus:
            for profession, bonus in profession_bonus.items():
                lines.append(f"║ - {profession}成功率：+{int(bonus * 100)}%".ljust(
                    40 - len(profession.encode('gbk')) + len(profession) - len(str(int(bonus * 100)))
                ) + "║")

        # 添加特性描述
        description = root_config.get('description', '')
        if description:
            lines.append("╠" + "─" * 38 + "╣")
            lines.append(f"║ 【特性】{description}".ljust(40 - len(description.encode('gbk')) + len(description)) + "║")

        lines.append("╚" + "═" * 38 + "╝")

        return "\n".join(lines)

    @staticmethod
    def format_combat_log(log: List[Dict[str, Any]]) -> str:
        """
        格式化战斗日志

        Args:
            log: 战斗日志列表

        Returns:
            格式化后的战斗日志字符串
        """
        if not log:
            return "无战斗记录"

        lines = [
            "╔" + "═" * 48 + "╗",
            "║" + "【战斗记录】".center(50) + "║",
            "╠" + "═" * 48 + "╣",
        ]

        for round_num, round_log in enumerate(log, 1):
            lines.append(f"║ 第{round_num}回合：".ljust(52 - len(str(round_num))) + "║")

            # 显示行动者
            actor = round_log.get('actor', '未知')
            action = round_log.get('action', '行动')
            target = round_log.get('target', '目标')
            damage = round_log.get('damage', 0)

            action_line = f"  {actor} 对 {target} 使用 {action}"
            lines.append(f"║ {action_line}".ljust(52 - len(action_line.encode('gbk')) + len(action_line)) + "║")

            if damage > 0:
                damage_line = f"  造成 {damage} 点伤害"
                lines.append(f"║ {damage_line}".ljust(52 - len(str(damage))) + "║")

            # 显示剩余生命
            hp_remain = round_log.get('target_hp', 0)
            max_hp = round_log.get('target_max_hp', 1)
            hp_percent = int(hp_remain / max_hp * 100) if max_hp > 0 else 0

            hp_line = f"  {target} 剩余生命：{hp_remain}/{max_hp} ({hp_percent}%)"
            lines.append(f"║ {hp_line}".ljust(
                52 - len(target.encode('gbk')) + len(target) - len(str(hp_remain)) - len(str(max_hp)) - len(str(hp_percent))
            ) + "║")

            lines.append("║" + "─" * 48 + "║")

        # 移除最后一条分隔线
        lines.pop()
        lines.append("╚" + "═" * 48 + "╝")

        return "\n".join(lines)

    @staticmethod
    def format_equipment_list(equipments: List[Equipment]) -> str:
        """
        格式化装备列表

        Args:
            equipments: 装备列表

        Returns:
            格式化后的装备列表字符串
        """
        if not equipments:
            return "背包空空如也，快去获取装备吧！"

        lines = [
            "╔" + "═" * 48 + "╗",
            "║" + "【装备背包】".center(50) + "║",
            "╠" + "═" * 48 + "╣",
        ]

        for idx, equip in enumerate(equipments, 1):
            # 装备标记
            equipped_mark = "[已装备]" if equip.is_equipped else ""
            enhance_mark = f"+{equip.enhance_level}" if equip.enhance_level > 0 else ""

            # 装备名称行
            name_line = f"{idx}. {equipped_mark}{equip.quality} {equip.name}{enhance_mark}"
            lines.append(f"║ {name_line}".ljust(52 - len(name_line.encode('gbk')) + len(name_line)) + "║")

            # 属性行
            stats = []
            if equip.attack > 0:
                stats.append(f"攻击+{equip.get_total_attack()}")
            if equip.defense > 0:
                stats.append(f"防御+{equip.get_total_defense()}")
            if equip.hp_bonus > 0:
                stats.append(f"生命+{equip.hp_bonus}")
            if equip.mp_bonus > 0:
                stats.append(f"法力+{equip.mp_bonus}")

            stats_line = "  " + " ".join(stats) if stats else "  无属性加成"
            lines.append(f"║ {stats_line}".ljust(52 - len(stats_line.encode('gbk')) + len(stats_line)) + "║")

            # 特殊效果
            if equip.special_effect:
                effect_line = f"  效果：{equip.special_effect}"
                lines.append(f"║ {effect_line}".ljust(52 - len(effect_line.encode('gbk')) + len(effect_line)) + "║")

            lines.append("║" + "─" * 48 + "║")

        # 移除最后一条分隔线
        lines.pop()
        lines.append("╚" + "═" * 48 + "╝")

        return "\n".join(lines)

    @staticmethod
    def format_simple_message(title: str, content: str) -> str:
        """
        格式化简单消息框

        Args:
            title: 标题
            content: 内容

        Returns:
            格式化后的消息
        """
        lines = [
            "╔" + "═" * 38 + "╗",
            f"║ {title}".ljust(42 - len(title.encode('gbk')) + len(title)) + "║",
            "╠" + "═" * 38 + "╣",
            f"║ {content}".ljust(42 - len(content.encode('gbk')) + len(content)) + "║",
            "╚" + "═" * 38 + "╝"
        ]
        return "\n".join(lines)

    @staticmethod
    def format_error(error_msg: str) -> str:
        """
        格式化错误消息

        Args:
            error_msg: 错误消息

        Returns:
            格式化后的错误消息
        """
        return f"❌ {error_msg}"

    @staticmethod
    def format_success(success_msg: str) -> str:
        """
        格式化成功消息

        Args:
            success_msg: 成功消息

        Returns:
            格式化后的成功消息
        """
        return f"✅ {success_msg}"
