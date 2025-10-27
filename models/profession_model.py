"""
职业系统数据模型
负责职业、职业技能、职业声望等相关数据结构定义
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List
import json


@dataclass
class Profession:
    """职业数据模型"""

    # 基础信息
    user_id: str = ""  # 玩家ID
    profession_type: str = ""  # 职业类型: alchemist/blacksmith/formation_master/talisman_master
    rank: int = 1  # 品级 1-7

    # 经验和等级
    experience: int = 0  # 职业经验
    level: int = 1  # 等级 (经验换算，通常1品=1-100级)
    skill_points: int = 0  # 技能点数

    # 声望和成就
    reputation: int = 0  # 职业声望
    achievements: List[str] = field(default_factory=list)  # 成就列表
    completed_tasks: int = 0  # 完成任务数

    # 成功率加成
    success_rate_bonus: float = 0.0  # 成功率加成
    quality_bonus: float = 0.0  # 品质加成

    # 统计数据
    total_creations: int = 0  # 总制作数量
    successful_creations: int = 0  # 成功制作数量
    high_quality_creations: int = 0  # 高品质制作数量

    # 时间信息
    created_at: datetime = field(default_factory=datetime.now)
    last_practice_at: Optional[datetime] = None
    updated_at: datetime = field(default_factory=datetime.now)

    def get_profession_name(self) -> str:
        """获取职业名称"""
        profession_names = {
            "alchemist": "炼丹师",
            "blacksmith": "炼器师",
            "formation_master": "阵法师",
            "talisman_master": "符箓师"
        }
        return profession_names.get(self.profession_type, "未知职业")

    def get_rank_name(self) -> str:
        """获取品级名称"""
        rank_names = {
            1: "一品",
            2: "二品",
            3: "三品",
            4: "四品",
            5: "五品",
            6: "六品",
            7: "七品"
        }
        return rank_names.get(self.rank, "一品")

    def get_full_title(self) -> str:
        """获取完整头衔"""
        return f"{self.get_rank_name()}{self.get_profession_name()}"

    def get_level_color(self) -> str:
        """获取品级颜色"""
        rank_colors = {
            1: "⚪",  # 白色
            2: "🟢",  # 绿色
            3: "🔵",  # 蓝色
            4: "🟣",  # 紫色
            5: "🟠",  # 橙色
            6: "🔴",  # 红色
            7: "🟡"   # 金色
        }
        return rank_colors.get(self.rank, "⚪")

    def get_success_rate(self) -> float:
        """获取实际成功率（基础成功率+加成）"""
        base_rates = {
            1: 0.6,   # 一品60%
            2: 0.65,  # 二品65%
            3: 0.7,   # 三品70%
            4: 0.75,  # 四品75%
            5: 0.8,   # 五品80%
            6: 0.85,  # 六品85%
            7: 0.9    # 七品90%
        }
        base_rate = base_rates.get(self.rank, 0.6)
        return min(0.95, base_rate + self.success_rate_bonus)  # 最高95%

    def get_experience_to_next_level(self) -> int:
        """获取升级所需经验"""
        # 品级越高，升级所需经验越多
        base_exp = 100 * (self.rank ** 2)
        return base_exp * self.level

    def add_experience(self, exp: int) -> bool:
        """添加经验，检查是否升级"""
        self.experience += exp
        self.updated_at = datetime.now()

        # 检查是否可以升级
        exp_needed = self.get_experience_to_next_level()
        if self.experience >= exp_needed:
            self.level += 1
            self.skill_points += 1  # 升级获得技能点
            self.experience -= exp_needed
            return True
        return False

    def check_rank_upgrade(self) -> bool:
        """检查是否可以升品"""
        # 6级以上才能升品
        if self.level >= 10 and self.rank < 7:
            # 升品需要声望和等级
            reputation_needed = self.rank * 1000
            if self.reputation >= reputation_needed:
                return True
        return False

    def upgrade_rank(self) -> bool:
        """升级品级"""
        if self.check_rank_upgrade():
            self.rank += 1
            self.level = 1  # 重置等级
            self.experience = 0
            self.updated_at = datetime.now()
            return True
        return False

    def get_display_info(self) -> str:
        """获取职业显示信息"""
        success_rate = self.get_success_rate() * 100

        lines = [
            f"{self.get_level_color()} {self.get_full_title()}",
            f"📊 等级：Lv.{self.level}",
            f"⭐ 品级：{self.rank}品",
            f"📈 经验：{self.experience}/{self.get_experience_to_next_level()}",
            f"🎯 成功率：{success_rate:.1f}%",
            f"🏆 声望：{self.reputation}",
            f"🎁 技能点：{self.skill_points}",
            "",
            f"📊 制作统计：",
            f"   总制作：{self.total_creations}",
            f"   成功率：{(self.successful_creations/max(1, self.total_creations)*100):.1f}%",
            f"   高品质率：{(self.high_quality_creations/max(1, self.total_creations)*100):.1f}%"
        ]

        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典用于数据库存储"""
        return {
            "user_id": self.user_id,
            "profession_type": self.profession_type,
            "rank": self.rank,
            "experience": self.experience,
            "level": self.level,
            "skill_points": self.skill_points,
            "reputation": self.reputation,
            "achievements": json.dumps(self.achievements),
            "completed_tasks": self.completed_tasks,
            "success_rate_bonus": self.success_rate_bonus,
            "quality_bonus": self.quality_bonus,
            "total_creations": self.total_creations,
            "successful_creations": self.successful_creations,
            "high_quality_creations": self.high_quality_creations,
            "created_at": self.created_at.isoformat(),
            "last_practice_at": self.last_practice_at.isoformat() if self.last_practice_at else None,
            "updated_at": self.updated_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Profession':
        """从字典创建对象"""
        # 处理datetime
        if data.get("created_at"):
            if isinstance(data["created_at"], str):
                data["created_at"] = datetime.fromisoformat(data["created_at"])
        if data.get("last_practice_at"):
            if isinstance(data["last_practice_at"], str):
                data["last_practice_at"] = datetime.fromisoformat(data["last_practice_at"])
        if data.get("updated_at"):
            if isinstance(data["updated_at"], str):
                data["updated_at"] = datetime.fromisoformat(data["updated_at"])

        # 处理JSON字段
        if data.get("achievements"):
            if isinstance(data["achievements"], str):
                data["achievements"] = json.loads(data["achievements"])
        else:
            data["achievements"] = []

        return cls(**data)


@dataclass
class ProfessionSkill:
    """职业技能数据模型"""

    # 基础信息
    id: Optional[str] = None
    profession_type: str = ""  # 所属职业
    skill_name: str = ""  # 技能名称
    skill_type: str = ""  # 技能类型: passive/active

    # 技能属性
    max_level: int = 10  # 最大等级
    current_level: int = 0  # 当前等级
    required_rank: int = 1  # 需要品级
    cost_points: int = 1  # 学习所需技能点

    # 效果描述
    description: str = ""  # 技能描述
    effects: Dict[str, float] = field(default_factory=dict)  # 技能效果

    # 学习状态
    is_learned: bool = False  # 是否已学习
    learned_at: Optional[datetime] = None  # 学习时间

    def can_learn(self, profession: Profession) -> bool:
        """检查是否可以学习"""
        if not is_learned and profession.rank >= self.required_rank:
            if profession.skill_points >= self.cost_points:
                return True
        return False

    def learn(self, profession: Profession) -> bool:
        """学习技能"""
        if self.can_learn(profession):
            profession.skill_points -= self.cost_points
            self.is_learned = True
            self.learned_at = datetime.now()
            return True
        return False

    def get_current_effect(self) -> Dict[str, float]:
        """获取当前等级效果"""
        if not self.is_learned:
            return {}

        current_effects = {}
        for effect_name, base_value in self.effects.items():
            # 效果值 = 基础值 * (当前等级 / 最大等级)
            current_effects[effect_name] = base_value * (self.current_level / self.max_level)

        return current_effects


@dataclass
class ProfessionTask:
    """职业任务数据模型"""

    # 基础信息
    id: Optional[str] = None
    task_name: str = ""
    profession_type: str = ""
    task_type: str = ""  # 任务类型: creation/exploration/knowledge

    # 任务要求
    target_count: int = 1  # 目标数量
    current_count: int = 0  # 当前进度
    difficulty: int = 1  # 难度 1-5

    # 奖励
    experience_reward: int = 0  # 经验奖励
    reputation_reward: int = 0  # 声望奖励
    item_rewards: List[str] = field(default_factory=list)  # 物品奖励

    # 任务状态
    is_completed: bool = False
    is_accepted: bool = False
    accepted_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def get_progress(self) -> float:
        """获取任务进度百分比"""
        if self.target_count <= 0:
            return 100.0
        return min(100.0, (self.current_count / self.target_count) * 100)

    def update_progress(self, count: int = 1) -> bool:
        """更新任务进度"""
        if not self.is_completed and self.is_accepted:
            self.current_count = min(self.current_count + count, self.target_count)
            if self.current_count >= self.target_count:
                self.is_completed = True
                self.completed_at = datetime.now()
                return True
        return False