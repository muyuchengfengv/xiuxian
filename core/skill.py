"""
技能系统
负责技能的查询、解锁、使用等功能
"""

import random
from typing import Dict, List, Optional
from datetime import datetime
from astrbot.api import logger

from .database import DatabaseManager
from .player import PlayerManager
from ..models.skill_model import Skill
from ..utils import XiuxianException


class SkillError(XiuxianException):
    """技能相关异常"""
    pass


class SkillNotFoundError(SkillError):
    """技能不存在异常"""
    pass


class SkillNotUnlockedError(SkillError):
    """技能未解锁异常"""
    pass


class InsufficientMPError(SkillError):
    """法力值不足异常"""
    pass


class SkillSystem:
    """技能系统类"""

    def __init__(self, db: DatabaseManager, player_mgr: PlayerManager):
        """
        初始化技能系统

        Args:
            db: 数据库管理器
            player_mgr: 玩家管理器
        """
        self.db = db
        self.player_mgr = player_mgr

    async def get_player_skills(self, user_id: str) -> List[Skill]:
        """
        获取玩家的所有技能

        Args:
            user_id: 用户ID

        Returns:
            技能列表
        """
        results = await self.db.fetchall(
            'SELECT * FROM skills WHERE user_id = ? ORDER BY skill_type, level DESC',
            (user_id,)
        )

        skills = []
        for result in results:
            skill_data = dict(result)
            skill = Skill.from_dict(skill_data)
            skills.append(skill)

        return skills

    async def check_and_unlock_skills(self, user_id: str, method_id: str, proficiency: int) -> List[str]:
        """
        检查并解锁功法技能

        Args:
            user_id: 用户ID
            method_id: 功法ID
            proficiency: 当前熟练度

        Returns:
            解锁的技能名称列表
        """
        # 查询此功法关联的技能
        method_skills = await self.db.fetchall(
            'SELECT * FROM method_skills WHERE method_id = ? AND unlock_proficiency <= ?',
            (method_id, proficiency)
        )

        unlocked_skills = []

        for method_skill in method_skills:
            skill_name = method_skill['skill_name']

            # 检查玩家是否已拥有此技能
            existing = await self.db.fetchone(
                'SELECT * FROM skills WHERE user_id = ? AND skill_name = ?',
                (user_id, skill_name)
            )

            if not existing:
                # 创建新技能
                await self.db.execute(
                    """
                    INSERT INTO skills (user_id, skill_name, skill_type, element,
                                       base_damage, mp_cost, cooldown, effect_description)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (user_id, skill_name, method_skill['skill_type'],
                     method_skill['element'], method_skill['base_damage'],
                     method_skill['mp_cost'], method_skill['cooldown'],
                     method_skill['effect_description'])
                )

                unlocked_skills.append(skill_name)
                logger.info(f'玩家 {user_id} 解锁技能: {skill_name}')

        return unlocked_skills

    async def use_skill(self, user_id: str, skill_name: str) -> Dict:
        """
        使用技能

        Args:
            user_id: 用户ID
            skill_name: 技能名称

        Returns:
            使用结果字典

        Raises:
            SkillNotFoundError: 技能不存在
            InsufficientMPError: 法力值不足
        """
        # 获取玩家信息
        player = await self.player_mgr.get_player_or_error(user_id)

        # 获取技能
        skill_data = await self.db.fetchone(
            'SELECT * FROM skills WHERE user_id = ? AND skill_name = ?',
            (user_id, skill_name)
        )

        if not skill_data:
            raise SkillNotFoundError(f'您还未学习技能：{skill_name}')

        skill = Skill.from_dict(dict(skill_data))

        # 检查法力值
        mp_cost = skill.get_mp_cost_by_level()
        if not skill.can_use(player.mp):
            raise InsufficientMPError(f'法力值不足！需要 {mp_cost} MP')

        # 消耗法力值
        player.mp -= mp_cost
        await self.player_mgr.update_player(player)

        # 计算技能伤害
        damage = skill.get_actual_damage(player.attack)

        # 增加技能熟练度
        can_level_up = skill.gain_proficiency(1)
        if can_level_up:
            skill.level_up()
            await self._update_skill(skill)

        return {
            'success': True,
            'skill_name': skill_name,
            'damage': damage,
            'mp_cost': mp_cost,
            'remaining_mp': player.mp,
            'leveled_up': can_level_up
        }

    async def _update_skill(self, skill: Skill):
        """更新技能信息"""
        await self.db.execute(
            """
            UPDATE skills SET level = ?, proficiency = ?, base_damage = ?
            WHERE id = ?
            """,
            (skill.level, skill.proficiency, skill.base_damage, skill.id)
        )
