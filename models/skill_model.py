"""
技能数据模型
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any


@dataclass
class Skill:
    """技能数据模型"""

    # 基础信息
    id: Optional[int] = None  # 技能ID(数据库自增)
    user_id: str = ""  # 拥有者ID
    skill_name: str = ""  # 技能名称

    # 技能类型
    skill_type: str = "attack"  # 技能类型: attack/defense/support/control
    element: Optional[str] = None  # 元素属性: 金/木/水/火/土/风/雷/冰/光/暗

    # 技能等级
    level: int = 1  # 技能等级(1-5)
    proficiency: int = 0  # 熟练度(0-100)

    # 技能效果
    base_damage: int = 0  # 基础伤害
    mp_cost: int = 10  # 法力消耗
    cooldown: int = 0  # 冷却回合数
    effect_description: Optional[str] = None  # 效果描述

    # 时间
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典用于数据库存储"""
        data = {
            "id": self.id,
            "user_id": self.user_id,
            "skill_name": self.skill_name,
            "skill_type": self.skill_type,
            "element": self.element,
            "level": self.level,
            "proficiency": self.proficiency,
            "base_damage": self.base_damage,
            "mp_cost": self.mp_cost,
            "cooldown": self.cooldown,
            "effect_description": self.effect_description,
            "created_at": self.created_at.isoformat()
        }
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Skill':
        """从字典创建对象"""
        # 处理datetime
        if data.get("created_at"):
            if isinstance(data["created_at"], str):
                data["created_at"] = datetime.fromisoformat(data["created_at"])
        else:
            data["created_at"] = datetime.now()

        return cls(**data)

    def get_actual_damage(self, base_attack: int = 0) -> int:
        """
        计算实际伤害

        Args:
            base_attack: 攻击者的基础攻击力

        Returns:
            实际伤害值
        """
        # 技能伤害 = 基础伤害 + 攻击力加成 * 技能等级倍率
        level_multiplier = 1.0 + (self.level - 1) * 0.2  # 每级+20%
        proficiency_bonus = 1.0 + self.proficiency / 100.0  # 熟练度加成

        total_damage = (self.base_damage + base_attack * 0.5) * level_multiplier * proficiency_bonus
        return int(total_damage)

    def can_use(self, current_mp: int) -> bool:
        """检查是否可以使用技能"""
        return current_mp >= self.mp_cost

    def get_mp_cost_by_level(self) -> int:
        """根据等级获取法力消耗"""
        return self.mp_cost + (self.level - 1) * 5  # 每级+5法力消耗

    def gain_proficiency(self, amount: int = 1) -> bool:
        """
        增加熟练度

        Args:
            amount: 增加的熟练度

        Returns:
            是否可以升级
        """
        self.proficiency = min(100, self.proficiency + amount)

        # 熟练度满且未达到最高等级时可以升级
        if self.proficiency >= 100 and self.level < 5:
            return True
        return False

    def level_up(self):
        """技能升级"""
        if self.level < 5:
            self.level += 1
            self.proficiency = 0  # 重置熟练度
            # 提升技能效果
            self.base_damage = int(self.base_damage * 1.3)

    def __repr__(self) -> str:
        """字符串表示"""
        element_str = f"[{self.element}]" if self.element else ""
        return (f"{element_str}{self.skill_name} Lv.{self.level} "
                f"(伤害:{self.base_damage} 消耗:{self.mp_cost}MP)")
