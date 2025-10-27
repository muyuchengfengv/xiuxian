"""
装备数据模型
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
import json


@dataclass
class Equipment:
    """装备数据模型"""

    # 基础信息
    id: Optional[int] = None  # 装备ID(数据库自增)
    user_id: str = ""  # 拥有者ID
    name: str = ""  # 装备名称

    # 装备类型
    type: str = "weapon"  # 装备类型: weapon/armor/accessory
    sub_type: Optional[str] = None  # 子类型: sword/robe/ring等
    quality: str = "凡品"  # 品质: 凡品/灵品/宝品/仙品/神品/道品/混沌品

    # 等级要求
    level: int = 1  # 等级要求
    enhance_level: int = 0  # 强化等级 +0 到 +20

    # 基础属性
    attack: int = 0
    defense: int = 0
    hp_bonus: int = 0
    mp_bonus: int = 0

    # 附加属性(JSON格式存储)
    extra_attrs: Optional[Dict[str, Any]] = None  # {"crit_rate": 10, "crit_damage": 20}

    # 特效
    special_effect: Optional[str] = None  # 特殊效果描述
    skill_id: Optional[int] = None  # 附带技能ID

    # 状态
    is_equipped: bool = False  # 是否已装备
    is_bound: bool = False  # 是否绑定

    # 时间
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典用于数据库存储"""
        data = {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "type": self.type,
            "sub_type": self.sub_type,
            "quality": self.quality,
            "level": self.level,
            "enhance_level": self.enhance_level,
            "attack": self.attack,
            "defense": self.defense,
            "hp_bonus": self.hp_bonus,
            "mp_bonus": self.mp_bonus,
            "extra_attrs": str(self.extra_attrs) if self.extra_attrs else None,
            "special_effect": self.special_effect,
            "skill_id": self.skill_id,
            "is_equipped": 1 if self.is_equipped else 0,
            "is_bound": 1 if self.is_bound else 0,
            "created_at": self.created_at.isoformat()
        }
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Equipment':
        """从字典创建对象"""
        # 处理布尔值
        if "is_equipped" in data:
            data["is_equipped"] = bool(data["is_equipped"])
        if "is_bound" in data:
            data["is_bound"] = bool(data["is_bound"])

        # 处理datetime
        if data.get("created_at"):
            if isinstance(data["created_at"], str):
                data["created_at"] = datetime.fromisoformat(data["created_at"])
        else:
            data["created_at"] = datetime.now()

        # 处理extra_attrs
        if data.get("extra_attrs") and isinstance(data["extra_attrs"], str):
            import json
            try:
                data["extra_attrs"] = json.loads(data["extra_attrs"].replace("'", '"'))
            except:
                data["extra_attrs"] = None

        return cls(**data)

    def get_total_attack(self) -> int:
        """获取总攻击力(包括强化)"""
        base_attack = self.attack
        enhance_bonus = base_attack * self.enhance_level * 0.1  # 每级强化+10%
        return int(base_attack + enhance_bonus)

    def get_total_defense(self) -> int:
        """获取总防御力(包括强化)"""
        base_defense = self.defense
        enhance_bonus = base_defense * self.enhance_level * 0.1
        return int(base_defense + enhance_bonus)

    def can_enhance(self) -> bool:
        """检查是否可以强化"""
        return self.enhance_level < 20

    def get_slot(self) -> str:
        """获取装备槽位"""
        slot_mapping = {
            "weapon": "武器",
            "armor": "护甲",
            "accessory": "饰品"
        }
        return slot_mapping.get(self.type, "未知")

    def get_quality_display(self) -> str:
        """获取品质显示名称"""
        quality_emojis = {
            "凡品": "⚪",
            "灵品": "🔵",
            "宝品": "🟣",
            "仙品": "🟡",
            "神品": "🔴",
            "道品": "🌟",
            "混沌品": "⚫"
        }
        return quality_emojis.get(self.quality, "⚪")

    def get_display_name(self) -> str:
        """获取显示名称"""
        quality_emoji = self.get_quality_display()
        enhance_mark = f"+{self.enhance_level}" if self.enhance_level > 0 else ""
        equipped_mark = "[装备]" if self.is_equipped else ""

        return f"{quality_emoji} {self.name}{enhance_mark} {equipped_mark}"

    def get_detailed_info(self) -> str:
        """获取装备详细信息"""
        lines = [
            f"{self.get_display_name()}",
            f"品质：{self.quality} | 等级要求：{self.level} | 类型：{self.type}"
        ]

        # 基础属性
        if self.attack > 0:
            lines.append(f"⚔️ 攻击力：+{self.get_total_attack()}")
        if self.defense > 0:
            lines.append(f"🛡️ 防御力：+{self.get_total_defense()}")
        if self.hp_bonus > 0:
            lines.append(f"❤️ 生命值：+{self.hp_bonus}")
        if self.mp_bonus > 0:
            lines.append(f"💙 法力值：+{self.mp_bonus}")

        # 强化信息
        if self.enhance_level > 0:
            lines.append(f"✨ 强化等级：+{self.enhance_level}")

        # 状态信息
        lines.append(f"📊 装备评分：{self.get_equipment_score()}")

        # 描述信息
        if self.special_effect:
            lines.append("")
            lines.append(f"✨ 特殊效果：{self.special_effect}")

        return "\n".join(lines)

    def get_equipment_score(self) -> int:
        """计算装备评分"""
        score = 0

        # 基础属性评分
        score += self.get_total_attack() * 1
        score += self.get_total_defense() * 1
        score += self.hp_bonus * 0.1
        score += self.mp_bonus * 0.1

        # 强化等级加成
        score += self.enhance_level * 50

        # 品质加成
        quality_bonus = {
            "凡品": 1.0,
            "灵品": 1.5,
            "宝品": 2.0,
            "仙品": 3.0,
            "神品": 5.0,
            "道品": 8.0,
            "混沌品": 10.0
        }
        score *= quality_bonus.get(self.quality, 1.0)

        return int(score)

    def __repr__(self) -> str:
        """字符串表示"""
        return self.get_display_name()
