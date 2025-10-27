"""
玩家管理器
负责玩家数据的CRUD操作
"""

from typing import Optional
import random
from datetime import datetime
from astrbot.api import logger

from .database import DatabaseManager
from .spirit_root import SpiritRootFactory
from ..models.player_model import Player
from ..utils.constants import (
    INITIAL_ATTRIBUTES,
    INITIAL_COMBAT_STATS,
    DEFAULT_INITIAL_SPIRIT_STONE,
    REALMS
)
from ..utils.exceptions import PlayerNotFoundError


class PlayerManager:
    """玩家管理器"""

    def __init__(self, db: DatabaseManager):
        """
        初始化玩家管理器

        Args:
            db: 数据库管理器实例
        """
        self.db = db

    async def player_exists(self, user_id: str) -> bool:
        """
        检查玩家是否存在

        Args:
            user_id: 用户ID

        Returns:
            是否存在
        """
        result = await self.db.fetchone(
            "SELECT user_id FROM players WHERE user_id = ?",
            (user_id,)
        )
        return result is not None

    async def get_player(self, user_id: str) -> Optional[Player]:
        """
        获取玩家信息

        Args:
            user_id: 用户ID

        Returns:
            玩家对象，如果不存在则返回None
        """
        result = await self.db.fetchone(
            "SELECT * FROM players WHERE user_id = ?",
            (user_id,)
        )

        if result is None:
            return None

        # 将Row对象转换为字典
        player_data = dict(result)
        return Player.from_dict(player_data)

    async def create_player(self, user_id: str, name: str) -> Player:
        """
        创建新玩家

        Args:
            user_id: 用户ID
            name: 玩家道号

        Returns:
            创建的玩家对象

        Raises:
            ValueError: 玩家已存在时抛出
        """
        # 1. 检查玩家是否已存在
        if await self.player_exists(user_id):
            raise ValueError("道友已经开始修仙之路，无需重复创建角色")

        # 2. 生成随机灵根
        spirit_root = SpiritRootFactory.generate_random()

        # 3. 生成初始属性 (根据灵根品质有差异)
        attributes = self._generate_initial_attributes(spirit_root)

        # 4. 计算初始战斗属性
        combat_stats = self._calculate_initial_combat_stats(attributes, spirit_root)

        # 5. 创建玩家对象
        player = Player(
            user_id=user_id,
            name=name,
            realm="炼气期",
            realm_level=1,
            cultivation=0,
            # 灵根信息
            spirit_root_type=spirit_root['type'],
            spirit_root_quality=spirit_root['quality'],
            spirit_root_value=spirit_root['value'],
            spirit_root_purity=spirit_root['purity'],
            # 基础属性
            constitution=attributes['constitution'],
            spiritual_power=attributes['spiritual_power'],
            comprehension=attributes['comprehension'],
            luck=attributes['luck'],
            root_bone=attributes['root_bone'],
            # 战斗属性
            hp=combat_stats['hp'],
            max_hp=combat_stats['max_hp'],
            mp=combat_stats['mp'],
            max_mp=combat_stats['max_mp'],
            attack=combat_stats['attack'],
            defense=combat_stats['defense'],
            # 资源
            spirit_stone=DEFAULT_INITIAL_SPIRIT_STONE,
            contribution=0,
            # 位置
            current_location="新手村",
            # 时间
            last_cultivation=None,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        # 6. 保存到数据库
        await self._insert_player(player)

        logger.info(f"创建新玩家: {name} ({user_id}), 灵根: {spirit_root['quality']} {spirit_root['type']}")

        return player

    def _generate_initial_attributes(self, spirit_root: dict) -> dict:
        """
        生成初始属性

        根据灵根品质调整属性范围

        Args:
            spirit_root: 灵根信息

        Returns:
            属性字典
        """
        quality = spirit_root['quality']

        # 品质影响属性范围
        quality_modifier = {
            "废灵根": -3,     # 属性-3
            "杂灵根": -1,     # 属性-1
            "双灵根": 0,      # 正常
            "单灵根": 2,      # 属性+2
            "变异灵根": 3,    # 属性+3
            "天灵根": 5       # 属性+5
        }

        modifier = quality_modifier.get(quality, 0)

        attributes = {}
        for attr_name, (min_val, max_val) in INITIAL_ATTRIBUTES.items():
            # 应用品质修正
            adjusted_min = max(1, min_val + modifier)
            adjusted_max = max_val + modifier

            # 随机生成
            value = random.randint(adjusted_min, adjusted_max)
            attributes[attr_name] = value

        return attributes

    def _calculate_initial_combat_stats(self, attributes: dict, spirit_root: dict) -> dict:
        """
        计算初始战斗属性

        Args:
            attributes: 基础属性
            spirit_root: 灵根信息

        Returns:
            战斗属性字典
        """
        # 从初始战斗属性开始
        combat_stats = INITIAL_COMBAT_STATS.copy()

        # 体质影响生命值
        hp_bonus = attributes['constitution'] * 50
        combat_stats['max_hp'] += hp_bonus
        combat_stats['hp'] = combat_stats['max_hp']

        # 灵力影响法力值和攻击力
        mp_bonus = attributes['spiritual_power'] * 30
        attack_bonus = attributes['spiritual_power'] * 2

        combat_stats['max_mp'] += mp_bonus
        combat_stats['mp'] = combat_stats['max_mp']
        combat_stats['attack'] += attack_bonus

        # 根骨影响防御力
        defense_bonus = attributes['root_bone'] * 1
        combat_stats['defense'] += defense_bonus

        # 灵根战斗加成
        bonuses = SpiritRootFactory.calculate_bonuses(spirit_root)
        combat_bonus = bonuses.get('combat_bonus', {})

        # 应用灵根战斗加成
        if 'attack' in combat_bonus:
            combat_stats['attack'] = int(combat_stats['attack'] * (1 + combat_bonus['attack']))
        if 'defense' in combat_bonus:
            combat_stats['defense'] = int(combat_stats['defense'] * (1 + combat_bonus['defense']))
        if 'max_hp' in combat_bonus:
            bonus_hp = int(combat_stats['max_hp'] * combat_bonus['max_hp'])
            combat_stats['max_hp'] += bonus_hp
            combat_stats['hp'] = combat_stats['max_hp']
        if 'max_mp' in combat_bonus:
            bonus_mp = int(combat_stats['max_mp'] * combat_bonus['max_mp'])
            combat_stats['max_mp'] += bonus_mp
            combat_stats['mp'] = combat_stats['max_mp']

        return combat_stats

    async def _insert_player(self, player: Player):
        """
        插入玩家到数据库

        Args:
            player: 玩家对象
        """
        player_dict = player.to_dict()

        # 构建SQL
        columns = ', '.join(player_dict.keys())
        placeholders = ', '.join(['?' for _ in player_dict])

        sql = f"INSERT INTO players ({columns}) VALUES ({placeholders})"
        values = tuple(player_dict.values())

        await self.db.execute(sql, values)

    async def update_player(self, player: Player):
        """
        更新玩家信息

        Args:
            player: 玩家对象
        """
        # 更新时间戳
        player.update_timestamp()

        player_dict = player.to_dict()

        # 构建UPDATE SQL (排除user_id)
        set_clause = ', '.join([f"{key} = ?" for key in player_dict.keys() if key != 'user_id'])
        values = [value for key, value in player_dict.items() if key != 'user_id']
        values.append(player.user_id)  # WHERE条件

        sql = f"UPDATE players SET {set_clause} WHERE user_id = ?"

        await self.db.execute(sql, tuple(values))

        logger.debug(f"更新玩家数据: {player.name} ({player.user_id})")

    async def delete_player(self, user_id: str) -> bool:
        """
        删除玩家

        Args:
            user_id: 用户ID

        Returns:
            是否删除成功
        """
        if not await self.player_exists(user_id):
            return False

        await self.db.execute(
            "DELETE FROM players WHERE user_id = ?",
            (user_id,)
        )

        logger.info(f"删除玩家: {user_id}")
        return True

    async def get_player_or_error(self, user_id: str) -> Player:
        """
        获取玩家，不存在时抛出异常

        Args:
            user_id: 用户ID

        Returns:
            玩家对象

        Raises:
            PlayerNotFoundError: 玩家不存在时抛出
        """
        player = await self.get_player(user_id)
        if player is None:
            raise PlayerNotFoundError(user_id)
        return player
