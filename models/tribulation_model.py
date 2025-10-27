"""
天劫数据模型
负责天劫相关的数据结构定义
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List
import json


@dataclass
class Tribulation:
    """天劫数据模型"""

    # 基础信息
    id: Optional[str] = None  # 天劫ID
    user_id: str = ""  # 渡劫者ID
    tribulation_type: str = "thunder"  # 天劫类型: thunder/fire/heart_demon/wind/ice/mixed

    # 天劫等级
    realm: str = "筑基期"  # 对应境界
    realm_level: int = 1  # 对应小等级
    tribulation_level: int = 1  # 天劫等级 1-9 (对应九重天劫)
    difficulty: str = "normal"  # 难度: easy/normal/hard/hell

    # 天劫属性
    total_waves: int = 3  # 总波数
    current_wave: int = 0  # 当前波数
    damage_per_wave: int = 100  # 每波伤害
    damage_reduction: float = 0.0  # 伤害减免

    # 渡劫状态
    status: str = "pending"  # 状态: pending/in_progress/success/failed
    success: bool = False  # 是否成功

    # 渡劫数据
    initial_hp: int = 0  # 初始生命值
    current_hp: int = 0  # 当前生命值
    total_damage_taken: int = 0  # 总承受伤害

    # 奖励和惩罚
    rewards: Dict[str, Any] = field(default_factory=dict)  # 奖励
    penalties: Dict[str, Any] = field(default_factory=dict)  # 惩罚

    # 天劫记录
    wave_logs: List[Dict[str, Any]] = field(default_factory=list)  # 每波记录

    # 时间信息
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典用于数据库存储"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "tribulation_type": self.tribulation_type,
            "realm": self.realm,
            "realm_level": self.realm_level,
            "tribulation_level": self.tribulation_level,
            "difficulty": self.difficulty,
            "total_waves": self.total_waves,
            "current_wave": self.current_wave,
            "damage_per_wave": self.damage_per_wave,
            "damage_reduction": self.damage_reduction,
            "status": self.status,
            "success": 1 if self.success else 0,
            "initial_hp": self.initial_hp,
            "current_hp": self.current_hp,
            "total_damage_taken": self.total_damage_taken,
            "rewards": json.dumps(self.rewards),
            "penalties": json.dumps(self.penalties),
            "wave_logs": json.dumps(self.wave_logs),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at": self.created_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Tribulation':
        """从字典创建对象"""
        # 处理布尔值
        if "success" in data:
            data["success"] = bool(data["success"])

        # 处理datetime
        if data.get("started_at"):
            if isinstance(data["started_at"], str):
                data["started_at"] = datetime.fromisoformat(data["started_at"])
        if data.get("completed_at"):
            if isinstance(data["completed_at"], str):
                data["completed_at"] = datetime.fromisoformat(data["completed_at"])
        if data.get("created_at"):
            if isinstance(data["created_at"], str):
                data["created_at"] = datetime.fromisoformat(data["created_at"])

        # 处理JSON字段
        if data.get("rewards"):
            if isinstance(data["rewards"], str):
                data["rewards"] = json.loads(data["rewards"])
        else:
            data["rewards"] = {}

        if data.get("penalties"):
            if isinstance(data["penalties"], str):
                data["penalties"] = json.loads(data["penalties"])
        else:
            data["penalties"] = {}

        if data.get("wave_logs"):
            if isinstance(data["wave_logs"], str):
                data["wave_logs"] = json.loads(data["wave_logs"])
        else:
            data["wave_logs"] = []

        return cls(**data)

    def get_type_emoji(self) -> str:
        """获取天劫类型图标"""
        type_emojis = {
            "thunder": "⚡",
            "fire": "🔥",
            "heart_demon": "👹",
            "wind": "💨",
            "ice": "❄️",
            "mixed": "🌀"
        }
        return type_emojis.get(self.tribulation_type, "⚡")

    def get_type_name(self) -> str:
        """获取天劫类型名称"""
        type_names = {
            "thunder": "雷劫",
            "fire": "火劫",
            "heart_demon": "心魔劫",
            "wind": "风劫",
            "ice": "冰劫",
            "mixed": "混合天劫"
        }
        return type_names.get(self.tribulation_type, "未知天劫")

    def get_difficulty_display(self) -> str:
        """获取难度显示"""
        difficulty_map = {
            "easy": "⭐ 简单",
            "normal": "⭐⭐ 普通",
            "hard": "⭐⭐⭐ 困难",
            "hell": "⭐⭐⭐⭐ 地狱"
        }
        return difficulty_map.get(self.difficulty, "未知")

    def get_status_display(self) -> str:
        """获取状态显示"""
        status_map = {
            "pending": "⏳ 待开始",
            "in_progress": "⚡ 进行中",
            "success": "✅ 成功",
            "failed": "❌ 失败"
        }
        return status_map.get(self.status, "未知")

    def get_hp_percentage(self) -> float:
        """获取生命百分比"""
        if self.initial_hp <= 0:
            return 0.0
        return (self.current_hp / self.initial_hp) * 100

    def is_in_progress(self) -> bool:
        """是否正在进行中"""
        return self.status == "in_progress"

    def is_completed(self) -> bool:
        """是否已完成"""
        return self.status in ["success", "failed"]

    def add_wave_log(self, wave: int, damage: int, hp_before: int, hp_after: int, message: str):
        """添加渡劫记录"""
        log = {
            "wave": wave,
            "damage": damage,
            "hp_before": hp_before,
            "hp_after": hp_after,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        self.wave_logs.append(log)

    def get_display_info(self) -> str:
        """获取天劫显示信息"""
        lines = [
            f"{self.get_type_emoji()} {self.get_type_name()}",
            f"境界：{self.realm} | 等级：{self.tribulation_level}重",
            f"难度：{self.get_difficulty_display()}",
            f"状态：{self.get_status_display()}",
            "",
            f"⚡ 总波数：{self.total_waves}波",
            f"📊 当前波数：{self.current_wave}/{self.total_waves}",
            f"💥 每波伤害：{self.damage_per_wave}",
        ]

        if self.is_in_progress() or self.is_completed():
            hp_pct = self.get_hp_percentage()
            lines.extend([
                "",
                f"❤️ 生命值：{self.current_hp}/{self.initial_hp} ({hp_pct:.1f}%)",
                f"💔 总承受伤害：{self.total_damage_taken}"
            ])

        if self.damage_reduction > 0:
            lines.append(f"🛡️ 伤害减免：{self.damage_reduction:.1%}")

        return "\n".join(lines)

    def __repr__(self) -> str:
        """字符串表示"""
        return f"{self.get_type_emoji()} {self.get_type_name()} ({self.get_status_display()})"