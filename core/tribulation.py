"""
天劫系统
负责天劫的创建、执行、奖励发放等功能
"""

import uuid
import random
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from astrbot.api import logger

from .database import DatabaseManager
from .player import PlayerManager
from ..models.tribulation_model import Tribulation
from ..utils.tribulation_constants import (
    TRIBULATION_TYPES, REALM_TRIBULATIONS, DIFFICULTY_MULTIPLIERS,
    TRIBULATION_REWARDS, TRIBULATION_PENALTIES, DAMAGE_REDUCTION_FACTORS,
    WAVE_DAMAGE_INCREASE
)
from ..utils import XiuxianException


class TribulationError(XiuxianException):
    """天劫相关异常"""
    pass


class TribulationNotFoundError(TribulationError):
    """天劫不存在异常"""
    pass


class TribulationInProgressError(TribulationError):
    """天劫进行中异常"""
    pass


class NoTribulationRequiredError(TribulationError):
    """无需渡劫异常"""
    pass


class InsufficientHPError(TribulationError):
    """生命值不足异常"""
    pass


class TribulationSystem:
    """天劫系统类"""

    def __init__(self, db: DatabaseManager, player_mgr: PlayerManager):
        """
        初始化天劫系统

        Args:
            db: 数据库管理器
            player_mgr: 玩家管理器
        """
        self.db = db
        self.player_mgr = player_mgr

    async def check_tribulation_required(self, realm: str) -> bool:
        """
        检查该境界是否需要渡劫

        Args:
            realm: 境界名称

        Returns:
            是否需要渡劫
        """
        config = REALM_TRIBULATIONS.get(realm, {})
        return config.get("has_tribulation", False)

    async def create_tribulation(self, user_id: str, target_realm: str) -> Tribulation:
        """
        创建天劫

        Args:
            user_id: 用户ID
            target_realm: 目标境界

        Returns:
            天劫对象

        Raises:
            NoTribulationRequiredError: 该境界无需渡劫
            TribulationInProgressError: 已有进行中的天劫
        """
        # 检查是否需要渡劫
        if not await self.check_tribulation_required(target_realm):
            raise NoTribulationRequiredError(f"{target_realm} 无需渡劫")

        # 检查是否已有进行中的天劫
        active_tribulation = await self.get_active_tribulation(user_id)
        if active_tribulation:
            raise TribulationInProgressError("已有进行中的天劫，请先完成当前天劫")

        # 获取玩家信息
        player = await self.player_mgr.get_player_or_error(user_id)

        # 获取境界天劫配置
        realm_config = REALM_TRIBULATIONS[target_realm]

        # 随机选择天劫类型
        tribulation_types = realm_config["types"]
        tribulation_type = random.choice(tribulation_types)
        type_config = TRIBULATION_TYPES[tribulation_type]

        # 计算基础伤害
        base_damage = realm_config["base_damage"]
        difficulty = realm_config["difficulty"]
        difficulty_multiplier = DIFFICULTY_MULTIPLIERS[difficulty]
        type_multiplier = type_config["damage_multiplier"]

        damage_per_wave = int(base_damage * difficulty_multiplier * type_multiplier)

        # 计算伤害减免
        damage_reduction = self._calculate_damage_reduction(player)

        # 创建天劫
        tribulation = Tribulation(
            id=str(uuid.uuid4()),
            user_id=user_id,
            tribulation_type=tribulation_type,
            realm=target_realm,
            realm_level=1,
            tribulation_level=realm_config["tribulation_level"],
            difficulty=difficulty,
            total_waves=realm_config["waves"],
            current_wave=0,
            damage_per_wave=damage_per_wave,
            damage_reduction=damage_reduction,
            initial_hp=player.hp,
            current_hp=player.hp
        )

        # 保存天劫
        await self._save_tribulation(tribulation)

        logger.info(f"玩家 {player.name} 触发天劫: {tribulation.get_type_name()} ({target_realm})")

        return tribulation

    async def start_tribulation(self, user_id: str) -> Tribulation:
        """
        开始渡劫

        Args:
            user_id: 用户ID

        Returns:
            天劫对象

        Raises:
            TribulationNotFoundError: 没有待渡的天劫
            InsufficientHPError: 生命值不足
        """
        # 获取待渡的天劫
        tribulation = await self.get_active_tribulation(user_id)
        if not tribulation:
            raise TribulationNotFoundError("没有待渡的天劫")

        # 检查状态
        if tribulation.status != "pending":
            raise TribulationError(f"天劫状态错误: {tribulation.status}")

        # 获取玩家信息
        player = await self.player_mgr.get_player_or_error(user_id)

        # 检查生命值是否充足（至少80%）
        hp_percentage = (player.hp / player.max_hp) * 100
        if hp_percentage < 80:
            raise InsufficientHPError(f"生命值不足，至少需要80%生命值才能渡劫（当前{hp_percentage:.1f}%）")

        # 更新状态
        tribulation.status = "in_progress"
        tribulation.started_at = datetime.now()
        tribulation.initial_hp = player.hp
        tribulation.current_hp = player.hp

        await self._update_tribulation(tribulation)

        logger.info(f"玩家 {player.name} 开始渡劫")

        return tribulation

    async def execute_wave(self, user_id: str) -> Tuple[Tribulation, Dict]:
        """
        执行一波天劫

        Args:
            user_id: 用户ID

        Returns:
            (天劫对象, 渡劫结果)

        Raises:
            TribulationNotFoundError: 没有进行中的天劫
        """
        # 获取进行中的天劫
        tribulation = await self.get_active_tribulation(user_id)
        if not tribulation or tribulation.status != "in_progress":
            raise TribulationNotFoundError("没有进行中的天劫")

        # 获取玩家信息
        player = await self.player_mgr.get_player_or_error(user_id)

        # 增加波数
        tribulation.current_wave += 1
        current_wave = tribulation.current_wave

        # 计算本波伤害
        base_damage = tribulation.damage_per_wave
        wave_multiplier = WAVE_DAMAGE_INCREASE ** (current_wave - 1)
        damage = int(base_damage * wave_multiplier)

        # 应用伤害减免
        actual_damage = int(damage * (1 - tribulation.damage_reduction))

        # 记录渡劫前的生命值
        hp_before = tribulation.current_hp

        # 应用伤害
        tribulation.current_hp = max(0, tribulation.current_hp - actual_damage)
        tribulation.total_damage_taken += actual_damage

        # 记录本波日志
        message = f"第{current_wave}波 {tribulation.get_type_name()}降临，造成 {actual_damage} 点伤害"
        tribulation.add_wave_log(current_wave, actual_damage, hp_before, tribulation.current_hp, message)

        # 检查是否完成所有波数
        completed = current_wave >= tribulation.total_waves

        # 检查是否失败（生命值归零）
        failed = tribulation.current_hp <= 0

        result = {
            "wave": current_wave,
            "damage": actual_damage,
            "hp_before": hp_before,
            "hp_after": tribulation.current_hp,
            "hp_percentage": tribulation.get_hp_percentage(),
            "completed": completed,
            "failed": failed,
            "message": message
        }

        # 如果完成或失败，结算天劫
        if completed or failed:
            await self._complete_tribulation(tribulation, player, not failed)
            result["final_result"] = "success" if not failed else "failed"
        else:
            await self._update_tribulation(tribulation)

        logger.info(f"玩家 {player.name} 渡劫第{current_wave}波: 伤害{actual_damage}, 剩余HP{tribulation.current_hp}")

        return tribulation, result

    async def _complete_tribulation(self, tribulation: Tribulation, player, success: bool):
        """
        完成天劫

        Args:
            tribulation: 天劫对象
            player: 玩家对象
            success: 是否成功
        """
        tribulation.status = "success" if success else "failed"
        tribulation.success = success
        tribulation.completed_at = datetime.now()

        if success:
            # 渡劫成功，发放奖励
            rewards = await self._grant_rewards(player, tribulation)
            tribulation.rewards = rewards
            logger.info(f"玩家 {player.name} 渡劫成功！")
        else:
            # 渡劫失败，施加惩罚
            penalties = await self._apply_penalties(player, tribulation)
            tribulation.penalties = penalties
            logger.info(f"玩家 {player.name} 渡劫失败！")

        await self._update_tribulation(tribulation)

    async def _grant_rewards(self, player, tribulation: Tribulation) -> Dict:
        """发放渡劫奖励"""
        rewards = {}

        # 修为提升
        cultivation_boost = int(player.cultivation * TRIBULATION_REWARDS["cultivation_boost"])
        player.cultivation += cultivation_boost
        rewards["cultivation_boost"] = cultivation_boost

        # 属性提升（随机选择一个属性）
        attribute_boost = TRIBULATION_REWARDS["attribute_boost"]
        boost_attributes = random.choice(["attack", "defense", "max_hp", "max_mp"])

        if boost_attributes == "attack":
            player.attack += attribute_boost
        elif boost_attributes == "defense":
            player.defense += attribute_boost
        elif boost_attributes == "max_hp":
            player.max_hp += attribute_boost * 10
            player.hp += attribute_boost * 10
        elif boost_attributes == "max_mp":
            player.max_mp += attribute_boost * 10
            player.mp += attribute_boost * 10

        rewards["attribute_boost"] = {boost_attributes: attribute_boost}

        # 恢复生命值到满
        player.hp = player.max_hp
        rewards["hp_restored"] = True

        # 保存玩家数据
        await self.player_mgr.update_player(player)

        return rewards

    async def _apply_penalties(self, player, tribulation: Tribulation) -> Dict:
        """施加渡劫失败惩罚"""
        penalties = {}

        # 修为损失
        cultivation_loss = int(player.cultivation * TRIBULATION_PENALTIES["cultivation_loss"])
        player.cultivation = max(0, player.cultivation - cultivation_loss)
        penalties["cultivation_loss"] = cultivation_loss

        # 生命值恢复到10%
        player.hp = int(player.max_hp * 0.1)
        penalties["hp_reduced"] = True

        # 保存玩家数据
        await self.player_mgr.update_player(player)

        return penalties

    def _calculate_damage_reduction(self, player) -> float:
        """
        计算伤害减免

        Args:
            player: 玩家对象

        Returns:
            伤害减免率（0-1之间）
        """
        reduction = 0.0

        # 防御力加成
        reduction += player.defense * DAMAGE_REDUCTION_FACTORS["defense"]

        # 灵根加成（假设灵根品质影响减免）
        # TODO: 根据实际灵根系统调整
        reduction += DAMAGE_REDUCTION_FACTORS["spirit_root"]

        # 限制最大减免为75%
        return min(0.75, reduction)

    async def get_active_tribulation(self, user_id: str) -> Optional[Tribulation]:
        """获取进行中或待开始的天劫"""
        await self._ensure_tribulations_table()

        result = await self.db.fetchone(
            "SELECT * FROM tribulations WHERE user_id = ? AND status IN ('pending', 'in_progress') ORDER BY created_at DESC LIMIT 1",
            (user_id,)
        )

        if result is None:
            return None

        tribulation_data = dict(result)
        return Tribulation.from_dict(tribulation_data)

    async def get_tribulation_history(self, user_id: str, limit: int = 10) -> List[Tribulation]:
        """获取天劫历史"""
        await self._ensure_tribulations_table()

        results = await self.db.fetchall(
            "SELECT * FROM tribulations WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit)
        )

        tribulations = []
        for result in results:
            tribulation_data = dict(result)
            tribulation = Tribulation.from_dict(tribulation_data)
            tribulations.append(tribulation)

        return tribulations

    async def get_tribulation_stats(self, user_id: str) -> Dict:
        """获取天劫统计信息"""
        history = await self.get_tribulation_history(user_id, 100)

        total = len(history)
        success_count = sum(1 for t in history if t.success)
        failed_count = sum(1 for t in history if not t.success and t.is_completed())

        success_rate = (success_count / total * 100) if total > 0 else 0

        # 统计各类型天劫
        type_stats = {}
        for t in history:
            if t.tribulation_type not in type_stats:
                type_stats[t.tribulation_type] = {"total": 0, "success": 0}
            type_stats[t.tribulation_type]["total"] += 1
            if t.success:
                type_stats[t.tribulation_type]["success"] += 1

        return {
            "total_tribulations": total,
            "success_count": success_count,
            "failed_count": failed_count,
            "success_rate": success_rate,
            "type_stats": type_stats
        }

    async def _save_tribulation(self, tribulation: Tribulation):
        """保存天劫到数据库"""
        await self._ensure_tribulations_table()

        tribulation_data = tribulation.to_dict()
        columns = list(tribulation_data.keys())
        placeholders = ', '.join(['?' for _ in columns])
        values = list(tribulation_data.values())

        sql = f"INSERT INTO tribulations ({', '.join(columns)}) VALUES ({placeholders})"
        await self.db.execute(sql, values)

    async def _update_tribulation(self, tribulation: Tribulation):
        """更新天劫信息"""
        tribulation_data = tribulation.to_dict()

        set_clause = ', '.join([f"{key} = ?" for key in tribulation_data.keys() if key != 'id'])
        values = [value for key, value in tribulation_data.items() if key != 'id']
        values.append(tribulation.id)

        sql = f"UPDATE tribulations SET {set_clause} WHERE id = ?"
        await self.db.execute(sql, tuple(values))

    async def _ensure_tribulations_table(self):
        """确保天劫表存在"""
        sql = """
        CREATE TABLE IF NOT EXISTS tribulations (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            tribulation_type TEXT NOT NULL,
            realm TEXT NOT NULL,
            realm_level INTEGER NOT NULL,
            tribulation_level INTEGER NOT NULL,
            difficulty TEXT NOT NULL,
            total_waves INTEGER NOT NULL,
            current_wave INTEGER DEFAULT 0,
            damage_per_wave INTEGER NOT NULL,
            damage_reduction REAL DEFAULT 0.0,
            status TEXT NOT NULL,
            success INTEGER DEFAULT 0,
            initial_hp INTEGER DEFAULT 0,
            current_hp INTEGER DEFAULT 0,
            total_damage_taken INTEGER DEFAULT 0,
            rewards TEXT,
            penalties TEXT,
            wave_logs TEXT,
            started_at TEXT,
            completed_at TEXT,
            created_at TEXT NOT NULL
        )
        """
        await self.db.execute(sql)