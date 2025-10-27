"""
功法数据模型
负责功法相关的数据结构定义
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List
import json


@dataclass
class CultivationMethod:
    """功法数据模型"""

    # 基础信息
    id: Optional[str] = None  # 功法ID
    name: str = ""  # 功法名称
    description: str = ""  # 功法描述

    # 功法分类
    method_type: str = "attack"  # 功法类型: attack/defense/speed/auxiliary
    element_type: str = "none"  # 元素属性: fire/water/earth/metal/wood/thunder/ice/none
    cultivation_type: str = "qi_refining"  # 修炼类型: sword_refining/body_refining/etc

    # 品质等级
    quality: str = "凡品"  # 品质: 凡品/灵品/宝品/仙品/神品/道品/天地品
    grade: int = 1  # 等级: 1-6 (凡品到天地品)

    # 等级要求
    min_realm: str = "炼气期"  # 最低境界要求
    min_realm_level: int = 1  # 最低小等级要求
    min_level: int = 1  # 最低综合等级要求

    # 功法属性
    attack_bonus: int = 0  # 攻击加成
    defense_bonus: int = 0  # 防御加成
    speed_bonus: int = 0  # 速度加成
    hp_bonus: int = 0  # 生命加成
    mp_bonus: int = 0  # 法力加成
    cultivation_speed_bonus: float = 0.0  # 修炼速度加成(百分比)
    breakthrough_rate_bonus: float = 0.0  # 突破成功率加成(百分比)

    # 特殊效果
    special_effects: List[str] = field(default_factory=list)  # 特殊效果列表
    skill_damage: int = 0  # 技能伤害
    cooldown_reduction: float = 0.0  # 冷却缩减(百分比)

    # 装备信息
    owner_id: Optional[str] = None  # 拥有者ID
    is_equipped: bool = False  # 是否装备
    equip_slot: Optional[str] = None  # 装备槽位: active_1/active_2/passive_1/passive_2

    # 熟练度
    proficiency: int = 0  # 熟练度
    max_proficiency: int = 1000  # 最大熟练度
    mastery_level: int = 0  # 掌握等级: 0-5 (入门→大成)

    # 功法来源
    source_type: str = "unknown"  # 来源: sect_reward/secret_realm/dungeon/purchase/gift
    source_detail: str = ""  # 来源详情

    # 时间信息
    created_at: datetime = field(default_factory=datetime.now)
    equipped_at: Optional[datetime] = None
    last_practiced_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典用于数据库存储"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "method_type": self.method_type,
            "element_type": self.element_type,
            "cultivation_type": self.cultivation_type,
            "quality": self.quality,
            "grade": self.grade,
            "min_realm": self.min_realm,
            "min_realm_level": self.min_realm_level,
            "min_level": self.min_level,
            "attack_bonus": self.attack_bonus,
            "defense_bonus": self.defense_bonus,
            "speed_bonus": self.speed_bonus,
            "hp_bonus": self.hp_bonus,
            "mp_bonus": self.mp_bonus,
            "cultivation_speed_bonus": self.cultivation_speed_bonus,
            "breakthrough_rate_bonus": self.breakthrough_rate_bonus,
            "special_effects": json.dumps(self.special_effects),
            "skill_damage": self.skill_damage,
            "cooldown_reduction": self.cooldown_reduction,
            "owner_id": self.owner_id,
            "is_equipped": 1 if self.is_equipped else 0,
            "equip_slot": self.equip_slot,
            "proficiency": self.proficiency,
            "max_proficiency": self.max_proficiency,
            "mastery_level": self.mastery_level,
            "source_type": self.source_type,
            "source_detail": self.source_detail,
            "created_at": self.created_at.isoformat(),
            "equipped_at": self.equipped_at.isoformat() if self.equipped_at else None,
            "last_practiced_at": self.last_practiced_at.isoformat() if self.last_practiced_at else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CultivationMethod':
        """从字典创建对象"""
        # 处理布尔值
        if "is_equipped" in data:
            data["is_equipped"] = bool(data["is_equipped"])

        # 处理datetime
        if data.get("created_at"):
            if isinstance(data["created_at"], str):
                data["created_at"] = datetime.fromisoformat(data["created_at"])

        if data.get("equipped_at"):
            if isinstance(data["equipped_at"], str):
                data["equipped_at"] = datetime.fromisoformat(data["equipped_at"])

        if data.get("last_practiced_at"):
            if isinstance(data["last_practiced_at"], str):
                data["last_practiced_at"] = datetime.fromisoformat(data["last_practiced_at"])

        # 处理特殊效果
        if data.get("special_effects"):
            if isinstance(data["special_effects"], str):
                data["special_effects"] = json.loads(data["special_effects"])
        else:
            data["special_effects"] = []

        return cls(**data)

    def get_quality_display(self) -> str:
        """获取品质���示名称"""
        quality_emojis = {
            "凡品": "⚪",
            "灵品": "🔵",
            "宝品": "🟣",
            "仙品": "🟡",
            "神品": "🔴",
            "道品": "🌟",
            "天地品": "⚫"
        }
        return quality_emojis.get(self.quality, "⚪")

    def get_type_display(self) -> str:
        """获取类型显示名称"""
        type_names = {
            "attack": "⚔️ 攻击功法",
            "defense": "🛡️ 防御功法",
            "speed": "💨 速度功法",
            "auxiliary": "✨ 辅助功法"
        }
        return type_names.get(self.method_type, "❓ 未知功法")

    def get_element_display(self) -> str:
        """获取元素显示名称"""
        element_emojis = {
            "fire": "🔥 火系",
            "water": "💧 水系",
            "earth": "🪨 土系",
            "metal": "⚔️ 金系",
            "wood": "🌿 木系",
            "thunder": "⚡ 雷系",
            "ice": "❄️ 冰系",
            "none": "⚪ 无属性"
        }
        return element_emojis.get(self.element_type, "⚪ 无属性")

    def get_equip_slot_display(self) -> str:
        """获取装备槽位显示名称"""
        slot_names = {
            "active_1": "主动功法1",
            "active_2": "主动功法2",
            "passive_1": "被动功法1",
            "passive_2": "被动功法2"
        }
        return slot_names.get(self.equip_slot, "未装备")

    def get_mastery_display(self) -> str:
        """获取熟练度显示"""
        mastery_names = ["入门", "初学", "掌握", "精通", "大成", "圆满"]
        mastery_name = mastery_names[min(self.mastery_level, 5)]

        progress = (self.proficiency / self.max_proficiency) * 100
        return f"{mastery_name} ({progress:.1f}%)"

    def get_display_name(self) -> str:
        """获取显示名称"""
        quality_emoji = self.get_quality_display()
        equipped_mark = "[已装备]" if self.is_equipped else ""
        return f"{quality_emoji} {self.name} {equipped_mark}"

    def get_detailed_info(self) -> str:
        """获取功法详细信息"""
        lines = [
            f"{self.get_display_name()}",
            f"{self.get_type_display()} | {self.get_element_display()} | 熟练度: {self.get_mastery_display()}",
            f"等级要求: {self.min_realm} {self.min_realm_level}级 | 来源: {self.source_detail}",
            "",
            f"📝 {self.description}",
            ""
        ]

        # 基础属性
        if self.attack_bonus > 0:
            lines.append(f"⚔️ 攻击力: +{self.attack_bonus}")
        if self.defense_bonus > 0:
            lines.append(f"🛡️ 防御力: +{self.defense_bonus}")
        if self.speed_bonus > 0:
            lines.append(f"💨 速度: +{self.speed_bonus}")
        if self.hp_bonus > 0:
            lines.append(f"❤️ 生命值: +{self.hp_bonus}")
        if self.mp_bonus > 0:
            lines.append(f"💙 法力值: +{self.mp_bonus}")

        # 加成属性
        if self.cultivation_speed_bonus > 0:
            lines.append(f"📈 修炼速度: +{self.cultivation_speed_bonus:.1%}")
        if self.breakthrough_rate_bonus > 0:
            lines.append(f"⚡ 突破成功率: +{self.breakthrough_rate_bonus:.1%}")

        # 特殊效果
        if self.special_effects:
            lines.append("")
            lines.append("✨ 特殊效果:")
            for effect in self.special_effects:
                lines.append(f"   • {effect}")

        # 技能伤害
        if self.skill_damage > 0:
            lines.append("")
            lines.append(f"💥 技能伤害: {self.skill_damage}")

        # 装备信息
        if self.is_equipped:
            lines.append("")
            lines.append(f"🎯 装备槽位: {self.get_equip_slot_display()}")

        lines.append("")
        lines.append(f"📊 功法评分: {self.get_method_score()}")

        return "\n".join(lines)

    def get_method_score(self) -> int:
        """计算功法评分"""
        score = 0

        # 基础属性评分
        score += self.attack_bonus * 1.5
        score += self.defense_bonus * 1.2
        score += self.speed_bonus * 1.0
        score += self.hp_bonus * 0.1
        score += self.mp_bonus * 0.1

        # 加成属性评分
        score += self.cultivation_speed_bonus * 100
        score += self.breakthrough_rate_bonus * 80
        score += self.skill_damage * 2.0

        # 熟练度加成
        if self.proficiency > 0:
            score += (self.proficiency / self.max_proficiency) * 50

        # 品质加成
        quality_bonus = {
            "凡品": 1.0,
            "灵品": 1.5,
            "宝品": 2.2,
            "仙品": 3.5,
            "神品": 5.5,
            "道品": 8.0,
            "天地品": 12.0
        }
        score *= quality_bonus.get(self.quality, 1.0)

        return int(score)

    def can_equip(self, realm: str, realm_level: int, player_level: int) -> bool:
        """检查是否可以装备"""
        # 境界检查
        realm_order = ["炼气期", "筑基期", "金丹期", "元婴期", "化神期",
                      "炼虚期", "合体期", "大乘期", "渡劫期", "真仙期",
                      "金仙期", "太乙金仙期", "大罗金仙期", "混元大罗金仙期", "��人期"]

        try:
            player_realm_index = realm_order.index(realm)
            method_realm_index = realm_order.index(self.min_realm)

            if player_realm_index < method_realm_index:
                return False

            if player_realm_index == method_realm_index and realm_level < self.min_realm_level:
                return False

        except ValueError:
            return False

        # 综合等级检查
        return player_level >= self.min_level

    def add_proficiency(self, amount: int) -> tuple:
        """增加熟练度，返回(是否升级, 新掌握等级)"""
        if self.proficiency >= self.max_proficiency:
            return False, self.mastery_level

        old_level = self.mastery_level
        self.proficiency = min(self.proficiency + amount, self.max_proficiency)

        # 检查是否升级
        proficiency_thresholds = [0, 200, 400, 600, 800, 1000]
        new_level = 0
        for i, threshold in enumerate(proficiency_thresholds):
            if self.proficiency >= threshold:
                new_level = i

        self.mastery_level = new_level
        leveled_up = new_level > old_level

        if leveled_up:
            # 升级时重置熟练度
            self.proficiency = 0
            self.max_proficiency = 200  # 每次升级需要200熟练度

        return leveled_up, self.mastery_level

    def __repr__(self) -> str:
        """字符串表示"""
        return self.get_display_name()