"""
物品管理系统
负责物品的使用、效果应用等功能
"""

from typing import Optional, Dict, Any
import json
from datetime import datetime
from astrbot.api import logger

from .database import DatabaseManager
from .player import PlayerManager
from ..models.player_model import Player
from ..utils.exceptions import PlayerNotFoundError


class ItemError(Exception):
    """物品系统基础异常"""
    pass


class ItemNotFoundError(ItemError):
    """物品不存在异常"""
    pass


class InsufficientItemError(ItemError):
    """物品数量不足异常"""
    pass


class ItemCannotUseError(ItemError):
    """物品无法使用异常"""
    pass


class ItemManager:
    """物品管理器"""

    def __init__(self, db: DatabaseManager, player_mgr: PlayerManager):
        """
        初始化物品管理器

        Args:
            db: 数据库管理器
            player_mgr: 玩家管理器
        """
        self.db = db
        self.player_mgr = player_mgr

    async def get_item(self, user_id: str, item_name: str) -> Optional[Dict[str, Any]]:
        """
        获取玩家的物品信息

        Args:
            user_id: 用户ID
            item_name: 物品名称

        Returns:
            物品信息字典，如果不存在则返回None
        """
        result = await self.db.fetchone(
            "SELECT * FROM items WHERE user_id = ? AND item_name = ?",
            (user_id, item_name)
        )

        if result is None:
            return None

        return dict(result)

    async def get_player_items(self, user_id: str, item_type: Optional[str] = None) -> list:
        """
        获取玩家的所有物品

        Args:
            user_id: 用户ID
            item_type: 物品类型筛选（可选）

        Returns:
            物品列表
        """
        if item_type:
            results = await self.db.fetchall(
                "SELECT * FROM items WHERE user_id = ? AND item_type = ? ORDER BY created_at DESC",
                (user_id, item_type)
            )
        else:
            results = await self.db.fetchall(
                "SELECT * FROM items WHERE user_id = ? ORDER BY item_type, created_at DESC",
                (user_id,)
            )

        return [dict(row) for row in results]

    async def add_item(self, user_id: str, item_name: str, item_type: str,
                       quality: str = "凡品", quantity: int = 1,
                       description: str = "", effect: Dict[str, Any] = None) -> bool:
        """
        添加物品到玩家背包

        Args:
            user_id: 用户ID
            item_name: 物品名称
            item_type: 物品类型（pill/talisman/material/consumable）
            quality: 品质
            quantity: 数量
            description: 描述
            effect: 效果（JSON格式）

        Returns:
            是否成功
        """
        # 检查是否已有该物品
        existing_item = await self.get_item(user_id, item_name)

        if existing_item:
            # 如果已存在，增加数量
            await self.db.execute(
                "UPDATE items SET quantity = quantity + ? WHERE user_id = ? AND item_name = ?",
                (quantity, user_id, item_name)
            )
        else:
            # 如果不存在，创建新物品
            effect_json = json.dumps(effect, ensure_ascii=False) if effect else None

            await self.db.execute("""
                INSERT INTO items (user_id, item_type, item_name, quality, quantity, description, effect)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_id, item_type, item_name, quality, quantity, description, effect_json))

        logger.info(f"玩家 {user_id} 获得物品: {item_name} x{quantity}")
        return True

    async def consume_item(self, user_id: str, item_name: str, quantity: int = 1) -> bool:
        """
        消耗物品

        Args:
            user_id: 用户ID
            item_name: 物品名称
            quantity: 消耗数量

        Returns:
            是否成功

        Raises:
            ItemNotFoundError: 物品不存在
            InsufficientItemError: 物品数量不足
        """
        item = await self.get_item(user_id, item_name)

        if not item:
            raise ItemNotFoundError(f"物品 {item_name} 不存在")

        if item['quantity'] < quantity:
            raise InsufficientItemError(f"物品 {item_name} 数量不足（需要{quantity}，拥有{item['quantity']}）")

        # 减少数量
        new_quantity = item['quantity'] - quantity

        if new_quantity <= 0:
            # 删除物品
            await self.db.execute(
                "DELETE FROM items WHERE user_id = ? AND item_name = ?",
                (user_id, item_name)
            )
        else:
            # 更新数量
            await self.db.execute(
                "UPDATE items SET quantity = ? WHERE user_id = ? AND item_name = ?",
                (new_quantity, user_id, item_name)
            )

        logger.info(f"玩家 {user_id} 消耗物品: {item_name} x{quantity}")
        return True

    async def use_item(self, user_id: str, item_name: str) -> Dict[str, Any]:
        """
        使用物品

        Args:
            user_id: 用户ID
            item_name: 物品名称

        Returns:
            使用结果字典，包含：
            {
                'success': bool,
                'message': str,
                'effects': Dict[str, Any]
            }

        Raises:
            PlayerNotFoundError: 玩家不存在
            ItemNotFoundError: 物品不存在
            ItemCannotUseError: 物品无法使用
        """
        # 获取玩家
        player = await self.player_mgr.get_player_or_error(user_id)

        # 获取物品
        item = await self.get_item(user_id, item_name)
        if not item:
            raise ItemNotFoundError(f"储物袋中没有 {item_name}")

        # 解析效果
        effect = json.loads(item['effect']) if item['effect'] else {}

        # 根据物品类型处理
        item_type = item['item_type']

        if item_type == 'pill':
            # 丹药效果
            result = await self._use_pill(player, item, effect)
        elif item_type == 'talisman':
            # 符箓效果
            result = await self._use_talisman(player, item, effect)
        elif item_type == 'consumable':
            # 消耗品效果
            result = await self._use_consumable(player, item, effect)
        else:
            raise ItemCannotUseError(f"{item_name} 无法使用（类型：{item_type}）")

        # 如果使用成功，消耗物品
        if result['success']:
            await self.consume_item(user_id, item_name, 1)
            # 更新玩家数据
            await self.player_mgr.update_player(player)

        return result

    async def _use_pill(self, player: Player, item: Dict[str, Any], effect: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用丹药

        Args:
            player: 玩家对象
            item: 物品信息
            effect: 效果字典

        Returns:
            使用结果
        """
        messages = []
        effects_applied = {}

        # 回复生命值
        if 'hp_restore' in effect:
            hp_restore = effect['hp_restore']
            old_hp = player.hp
            player.hp = min(player.max_hp, player.hp + hp_restore)
            actual_restore = player.hp - old_hp
            messages.append(f"恢复生命值 {actual_restore}")
            effects_applied['hp_restore'] = actual_restore

        # 回复法力值
        if 'mp_restore' in effect:
            mp_restore = effect['mp_restore']
            old_mp = player.mp
            player.mp = min(player.max_mp, player.mp + mp_restore)
            actual_restore = player.mp - old_mp
            messages.append(f"恢复法力值 {actual_restore}")
            effects_applied['mp_restore'] = actual_restore

        # 增加修为
        if 'cultivation' in effect:
            cultivation_gain = effect['cultivation']
            player.cultivation += cultivation_gain
            messages.append(f"修为 +{cultivation_gain}")
            effects_applied['cultivation'] = cultivation_gain

        # 永久属性提升
        if 'permanent_stats' in effect:
            stats = effect['permanent_stats']
            for stat_name, value in stats.items():
                if hasattr(player, stat_name):
                    old_value = getattr(player, stat_name)
                    setattr(player, stat_name, old_value + value)
                    messages.append(f"{stat_name} +{value}")
                    effects_applied[f'permanent_{stat_name}'] = value

        # 临时BUFF（暂时只记录，实际应用需要buff系统）
        if 'temporary_buff' in effect:
            buff = effect['temporary_buff']
            messages.append(f"获得临时增益：{buff.get('name', '未知效果')}")
            effects_applied['buff'] = buff

        # 特殊效果
        if 'special' in effect:
            special = effect['special']
            messages.append(f"触发特殊效果：{special}")
            effects_applied['special'] = special

        message = f"使用 {item['item_name']}，" + "，".join(messages)

        return {
            'success': True,
            'message': message,
            'effects': effects_applied
        }

    async def _use_talisman(self, player: Player, item: Dict[str, Any], effect: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用符箓

        Args:
            player: 玩家对象
            item: 物品信息
            effect: 效果字典

        Returns:
            使用结果
        """
        messages = []
        effects_applied = {}

        # 攻击型符箓
        if effect.get('type') == 'attack':
            damage = effect.get('damage', 0)
            messages.append(f"释放攻击符箓，造成 {damage} 点伤害")
            effects_applied['damage'] = damage

        # 防御型符箓
        elif effect.get('type') == 'defense':
            shield = effect.get('shield', 0)
            duration = effect.get('duration', 0)
            messages.append(f"获得 {shield} 点护盾，持续 {duration} 回合")
            effects_applied['shield'] = shield
            effects_applied['duration'] = duration

        # 辅助型符箓
        elif effect.get('type') == 'support':
            buff_type = effect.get('buff_type', '')
            buff_value = effect.get('buff_value', 0)
            duration = effect.get('duration', 0)
            messages.append(f"{buff_type} +{buff_value}，持续 {duration} 回合")
            effects_applied['buff_type'] = buff_type
            effects_applied['buff_value'] = buff_value
            effects_applied['duration'] = duration

        # 传送符
        elif effect.get('type') == 'teleport':
            target_location = effect.get('target_location', '随机地点')
            messages.append(f"传送至 {target_location}")
            effects_applied['teleport_to'] = target_location

        # 探测符
        elif effect.get('type') == 'detect':
            detect_range = effect.get('range', 100)
            messages.append(f"探测周围 {detect_range} 米范围")
            effects_applied['detect_range'] = detect_range

        # 其他符箓效果
        else:
            description = effect.get('description', '未知效果')
            messages.append(description)
            effects_applied = effect

        message = f"使用 {item['item_name']}，" + "，".join(messages)

        return {
            'success': True,
            'message': message,
            'effects': effects_applied
        }

    async def _use_consumable(self, player: Player, item: Dict[str, Any], effect: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用其他消耗品

        Args:
            player: 玩家对象
            item: 物品信息
            effect: 效果字典

        Returns:
            使用结果
        """
        messages = []
        effects_applied = {}

        # 经验道具
        if 'experience' in effect:
            exp_gain = effect['experience']
            # 这里可以添加经验系统的逻辑
            messages.append(f"获得经验 {exp_gain}")
            effects_applied['experience'] = exp_gain

        # 灵石道具
        if 'spirit_stone' in effect:
            stone_gain = effect['spirit_stone']
            player.spirit_stone += stone_gain
            messages.append(f"灵石 +{stone_gain}")
            effects_applied['spirit_stone'] = stone_gain

        # 其他效果
        if 'description' in effect:
            messages.append(effect['description'])

        message = f"使用 {item['item_name']}，" + "，".join(messages) if messages else f"使用了 {item['item_name']}"

        return {
            'success': True,
            'message': message,
            'effects': effects_applied
        }

    async def has_item(self, user_id: str, item_name: str, quantity: int = 1) -> bool:
        """
        检查玩家是否拥有足够数量的物品

        Args:
            user_id: 用户ID
            item_name: 物品名称
            quantity: 需要的数量

        Returns:
            是否拥有
        """
        item = await self.get_item(user_id, item_name)
        if not item:
            return False

        return item['quantity'] >= quantity

    async def get_item_count(self, user_id: str, item_name: str) -> int:
        """
        获取玩家拥有的物品数量

        Args:
            user_id: 用户ID
            item_name: 物品名称

        Returns:
            物品数量
        """
        item = await self.get_item(user_id, item_name)
        if not item:
            return 0

        return item['quantity']
