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

        lines = [
            f"👤{player.name} | {full_realm}",
            f"📊修为 {player.cultivation} | 💎{player.spirit_stone}灵石",
            f"❤️{player.hp}/{player.max_hp} | 💙{player.mp}/{player.max_mp}",
            f"⚔️攻{player.attack} | 🛡️防{player.defense}",
            f"体{player.constitution} 灵{player.spiritual_power} 悟{player.comprehension} 运{player.luck} 骨{player.root_bone}"
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
            return "尚未检测灵根"

        spirit_type = player.spirit_root_type
        spirit_quality = player.spirit_root_quality
        spirit_value = player.spirit_root_value
        spirit_purity = player.spirit_root_purity

        # 获取灵根配置
        root_config = SPIRIT_ROOTS.get(spirit_type, {})

        lines = [
            f"🌟{spirit_quality} {spirit_type}系灵根",
            f"纯度{spirit_purity}% | 灵根值{spirit_value}/100"
        ]

        # 添加修为加成
        cult_bonus = root_config.get('cultivation_bonus', 0)
        if cult_bonus > 0:
            lines.append(f"修为+{int(cult_bonus * 100)}%")

        # 添加技能加成
        skill_bonus = root_config.get('skill_bonus', 0)
        if skill_bonus > 0:
            lines.append(f"{spirit_type}系法术+{int(skill_bonus * 100)}%")

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
            return "⚔️无战斗记录"

        lines = ["⚔️战斗记录:"]

        for round_num, round_log in enumerate(log, 1):
            actor = round_log.get('actor', '未知')
            action = round_log.get('action', '行动')
            target = round_log.get('target', '目标')
            damage = round_log.get('damage', 0)
            hp_remain = round_log.get('target_hp', 0)
            max_hp = round_log.get('target_max_hp', 1)
            hp_percent = int(hp_remain / max_hp * 100) if max_hp > 0 else 0

            lines.append(f"R{round_num}.{actor}→{target} {action} -{damage} HP:{hp_remain}/{max_hp}({hp_percent}%)")

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
            return "🎒背包空空"

        lines = ["🎒装备背包:"]

        for idx, equip in enumerate(equipments, 1):
            # 装备标记
            equipped_mark = "✓" if equip.is_equipped else str(idx)
            enhance_mark = f"+{equip.enhance_level}" if equip.enhance_level > 0 else ""

            # 装备名称行
            name = f"{equipped_mark}.{equip.quality}{equip.name}{enhance_mark}"

            # 属性行
            stats = []
            if equip.attack > 0:
                stats.append(f"攻{equip.get_total_attack()}")
            if equip.defense > 0:
                stats.append(f"防{equip.get_total_defense()}")
            if equip.hp_bonus > 0:
                stats.append(f"HP+{equip.hp_bonus}")
            if equip.mp_bonus > 0:
                stats.append(f"MP+{equip.mp_bonus}")

            stats_str = " ".join(stats) if stats else "无加成"
            lines.append(f"{name} {stats_str}")

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
        return f"{title}\n{content}"

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
