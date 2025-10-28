"""
修炼系统
负责玩家修炼、修为获取、冷却管理、闭关修炼
"""

from datetime import datetime, timedelta
from typing import Dict, Optional
from astrbot.api import logger

from .database import DatabaseManager
from .player import PlayerManager
from ..models.player_model import Player
from ..utils import (
    CombatCalculator,
    CooldownNotReadyError,
    DEFAULT_CULTIVATION_COOLDOWN,
    get_next_realm,
    get_cultivation_required
)


class RetreatError(Exception):
    """闭关相关错误"""
    pass


class AlreadyInRetreatError(RetreatError):
    """已经在闭关中"""
    pass


class NotInRetreatError(RetreatError):
    """不在闭关中"""
    pass


class RetreatNotFinishedError(RetreatError):
    """闭关未结束"""
    pass


class CultivationSystem:
    """修炼系统类"""

    def __init__(self, db: DatabaseManager, player_mgr: PlayerManager):
        """
        初始化修炼系统

        Args:
            db: 数据库管理器
            player_mgr: 玩家管理器
        """
        self.db = db
        self.player_mgr = player_mgr
        self.cooldown_seconds = DEFAULT_CULTIVATION_COOLDOWN  # 默认1小时
        self.sect_sys = None  # 宗门系统（可选）

    def set_cooldown(self, seconds: int):
        """
        设置修炼冷却时间

        Args:
            seconds: 冷却秒数
        """
        self.cooldown_seconds = seconds
        logger.info(f"修炼冷却时间设置为 {seconds} 秒")

    def set_sect_system(self, sect_sys):
        """
        设置宗门系统（用于加成计算）

        Args:
            sect_sys: 宗门系统实例
        """
        self.sect_sys = sect_sys

    async def cultivate(self, user_id: str) -> Dict:
        """
        执行修炼

        Args:
            user_id: 用户ID

        Returns:
            修炼结果字典 {
                'cultivation_gained': 获得的修为,
                'total_cultivation': 总修为,
                'can_breakthrough': 是否可以突破,
                'next_realm': 下一境界名称,
                'required_cultivation': 所需修为
            }

        Raises:
            PlayerNotFoundError: 玩家不存在
            CooldownNotReadyError: 冷却未完成
        """
        # 1. 获取玩家信息
        player = await self.player_mgr.get_player_or_error(user_id)

        # 2. 检查冷却时间
        remaining = self.check_cooldown(player)
        if remaining > 0:
            raise CooldownNotReadyError("修炼", remaining)

        # 3. 计算修为获取
        cultivation_gained = self.calculate_cultivation_gain(player)

        # 3.5 应用宗门加成
        sect_bonus_rate = 0.0
        if self.sect_sys:
            try:
                cultivation_gained, sect_bonus_rate = await self.sect_sys.apply_sect_bonus(
                    user_id, "cultivation_bonus", cultivation_gained
                )
            except Exception as e:
                # 如果宗门加成失败，记录日志但不影响修炼
                logger.warning(f"应用宗门加成失败: {e}")

        # 4. 更新玩家数据
        player.cultivation += int(cultivation_gained)
        player.last_cultivation = datetime.now()

        # 5. 保存到数据库
        await self.player_mgr.update_player(player)

        # 6. 检查是否可以突破
        can_breakthrough, next_realm_info = self._check_breakthrough_available(player)

        logger.info(
            f"玩家 {player.name} 修炼完成: "
            f"获得修为 {int(cultivation_gained)} (宗门加成: {sect_bonus_rate*100:.0f}%), "
            f"总修为 {player.cultivation}"
        )

        return {
            'cultivation_gained': int(cultivation_gained),
            'sect_bonus_rate': sect_bonus_rate,
            'total_cultivation': player.cultivation,
            'can_breakthrough': can_breakthrough,
            'next_realm': next_realm_info['name'] if can_breakthrough else None,
            'required_cultivation': next_realm_info['required'] if can_breakthrough else None
        }

    def check_cooldown(self, player: Player) -> int:
        """
        检查修炼冷却时间

        Args:
            player: 玩家对象

        Returns:
            剩余冷却秒数，0表示可以修炼
        """
        return player.get_cultivation_cooldown_remaining(self.cooldown_seconds)

    def calculate_cultivation_gain(self, player: Player) -> int:
        """
        计算修为获取量

        使用CombatCalculator的calculate_cultivation_gain方法

        Args:
            player: 玩家对象

        Returns:
            获得的修为值
        """
        return CombatCalculator.calculate_cultivation_gain(player)

    def _check_breakthrough_available(self, player: Player) -> tuple[bool, Dict]:
        """
        检查是否可以突破

        Args:
            player: 玩家对象

        Returns:
            (是否可以突破, 下一境界信息字典)
        """
        # 获取下一个境界和等级
        next_realm, next_level = get_next_realm(player.realm, player.realm_level)

        # 如果已经是最高境界，无法突破
        if next_realm == player.realm and next_level == player.realm_level:
            return False, {'name': None, 'required': None}

        # 获取下一境界所需修为
        required_cultivation = get_cultivation_required(next_realm, next_level)

        # 检查修为是否足够
        can_breakthrough = player.cultivation >= required_cultivation

        realm_name = f"{next_realm}" if next_level == 1 else f"{player.realm}"
        from ..utils.constants import REALM_LEVEL_NAMES
        level_name = REALM_LEVEL_NAMES[next_level - 1]
        full_name = f"{realm_name}{level_name}"

        return can_breakthrough, {
            'name': full_name,
            'required': required_cultivation
        }

    async def get_cultivation_info(self, user_id: str) -> Dict:
        """
        获取修炼信息

        Args:
            user_id: 用户ID

        Returns:
            修炼信息字典
        """
        player = await self.player_mgr.get_player_or_error(user_id)

        # 检查冷却
        cooldown_remaining = self.check_cooldown(player)

        # 检查是否可以突破
        can_breakthrough, next_realm_info = self._check_breakthrough_available(player)

        # 计算下次修炼可获得的修为
        next_gain = self.calculate_cultivation_gain(player)

        return {
            'player': player,
            'cooldown_remaining': cooldown_remaining,
            'can_cultivate': cooldown_remaining == 0,
            'next_cultivation_gain': next_gain,
            'can_breakthrough': can_breakthrough,
            'next_realm': next_realm_info
        }

    # ========== 闭关修炼系统 ==========

    async def start_retreat(self, user_id: str, duration_hours: int) -> Dict:
        """
        开始闭关修炼

        Args:
            user_id: 用户ID
            duration_hours: 闭关时长（小时）

        Returns:
            闭关信息字典 {
                'duration_hours': 闭关时长,
                'start_time': 开始时间,
                'end_time': 结束时间,
                'estimated_reward': 预计获得修为
            }

        Raises:
            PlayerNotFoundError: 玩家不存在
            AlreadyInRetreatError: 已经在闭关中
            ValueError: 闭关时长无效
        """
        # 1. 获取玩家信息
        player = await self.player_mgr.get_player_or_error(user_id)

        # 2. 检查是否已经在闭关中
        if player.in_retreat:
            raise AlreadyInRetreatError("道友正在闭关中，不可重复闭关！")

        # 3. 验证闭关时长
        if duration_hours < 1:
            raise ValueError("闭关时长至少为1小时")
        if duration_hours > 168:  # 最多7天
            raise ValueError("单次闭关时长不能超过168小时（7天）")

        # 4. 计算预计获得修为
        estimated_reward = self.calculate_retreat_reward(player, duration_hours)

        # 5. 更新玩家状态
        player.in_retreat = True
        player.retreat_start = datetime.now()
        player.retreat_duration = duration_hours

        # 6. 保存到数据库
        await self.player_mgr.update_player(player)

        # 7. 计算结束时间
        end_time = player.retreat_start + timedelta(hours=duration_hours)

        logger.info(
            f"玩家 {player.name} 开始闭关: "
            f"时长 {duration_hours} 小时, 预计修为 {estimated_reward}"
        )

        return {
            'duration_hours': duration_hours,
            'start_time': player.retreat_start,
            'end_time': end_time,
            'estimated_reward': estimated_reward
        }

    async def end_retreat(self, user_id: str, force: bool = False) -> Dict:
        """
        结束闭关修炼（出关）

        Args:
            user_id: 用户ID
            force: 是否强制出关（未到时间也可出关，但奖励减半）

        Returns:
            出关结果字典 {
                'cultivation_gained': 获得的修为,
                'total_cultivation': 总修为,
                'actual_duration': 实际闭关时长（小时）,
                'is_early': 是否提前出关,
                'penalty_applied': 是否应用了惩罚,
                'can_breakthrough': 是否可以突破,
                'next_realm': 下一境界名称,
                'required_cultivation': 所需修为
            }

        Raises:
            PlayerNotFoundError: 玩家不存在
            NotInRetreatError: 不在闭关中
            RetreatNotFinishedError: 闭关未结束（非强制出关时）
        """
        # 1. 获取玩家信息
        player = await self.player_mgr.get_player_or_error(user_id)

        # 2. 检查是否在闭关中
        if not player.in_retreat:
            raise NotInRetreatError("道友当前不在闭关中！")

        # 3. 计算实际闭关时长
        now = datetime.now()
        actual_duration = (now - player.retreat_start).total_seconds() / 3600  # 转为小时

        # 4. 检查是否到时间
        planned_duration = player.retreat_duration
        is_early = actual_duration < planned_duration
        penalty_applied = False

        if is_early and not force:
            remaining_hours = planned_duration - actual_duration
            raise RetreatNotFinishedError(
                f"闭关尚未结束！还需 {remaining_hours:.1f} 小时\n"
                f"💡 使用 /出关 强制 可以提前出关（修为减半）"
            )

        # 5. 计算修为奖励
        # 使用实际时长计算，但不超过计划时长
        effective_duration = min(actual_duration, planned_duration)
        cultivation_gained = self.calculate_retreat_reward(player, effective_duration)

        # 6. 如果提前出关，奖励减半
        if is_early and force:
            cultivation_gained = cultivation_gained // 2
            penalty_applied = True
            logger.info(f"玩家 {player.name} 提前出关，修为奖励减半")

        # 7. 更新玩家数据
        player.cultivation += cultivation_gained
        player.in_retreat = False
        player.retreat_start = None
        player.retreat_duration = 0
        player.last_cultivation = now  # 更新最后修炼时间

        # 8. 保存到数据库
        await self.player_mgr.update_player(player)

        # 9. 检查是否可以突破
        can_breakthrough, next_realm_info = self._check_breakthrough_available(player)

        logger.info(
            f"玩家 {player.name} 出关: "
            f"获得修为 {cultivation_gained}, 总修为 {player.cultivation}, "
            f"实际时长 {actual_duration:.1f}h"
        )

        return {
            'cultivation_gained': cultivation_gained,
            'total_cultivation': player.cultivation,
            'actual_duration': actual_duration,
            'planned_duration': planned_duration,
            'is_early': is_early,
            'penalty_applied': penalty_applied,
            'can_breakthrough': can_breakthrough,
            'next_realm': next_realm_info['name'] if can_breakthrough else None,
            'required_cultivation': next_realm_info['required'] if can_breakthrough else None
        }

    def calculate_retreat_reward(self, player: Player, duration_hours: float) -> int:
        """
        计算闭关修为奖励

        奖励计算公式：
        - 基础奖励 = 单次修炼获得 * 时长（小时）* 效率系数
        - 效率系数根据时长递减（避免无限闭关）

        Args:
            player: 玩家对象
            duration_hours: 闭关时长（小时）

        Returns:
            获得的修为值
        """
        # 基础单次修炼获得
        base_gain = CombatCalculator.calculate_cultivation_gain(player)

        # 计算效率系数（时长越长，效率递减）
        # 1-24小时: 100%效率
        # 24-72小时: 90%效率
        # 72-168小时: 80%效率
        if duration_hours <= 24:
            efficiency = 1.0
        elif duration_hours <= 72:
            efficiency = 0.9
        else:
            efficiency = 0.8

        # 计算总奖励
        total_reward = int(base_gain * duration_hours * efficiency)

        # 添加随机波动（±10%）
        import random
        fluctuation = random.uniform(0.9, 1.1)
        total_reward = int(total_reward * fluctuation)

        return max(total_reward, 1)  # 至少获得1点修为

    async def get_retreat_info(self, user_id: str) -> Optional[Dict]:
        """
        获取闭关信息

        Args:
            user_id: 用户ID

        Returns:
            闭关信息字典，如果不在闭关中返回None {
                'in_retreat': 是否在闭关中,
                'start_time': 开始时间,
                'duration_hours': 计划时长,
                'end_time': 结束时间,
                'elapsed_hours': 已经过时长,
                'remaining_hours': 剩余时长,
                'is_finished': 是否已完成,
                'estimated_reward': 预计修为奖励
            }
        """
        player = await self.player_mgr.get_player_or_error(user_id)

        if not player.in_retreat:
            return None

        now = datetime.now()
        elapsed = (now - player.retreat_start).total_seconds() / 3600
        remaining = max(0, player.retreat_duration - elapsed)
        end_time = player.retreat_start + timedelta(hours=player.retreat_duration)
        is_finished = remaining == 0

        # 计算预计奖励
        estimated_reward = self.calculate_retreat_reward(player, player.retreat_duration)

        return {
            'in_retreat': True,
            'start_time': player.retreat_start,
            'duration_hours': player.retreat_duration,
            'end_time': end_time,
            'elapsed_hours': elapsed,
            'remaining_hours': remaining,
            'is_finished': is_finished,
            'estimated_reward': estimated_reward
        }
