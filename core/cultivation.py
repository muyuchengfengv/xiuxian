"""
修炼系统
负责玩家修炼、修为获取、冷却管理
"""

from datetime import datetime
from typing import Dict
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

    def set_cooldown(self, seconds: int):
        """
        设置修炼冷却时间

        Args:
            seconds: 冷却秒数
        """
        self.cooldown_seconds = seconds
        logger.info(f"修炼冷却时间设置为 {seconds} 秒")

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

        # 4. 更新玩家数据
        player.cultivation += cultivation_gained
        player.last_cultivation = datetime.now()

        # 5. 保存到数据库
        await self.player_mgr.update_player(player)

        # 6. 检查是否可以突破
        can_breakthrough, next_realm_info = self._check_breakthrough_available(player)

        logger.info(
            f"玩家 {player.name} 修炼完成: "
            f"获得修为 {cultivation_gained}, 总修为 {player.cultivation}"
        )

        return {
            'cultivation_gained': cultivation_gained,
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
