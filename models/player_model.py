"""
玩家数据模型
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any


@dataclass
class Player:
    """玩家数据模型"""

    # 基础信息
    user_id: str
    name: str

    # 境界信息
    realm: str = "炼气期"
    realm_level: int = 1  # 1=初期, 2=中期, 3=后期, 4=大圆满
    cultivation: int = 0  # 当前修为值

    # 灵根信息
    spirit_root_type: Optional[str] = None  # 灵根类型(金/木/水/火/土等)
    spirit_root_quality: Optional[str] = None  # 灵根品质(废/杂/双/单/变异/天)
    spirit_root_value: int = 50  # 灵根值(0-100)
    spirit_root_purity: int = 50  # 灵根纯度(0-100%)

    # 基础属性
    constitution: int = 10  # 体质
    spiritual_power: int = 10  # 灵力
    comprehension: int = 10  # 悟性
    luck: int = 10  # 幸运
    root_bone: int = 10  # 根骨

    # 战斗属性
    hp: int = 100  # 当前生命值
    max_hp: int = 100  # 最大生命值
    mp: int = 100  # 当前法力值
    max_mp: int = 100  # 最大法力值
    attack: int = 10  # 攻击力
    defense: int = 10  # 防御力

    # 资源
    spirit_stone: int = 1000  # 灵石
    contribution: int = 0  # 宗门贡献值

    # 宗门
    sect_id: Optional[int] = None  # 所属宗门ID
    sect_position: Optional[str] = None  # 宗门职位

    # 位置
    current_location: str = "新手村"  # 当前位置

    # 时间
    last_cultivation: Optional[datetime] = None  # 上次修炼时间
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典用于数据库存储"""
        data = {
            "user_id": self.user_id,
            "name": self.name,
            "realm": self.realm,
            "realm_level": self.realm_level,
            "cultivation": self.cultivation,
            "spirit_root_type": self.spirit_root_type,
            "spirit_root_quality": self.spirit_root_quality,
            "spirit_root_value": self.spirit_root_value,
            "spirit_root_purity": self.spirit_root_purity,
            "constitution": self.constitution,
            "spiritual_power": self.spiritual_power,
            "comprehension": self.comprehension,
            "luck": self.luck,
            "root_bone": self.root_bone,
            "hp": self.hp,
            "max_hp": self.max_hp,
            "mp": self.mp,
            "max_mp": self.max_mp,
            "attack": self.attack,
            "defense": self.defense,
            "spirit_stone": self.spirit_stone,
            "contribution": self.contribution,
            "sect_id": self.sect_id,
            "sect_position": self.sect_position,
            "current_location": self.current_location,
            "last_cultivation": self.last_cultivation.isoformat() if self.last_cultivation else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Player':
        """从字典创建对象"""
        # 处理datetime字段
        if data.get("last_cultivation"):
            if isinstance(data["last_cultivation"], str):
                data["last_cultivation"] = datetime.fromisoformat(data["last_cultivation"])
        else:
            data["last_cultivation"] = None

        if data.get("created_at"):
            if isinstance(data["created_at"], str):
                data["created_at"] = datetime.fromisoformat(data["created_at"])
        else:
            data["created_at"] = datetime.now()

        if data.get("updated_at"):
            if isinstance(data["updated_at"], str):
                data["updated_at"] = datetime.fromisoformat(data["updated_at"])
        else:
            data["updated_at"] = datetime.now()

        return cls(**data)

    def is_alive(self) -> bool:
        """检查是否存活"""
        return self.hp > 0

    def can_cultivate(self, cooldown_seconds: int = 3600) -> bool:
        """检查是否可以修炼"""
        if self.last_cultivation is None:
            return True
        elapsed = (datetime.now() - self.last_cultivation).total_seconds()
        return elapsed >= cooldown_seconds

    def get_cultivation_cooldown_remaining(self, cooldown_seconds: int = 3600) -> int:
        """获取修炼冷却剩余秒数"""
        if self.last_cultivation is None:
            return 0
        elapsed = (datetime.now() - self.last_cultivation).total_seconds()
        remaining = max(0, cooldown_seconds - elapsed)
        return int(remaining)

    def update_timestamp(self):
        """更新时间戳"""
        self.updated_at = datetime.now()

    def __repr__(self) -> str:
        """字符串表示"""
        return (f"Player(user_id='{self.user_id}', name='{self.name}', "
                f"realm='{self.realm}', level={self.realm_level})")
