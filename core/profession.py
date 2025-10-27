"""
职业系统核心管理器
负责职业的学习、升级、经验管理等通用功能
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from astrbot.api import logger

from ..models.profession_model import Profession
from ..core.database import DatabaseManager
from ..core.player import PlayerManager
from ..utils.exceptions import PlayerNotFoundError


class ProfessionError(Exception):
    """职业系统基础异常"""
    pass


class AlreadyLearnedError(ProfessionError):
    """已经学习该职业"""
    pass


class InsufficientLevelError(ProfessionError):
    """等级不足"""
    pass


class InsufficientReputationError(ProfessionError):
    """声望不足"""
    pass


class ProfessionNotFoundError(ProfessionError):
    """职业未找到"""
    pass


class ProfessionManager:
    """职业管理器 - 管理所有职业通用功能"""

    # 职业类型配置
    PROFESSION_TYPES = {
        "alchemist": {
            "name": "炼丹师",
            "description": "精通炼制各类丹药的修仙者",
            "max_rank": 7,
            "min_realm": "炼气期"
        },
        "blacksmith": {
            "name": "炼器师",
            "description": "精通炼制各类法宝装备的修仙者",
            "max_rank": 7,
            "min_realm": "炼气期"
        },
        "formation_master": {
            "name": "阵法师",
            "description": "精通布置和破解各类阵法的修仙者",
            "max_rank": 5,
            "min_realm": "筑基期"
        },
        "talisman_master": {
            "name": "符箓师",
            "description": "精通制作和使用各类符箓的修仙者",
            "max_rank": 4,
            "min_realm": "炼气期"
        }
    }

    # 品级对应的境界要求
    RANK_REQUIREMENTS = {
        1: "炼气期",
        2: "筑基期",
        3: "金丹期",
        4: "元婴期",
        5: "化神期",
        6: "炼虚期",
        7: "合体期"
    }

    def __init__(self, db: DatabaseManager, player_mgr: PlayerManager):
        """
        初始化职业管理器

        Args:
            db: 数据库管理器
            player_mgr: 玩家管理器
        """
        self.db = db
        self.player_mgr = player_mgr

    async def learn_profession(
        self,
        user_id: str,
        profession_type: str
    ) -> Profession:
        """
        学习新职业

        Args:
            user_id: 玩家ID
            profession_type: 职业类型 (alchemist/blacksmith/formation_master/talisman_master)

        Returns:
            Profession: 职业对象

        Raises:
            PlayerNotFoundError: 玩家不存在
            AlreadyLearnedError: 已经学习该职业
            ValueError: 无效的职业类型
        """
        # 检查玩家是否存在
        player = await self.player_mgr.get_player_or_error(user_id)

        # 验证职业类型
        if profession_type not in self.PROFESSION_TYPES:
            raise ValueError(f"无效的职业类型: {profession_type}")

        # 检查是否已经学习该职业
        existing = await self.get_profession(user_id, profession_type)
        if existing:
            raise AlreadyLearnedError(f"已经学习了{self.PROFESSION_TYPES[profession_type]['name']}")

        # 创建新职业
        profession = Profession(
            user_id=user_id,
            profession_type=profession_type,
            rank=1,
            experience=0,
            level=1,
            reputation=0,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        # 保存到数据库
        await self.db.execute(
            """
            INSERT INTO professions (
                user_id, profession_type, rank, experience,
                reputation, reputation_level, success_rate_bonus, quality_bonus,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                profession.user_id,
                profession.profession_type,
                profession.rank,
                profession.experience,
                profession.reputation,
                "无名小卒",
                profession.success_rate_bonus,
                profession.quality_bonus,
                profession.created_at.isoformat(),
                profession.updated_at.isoformat()
            )
        )

        logger.info(f"玩家 {user_id} 学习了职业: {profession_type}")

        return profession

    async def get_profession(
        self,
        user_id: str,
        profession_type: str
    ) -> Optional[Profession]:
        """
        获取玩家的指定职业

        Args:
            user_id: 玩家ID
            profession_type: 职业类型

        Returns:
            Optional[Profession]: 职业对象,不存在则返回None
        """
        row = await self.db.fetchone(
            """
            SELECT * FROM professions
            WHERE user_id = ? AND profession_type = ?
            """,
            (user_id, profession_type)
        )

        if not row:
            return None

        # 转换为字典
        profession_data = dict(row)

        # 创建Profession对象
        profession = Profession(
            user_id=profession_data['user_id'],
            profession_type=profession_data['profession_type'],
            rank=profession_data['rank'],
            experience=profession_data['experience'],
            level=1,  # 从数据库读取的时候没有level字段,这里先设为1
            reputation=profession_data['reputation'],
            success_rate_bonus=profession_data['success_rate_bonus'] / 100.0,
            quality_bonus=profession_data['quality_bonus'] / 100.0,
            created_at=datetime.fromisoformat(profession_data['created_at']) if profession_data['created_at'] else datetime.now(),
            updated_at=datetime.fromisoformat(profession_data['updated_at']) if profession_data['updated_at'] else datetime.now()
        )

        return profession

    async def get_all_professions(self, user_id: str) -> List[Profession]:
        """
        获取玩家的所有职业

        Args:
            user_id: 玩家ID

        Returns:
            List[Profession]: 职业列表
        """
        rows = await self.db.fetchall(
            """
            SELECT * FROM professions
            WHERE user_id = ?
            ORDER BY rank DESC, experience DESC
            """,
            (user_id,)
        )

        professions = []
        for row in rows:
            profession_data = dict(row)
            profession = Profession(
                user_id=profession_data['user_id'],
                profession_type=profession_data['profession_type'],
                rank=profession_data['rank'],
                experience=profession_data['experience'],
                level=1,
                reputation=profession_data['reputation'],
                success_rate_bonus=profession_data['success_rate_bonus'] / 100.0,
                quality_bonus=profession_data['quality_bonus'] / 100.0,
                created_at=datetime.fromisoformat(profession_data['created_at']) if profession_data['created_at'] else datetime.now(),
                updated_at=datetime.fromisoformat(profession_data['updated_at']) if profession_data['updated_at'] else datetime.now()
            )
            professions.append(profession)

        return professions

    async def add_experience(
        self,
        user_id: str,
        profession_type: str,
        exp: int
    ) -> Dict[str, Any]:
        """
        增加职业经验

        Args:
            user_id: 玩家ID
            profession_type: 职业类型
            exp: 经验值

        Returns:
            Dict: 包含升级信息的字典

        Raises:
            ProfessionNotFoundError: 职业不存在
        """
        profession = await self.get_profession(user_id, profession_type)
        if not profession:
            raise ProfessionNotFoundError(f"未学习{profession_type}职业")

        # 添加经验
        leveled_up = profession.add_experience(exp)

        # 更新数据库
        await self.db.execute(
            """
            UPDATE professions
            SET experience = ?, updated_at = ?
            WHERE user_id = ? AND profession_type = ?
            """,
            (
                profession.experience,
                profession.updated_at.isoformat(),
                user_id,
                profession_type
            )
        )

        result = {
            'experience_gained': exp,
            'total_experience': profession.experience,
            'leveled_up': leveled_up,
            'current_level': profession.level
        }

        if leveled_up:
            logger.info(f"玩家 {user_id} 的职业 {profession_type} 升级到 Lv.{profession.level}")

        return result

    async def add_reputation(
        self,
        user_id: str,
        profession_type: str,
        reputation: int
    ) -> int:
        """
        增加职业声望

        Args:
            user_id: 玩家ID
            profession_type: 职业类型
            reputation: 声望值

        Returns:
            int: 新的总声望值

        Raises:
            ProfessionNotFoundError: 职业不存在
        """
        profession = await self.get_profession(user_id, profession_type)
        if not profession:
            raise ProfessionNotFoundError(f"未学习{profession_type}职业")

        old_level = profession.get_reputation_level()
        profession.reputation += reputation
        profession.updated_at = datetime.now()
        new_level = profession.get_reputation_level()

        # 更新数据库
        await self.db.execute(
            """
            UPDATE professions
            SET reputation = ?, reputation_level = ?, updated_at = ?
            WHERE user_id = ? AND profession_type = ?
            """,
            (
                profession.reputation,
                new_level,
                profession.updated_at.isoformat(),
                user_id,
                profession_type
            )
        )

        logger.info(f"玩家 {user_id} 的职业 {profession_type} 声望增加 +{reputation}")

        # 如果声望等级提升,记录日志
        if old_level != new_level:
            logger.info(f"玩家 {user_id} 的 {profession_type} 声望等级提升: {old_level} → {new_level}")

        return profession.reputation

    async def upgrade_rank(
        self,
        user_id: str,
        profession_type: str
    ) -> Profession:
        """
        升级职业品级

        Args:
            user_id: 玩家ID
            profession_type: 职业类型

        Returns:
            Profession: 升级后的职业对象

        Raises:
            ProfessionNotFoundError: 职业不存在
            InsufficientLevelError: 等级不足
            InsufficientReputationError: 声望不足
        """
        profession = await self.get_profession(user_id, profession_type)
        if not profession:
            raise ProfessionNotFoundError(f"未学习{profession_type}职业")

        # 检查是否可以升品
        if not profession.check_rank_upgrade():
            if profession.level < 10:
                raise InsufficientLevelError(f"等级不足,需要Lv.10以上")

            reputation_needed = profession.rank * 1000
            if profession.reputation < reputation_needed:
                raise InsufficientReputationError(f"声望不足,需要{reputation_needed}声望")

        # 升品
        if profession.upgrade_rank():
            # 更新数据库
            await self.db.execute(
                """
                UPDATE professions
                SET rank = ?, level = ?, experience = ?, updated_at = ?
                WHERE user_id = ? AND profession_type = ?
                """,
                (
                    profession.rank,
                    profession.level,
                    profession.experience,
                    profession.updated_at.isoformat(),
                    user_id,
                    profession_type
                )
            )

            logger.info(f"玩家 {user_id} 的职业 {profession_type} 升级到 {profession.rank}品")

        return profession

    async def format_profession_list(self, user_id: str) -> str:
        """
        格式化职业列表显示

        Args:
            user_id: 玩家ID

        Returns:
            str: 格式化的职业列表文本
        """
        professions = await self.get_all_professions(user_id)

        if not professions:
            return (
                "📜 职业信息\n"
                "─" * 40 + "\n\n"
                "您还没有学习任何职业\n\n"
                "💡 使用 /学习职业 [职业类型] 学习新职业\n"
                "💡 可用职业：炼丹师、炼器师、阵法师、符箓师"
            )

        lines = ["📜 职业信息", "─" * 40, ""]

        for i, profession in enumerate(professions, 1):
            lines.append(f"{i}. {profession.get_display_info()}")
            lines.append("")

        lines.extend([
            "💡 使用 /职业详情 [编号] 查看详细信息",
            "💡 使用 /学习职业 学习新职业"
        ])

        return "\n".join(lines)

    async def get_profession_config(self, profession_type: str) -> Dict[str, Any]:
        """
        获取职业配置信息

        Args:
            profession_type: 职业类型

        Returns:
            Dict: 职业配置
        """
        return self.PROFESSION_TYPES.get(profession_type, {})
