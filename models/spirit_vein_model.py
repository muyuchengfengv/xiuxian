"""
灵脉数据模型
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any


@dataclass
class SpiritVein:
    """灵脉数据模型"""

    id: int  # 灵脉ID
    name: str  # 灵脉名称
    level: int  # 灵脉等级(1-5)
    location: str  # 所在位置
    base_income: int  # 基础每小时收益
    owner_id: Optional[str] = None  # 占领者user_id
    owner_name: Optional[str] = None  # 占领者名称
    occupied_at: Optional[datetime] = None  # 占领时间
    last_collect_at: Optional[datetime] = None  # 上次收取时间
    created_at: datetime = None  # 创建时间

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典用于数据库存储"""
        return {
            "id": self.id,
            "name": self.name,
            "level": self.level,
            "location": self.location,
            "base_income": self.base_income,
            "owner_id": self.owner_id,
            "owner_name": self.owner_name,
            "occupied_at": self.occupied_at.isoformat() if self.occupied_at else None,
            "last_collect_at": self.last_collect_at.isoformat() if self.last_collect_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SpiritVein':
        """从字典创建对象"""
        # 处理datetime字段
        if data.get("occupied_at"):
            if isinstance(data["occupied_at"], str):
                data["occupied_at"] = datetime.fromisoformat(data["occupied_at"])

        if data.get("last_collect_at"):
            if isinstance(data["last_collect_at"], str):
                data["last_collect_at"] = datetime.fromisoformat(data["last_collect_at"])

        if data.get("created_at"):
            if isinstance(data["created_at"], str):
                data["created_at"] = datetime.fromisoformat(data["created_at"])
        else:
            data["created_at"] = datetime.now()

        return cls(**data)

    def is_occupied(self) -> bool:
        """检查是否已被占领"""
        return self.owner_id is not None

    def get_hourly_income(self) -> int:
        """获取每小时收益"""
        return self.base_income

    def __repr__(self) -> str:
        """字符串表示"""
        owner_info = f"占领者: {self.owner_name}" if self.owner_id else "无主"
        return f"SpiritVein(id={self.id}, name='{self.name}', level={self.level}, {owner_info})"
