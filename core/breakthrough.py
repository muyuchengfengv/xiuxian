"""
境界突破系统
负责玩家境界突破的成功率计算、突破执行等
"""

import random
from typing import Dict, Tuple, TYPE_CHECKING
from datetime import datetime
from astrbot.api import logger

from .database import DatabaseManager
from .player import PlayerManager
from ..models.player_model import Player
from ..utils import (
    CombatCalculator,
    BreakthroughFailedError,
    get_next_realm,
    get_cultivation_required,
    get_realm_level_name,
    REALM_LEVEL_NAMES
)

if TYPE_CHECKING:
    from .tribulation import TribulationSystem


class BreakthroughSystem:
    """境界突破系统类"""

    def __init__(self, db: DatabaseManager, player_mgr: PlayerManager):
        """
        初始化突破系统

        Args:
            db: 数据库管理器
            player_mgr: 玩家管理器
        """
        self.db = db
        self.player_mgr = player_mgr
        self.tribulation_sys = None  # 将在主程序中设置

    def set_tribulation_system(self, tribulation_sys: 'TribulationSystem'):
        """
        设置天劫系统（依赖注入）

        Args:
            tribulation_sys: 天劫系统实例
        """
        self.tribulation_sys = tribulation_sys

    async def attempt_breakthrough(self, user_id: str, skip_tribulation: bool = False) -> Dict:
        """
        尝试境界突破

        Args:
            user_id: 用户ID
            skip_tribulation: 是否跳过天劫检查（内部使用，渡劫成功后调用）

        Returns:
            突破结果字典 {
                'success': 是否成功,
                'message': 结果消息,
                'old_realm': 原境界,
                'new_realm': 新境界(成功时),
                'breakthrough_rate': 突破成功率,
                'requires_tribulation': 是否需要渡劫,
                'tribulation_created': 是否已创建天劫
            }

        Raises:
            PlayerNotFoundError: 玩家不存在
            BreakthroughFailedError: 突破失败
        """
        # 1. 获取玩家信息
        player = await self.player_mgr.get_player_or_error(user_id)

        # 2. 检查是否可以突破
        can_breakthrough, next_realm_info = self._check_breakthrough_available(player)
        if not can_breakthrough:
            raise BreakthroughFailedError("当前条件不满足突破要求")

        # 3. 记录原始境界
        old_realm_name = get_realm_level_name(player.realm, player.realm_level)
        old_realm = f"{player.realm}{old_realm_name}"
        new_realm = next_realm_info['name']
        target_realm = next_realm_info['realm']

        # 4. 检查是否需要渡劫（只在小等级为9，即突破到新大境界时检查）
        requires_tribulation = False
        if self.tribulation_sys and not skip_tribulation and next_realm_info['level'] == 1:
            requires_tribulation = await self.tribulation_sys.check_tribulation_required(target_realm)

            if requires_tribulation:
                # 检查是否已有进行中的天劫
                active_tribulation = await self.tribulation_sys.get_active_tribulation(user_id)

                if not active_tribulation:
                    # 创建天劫
                    tribulation = await self.tribulation_sys.create_tribulation(user_id, target_realm)

                    return {
                        'success': False,
                        'message': f"⚡ 突破至 {new_realm} 需要渡过天劫！\n天劫已降临，请使用 /渡劫 命令开始渡劫",
                        'old_realm': old_realm,
                        'new_realm': new_realm,
                        'requires_tribulation': True,
                        'tribulation_created': True,
                        'tribulation': tribulation
                    }
                else:
                    # 已有天劫但未完成
                    return {
                        'success': False,
                        'message': f"⚡ 突破至 {new_realm} 需要渡过天劫！\n您还有未完成的天劫，请使用 /渡劫 命令继续渡劫",
                        'old_realm': old_realm,
                        'new_realm': new_realm,
                        'requires_tribulation': True,
                        'tribulation_created': False,
                        'tribulation': active_tribulation
                    }

        # 5. 计算突破成功率
        success_rate, rate_factors = CombatCalculator.calculate_breakthrough_rate(player)

        # 6. 执行突破判定
        is_success = random.random() < success_rate

        if is_success:
            # 突破成功
            await self._perform_breakthrough(player, next_realm_info)

            result = {
                'success': True,
                'message': f"🎉 突破成功！从 {old_realm} 突破至 {new_realm}！",
                'old_realm': old_realm,
                'new_realm': new_realm,
                'breakthrough_rate': success_rate,
                'rate_factors': rate_factors,
                'requires_tribulation': False
            }

            logger.info(f"玩家 {player.name} 突破成功: {old_realm} -> {new_realm}")

        else:
            # 突破失败
            await self._handle_breakthrough_failure(player)

            result = {
                'success': False,
                'message': f"💔 突破失败！从 {old_realm} 突破至 {new_realm} 失败！",
                'old_realm': old_realm,
                'new_realm': new_realm,
                'breakthrough_rate': success_rate,
                'rate_factors': rate_factors,
                'requires_tribulation': False
            }

            logger.info(f"玩家 {player.name} 突破失败: {old_realm} -> {new_realm}")

        return result

    def _check_breakthrough_available(self, player: Player) -> Tuple[bool, Dict]:
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

        # 获取境界名称
        realm_name = f"{next_realm}" if next_level == 1 else f"{player.realm}"
        level_name = get_realm_level_name(next_realm, next_level)
        full_name = f"{realm_name}{level_name}"

        return can_breakthrough, {
            'name': full_name,
            'required': required_cultivation,
            'realm': next_realm,
            'level': next_level
        }

    async def _perform_breakthrough(self, player: Player, next_realm_info: Dict):
        """
        执行突破成功后的处理

        Args:
            player: 玩家对象
            next_realm_info: 下一境界信息
        """
        # 1. 记录旧境界信息
        old_realm = player.realm
        old_realm_level = player.realm_level

        # 2. 更新境界和等级
        player.realm = next_realm_info['realm']
        player.realm_level = next_realm_info['level']

        # 3. 应用境界属性加成
        from ..utils.constants import REALMS
        new_realm_config = REALMS.get(player.realm, REALMS["炼气期"])
        attribute_bonus = new_realm_config.get("attribute_bonus", {})

        # 判断是小境界提升还是大境界突破
        if old_realm == player.realm:
            # 小境界提升：属性按比例增长（每级25%的境界属性加成）
            level_ratio = 0.25
            hp_bonus = int(attribute_bonus.get("max_hp", 0) * level_ratio)
            mp_bonus = int(attribute_bonus.get("max_mp", 0) * level_ratio)
            attack_bonus = int(attribute_bonus.get("attack", 0) * level_ratio)
            defense_bonus = int(attribute_bonus.get("defense", 0) * level_ratio)
        else:
            # 大境界突破：获得完整的境界属性加成
            hp_bonus = attribute_bonus.get("max_hp", 0)
            mp_bonus = attribute_bonus.get("max_mp", 0)
            attack_bonus = attribute_bonus.get("attack", 0)
            defense_bonus = attribute_bonus.get("defense", 0)

        # 应用属性加成
        player.max_hp += hp_bonus
        player.max_mp += mp_bonus
        player.attack += attack_bonus
        player.defense += defense_bonus

        # 突破成功后恢复满血满蓝
        player.hp = player.max_hp
        player.mp = player.max_mp

        # 4. 扣除突破所需修为
        required_cultivation = next_realm_info['required']
        player.cultivation -= required_cultivation

        # 5. 突破成功奖励（额外修为）
        bonus_cultivation = int(required_cultivation * 0.1)  # 10%额外修为奖励
        player.cultivation += bonus_cultivation

        # 6. 更新时间戳
        player.updated_at = datetime.now()

        # 7. 保存到数据库
        await self.player_mgr.update_player(player)

        logger.info(
            f"玩家 {player.name} 突破成功, 获得奖励修为: {bonus_cultivation}, "
            f"属性提升 - HP:+{hp_bonus}({player.max_hp}), MP:+{mp_bonus}({player.max_mp}), "
            f"攻击:+{attack_bonus}({player.attack}), 防御:+{defense_bonus}({player.defense})"
        )

    async def _handle_breakthrough_failure(self, player: Player):
        """
        处理突破失败

        Args:
            player: 玩家对象
        """
        # 突破失败惩罚：损失部分修为
        penalty_rate = 0.2  # 损失20%的当前修为
        lost_cultivation = int(player.cultivation * penalty_rate)
        player.cultivation -= lost_cultivation

        # 确保修为不会变成负数
        player.cultivation = max(0, player.cultivation)

        # 更新时间戳
        player.updated_at = datetime.now()

        # 保存到数据库
        await self.player_mgr.update_player(player)

        logger.info(f"玩家 {player.name} 突破失败, 损失修为: {lost_cultivation}")

    async def get_breakthrough_info(self, user_id: str) -> Dict:
        """
        获取突破信息

        Args:
            user_id: 用户ID

        Returns:
            突破信息字典
        """
        player = await self.player_mgr.get_player_or_error(user_id)

        # 检查是否可以突破
        can_breakthrough, next_realm_info = self._check_breakthrough_available(player)

        if not can_breakthrough:
            return {
                'can_breakthrough': False,
                'reason': '已达最高境界' if next_realm_info['name'] is None else '修为不足',
                'current_cultivation': player.cultivation,
                'required_cultivation': next_realm_info.get('required', 0),
                'next_realm': next_realm_info.get('name', None)
            }

        # 计算突破成功率
        success_rate, rate_factors = CombatCalculator.calculate_breakthrough_rate(player)

        # 计算当前境界全名
        current_realm_name = get_realm_level_name(player.realm, player.realm_level)
        current_full_realm = f"{player.realm}{current_realm_name}"

        return {
            'can_breakthrough': True,
            'success_rate': success_rate,
            'rate_factors': rate_factors,
            'current_realm': current_full_realm,
            'next_realm': next_realm_info['name'],
            'current_cultivation': player.cultivation,
            'required_cultivation': next_realm_info['required'],
            'cultivation_surplus': player.cultivation - next_realm_info['required']
        }