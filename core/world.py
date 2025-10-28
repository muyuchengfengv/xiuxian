"""
世界/探索系统
负责地点管理、玩家移动、探索等功能
"""

import json
import random
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple
from astrbot.api import logger

from .database import DatabaseManager
from .player import PlayerManager
from ..models.location_model import Location, PlayerLocation
from ..models.player_model import Player


class WorldException(Exception):
    """世界系统基础异常"""
    pass


class LocationNotFoundError(WorldException):
    """地点不存在"""
    pass


class InvalidMoveError(WorldException):
    """非法移动"""
    pass


class MoveCooldownError(WorldException):
    """移动冷却中"""
    pass


class WorldManager:
    """世界管理器 - 管理地点和玩家探索"""

    # 移动冷却时间(秒)
    MOVE_COOLDOWN = 60  # 1分钟

    def __init__(self, db: DatabaseManager, player_mgr: PlayerManager):
        self.db = db
        self.player_mgr = player_mgr

    async def get_location(self, location_id: int) -> Optional[Location]:
        """获取地点信息"""
        cursor = await self.db.execute(
            "SELECT * FROM locations WHERE id = ?",
            (location_id,)
        )
        row = await cursor.fetchone()

        if row:
            return Location(**dict(row))
        return None

    async def get_location_by_name(self, name: str) -> Optional[Location]:
        """根据名称获取地点"""
        cursor = await self.db.execute(
            "SELECT * FROM locations WHERE name = ?",
            (name,)
        )
        row = await cursor.fetchone()

        if row:
            return Location(**dict(row))
        return None

    async def get_player_location(self, user_id: str) -> Tuple[Location, PlayerLocation]:
        """
        获取玩家当前所在地点

        Returns:
            (Location, PlayerLocation): 地点对象和玩家位置记录
        """
        # 获取玩家位置记录
        cursor = await self.db.execute(
            "SELECT * FROM player_locations WHERE user_id = ?",
            (user_id,)
        )
        row = await cursor.fetchone()

        if not row:
            # 玩家首次进入世界，初始化在新手村(ID=1)
            await self.db.execute(
                "INSERT INTO player_locations (user_id, current_location_id) VALUES (?, 1)",
                (user_id,)
            )
            row = {'user_id': user_id, 'current_location_id': 1, 'total_moves': 0, 'total_exploration_score': 0}

        player_loc = PlayerLocation(**dict(row))
        location = await self.get_location(player_loc.current_location_id)

        if not location:
            # 如果地点不存在，重置到新手村
            logger.warning(f"玩家 {user_id} 的位置地点不存在，重置到新手村")
            await self.db.execute(
                "UPDATE player_locations SET current_location_id = 1 WHERE user_id = ?",
                (user_id,)
            )
            location = await self.get_location(1)

        return location, player_loc

    async def get_connected_locations(self, location: Location) -> List[Location]:
        """获取与指定地点相连的所有地点"""
        try:
            connected_ids = json.loads(location.connected_locations)
        except (json.JSONDecodeError, TypeError):
            connected_ids = []

        locations = []
        for loc_id in connected_ids:
            loc = await self.get_location(int(loc_id))
            if loc:
                locations.append(loc)

        return locations

    async def can_move(self, user_id: str) -> Tuple[bool, Optional[str]]:
        """
        检查玩家是否可以移动

        Returns:
            (bool, Optional[str]): (是否可以移动, 不能移动的原因)
        """
        cursor = await self.db.execute(
            "SELECT last_move_time FROM player_locations WHERE user_id = ?",
            (user_id,)
        )
        row = await cursor.fetchone()

        if not row or not row['last_move_time']:
            return True, None

        last_move = datetime.fromisoformat(row['last_move_time'])
        now = datetime.now()
        elapsed = (now - last_move).total_seconds()

        if elapsed < self.MOVE_COOLDOWN:
            remaining = int(self.MOVE_COOLDOWN - elapsed)
            return False, f"移动冷却中，还需 {remaining} 秒"

        return True, None

    async def move_to(self, user_id: str, destination_id: int) -> Dict:
        """
        移动到指定地点

        Args:
            user_id: 用户ID
            destination_id: 目标地点ID

        Returns:
            移动结果信息
        """
        # 检查移动冷却
        can_move, reason = await self.can_move(user_id)
        if not can_move:
            raise MoveCooldownError(reason)

        # 获取当前位置
        current_loc, player_loc = await self.get_player_location(user_id)

        # 获取目标地点
        destination = await self.get_location(destination_id)
        if not destination:
            raise LocationNotFoundError(f"地点 ID {destination_id} 不存在")

        # 检查目标地点是否相连
        connected_locations = await self.get_connected_locations(current_loc)
        connected_ids = [loc.id for loc in connected_locations]

        if destination_id not in connected_ids:
            raise InvalidMoveError(f"{destination.name} 无法从 {current_loc.name} 直接到达")

        # 获取玩家信息（检查境界要求）
        player = await self.player_mgr.get_player(user_id)
        if player and self._check_realm_requirement(player.realm, destination.min_realm) < 0:
            logger.warning(f"玩家 {user_id} 境界不足，但仍允许前往 {destination.name}")
            # 只警告，不阻止

        # 执行移动
        await self.db.execute("""
            UPDATE player_locations
            SET current_location_id = ?,
                last_move_time = ?,
                total_moves = total_moves + 1
            WHERE user_id = ?
        """, (destination_id, datetime.now().isoformat(), user_id))

        # 计算探索积分奖励（首次到达新地点）
        exploration_reward = 0
        # TODO: 检查是否首次到达该地点，给予探索积分

        # 可能触发随机事件
        encounter = await self._try_trigger_encounter(user_id, destination)

        return {
            'success': True,
            'from_location': current_loc.name,
            'to_location': destination.name,
            'destination': destination,
            'exploration_reward': exploration_reward,
            'encounter': encounter,
            'move_count': player_loc.total_moves + 1
        }

    async def explore_current_location(self, user_id: str) -> Dict:
        """
        探索当前地点，可能发现新地点、遭遇事件等

        Returns:
            探索结果
        """
        location, _ = await self.get_player_location(user_id)
        player = await self.player_mgr.get_player(user_id)

        if not player:
            raise WorldException("玩家不存在")

        results = {
            'location': location,
            'discoveries': [],
            'encounters': [],
            'rewards': {}
        }

        # 探索可能的发现
        discovery_chance = 0.3 + (location.spirit_energy_density / 500.0)

        if random.random() < discovery_chance:
            # 发现了什么
            discovery_type = random.choice(['resource', 'hidden_path', 'secret'])

            if discovery_type == 'resource':
                # 发现资源（灵石、材料等）
                spirit_stone_found = random.randint(10, 50) * location.danger_level
                results['discoveries'].append({
                    'type': 'resource',
                    'description': f'发现了 {spirit_stone_found} 灵石',
                    'reward': {'spirit_stone': spirit_stone_found}
                })
                results['rewards']['spirit_stone'] = spirit_stone_found

        # 可能遭遇危险/机遇
        encounter = await self._try_trigger_encounter(user_id, location)
        if encounter:
            results['encounters'].append(encounter)

        return results

    async def _try_trigger_encounter(self, user_id: str, location: Location) -> Optional[Dict]:
        """
        尝试触发遭遇事件

        Returns:
            遭遇事件信息，如果没有触发则返回None
        """
        # 遭遇概率基于地点危险等级
        encounter_chance = location.danger_level * 0.05  # 5% per danger level

        if random.random() < encounter_chance:
            encounter_types = ['monster', 'treasure', 'cultivator', 'event']
            encounter_type = random.choice(encounter_types)

            encounters = {
                'monster': {
                    'type': 'monster',
                    'description': f'遭遇了 {location.danger_level} 阶妖兽！',
                    'danger_level': location.danger_level
                },
                'treasure': {
                    'type': 'treasure',
                    'description': '发现了一处宝藏！',
                    'value': random.randint(100, 500) * location.danger_level
                },
                'cultivator': {
                    'type': 'cultivator',
                    'description': '遇到了其他修士',
                    'friendly': random.choice([True, False])
                },
                'event': {
                    'type': 'event',
                    'description': '触发了神秘事件',
                    'event_id': random.randint(1, 100)
                }
            }

            return encounters[encounter_type]

        return None

    def _check_realm_requirement(self, current_realm: str, required_realm: str) -> int:
        """
        检查境界需求

        Returns:
            int:
                > 0 表示当前境界高于要求
                = 0 表示恰好满足要求
                < 0 表示境界不足
        """
        realm_order = [
            '炼气期', '筑基期', '金丹期', '元婴期', '化神期',
            '炼虚期', '合体期', '大乘期', '渡劫期',
            '地仙', '天仙', '金仙', '大罗金仙', '准圣', '混元圣人'
        ]

        try:
            current_idx = realm_order.index(current_realm)
            required_idx = realm_order.index(required_realm)
            return current_idx - required_idx
        except ValueError:
            # 未知境界，默认允许
            return 0

    async def get_all_locations(self, min_danger: int = 0, max_danger: int = 10) -> List[Location]:
        """获取所有地点（可按危险等级筛选）"""
        cursor = await self.db.execute("""
            SELECT * FROM locations
            WHERE danger_level >= ? AND danger_level <= ?
            ORDER BY danger_level ASC
        """, (min_danger, max_danger))

        rows = await cursor.fetchall()
        return [Location(**dict(row)) for row in rows]

    async def format_location_list(self, user_id: str) -> str:
        """格式化地点列表显示"""
        current_loc, player_loc = await self.get_player_location(user_id)
        connected_locs = await self.get_connected_locations(current_loc)

        lines = [
            f"🗺️ 当前位置: {current_loc.get_simple_info()}",
            "─" * 40,
            "",
            "📍 可到达的地点:",
            ""
        ]

        if not connected_locs:
            lines.append("   (暂无可到达的地点)")
        else:
            for i, loc in enumerate(connected_locs, 1):
                lines.append(f"{i}. {loc.get_simple_info()}")

        lines.extend([
            "",
            f"🚶 移动次数: {player_loc.total_moves}",
            "",
            "💡 使用 /前往 [编号] 前往目标地点",
            "💡 使用 /地点详情 [编号] 查看地点详细信息",
            "💡 使用 /探索 探索当前地点"
        ])

        return "\n".join(lines)

    async def format_world_map(self, user_id: str) -> str:
        """格式化世界地图显示（显示所有地点）"""
        current_loc, _ = await self.get_player_location(user_id)
        all_locations = await self.get_all_locations()

        lines = [
            "🗺️ 修仙世界地图",
            "─" * 40,
            "",
            f"📍 当前位置: {current_loc.name}",
            ""
        ]

        # 按危险等级分组
        by_danger = {}
        for loc in all_locations:
            danger = loc.danger_level
            if danger not in by_danger:
                by_danger[danger] = []
            by_danger[danger].append(loc)

        for danger_level in sorted(by_danger.keys()):
            locs = by_danger[danger_level]
            lines.append(f"⚠️ 危险等级 {danger_level}:")

            for loc in locs:
                current_marker = " 👈" if loc.id == current_loc.id else ""
                lines.append(f"   {loc.get_simple_info()}{current_marker}")

            lines.append("")

        lines.extend([
            "💡 使用 /地点 查看可到达的地点",
            "💡 使用 /地点详情 [地点名] 查看详细信息"
        ])

        return "\n".join(lines)
