"""
灵宠数据模型
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime


@dataclass
class Pet:
    """灵宠模板类"""
    id: int
    name: str
    pet_type: str  # 类型：辅助型、战斗型、采集型等
    rarity: str  # 稀有度：普通、稀有、史诗、传说、神话
    description: str
    base_attributes: str  # JSON格式的基础属性
    growth_rate: float  # 成长率
    max_level: int  # 最大等级
    element: Optional[str] = None  # 元素属性（可选）
    evolution_to: Optional[int] = None  # 可进化成的灵宠ID（可选）
    capture_difficulty: int = 50  # 捕获难度（1-100）
    created_at: Optional[str] = None

    @classmethod
    def from_db_row(cls, row: Dict[str, Any]) -> 'Pet':
        """从数据库行创建灵宠对象"""
        return cls(
            id=row['id'],
            name=row['name'],
            pet_type=row['pet_type'],
            rarity=row['rarity'],
            description=row['description'],
            base_attributes=row['base_attributes'],
            growth_rate=row['growth_rate'],
            max_level=row['max_level'],
            element=row.get('element'),
            evolution_to=row.get('evolution_to'),
            capture_difficulty=row.get('capture_difficulty', 50),
            created_at=row.get('created_at')
        )

    def get_rarity_color(self) -> str:
        """获取稀有度颜色标识"""
        rarity_colors = {
            "普通": "⚪",
            "稀有": "🟢",
            "史诗": "🔵",
            "传说": "🟣",
            "神话": "🟠"
        }
        return rarity_colors.get(self.rarity, "⚪")


@dataclass
class PlayerPet:
    """玩家拥有的灵宠类"""
    id: int
    user_id: str
    pet_id: int
    pet_name: str  # 灵宠昵称（可自定义）
    level: int
    experience: int
    is_active: bool  # 是否激活（出战）
    intimacy: int  # 亲密度（0-100）
    battle_count: int  # 参战次数
    acquired_from: str  # 获取途径：sect/secret_realm/capture/gift等
    acquired_at: str
    updated_at: Optional[str] = None

    # 运行时属性（从Pet模板加载）
    pet_template: Optional[Pet] = None

    @classmethod
    def from_db_row(cls, row: Dict[str, Any]) -> 'PlayerPet':
        """从数据库行创建玩家灵宠对象"""
        return cls(
            id=row['id'],
            user_id=row['user_id'],
            pet_id=row['pet_id'],
            pet_name=row['pet_name'],
            level=row['level'],
            experience=row['experience'],
            is_active=bool(row['is_active']),
            intimacy=row['intimacy'],
            battle_count=row.get('battle_count', 0),
            acquired_from=row['acquired_from'],
            acquired_at=row['acquired_at'],
            updated_at=row.get('updated_at')
        )

    def get_next_level_exp(self) -> int:
        """获取升级所需经验"""
        # 经验需求随等级指数增长
        return int(100 * (1.5 ** self.level))

    def get_intimacy_level(self) -> str:
        """获取亲密度等级"""
        if self.intimacy >= 90:
            return "心有灵犀"
        elif self.intimacy >= 70:
            return "亲密无间"
        elif self.intimacy >= 50:
            return "情同手足"
        elif self.intimacy >= 30:
            return "渐入佳境"
        else:
            return "初识"

    def can_level_up(self) -> bool:
        """检查是否可以升级"""
        if not self.pet_template:
            return False
        return self.level < self.pet_template.max_level and self.experience >= self.get_next_level_exp()

    def get_display_name(self) -> str:
        """获取显示名称"""
        if self.pet_template:
            rarity_color = self.pet_template.get_rarity_color()
            return f"{rarity_color}{self.pet_name} Lv.{self.level}"
        return f"{self.pet_name} Lv.{self.level}"


@dataclass
class PetSecretRealm:
    """灵宠秘境记录类"""
    id: int
    user_id: str
    realm_level: int  # 秘境等级
    exploration_count: int  # 探索次数
    last_exploration_at: Optional[str]  # 上次探索时间
    created_at: str

    @classmethod
    def from_db_row(cls, row: Dict[str, Any]) -> 'PetSecretRealm':
        """从数据库行创建秘境记录对象"""
        return cls(
            id=row['id'],
            user_id=row['user_id'],
            realm_level=row['realm_level'],
            exploration_count=row['exploration_count'],
            last_exploration_at=row.get('last_exploration_at'),
            created_at=row['created_at']
        )
