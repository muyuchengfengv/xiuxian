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
from .story_generator import LLMStoryGenerator
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

    def __init__(self, db: DatabaseManager, player_mgr: PlayerManager, context=None, enable_ai: bool = True):
        self.db = db
        self.player_mgr = player_mgr
        self.context = context
        self.enable_ai = enable_ai
        self.story_generator = LLMStoryGenerator(db, player_mgr, context)

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
            'event': None,  # 触发的事件（需要玩家选择）
            'story': None,  # LLM生成的故事
            'discoveries': [],
            'encounters': [],
            'rewards': {},
            'has_choice': False  # 是否需要玩家做出选择
        }

        # 探索触发事件概率（基于地点危险等级和灵气浓度）
        # 提高基础概率从0.4到0.7，让玩家更容易遇到事件
        event_chance = 0.7 + (location.danger_level * 0.05) + (location.spirit_energy_density / 1000.0)

        if random.random() < event_chance:
            # 使用LLM生成动态故事
            try:
                story = await self.story_generator.generate_exploration_story(
                    user_id, location, player, self.enable_ai
                )
                results['story'] = story

                # 检查是否有选择
                choices = json.loads(story.get('choices', '[]'))
                if choices:
                    results['has_choice'] = True
                    results['event'] = {
                        'type': story['story_type'],
                        'title': story['story_title'],
                        'description': story['story_content'],
                        'has_choice': True,
                        'choices': choices,
                        'story_id': story['id']
                    }
                else:
                    # 自动结算
                    rewards = json.loads(story.get('rewards', '{}'))
                    results['rewards'] = rewards
                    results['message'] = story['story_content']

                    # 应用奖励
                    await self._apply_story_rewards(user_id, rewards)

            except Exception as e:
                logger.error(f"生成LLM故事失败: {e}")
                # 回退到原有的事件生成
                event = await self._generate_exploration_event(user_id, location, player)
                results['event'] = event

                if event.get('has_choice'):
                    results['has_choice'] = True
                else:
                    if 'auto_result' in event:
                        results.update(event['auto_result'])

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
            "💡 使用 /地点详情 [地点名] 查看详细信息",
            "💡 使用 /路线图 查看完整的地点连接网络",
            "💡 使用 /寻路 [目标地点] 查找前往路线"
        ])

        return "\n".join(lines)

    async def find_path(self, start_location_id: int, end_location_id: int) -> Optional[List[Location]]:
        """
        使用BFS查找两个地点之间的最短路径

        Args:
            start_location_id: 起始地点ID
            end_location_id: 目标地点ID

        Returns:
            路径中的Location对象列表，如果无法到达则返回None
        """
        if start_location_id == end_location_id:
            start_loc = await self.get_location(start_location_id)
            return [start_loc] if start_loc else None

        # BFS查找最短路径
        from collections import deque

        queue = deque([(start_location_id, [start_location_id])])
        visited = {start_location_id}

        while queue:
            current_id, path = queue.popleft()
            current_loc = await self.get_location(current_id)

            if not current_loc:
                continue

            # 获取相连的地点
            connected = await self.get_connected_locations(current_loc)

            for next_loc in connected:
                if next_loc.id == end_location_id:
                    # 找到目标，返回完整路径
                    full_path = path + [next_loc.id]
                    result = []
                    for loc_id in full_path:
                        loc = await self.get_location(loc_id)
                        if loc:
                            result.append(loc)
                    return result

                if next_loc.id not in visited:
                    visited.add(next_loc.id)
                    queue.append((next_loc.id, path + [next_loc.id]))

        return None

    async def format_route_map(self, user_id: str) -> str:
        """
        格式化路线图显示，展示地点之间的连接关系

        Returns:
            路线图的文本表示
        """
        current_loc, _ = await self.get_player_location(user_id)
        all_locations = await self.get_all_locations()

        lines = [
            "🗺️ 修仙世界路线图",
            "─" * 40,
            "",
            f"📍 当前位置: {current_loc.name}",
            "",
            "地点连接网络:",
            ""
        ]

        # 为每个地点显示连接关系
        for loc in all_locations:
            connected = await self.get_connected_locations(loc)
            connected_names = [f"{c.name}({c.id})" for c in connected]

            current_marker = "👈" if loc.id == current_loc.id else "  "
            lines.append(f"{current_marker} [{loc.id}] {loc.name} (危险{loc.danger_level})")

            if connected_names:
                lines.append(f"    └─ 可前往: {' → '.join(connected_names)}")
            else:
                lines.append(f"    └─ (无连接)")
            lines.append("")

        lines.extend([
            "─" * 40,
            "💡 使用 /前往 [编号] 前往目标地点",
            "💡 使用 /寻路 [目标地点] 查找前往路线"
        ])

        return "\n".join(lines)

    async def format_pathfinding(self, user_id: str, destination_name: str) -> str:
        """
        格式化寻路结果显示

        Args:
            user_id: 用户ID
            destination_name: 目标地点名称

        Returns:
            寻路结果的文本表示
        """
        current_loc, _ = await self.get_player_location(user_id)
        destination = await self.get_location_by_name(destination_name)

        if not destination:
            return f"❌ 未找到名为 '{destination_name}' 的地点"

        if current_loc.id == destination.id:
            return f"📍 你已经在 {destination.name} 了"

        # 查找路径
        path = await self.find_path(current_loc.id, destination.id)

        if not path:
            return f"❌ 无法从 {current_loc.name} 到达 {destination.name}"

        lines = [
            f"🧭 寻路: {current_loc.name} → {destination.name}",
            "─" * 40,
            "",
            f"📍 起点: {current_loc.name}",
            f"🎯 终点: {destination.name}",
            f"📏 路径长度: {len(path) - 1} 步",
            "",
            "推荐路线:",
            ""
        ]

        # 显示路径
        for i, loc in enumerate(path):
            if i == 0:
                lines.append(f"  {i+1}. 📍 {loc.name} (当前位置)")
            elif i == len(path) - 1:
                lines.append(f"  {i+1}. 🎯 {loc.name} (目的地)")
            else:
                lines.append(f"  {i+1}. ➡️  {loc.name}")

        lines.extend([
            "",
            "─" * 40,
            f"💡 使用 /前往 {path[1].id} 开始前往 {path[1].name}"
        ])

        return "\n".join(lines)

    async def _generate_exploration_event(self, user_id: str, location: Location, player: Player) -> Dict:
        """
        生成探索事件

        Returns:
            事件信息字典
        """
        # 根据地点危险等级和灵气浓度选择事件类型
        event_types = []

        # 基础事件（所有地点都可能出现）
        event_types.extend(['resource_find', 'cultivation_insight', 'mysterious_npc'])

        # 根据危险等级添加不同事件
        if location.danger_level >= 3:
            event_types.extend(['monster_encounter', 'treasure_chest', 'ancient_ruin'])

        if location.danger_level >= 5:
            event_types.extend(['dangerous_trap', 'powerful_cultivator', 'secret_realm_entrance'])

        if location.danger_level >= 7:
            event_types.extend(['heaven_material', 'ancient_inheritance', 'spatial_anomaly'])

        # 根据灵气浓度添加事件
        if location.spirit_energy_density >= 60:
            event_types.extend(['spirit_spring', 'rare_herb'])

        event_type = random.choice(event_types)

        # 生成对应的事件
        event_generators = {
            'resource_find': self._event_resource_find,
            'cultivation_insight': self._event_cultivation_insight,
            'mysterious_npc': self._event_mysterious_npc,
            'monster_encounter': self._event_monster_encounter,
            'treasure_chest': self._event_treasure_chest,
            'ancient_ruin': self._event_ancient_ruin,
            'dangerous_trap': self._event_dangerous_trap,
            'powerful_cultivator': self._event_powerful_cultivator,
            'secret_realm_entrance': self._event_secret_realm,
            'heaven_material': self._event_heaven_material,
            'ancient_inheritance': self._event_ancient_inheritance,
            'spatial_anomaly': self._event_spatial_anomaly,
            'spirit_spring': self._event_spirit_spring,
            'rare_herb': self._event_rare_herb,
        }

        generator = event_generators.get(event_type, self._event_resource_find)
        return await generator(user_id, location, player)

    async def _event_resource_find(self, user_id: str, location: Location, player: Player) -> Dict:
        """事件：发现资源"""
        spirit_stone = random.randint(50, 200) * location.danger_level
        return {
            'type': 'resource_find',
            'title': '💎 发现资源',
            'description': f'在探索过程中，你发现了一处灵石矿脉的遗迹！',
            'has_choice': False,
            'auto_result': {
                'rewards': {'spirit_stone': spirit_stone},
                'message': f'获得了 {spirit_stone} 灵石！'
            }
        }

    async def _event_cultivation_insight(self, user_id: str, location: Location, player: Player) -> Dict:
        """事件：修炼顿悟"""
        cultivation_gain = random.randint(100, 300) * (1 + location.spirit_energy_density / 100)
        return {
            'type': 'cultivation_insight',
            'title': '✨ 修炼顿悟',
            'description': f'在{location.name}的灵气环境中，你突然有所感悟！',
            'has_choice': False,
            'auto_result': {
                'rewards': {'cultivation': int(cultivation_gain)},
                'message': f'获得了 {int(cultivation_gain)} 修为！'
            }
        }

    async def _event_mysterious_npc(self, user_id: str, location: Location, player: Player) -> Dict:
        """事件：神秘NPC"""
        choices = [
            {
                'id': 'talk',
                'text': '上前交谈',
                'description': '可能获得情报或任务'
            },
            {
                'id': 'trade',
                'text': '进行交易',
                'description': '花费灵石购买物品'
            },
            {
                'id': 'ignore',
                'text': '离开',
                'description': '无事发生'
            }
        ]

        return {
            'type': 'mysterious_npc',
            'title': '🧙 神秘修士',
            'description': '你遇到了一位神秘的修士，他似乎有话要说...',
            'has_choice': True,
            'choices': choices,
            'event_data': {
                'npc_level': location.danger_level,
                'location_id': location.id
            }
        }

    async def _event_monster_encounter(self, user_id: str, location: Location, player: Player) -> Dict:
        """事件：妖兽遭遇"""
        monster_level = location.danger_level + random.randint(-1, 2)
        choices = [
            {
                'id': 'fight',
                'text': '战斗',
                'description': f'与 {monster_level} 阶妖兽战斗，胜利可获得丰厚奖励'
            },
            {
                'id': 'flee',
                'text': '逃跑',
                'description': '消耗灵石逃离，保证安全'
            }
        ]

        return {
            'type': 'monster_encounter',
            'title': '⚔️ 妖兽袭击',
            'description': f'你遭遇了一只 {monster_level} 阶妖兽！',
            'has_choice': True,
            'choices': choices,
            'event_data': {
                'monster_level': monster_level,
                'location_danger': location.danger_level
            }
        }

    async def _event_treasure_chest(self, user_id: str, location: Location, player: Player) -> Dict:
        """事件：宝箱"""
        choices = [
            {
                'id': 'open_direct',
                'text': '直接打开',
                'description': '可能触发陷阱，但也可能直接获得宝物'
            },
            {
                'id': 'open_careful',
                'text': '小心打开',
                'description': '花费时间仔细检查，更安全但奖励可能减少'
            },
            {
                'id': 'ignore',
                'text': '不打开',
                'description': '离开宝箱'
            }
        ]

        return {
            'type': 'treasure_chest',
            'title': '📦 神秘宝箱',
            'description': '你发现了一个古老的宝箱，散发着微弱的灵光...',
            'has_choice': True,
            'choices': choices,
            'event_data': {
                'chest_quality': location.danger_level,
                'trap_chance': location.danger_level * 0.1
            }
        }

    async def _event_ancient_ruin(self, user_id: str, location: Location, player: Player) -> Dict:
        """事件：古代遗迹"""
        choices = [
            {
                'id': 'explore',
                'text': '探索遗迹',
                'description': '可能发现珍贵功法或宝物，但有危险'
            },
            {
                'id': 'mark',
                'text': '标记位置后离开',
                'description': '记录位置，日后再来'
            }
        ]

        return {
            'type': 'ancient_ruin',
            'title': '🏛️ 古代遗迹',
            'description': '你发现了一处古代修士的洞府遗迹！',
            'has_choice': True,
            'choices': choices,
            'event_data': {
                'ruin_level': location.danger_level,
                'location_id': location.id
            }
        }

    async def _event_dangerous_trap(self, user_id: str, location: Location, player: Player) -> Dict:
        """事件：危险陷阱"""
        damage = random.randint(50, 200) * location.danger_level
        dodge_chance = min(0.8, player.luck / 100 + 0.2)

        if random.random() < dodge_chance:
            return {
                'type': 'dangerous_trap',
                'title': '⚠️ 陷阱',
                'description': f'你凭借敏锐的感知，成功避开了一处危险的阵法陷阱！',
                'has_choice': False,
                'auto_result': {
                    'message': '幸运地躲过了陷阱！'
                }
            }
        else:
            return {
                'type': 'dangerous_trap',
                'title': '💥 触发陷阱',
                'description': f'你不慎触发了古代阵法，受到了攻击！',
                'has_choice': False,
                'auto_result': {
                    'damage': damage,
                    'message': f'受到了 {damage} 点伤害！'
                }
            }

    async def _event_powerful_cultivator(self, user_id: str, location: Location, player: Player) -> Dict:
        """事件：强大修士"""
        choices = [
            {
                'id': 'greet',
                'text': '礼貌问候',
                'description': '可能获得指点或物品'
            },
            {
                'id': 'challenge',
                'text': '请求切磋',
                'description': '胜利可获得经验，失败会受伤'
            },
            {
                'id': 'avoid',
                'text': '避开',
                'description': '无事发生'
            }
        ]

        return {
            'type': 'powerful_cultivator',
            'title': '👤 强大修士',
            'description': f'你遇到了一位气息强大的修士，他的修为远超于你...',
            'has_choice': True,
            'choices': choices,
            'event_data': {
                'cultivator_realm': location.min_realm,
                'friendly': random.random() > 0.3
            }
        }

    async def _event_secret_realm(self, user_id: str, location: Location, player: Player) -> Dict:
        """事件：秘境入口"""
        choices = [
            {
                'id': 'enter',
                'text': '进入秘境',
                'description': '机遇与危险并存'
            },
            {
                'id': 'later',
                'text': '标记后离开',
                'description': '等实力提升后再来'
            }
        ]

        return {
            'type': 'secret_realm',
            'title': '🌀 秘境入口',
            'description': '空间扭曲，一个神秘的秘境入口出现在你面前！',
            'has_choice': True,
            'choices': choices,
            'event_data': {
                'realm_level': location.danger_level,
                'min_realm': location.min_realm
            }
        }

    async def _event_heaven_material(self, user_id: str, location: Location, player: Player) -> Dict:
        """事件：天材地宝"""
        material_value = random.randint(500, 2000) * location.danger_level
        return {
            'type': 'heaven_material',
            'title': '🌟 天材地宝',
            'description': f'你发现了一株罕见的天材地宝！',
            'has_choice': False,
            'auto_result': {
                'rewards': {'spirit_stone': material_value},
                'message': f'采集了珍贵的天材地宝，价值 {material_value} 灵石！'
            }
        }

    async def _event_ancient_inheritance(self, user_id: str, location: Location, player: Player) -> Dict:
        """事件：古代传承"""
        choices = [
            {
                'id': 'accept',
                'text': '接受传承',
                'description': '可能获得强大功法，但需要通过考验'
            },
            {
                'id': 'decline',
                'text': '放弃',
                'description': '放弃这次机会'
            }
        ]

        return {
            'type': 'ancient_inheritance',
            'title': '📜 古代传承',
            'description': '你触发了一个古代修士留下的传承！',
            'has_choice': True,
            'choices': choices,
            'event_data': {
                'inheritance_quality': location.danger_level,
                'test_difficulty': location.danger_level
            }
        }

    async def _event_spatial_anomaly(self, user_id: str, location: Location, player: Player) -> Dict:
        """事件：空间异常"""
        choices = [
            {
                'id': 'investigate',
                'text': '调查',
                'description': '可能获得空间类宝物'
            },
            {
                'id': 'avoid',
                'text': '远离',
                'description': '避免危险'
            }
        ]

        return {
            'type': 'spatial_anomaly',
            'title': '🌌 空间异常',
            'description': '空间出现了不稳定的波动，似乎隐藏着什么...',
            'has_choice': True,
            'choices': choices,
            'event_data': {
                'anomaly_level': location.danger_level
            }
        }

    async def _event_spirit_spring(self, user_id: str, location: Location, player: Player) -> Dict:
        """事件：灵泉"""
        cultivation_boost = random.randint(200, 500) * (location.spirit_energy_density / 50)
        return {
            'type': 'spirit_spring',
            'title': '💧 灵泉',
            'description': '你发现了一处灵泉，泉水蕴含浓郁的灵气！',
            'has_choice': False,
            'auto_result': {
                'rewards': {'cultivation': int(cultivation_boost)},
                'message': f'饮用灵泉水后，修为增长 {int(cultivation_boost)}！'
            }
        }

    async def _event_rare_herb(self, user_id: str, location: Location, player: Player) -> Dict:
        """事件：稀有灵药"""
        herb_value = random.randint(300, 1000) * (location.spirit_energy_density / 50)
        return {
            'type': 'rare_herb',
            'title': '🌿 稀有灵药',
            'description': '你发现了一株稀有的灵药，散发着浓郁的药香！',
            'has_choice': False,
            'auto_result': {
                'rewards': {'spirit_stone': int(herb_value)},
                'message': f'采集了稀有灵药，价值 {int(herb_value)} 灵石！'
            }
        }

    async def handle_event_choice(
        self,
        user_id: str,
        event_info: Dict,
        selected_choice: Dict,
        location: Location
    ) -> Dict:
        """
        处理探索事件的选择结果

        Args:
            user_id: 用户ID
            event_info: 事件信息
            selected_choice: 玩家选择的选项
            location: 当前地点

        Returns:
            选择结果字典
        """
        # 检查是否是新的LLM故事
        if 'story_id' in event_info:
            # 使用LLM故事生成器处理选择
            try:
                result = await self.story_generator.handle_story_choice(
                    user_id,
                    event_info['story_id'],
                    selected_choice.get('id'),
                    self.enable_ai
                )

                # 应用奖励
                if 'rewards' in result:
                    await self._apply_story_rewards(user_id, result['rewards'])

                return result
            except Exception as e:
                logger.error(f"处理LLM故事选择失败: {e}")
                # 回退到传统处理

        # 传统事件处理
        event_type = event_info.get('type')
        choice_id = selected_choice.get('id')
        event_data = event_info.get('event_data', {})

        # 获取玩家信息
        player = await self.player_mgr.get_player(user_id)
        if not player:
            raise WorldException("玩家不存在")

        # 根据事件类型和选择处理结果
        handlers = {
            'mysterious_npc': self._handle_mysterious_npc_choice,
            'monster_encounter': self._handle_monster_encounter_choice,
            'treasure_chest': self._handle_treasure_chest_choice,
            'ancient_ruin': self._handle_ancient_ruin_choice,
            'powerful_cultivator': self._handle_powerful_cultivator_choice,
            'secret_realm': self._handle_secret_realm_choice,
            'ancient_inheritance': self._handle_ancient_inheritance_choice,
            'spatial_anomaly': self._handle_spatial_anomaly_choice,
        }

        handler = handlers.get(event_type)
        if handler:
            return await handler(user_id, player, choice_id, event_data, location)
        else:
            # 默认处理
            return {
                'message': '什么也没有发生...',
                'rewards': {}
            }

    async def _handle_mysterious_npc_choice(self, user_id: str, player: Player, choice_id: str, event_data: Dict, location: Location) -> Dict:
        """处理神秘NPC选择"""
        if choice_id == 'talk':
            # 交谈获得情报或小奖励
            reward = random.randint(50, 200) * location.danger_level
            return {
                'message': '神秘修士向你透露了一些修炼心得...',
                'rewards': {'cultivation': reward}
            }
        elif choice_id == 'trade':
            # 交易
            cost = random.randint(200, 500) * location.danger_level
            reward = int(cost * random.uniform(1.2, 2.0))
            return {
                'message': f'你花费 {cost} 灵石从神秘修士处购买了一些物品，转手卖出获得 {reward} 灵石！',
                'rewards': {'spirit_stone': reward - cost}
            }
        else:  # ignore
            return {'message': '你离开了神秘修士...'}

    async def _handle_monster_encounter_choice(self, user_id: str, player: Player, choice_id: str, event_data: Dict, location: Location) -> Dict:
        """处理妖兽遭遇选择"""
        monster_level = event_data.get('monster_level', location.danger_level)

        if choice_id == 'fight':
            # 简单的战斗判定
            player_power = player.attack + player.defense + player.realm_level * 10
            monster_power = monster_level * 30 + random.randint(-10, 10)

            if player_power > monster_power:
                # 胜利
                reward = random.randint(100, 300) * monster_level
                return {
                    'message': f'激战之后，你成功击败了 {monster_level} 阶妖兽！',
                    'rewards': {'spirit_stone': reward}
                }
            else:
                # 失败
                damage = random.randint(50, 150) * monster_level
                return {
                    'message': f'你败在了妖兽手下，仓皇逃离...',
                    'damage': damage
                }
        else:  # flee
            cost = random.randint(50, 150)
            return {
                'message': f'你花费 {cost} 灵石使用了传送符逃离！',
                'rewards': {'spirit_stone': -cost}
            }

    async def _handle_treasure_chest_choice(self, user_id: str, player: Player, choice_id: str, event_data: Dict, location: Location) -> Dict:
        """处理宝箱选择"""
        chest_quality = event_data.get('chest_quality', location.danger_level)
        trap_chance = event_data.get('trap_chance', 0.3)

        if choice_id == 'open_direct':
            # 直接打开，有陷阱风险但奖励高
            if random.random() < trap_chance:
                damage = random.randint(100, 300) * chest_quality
                return {
                    'message': '宝箱是陷阱！你触发了机关！',
                    'damage': damage
                }
            else:
                reward = random.randint(500, 1000) * chest_quality
                return {
                    'message': '宝箱中装满了宝物！',
                    'rewards': {'spirit_stone': reward}
                }
        elif choice_id == 'open_careful':
            # 小心打开，安全但奖励减半
            reward = random.randint(250, 500) * chest_quality
            return {
                'message': '你小心翼翼地打开了宝箱...',
                'rewards': {'spirit_stone': reward}
            }
        else:  # ignore
            return {'message': '你选择不打开宝箱，离开了...'}

    async def _handle_ancient_ruin_choice(self, user_id: str, player: Player, choice_id: str, event_data: Dict, location: Location) -> Dict:
        """处理古代遗迹选择"""
        ruin_level = event_data.get('ruin_level', location.danger_level)

        if choice_id == 'explore':
            # 探索遗迹，随机结果
            roll = random.random()
            if roll < 0.3:
                # 获得大量奖励
                reward = random.randint(1000, 2000) * ruin_level
                return {
                    'message': '你在遗迹深处发现了前人留下的宝藏！',
                    'rewards': {'spirit_stone': reward, 'cultivation': reward // 2}
                }
            elif roll < 0.6:
                # 获得少量奖励
                reward = random.randint(300, 600) * ruin_level
                return {
                    'message': '你在遗迹中找到了一些有价值的东西...',
                    'rewards': {'spirit_stone': reward}
                }
            else:
                # 触发危险
                damage = random.randint(100, 300) * ruin_level
                return {
                    'message': '遗迹中的禁制突然发动，你受到了攻击！',
                    'damage': damage
                }
        else:  # mark
            return {'message': '你标记了遗迹的位置，打算日后再来探索...'}

    async def _handle_powerful_cultivator_choice(self, user_id: str, player: Player, choice_id: str, event_data: Dict, location: Location) -> Dict:
        """处理强大修士选择"""
        is_friendly = event_data.get('friendly', True)

        if choice_id == 'greet':
            if is_friendly:
                reward = random.randint(200, 500) * location.danger_level
                return {
                    'message': '前辈很欣赏你的礼貌，赠予了你一些修炼资源！',
                    'rewards': {'cultivation': reward}
                }
            else:
                return {'message': '对方冷冷地看了你一眼，没有理会...'}
        elif choice_id == 'challenge':
            # 切磋，失败概率高
            if random.random() < 0.2:
                reward = random.randint(500, 1000) * location.danger_level
                return {
                    'message': '你在切磋中表现出色，前辈传授了你一些经验！',
                    'rewards': {'cultivation': reward}
                }
            else:
                damage = random.randint(100, 300)
                return {
                    'message': '你在切磋中落败，受了一些轻伤...',
                    'damage': damage
                }
        else:  # avoid
            return {'message': '你选择避开这位强大的修士...'}

    async def _handle_secret_realm_choice(self, user_id: str, player: Player, choice_id: str, event_data: Dict, location: Location) -> Dict:
        """处理秘境入口选择"""
        realm_level = event_data.get('realm_level', location.danger_level)

        if choice_id == 'enter':
            # 进入秘境，高风险高收益
            roll = random.random()
            if roll < 0.4:
                # 大成功
                reward = random.randint(2000, 5000) * realm_level
                return {
                    'message': '你在秘境中获得了惊人的机缘！',
                    'rewards': {'spirit_stone': reward, 'cultivation': reward}
                }
            elif roll < 0.7:
                # 小成功
                reward = random.randint(500, 1500) * realm_level
                return {
                    'message': '你在秘境中获得了一些收获...',
                    'rewards': {'cultivation': reward}
                }
            else:
                # 危险
                damage = random.randint(200, 500) * realm_level
                return {
                    'message': '秘境中充满危险，你受了重伤！',
                    'damage': damage
                }
        else:  # later
            return {'message': '你标记了秘境入口的位置，打算实力提升后再来...'}

    async def _handle_ancient_inheritance_choice(self, user_id: str, player: Player, choice_id: str, event_data: Dict, location: Location) -> Dict:
        """处理古代传承选择"""
        inheritance_quality = event_data.get('inheritance_quality', location.danger_level)

        if choice_id == 'accept':
            # 接受传承，基于幸运和悟性判定
            success_rate = 0.3 + (player.luck / 200) + (player.comprehension / 200)
            if random.random() < success_rate:
                reward = random.randint(3000, 8000) * inheritance_quality
                return {
                    'message': '你通过了传承考验，获得了古代修士的传承！',
                    'rewards': {'cultivation': reward}
                }
            else:
                damage = random.randint(50, 200)
                return {
                    'message': '你未能通过传承考验，受到了反噬...',
                    'damage': damage,
                    'rewards': {'cultivation': 100 * inheritance_quality}
                }
        else:  # decline
            return {'message': '你选择放弃这次传承机会...'}

    async def _handle_spatial_anomaly_choice(self, user_id: str, player: Player, choice_id: str, event_data: Dict, location: Location) -> Dict:
        """处理空间异常选择"""
        anomaly_level = event_data.get('anomaly_level', location.danger_level)

        if choice_id == 'investigate':
            roll = random.random()
            if roll < 0.5:
                reward = random.randint(1000, 3000) * anomaly_level
                return {
                    'message': '你在空间裂缝中找到了珍贵的空间属性材料！',
                    'rewards': {'spirit_stone': reward}
                }
            else:
                damage = random.randint(150, 400) * anomaly_level
                return {
                    'message': '空间波动伤到了你！',
                    'damage': damage
                }
        else:  # avoid
            return {'message': '你明智地远离了不稳定的空间异常...'}

    async def _apply_story_rewards(self, user_id: str, rewards: Dict):
        """
        应用故事奖励

        Args:
            user_id: 用户ID
            rewards: 奖励字典
        """
        player = await self.player_mgr.get_player(user_id)
        if not player:
            return

        # 基础奖励
        base_rewards = rewards.get('base_rewards', {})

        # 灵石
        if 'spirit_stone' in base_rewards:
            spirit_stone = base_rewards['spirit_stone']
            await self.db.execute(
                "UPDATE players SET spirit_stone = spirit_stone + ? WHERE user_id = ?",
                (spirit_stone, user_id)
            )
            logger.info(f"玩家 {user_id} 获得灵石: {spirit_stone}")

        # 修为
        if 'cultivation' in base_rewards:
            cultivation = base_rewards['cultivation']
            await self.db.execute(
                "UPDATE players SET cultivation = cultivation + ? WHERE user_id = ?",
                (cultivation, user_id)
            )
            logger.info(f"玩家 {user_id} 获得修为: {cultivation}")

        # 特殊物品
        items = rewards.get('items', [])
        for item in items:
            await self.db.execute("""
                INSERT INTO items (
                    user_id, item_type, item_name, quality, description, effect
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                'special',
                item.get('name', '神秘物品'),
                item.get('quality', '凡品'),
                item.get('description', ''),
                item.get('effect', '')
            ))
            logger.info(f"玩家 {user_id} 获得物品: {item.get('name')}")

        # 伤害
        if 'damage' in base_rewards:
            damage = base_rewards['damage']
            await self.db.execute(
                "UPDATE players SET hp = MAX(1, hp - ?) WHERE user_id = ?",
                (damage, user_id)
            )
            logger.info(f"玩家 {user_id} 受到伤害: {damage}")
