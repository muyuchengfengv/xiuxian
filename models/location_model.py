"""
地点(Location)数据模型
"""

from datetime import datetime
from typing import Optional, List, Dict, Any


class Location:
    """地点模型 - 代表修仙世界中的一个地点"""

    def __init__(
        self,
        id: int,
        name: str,
        description: str,
        region_type: str,  # 区域类型: mountain, cave, city, forest, desert, ocean, sky, void
        danger_level: int,  # 危险等级 1-10
        spirit_energy_density: int,  # 灵气浓度 1-100
        min_realm: str = "炼气期",  # 推荐最低境界
        coordinates_x: int = 0,  # X坐标
        coordinates_y: int = 0,  # Y坐标
        resources: Optional[str] = None,  # 资源列表(JSON字符串)
        connected_locations: Optional[str] = None,  # 连接的地点ID列表(JSON字符串)
        is_safe_zone: int = 0,  # 是否为安全区(不可PK)
        discovered_by: Optional[str] = None,  # 首次发现者user_id
        created_at: Optional[datetime] = None,
        **kwargs
    ):
        self.id = id
        self.name = name
        self.description = description
        self.region_type = region_type
        self.danger_level = danger_level
        self.spirit_energy_density = spirit_energy_density
        self.min_realm = min_realm
        self.coordinates_x = coordinates_x
        self.coordinates_y = coordinates_y
        self.resources = resources or "[]"
        self.connected_locations = connected_locations or "[]"
        self.is_safe_zone = is_safe_zone
        self.discovered_by = discovered_by
        self.created_at = created_at or datetime.now()

    def get_region_emoji(self) -> str:
        """获取区域类型对应的emoji"""
        emoji_map = {
            'mountain': '⛰️',
            'cave': '🕳️',
            'city': '🏙️',
            'forest': '🌲',
            'desert': '🏜️',
            'ocean': '🌊',
            'sky': '☁️',
            'void': '🌌',
            'sect': '🏛️',
            'secret': '🔮'
        }
        return emoji_map.get(self.region_type, '📍')

    def get_danger_display(self) -> str:
        """获取危险等级显示"""
        if self.danger_level <= 2:
            return "🟢 安全"
        elif self.danger_level <= 4:
            return "🟡 较低"
        elif self.danger_level <= 6:
            return "🟠 中等"
        elif self.danger_level <= 8:
            return "🔴 危险"
        else:
            return "⚫ 极危"

    def get_spirit_density_display(self) -> str:
        """获取灵气浓度显示"""
        if self.spirit_energy_density <= 20:
            return "⚪ 稀薄"
        elif self.spirit_energy_density <= 40:
            return "🔵 普通"
        elif self.spirit_energy_density <= 60:
            return "🟢 充沛"
        elif self.spirit_energy_density <= 80:
            return "🟣 浓郁"
        else:
            return "🔶 极浓"

    def get_cultivation_bonus(self) -> float:
        """获取修炼加成 (基于灵气浓度)"""
        return 1.0 + (self.spirit_energy_density / 100.0)

    def get_display_info(self, show_coordinates: bool = False) -> str:
        """获取地点显示信息"""
        lines = [
            f"{self.get_region_emoji()} {self.name}",
            "─" * 40,
            "",
            f"📜 {self.description}",
            "",
            f"⚠️ 危险等级: {self.get_danger_display()} (Lv.{self.danger_level})",
            f"💠 灵气浓度: {self.get_spirit_density_display()} ({self.spirit_energy_density}%)",
            f"🎯 推荐境界: {self.min_realm}以上",
            f"✨ 修炼加成: +{int((self.get_cultivation_bonus() - 1) * 100)}%"
        ]

        if self.is_safe_zone:
            lines.append("🛡️ 安全区域 (禁止PK)")

        if show_coordinates:
            lines.append(f"📌 坐标: ({self.coordinates_x}, {self.coordinates_y})")

        return "\n".join(lines)

    def get_simple_info(self) -> str:
        """获取简略信息"""
        return (
            f"{self.get_region_emoji()} {self.name} | "
            f"{self.get_danger_display()} | "
            f"灵气{self.spirit_energy_density}%"
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Location':
        """从字典创建Location对象"""
        return cls(**data)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'region_type': self.region_type,
            'danger_level': self.danger_level,
            'spirit_energy_density': self.spirit_energy_density,
            'min_realm': self.min_realm,
            'coordinates_x': self.coordinates_x,
            'coordinates_y': self.coordinates_y,
            'resources': self.resources,
            'connected_locations': self.connected_locations,
            'is_safe_zone': self.is_safe_zone,
            'discovered_by': self.discovered_by,
            'created_at': self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at
        }


class PlayerLocation:
    """玩家位置模型 - 跟踪玩家当前所在地点"""

    def __init__(
        self,
        user_id: str,
        current_location_id: int,
        last_move_time: Optional[datetime] = None,
        total_moves: int = 0,
        total_exploration_score: int = 0,  # 探索积分
        **kwargs
    ):
        self.user_id = user_id
        self.current_location_id = current_location_id
        self.last_move_time = last_move_time or datetime.now()
        self.total_moves = total_moves
        self.total_exploration_score = total_exploration_score

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PlayerLocation':
        """从字典创建PlayerLocation对象"""
        return cls(**data)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'user_id': self.user_id,
            'current_location_id': self.current_location_id,
            'last_move_time': self.last_move_time.isoformat() if isinstance(self.last_move_time, datetime) else self.last_move_time,
            'total_moves': self.total_moves,
            'total_exploration_score': self.total_exploration_score
        }
