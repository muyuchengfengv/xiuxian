"""
宗门数据模型
负责宗门相关的数据结构定义
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List
import json


@dataclass
class Sect:
    """宗门数据模型"""

    # 基础信息
    id: Optional[str] = None  # 宗门ID
    name: str = ""  # 宗门名称
    description: str = ""  # 宗门描述
    announcement: str = ""  # 宗门公告

    # 宗门类型
    sect_type: str = "正派"  # 宗门类型: 正派/魔道/中立
    sect_style: str = "剑修"  # 宗门风格: 剑修/法修/体修/丹修/器修等

    # 宗门等级
    level: int = 1  # 宗门等级 1-10
    experience: int = 0  # 宗门经验
    max_experience: int = 1000  # 升级所需经验

    # 宗门资源
    spirit_stone: int = 0  # 灵石
    contribution: int = 0  # 总贡献度
    reputation: int = 0  # 声望
    power: int = 0  # 实力值（所有成员战力总和）

    # 宗门成员
    leader_id: str = ""  # 宗主ID
    member_count: int = 0  # 成员数量
    max_members: int = 20  # 最大成员数

    # 宗门建筑
    buildings: Dict[str, int] = field(default_factory=dict)  # 建筑等级 {建筑名: 等级}

    # 宗门技能
    sect_skills: List[str] = field(default_factory=list)  # 宗门技能ID列表

    # 宗门状态
    is_recruiting: bool = True  # 是否招募
    join_requirement: Dict[str, Any] = field(default_factory=dict)  # 加入要求

    # 战争状态
    in_war: bool = False  # 是否在战争中
    war_target_id: Optional[str] = None  # 战争目标宗门ID
    war_score: int = 0  # 战争积分

    # 时间信息
    created_at: datetime = field(default_factory=datetime.now)
    last_active_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典用于数据库存储"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "announcement": self.announcement,
            "sect_type": self.sect_type,
            "sect_style": self.sect_style,
            "level": self.level,
            "experience": self.experience,
            "max_experience": self.max_experience,
            "spirit_stone": self.spirit_stone,
            "contribution": self.contribution,
            "reputation": self.reputation,
            "power": self.power,
            "leader_id": self.leader_id,
            "member_count": self.member_count,
            "max_members": self.max_members,
            "buildings": json.dumps(self.buildings),
            "sect_skills": json.dumps(self.sect_skills),
            "is_recruiting": 1 if self.is_recruiting else 0,
            "join_requirement": json.dumps(self.join_requirement),
            "in_war": 1 if self.in_war else 0,
            "war_target_id": self.war_target_id,
            "war_score": self.war_score,
            "created_at": self.created_at.isoformat(),
            "last_active_at": self.last_active_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Sect':
        """从字典创建对象"""
        # 处理布尔值
        if "is_recruiting" in data:
            data["is_recruiting"] = bool(data["is_recruiting"])
        if "in_war" in data:
            data["in_war"] = bool(data["in_war"])

        # 处理datetime
        if data.get("created_at"):
            if isinstance(data["created_at"], str):
                data["created_at"] = datetime.fromisoformat(data["created_at"])
        if data.get("last_active_at"):
            if isinstance(data["last_active_at"], str):
                data["last_active_at"] = datetime.fromisoformat(data["last_active_at"])

        # 处理JSON字段
        if data.get("buildings"):
            if isinstance(data["buildings"], str):
                data["buildings"] = json.loads(data["buildings"])
        else:
            data["buildings"] = {}

        if data.get("sect_skills"):
            if isinstance(data["sect_skills"], str):
                data["sect_skills"] = json.loads(data["sect_skills"])
        else:
            data["sect_skills"] = []

        if data.get("join_requirement"):
            if isinstance(data["join_requirement"], str):
                data["join_requirement"] = json.loads(data["join_requirement"])
        else:
            data["join_requirement"] = {}

        return cls(**data)

    def get_type_emoji(self) -> str:
        """获取宗门类型图标"""
        type_emojis = {
            "正派": "☀️",
            "魔道": "🌙",
            "中立": "⚖️"
        }
        return type_emojis.get(self.sect_type, "⚪")

    def get_level_display(self) -> str:
        """获取宗门等级显示"""
        level_names = {
            1: "初创宗门",
            2: "小型宗门",
            3: "中型宗门",
            4: "大型宗门",
            5: "一流宗门",
            6: "顶级宗门",
            7: "圣地宗门",
            8: "传说宗门",
            9: "神话宗门",
            10: "永恒宗门"
        }
        return level_names.get(self.level, "未知等级")

    def can_level_up(self) -> bool:
        """检查是否可以升级"""
        return self.experience >= self.max_experience and self.level < 10

    def level_up(self) -> bool:
        """宗门升级"""
        if not self.can_level_up():
            return False

        self.level += 1
        self.experience -= self.max_experience
        self.max_experience = int(self.max_experience * 1.5)
        self.max_members += 10  # 每级增加10个成员位

        return True

    def add_experience(self, amount: int) -> bool:
        """增加经验，返回是否升级"""
        self.experience += amount
        leveled_up = False

        while self.can_level_up():
            self.level_up()
            leveled_up = True

        return leveled_up

    def can_recruit(self) -> bool:
        """检查是否可以招募新成员"""
        return self.is_recruiting and self.member_count < self.max_members

    def get_building_level(self, building_name: str) -> int:
        """获取建筑等级"""
        return self.buildings.get(building_name, 0)

    def upgrade_building(self, building_name: str) -> bool:
        """升级建筑"""
        current_level = self.get_building_level(building_name)
        if current_level >= 10:  # 建筑最高10级
            return False

        self.buildings[building_name] = current_level + 1
        return True

    def get_display_info(self) -> str:
        """获取宗门显示信息"""
        lines = [
            f"{self.get_type_emoji()} {self.name}",
            f"等级：{self.get_level_display()} Lv.{self.level}",
            f"类型：{self.sect_type} | 风格：{self.sect_style}",
            "",
            f"📝 {self.description}",
            "",
            f"👥 成员：{self.member_count}/{self.max_members}",
            f"💎 灵石：{self.spirit_stone}",
            f"⭐ 声望：{self.reputation}",
            f"⚔️ 实力：{self.power}",
            f"📊 经验：{self.experience}/{self.max_experience}",
        ]

        if self.announcement:
            lines.extend(["", f"📢 公告：{self.announcement}"])

        if self.in_war:
            lines.extend(["", f"⚔️ 战争状态：进行中 | 积分：{self.war_score}"])

        return "\n".join(lines)

    def __repr__(self) -> str:
        """字符串表示"""
        return f"{self.get_type_emoji()} {self.name} (Lv.{self.level})"


@dataclass
class SectMember:
    """宗门成员数据模型"""

    # 基础信息
    id: Optional[int] = None  # 记录ID
    user_id: str = ""  # 用户ID
    sect_id: str = ""  # 宗门ID

    # 职位信息
    position: str = "弟子"  # 职位: 宗主/长老/执事/精英弟子/弟子
    position_level: int = 1  # 职位等级 1-5

    # 贡献信息
    contribution: int = 0  # 个人贡献度
    total_contribution: int = 0  # 历史总贡献

    # 活跃度
    activity: int = 0  # 活跃度
    last_active_at: datetime = field(default_factory=datetime.now)

    # 时间信息
    joined_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "sect_id": self.sect_id,
            "position": self.position,
            "position_level": self.position_level,
            "contribution": self.contribution,
            "total_contribution": self.total_contribution,
            "activity": self.activity,
            "last_active_at": self.last_active_at.isoformat(),
            "joined_at": self.joined_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SectMember':
        """从字典创建对象"""
        if data.get("last_active_at"):
            if isinstance(data["last_active_at"], str):
                data["last_active_at"] = datetime.fromisoformat(data["last_active_at"])
        if data.get("joined_at"):
            if isinstance(data["joined_at"], str):
                data["joined_at"] = datetime.fromisoformat(data["joined_at"])

        return cls(**data)

    def get_position_emoji(self) -> str:
        """获取职位图标"""
        position_emojis = {
            "宗主": "👑",
            "长老": "🎖️",
            "执事": "🏅",
            "精英弟子": "⭐",
            "弟子": "📚"
        }
        return position_emojis.get(self.position, "📚")

    def get_position_display(self) -> str:
        """获取职位显示名称"""
        emoji = self.get_position_emoji()
        return f"{emoji} {self.position}"

    def can_manage_members(self) -> bool:
        """是否可以管理成员"""
        return self.position in ["宗主", "长老", "执事"]

    def can_upgrade_buildings(self) -> bool:
        """是否可以升级建筑"""
        return self.position in ["宗主", "长老"]

    def can_declare_war(self) -> bool:
        """是否可以宣战"""
        return self.position == "宗主"

    def __repr__(self) -> str:
        """字符串表示"""
        return f"{self.get_position_display()} ({self.user_id})"