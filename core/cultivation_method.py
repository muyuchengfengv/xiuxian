"""
功法系统
负责功法的获取、装备、升级、熟练度管理等功能
"""

import uuid
import random
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from astrbot.api import logger

from .database import DatabaseManager
from .player import PlayerManager
from ..models.cultivation_method_model import CultivationMethod
from ..utils.cultivation_constants import (
    METHOD_TYPES, ELEMENT_TYPES, METHOD_SOURCES, EQUIPMENT_SLOTS,
    METHOD_TEMPLATES, PROFICIENCY_GAIN, METHOD_LIMITS, MASTERY_LEVELS
)
from ..utils import XiuxianException


class CultivationMethodError(XiuxianException):
    """功法相关异常"""
    pass


class MethodNotFoundError(CultivationMethodError):
    """功法不存在异常"""
    pass


class MethodNotOwnError(CultivationMethodError):
    """功法未拥有异常"""
    pass


class MethodAlreadyEquippedError(CultivationMethodError):
    """功法已装备异常"""
    pass


class SlotOccupiedError(CultivationMethodError):
    """槽位已被占用异常"""
    pass


class InsufficientLevelError(CultivationMethodError):
    """等级不足异常"""
    pass


class CultivationMethodSystem:
    """功法系统类"""

    def __init__(self, db: DatabaseManager, player_mgr: PlayerManager):
        """
        初始化功法系统

        Args:
            db: 数据库管理器
            player_mgr: 玩家管理器
        """
        self.db = db
        self.player_mgr = player_mgr

    async def generate_method(self, user_id: str, method_type: Optional[str] = None,
                             quality: Optional[str] = None) -> CultivationMethod:
        """
        为玩家生成随��功法

        Args:
            user_id: 用户ID
            method_type: 指定功法类型(可选)
            quality: 指定品质(可选)

        Returns:
            生成的功法对象

        Raises:
            ValueError: 参数错误
        """
        # 获取玩家信息
        player = await self.player_mgr.get_player_or_error(user_id)
        player_level = self._calculate_player_level(player)

        # 确定功法类型
        if method_type is None:
            method_type = random.choice(list(METHOD_TYPES.keys()))

        if method_type not in METHOD_TYPES:
            raise ValueError(f"不支持的功法类型: {method_type}")

        # 获取适合的模板
        available_templates = self._get_available_templates(method_type, player)

        if not available_templates:
            # 如果没有合适模板，使用最低级的
            templates = METHOD_TEMPLATES.get(method_type, [])
            if not templates:
                raise ValueError(f"没有找到{method_type}类型的功法模板")
            template = templates[0]
        else:
            # 根据玩家等级权重选择
            weights = []
            for template in available_templates:
                level_diff = abs(template.get("min_level", 1) - player_level)
                weight = max(1, 10 - level_diff)
                weights.append(weight)

            template = random.choices(available_templates, weights=weights)[0]

        # 创建功法
        method = self._create_method_from_template(template, user_id, quality)

        # 保存到数据库
        await self._save_method(method)

        logger.info(f"为玩家 {player.name} 生成功法: {method.get_display_name()}")

        return method

    def _get_available_templates(self, method_type: str, player) -> List[Dict]:
        """获取适合玩家等级的模板"""
        player_level = self._calculate_player_level(player)
        templates = METHOD_TEMPLATES.get(method_type, [])

        # 根据境界筛选
        realm_order = ["炼气期", "筑基期", "金丹期", "元婴期", "化神期",
                      "炼虚期", "合体期", "大乘期", "渡劫期", "真仙期",
                      "金仙期", "太乙金仙期", "大罗金仙期", "混元大罗金仙期", "圣人期"]

        player_realm_index = realm_order.index(player.realm) if player.realm in realm_order else 0

        available = []
        for template in templates:
            template_realm = template.get("min_realm", "炼气期")
            template_realm_index = realm_order.index(template_realm) if template_realm in realm_order else 0

            if template_realm_index <= player_realm_index:
                available.append(template)

        return available

    def _create_method_from_template(self, template: Dict, user_id: str,
                                   quality_override: Optional[str] = None) -> CultivationMethod:
        """从模板创建功法"""
        method = CultivationMethod(
            id=str(uuid.uuid4()),
            owner_id=user_id,
            name=template["name"],
            description=template["description"],
            method_type=template.get("method_type", "attack"),
            element_type=template.get("element_type", "none"),
            cultivation_type=template.get("cultivation_type", "qi_refining"),
            quality=quality_override or template.get("quality", "凡品"),
            grade=self._get_grade_by_quality(quality_override or template.get("quality", "凡品")),
            min_realm=template.get("min_realm", "炼气期"),
            min_realm_level=template.get("min_realm_level", 1),
            min_level=template.get("min_level", 1),
            attack_bonus=template.get("attack_bonus", 0),
            defense_bonus=template.get("defense_bonus", 0),
            speed_bonus=template.get("speed_bonus", 0),
            hp_bonus=template.get("hp_bonus", 0),
            mp_bonus=template.get("mp_bonus", 0),
            cultivation_speed_bonus=template.get("cultivation_speed_bonus", 0.0),
            breakthrough_rate_bonus=template.get("breakthrough_rate_bonus", 0.0),
            special_effects=template.get("special_effects", []),
            skill_damage=template.get("skill_damage", 0),
            cooldown_reduction=template.get("cooldown_reduction", 0.0),
            source_type=random.choice(list(METHOD_SOURCES.keys())),
            source_detail=random.choice(list(METHOD_SOURCES.values()))["name"]
        )

        return method

    def _get_grade_by_quality(self, quality: str) -> int:
        """根据品质获取等级"""
        grade_map = {
            "凡品": 1, "灵品": 2, "宝品": 3, "仙品": 4,
            "神品": 5, "道品": 6, "天地品": 7
        }
        return grade_map.get(quality, 1)

    def _calculate_player_level(self, player) -> int:
        """计算玩家综合等级"""
        realm_levels = {
            '炼气期': 1, '筑基期': 10, '金丹期': 20, '元婴期': 30,
            '化神期': 40, '炼虚期': 50, '合体期': 60, '大乘期': 70,
            '渡劫期': 80, '真仙期': 90, '金仙期': 100, '太乙金仙期': 110,
            '大罗金仙期': 120, '混元大罗金仙期': 130, '圣人期': 140
        }
        base_level = realm_levels.get(player.realm, 1)
        return base_level + player.realm_level - 1

    async def _save_method(self, method: CultivationMethod):
        """保存功法到数据库"""
        await self._ensure_methods_table()

        method_data = method.to_dict()
        columns = list(method_data.keys())
        placeholders = ', '.join(['?' for _ in columns])
        values = list(method_data.values())

        sql = f"INSERT INTO cultivation_methods ({', '.join(columns)}) VALUES ({placeholders})"
        await self.db.execute(sql, values)

    async def _ensure_methods_table(self):
        """确保功法表存在"""
        sql = """
        CREATE TABLE IF NOT EXISTS cultivation_methods (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            method_type TEXT NOT NULL,
            element_type TEXT NOT NULL,
            cultivation_type TEXT NOT NULL,
            quality TEXT NOT NULL,
            grade INTEGER NOT NULL,
            min_realm TEXT NOT NULL,
            min_realm_level INTEGER NOT NULL,
            min_level INTEGER NOT NULL,
            attack_bonus INTEGER DEFAULT 0,
            defense_bonus INTEGER DEFAULT 0,
            speed_bonus INTEGER DEFAULT 0,
            hp_bonus INTEGER DEFAULT 0,
            mp_bonus INTEGER DEFAULT 0,
            cultivation_speed_bonus REAL DEFAULT 0.0,
            breakthrough_rate_bonus REAL DEFAULT 0.0,
            special_effects TEXT,
            skill_damage INTEGER DEFAULT 0,
            cooldown_reduction REAL DEFAULT 0.0,
            owner_id TEXT,
            is_equipped INTEGER DEFAULT 0,
            equip_slot TEXT,
            proficiency INTEGER DEFAULT 0,
            max_proficiency INTEGER DEFAULT 1000,
            mastery_level INTEGER DEFAULT 0,
            source_type TEXT,
            source_detail TEXT,
            created_at TEXT NOT NULL,
            equipped_at TEXT,
            last_practiced_at TEXT
        )
        """
        await self.db.execute(sql)

    async def get_player_methods(self, user_id: str) -> List[CultivationMethod]:
        """获取玩家的所有功法"""
        await self._ensure_methods_table()

        results = await self.db.fetchall(
            "SELECT * FROM cultivation_methods WHERE owner_id = ? ORDER BY created_at DESC",
            (user_id,)
        )

        methods = []
        for result in results:
            method_data = dict(result)
            method = CultivationMethod.from_dict(method_data)
            methods.append(method)

        return methods

    async def get_method_by_id(self, method_id: str, user_id: str) -> CultivationMethod:
        """根据ID获取功法"""
        await self._ensure_methods_table()

        result = await self.db.fetchone(
            "SELECT * FROM cultivation_methods WHERE id = ? AND owner_id = ?",
            (method_id, user_id)
        )

        if result is None:
            raise MethodNotFoundError(method_id)

        method_data = dict(result)
        return CultivationMethod.from_dict(method_data)

    async def equip_method(self, user_id: str, method_id: str, slot: str) -> CultivationMethod:
        """
        装备功法

        Args:
            user_id: 用户ID
            method_id: 功法ID
            slot: 装备槽位

        Returns:
            装备的功法对象

        Raises:
            MethodNotFoundError: 功法不存在
            InsufficientLevelError: 等级不足
            SlotOccupiedError: 槽位被占用
        """
        # 获取功法
        method = await self.get_method_by_id(method_id, user_id)
        player = await self.player_mgr.get_player_or_error(user_id)

        # 检查等级要求
        if not method.can_equip(player.realm, player.realm_level, self._calculate_player_level(player)):
            raise InsufficientLevelError(f"需要{method.min_realm} {method.min_realm_level}级才能装备此功法")

        # 检查槽位是否合法
        if slot not in EQUIPMENT_SLOTS:
            raise ValueError(f"无效的装备槽位: {slot}")

        # 检查功法类型是否匹配槽位
        slot_type = EQUIPMENT_SLOTS[slot]["type"]
        method_type = method.method_type

        # 主动功法只能装备在主动槽位，被动功法只能装备在被动槽位
        if slot_type == "active" and method_type not in ["attack"]:
            raise ValueError(f"只有攻击功法可以装备在主动槽位")
        if slot_type == "passive" and method_type in ["attack"]:
            raise ValueError(f"攻击功法不能装备在被动槽位")

        # 检查槽位是否已被占用
        equipped_methods = await self.get_equipped_methods(user_id)
        if slot in equipped_methods:
            # 卸下当前槽位的功法
            current_method = equipped_methods[slot]
            current_method.is_equipped = False
            current_method.equip_slot = None
            await self._update_method(current_method)

        # 装备新功法
        method.is_equipped = True
        method.equip_slot = slot
        method.equipped_at = datetime.now()
        await self._update_method(method)

        logger.info(f"玩家 {player.name} 装备了功法: {method.get_display_name()} 到槽位 {slot}")

        return method

    async def unequip_method(self, user_id: str, slot: str) -> CultivationMethod:
        """
        卸下功法

        Args:
            user_id: 用户ID
            slot: 装备槽位

        Returns:
            卸下的功法对象

        Raises:
            MethodNotFoundError: 槽位没有功法
        """
        equipped_methods = await self.get_equipped_methods(user_id)

        if slot not in equipped_methods:
            raise MethodNotFoundError(f"槽位 {slot} 没有装备功法")

        method = equipped_methods[slot]
        method.is_equipped = False
        method.equip_slot = None
        await self._update_method(method)

        player = await self.player_mgr.get_player_or_error(user_id)
        logger.info(f"玩家 {player.name} 卸下了功法: {method.get_display_name()}")

        return method

    async def get_equipped_methods(self, user_id: str) -> Dict[str, CultivationMethod]:
        """获取玩家已装备的功法"""
        all_methods = await self.get_player_methods(user_id)
        equipped = {}

        for method in all_methods:
            if method.is_equipped and method.equip_slot:
                equipped[method.equip_slot] = method

        return equipped

    async def _update_method(self, method: CultivationMethod):
        """更新功法信息"""
        method_data = method.to_dict()

        set_clause = ', '.join([f"{key} = ?" for key in method_data.keys() if key != 'id'])
        values = [value for key, value in method_data.items() if key != 'id']
        values.append(method.id)

        sql = f"UPDATE cultivation_methods SET {set_clause} WHERE id = ?"
        await self.db.execute(sql, tuple(values))

    async def add_method_proficiency(self, user_id: str, method_id: str,
                                   amount: int, reason: str = "修炼") -> Tuple[bool, int]:
        """
        增加功法熟练度

        Args:
            user_id: 用户ID
            method_id: 功法ID
            amount: 增加数量
            reason: 增加原因

        Returns:
            (是否升级, 新掌握等级)
        """
        method = await self.get_method_by_id(method_id, user_id)

        # 增加熟练度
        leveled_up, new_level = method.add_proficiency(amount)
        method.last_practiced_at = datetime.now()

        await self._update_method(method)

        if leveled_up:
            player = await self.player_mgr.get_player_or_error(user_id)
            logger.info(f"玩家 {player.name} 的功法 {method.name} 熟练度提升至 {method.get_mastery_display()}")

        return leveled_up, new_level

    async def get_method_stats(self, user_id: str) -> Dict:
        """获取玩家功法统计信息"""
        all_methods = await self.get_player_methods(user_id)
        equipped_methods = await self.get_equipped_methods(user_id)

        total_attack = sum(method.attack_bonus for method in equipped_methods.values())
        total_defense = sum(method.defense_bonus for method in equipped_methods.values())
        total_speed = sum(method.speed_bonus for method in equipped_methods.values())
        total_hp = sum(method.hp_bonus for method in equipped_methods.values())
        total_mp = sum(method.mp_bonus for method in equipped_methods.values())

        cultivation_speed_bonus = sum(method.cultivation_speed_bonus for method in equipped_methods.values())
        breakthrough_rate_bonus = sum(method.breakthrough_rate_bonus for method in equipped_methods.values())

        # 按类型统计
        type_stats = {}
        for method in all_methods:
            if method.method_type not in type_stats:
                type_stats[method.method_type] = {"count": 0, "equipped": 0}
            type_stats[method.method_type]["count"] += 1
            if method.is_equipped:
                type_stats[method.method_type]["equipped"] += 1

        # 按品质统计
        quality_stats = {}
        for method in all_methods:
            if method.quality not in quality_stats:
                quality_stats[method.quality] = 0
            quality_stats[method.quality] += 1

        return {
            "total_methods": len(all_methods),
            "equipped_methods": len(equipped_methods),
            "total_attack": total_attack,
            "total_defense": total_defense,
            "total_speed": total_speed,
            "total_hp_bonus": total_hp,
            "total_mp_bonus": total_mp,
            "cultivation_speed_bonus": cultivation_speed_bonus,
            "breakthrough_rate_bonus": breakthrough_rate_bonus,
            "type_stats": type_stats,
            "quality_stats": quality_stats,
            "equipped_methods": equipped_methods
        }

    async def format_method_list(self, user_id: str) -> str:
        """格式化功法列表"""
        methods = await self.get_player_methods(user_id)
        equipped_methods = await self.get_equipped_methods(user_id)

        if not methods:
            return "📜 功法簿空空如也，还没有任何功法"

        lines = ["📜 功法簿", "─" * 40]

        # 按类型分组显示
        by_type = {}
        for method in methods:
            if method.method_type not in by_type:
                by_type[method.method_type] = []
            by_type[method.method_type].append(method)

        type_names = {
            'attack': '⚔️ 攻击功法',
            'defense': '🛡️ 防御功法',
            'speed': '💨 速度功法',
            'auxiliary': '�� 辅助功法'
        }

        for method_type, method_list in by_type.items():
            type_name = type_names.get(method_type, f"📜 {method_type}")
            lines.append(f"\n{type_name}:")

            for i, method in enumerate(method_list, 1):
                status = "✅" if method.is_equipped else "⭕"
                slot_info = f"[{method.get_equip_slot_display()}]" if method.is_equipped else ""
                lines.append(f"  {status} {i}. {method.get_display_name()} {slot_info}")
                lines.append(f"     熟练度: {method.get_mastery_display()}")

        lines.append("\n💡 使用 /功法装备 [编号] [槽位] 装备功法")
        lines.append("💡 使用 /功法卸下 [槽位] 卸下功法")
        lines.append("💡 使用 /功法详情 [编号] 查看详细信息")

        return "\n".join(lines)

    async def format_equipped_methods(self, user_id: str) -> str:
        """格式化已装备功法信息"""
        equipped_methods = await self.get_equipped_methods(user_id)

        if not equipped_methods:
            return "⚠️ 还没有装备任何功法"

        lines = ["⚔️ 已装备功法", "─" * 40]

        for slot, method in equipped_methods.items():
            slot_name = EQUIPMENT_SLOTS[slot]["name"]
            lines.append(f"\n{slot_name}:")
            lines.append(f"  {method.get_display_name()}")
            lines.append(f"  熟练度: {method.get_mastery_display()}")
            lines.append(f"  {method.get_detailed_info()}")

        lines.append("\n💡 使用 /功法卸下 [槽位] 卸下功法")

        return "\n".join(lines)