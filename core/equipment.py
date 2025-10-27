"""
装备系统
负责装备的生成、管理、穿戴等功能
"""

import random
import uuid
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from astrbot.api import logger

from .database import DatabaseManager
from .player import PlayerManager
from ..models.equipment_model import Equipment
from ..utils import (
    XiuxianException,
    EquipmentNotFoundError,
    InsufficientLevelError,
    InvalidOperationError
)


class EquipmentSystem:
    """装备系统类"""

    def __init__(self, db: DatabaseManager, player_mgr: PlayerManager):
        """
        初始化装备系统

        Args:
            db: 数据库管理器
            player_mgr: 玩家管理器
        """
        self.db = db
        self.player_mgr = player_mgr

        # 装备槽位配置
        self.equipment_slots = {
            'weapon': '武器',
            'armor': '护甲',
            'accessory': '饰品'
        }

        # 装备模板库
        self.equipment_templates = self._init_equipment_templates()

    def _init_equipment_templates(self) -> Dict[str, List[Dict]]:
        """初始化装备模板"""
        templates = {
            'weapon': [
                {
                    'name': '新手剑',
                    'quality': '凡品',
                    'min_level': 1,
                    'max_level': 5,
                    'attack_range': (10, 20),
                    'description': '一把简单的新手剑'
                },
                {
                    'name': '精钢剑',
                    'quality': '灵品',
                    'min_level': 5,
                    'max_level': 15,
                    'attack_range': (20, 35),
                    'description': '用精钢打造的长剑'
                },
                {
                    'name': '灵剑',
                    'quality': '宝品',
                    'min_level': 15,
                    'max_level': 25,
                    'attack_range': (35, 50),
                    'crit_rate_chance': 0.3,
                    'description': '注入了灵力的宝剑'
                },
                {
                    'name': '仙剑',
                    'quality': '仙品',
                    'min_level': 25,
                    'max_level': 35,
                    'attack_range': (50, 70),
                    'crit_rate_chance': 0.5,
                    'special_effect': '攻击时额外造成10%伤害',
                    'description': '仙人使用的飞剑'
                }
            ],
            'armor': [
                {
                    'name': '布衣',
                    'quality': '凡品',
                    'min_level': 1,
                    'max_level': 5,
                    'defense_range': (5, 10),
                    'hp_range': (20, 30),
                    'description': '简单的布制衣服'
                },
                {
                    'name': '皮甲',
                    'quality': '灵品',
                    'min_level': 5,
                    'max_level': 15,
                    'defense_range': (10, 20),
                    'hp_range': (40, 60),
                    'description': '用兽皮制作的护甲'
                },
                {
                    'name': '灵甲',
                    'quality': '宝品',
                    'min_level': 15,
                    'max_level': 25,
                    'defense_range': (20, 35),
                    'hp_range': (80, 120),
                    'dodge_rate_chance': 0.3,
                    'description': '注入了灵力的护甲'
                },
                {
                    'name': '仙甲',
                    'quality': '仙品',
                    'min_level': 25,
                    'max_level': 35,
                    'defense_range': (35, 50),
                    'hp_range': (150, 200),
                    'dodge_rate_chance': 0.4,
                    'special_effect': '受到伤害时减少10%',
                    'description': '仙人护体的宝甲'
                }
            ],
            'accessory': [
                {
                    'name': '木戒指',
                    'quality': '凡品',
                    'min_level': 1,
                    'max_level': 5,
                    'mp_range': (10, 20),
                    'description': '简单的木制戒指'
                },
                {
                    'name': '玉佩',
                    'quality': '灵品',
                    'min_level': 5,
                    'max_level': 15,
                    'mp_range': (20, 40),
                    'hp_range': (30, 50),
                    'description': '温润的玉佩'
                },
                {
                    'name': '灵玉',
                    'quality': '宝品',
                    'min_level': 15,
                    'max_level': 25,
                    'mp_range': (50, 80),
                    'hp_range': (60, 100),
                    'speed_bonus_chance': 0.3,
                    'description': '蕴含灵力的宝玉'
                },
                {
                    'name': '仙玉',
                    'quality': '仙品',
                    'min_level': 25,
                    'max_level': 35,
                    'mp_range': (100, 150),
                    'hp_range': (120, 180),
                    'speed_bonus_chance': 0.5,
                    'special_effect': '法力恢复速度提升20%',
                    'description': '仙人佩戴的宝玉'
                }
            ]
        }

        return templates

    async def create_equipment(self, user_id: str, equipment_type: str, level: Optional[int] = None) -> Equipment:
        """
        为玩家创建装备

        Args:
            user_id: 用户ID
            equipment_type: 装备类型
            level: 指定等级(可选)

        Returns:
            创建的装备对象

        Raises:
            ValueError: 装备类型不存在
        """
        # 获取玩家等级
        player = await self.player_mgr.get_player_or_error(user_id)
        player_level = self._get_player_level(player)

        # 检查装备类型
        if equipment_type not in self.equipment_templates:
            raise ValueError(f"不支持的装备类型: {equipment_type}")

        # 选择合适的模板
        available_templates = [
            template for template in self.equipment_templates[equipment_type]
            if template['min_level'] <= player_level
        ]

        if not available_templates:
            # 如果没有合适的模板，使用最低级的
            template = self.equipment_templates[equipment_type][0]
        else:
            # 根据玩家等级权重选择模板
            weights = []
            for template in available_templates:
                # 等级越接近玩家等级，权重越高
                level_diff = abs(template['min_level'] - player_level)
                weight = max(1, 10 - level_diff)
                weights.append(weight)

            template = random.choices(available_templates, weights=weights)[0]

        # 生成装备
        equipment = self._generate_equipment_from_template(template, user_id, level or player_level)

        # 保存到数据库
        await self._save_equipment(equipment)

        logger.info(f"为玩家 {player.name} 生成装备: {equipment.get_display_name()}")

        return equipment

    def _generate_equipment_from_template(self, template: Dict, user_id: str, level: int) -> Equipment:
        """从模板生成装备"""
        equipment = Equipment(
            id=str(uuid.uuid4()),
            user_id=user_id,
            name=template['name'],
            type=template.get('type', 'weapon'),
            quality=template['quality'],
            level=level,
            attack=0,
            defense=0,
            hp_bonus=0,
            mp_bonus=0,
            description=template.get('description', ''),
            special_effect=template.get('special_effect')
        )

        # 生成基础属性
        if 'attack_range' in template:
            equipment.attack = random.randint(*template['attack_range'])
        if 'defense_range' in template:
            equipment.defense = random.randint(*template['defense_range'])
        if 'hp_range' in template:
            equipment.hp_bonus = random.randint(*template['hp_range'])
        if 'mp_range' in template:
            equipment.mp_bonus = random.randint(*template['mp_range'])

        # 根据等级调整属性
        if level > template['min_level']:
            level_multiplier = 1 + (level - template['min_level']) * 0.1
            equipment.attack = int(equipment.attack * level_multiplier)
            equipment.defense = int(equipment.defense * level_multiplier)
            equipment.hp_bonus = int(equipment.hp_bonus * level_multiplier)
            equipment.mp_bonus = int(equipment.mp_bonus * level_multiplier)

        # 额外属性
        if template.get('crit_rate_chance', 0) > 0 and random.random() < template['crit_rate_chance']:
            equipment.extra_attrs = equipment.extra_attrs or {}
            equipment.extra_attrs['crit_rate'] = 0.05  # 5%暴击率

        if template.get('dodge_rate_chance', 0) > 0 and random.random() < template['dodge_rate_chance']:
            equipment.extra_attrs = equipment.extra_attrs or {}
            equipment.extra_attrs['dodge_rate'] = 0.05  # 5%闪避率

        if template.get('speed_bonus_chance', 0) > 0 and random.random() < template['speed_bonus_chance']:
            equipment.extra_attrs = equipment.extra_attrs or {}
            equipment.extra_attrs['speed_bonus'] = 5  # 5点速度

        return equipment

    def _get_player_level(self, player) -> int:
        """获取玩家等级(基于境界的简化计算)"""
        # 根据境界和等级计算一个综合等级
        realm_levels = {
            '炼气期': 1,
            '筑基期': 10,
            '金丹期': 20,
            '元婴期': 30,
            '化神期': 40,
            '炼虚期': 50,
            '合体期': 60,
            '大乘期': 70,
            '渡劫期': 80
        }

        base_level = realm_levels.get(player.realm, 1)
        return base_level + player.realm_level - 1

    async def _save_equipment(self, equipment: Equipment):
        """保存装备到数据库"""
        # 确保装备表存在
        await self._ensure_equipment_table()

        # 插入装备数据
        equipment_data = equipment.to_dict()
        columns = list(equipment_data.keys())
        placeholders = ', '.join(['?' for _ in columns])
        values = list(equipment_data.values())

        sql = f"INSERT INTO equipment ({', '.join(columns)}) VALUES ({placeholders})"
        await self.db.execute(sql, values)

    async def _ensure_equipment_table(self):
        """确保装备表存在"""
        sql = """
        CREATE TABLE IF NOT EXISTS equipment (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            sub_type TEXT,
            quality TEXT NOT NULL,
            level INTEGER NOT NULL,
            enhance_level INTEGER DEFAULT 0,
            attack INTEGER DEFAULT 0,
            defense INTEGER DEFAULT 0,
            hp_bonus INTEGER DEFAULT 0,
            mp_bonus INTEGER DEFAULT 0,
            extra_attrs TEXT,
            special_effect TEXT,
            skill_id INTEGER,
            is_equipped INTEGER DEFAULT 0,
            is_bound INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
        """
        await self.db.execute(sql)

    async def get_player_equipment(self, user_id: str) -> List[Equipment]:
        """获取玩家的所有装备"""
        await self._ensure_equipment_table()

        results = await self.db.fetchall(
            "SELECT * FROM equipment WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,)
        )

        equipment_list = []
        for result in results:
            equipment_data = dict(result)
            equipment = Equipment.from_dict(equipment_data)
            equipment_list.append(equipment)

        return equipment_list

    async def get_equipment_by_id(self, equipment_id: str, user_id: str) -> Equipment:
        """根据ID获取装备"""
        await self._ensure_equipment_table()

        result = await self.db.fetchone(
            "SELECT * FROM equipment WHERE id = ? AND user_id = ?",
            (equipment_id, user_id)
        )

        if result is None:
            raise EquipmentNotFoundError(equipment_id)

        equipment_data = dict(result)
        return Equipment.from_dict(equipment_data)

    async def equip_item(self, user_id: str, equipment_id: str) -> Equipment:
        """装备物品"""
        # 获取装备
        equipment = await self.get_equipment_by_id(equipment_id, user_id)
        player = await self.player_mgr.get_player_or_error(user_id)

        # 检查等级要求
        player_level = self._get_player_level(player)
        if not equipment.can_enhance():  # 这里用can_enhance来检查等级要求
            raise InsufficientLevelError(equipment.level)

        # 检查是否已有同类型装备
        current_equipment = await self.get_player_equipment(user_id)
        for item in current_equipment:
            if item.is_equipped and item.type == equipment.type:
                # 卸下当前装备
                item.unequip()
                await self._update_equipment(item)

        # 装备新物品
        equipment.equip(equipment.get_slot())
        await self._update_equipment(equipment)

        logger.info(f"玩家 {player.name} 装备了: {equipment.get_display_name()}")

        return equipment

    async def unequip_item(self, user_id: str, slot: str) -> Equipment:
        """卸下装备"""
        # 获取当前装备的物品
        current_equipment = await self.get_player_equipment(user_id)
        equipped_item = None

        for item in current_equipment:
            if item.is_equipped and item.get_slot() == slot:
                equipped_item = item
                break

        if equipped_item is None:
            raise EquipmentNotFoundError(f"槽位 {slot} 没有装备")

        # 卸下装备
        equipped_item.unequip()
        await self._update_equipment(equipped_item)

        player = await self.player_mgr.get_player_or_error(user_id)
        logger.info(f"玩家 {player.name} 卸下了: {equipped_item.get_display_name()}")

        return equipped_item

    async def _update_equipment(self, equipment: Equipment):
        """更新装备信息"""
        equipment_data = equipment.to_dict()

        # 构建UPDATE语句
        set_clause = ', '.join([f"{key} = ?" for key in equipment_data.keys() if key != 'id'])
        values = [value for key, value in equipment_data.items() if key != 'id']
        values.append(equipment.id)

        sql = f"UPDATE equipment SET {set_clause} WHERE id = ?"
        await self.db.execute(sql, tuple(values))

    async def get_equipped_items(self, user_id: str) -> Dict[str, Equipment]:
        """获取玩家已装备的物品"""
        all_equipment = await self.get_player_equipment(user_id)
        equipped = {}

        for item in all_equipment:
            if item.is_equipped:
                equipped[item.get_slot()] = item

        return equipped

    async def format_equipment_list(self, user_id: str) -> str:
        """格式化装备列表"""
        equipment_list = await self.get_player_equipment(user_id)
        equipped_items = await self.get_equipped_items(user_id)

        if not equipment_list:
            return "📦 背包空空如也，还没有任何装备"

        lines = ["🎒 装备背包", "─" * 40]

        # 按类型分组显示
        by_type = {}
        for item in equipment_list:
            if item.type not in by_type:
                by_type[item.type] = []
            by_type[item.type].append(item)

        type_names = {
            'weapon': '⚔️ 武器',
            'armor': '🛡️ 护甲',
            'accessory': '💍 饰品'
        }

        for equip_type, items in by_type.items():
            type_name = type_names.get(equip_type, f"📦 {equip_type}")
            lines.append(f"\n{type_name}:")

            for i, item in enumerate(items, 1):
                status = "✅" if item.is_equipped else "⭕"
                lines.append(f"  {status} {i}. {item.get_display_name()}")

        lines.append("\n💡 使用 /装备 [编号] 穿戴装备")
        lines.append("💡 使用 /卸下 [槽位] 卸下装备")

        return "\n".join(lines)

    async def get_equipment_stats(self, user_id: str) -> Dict:
        """获取装备统计信息"""
        equipped_items = await self.get_equipped_items(user_id)

        total_attack = sum(item.get_total_attack() for item in equipped_items.values())
        total_defense = sum(item.get_total_defense() for item in equipped_items.values())
        total_hp = sum(item.hp_bonus for item in equipped_items.values())
        total_mp = sum(item.mp_bonus for item in equipped_items.values())
        total_score = sum(item.get_equipment_score() for item in equipped_items.values())

        return {
            'equipped_count': len(equipped_items),
            'total_attack': total_attack,
            'total_defense': total_defense,
            'total_hp_bonus': total_hp,
            'total_mp_bonus': total_mp,
            'total_score': total_score,
            'equipped_items': equipped_items
        }