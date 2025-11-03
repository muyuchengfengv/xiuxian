"""
坊市交易系统
负责物品/装备/功法的交易、上架、购买等功能
"""

import uuid
import json
from typing import Dict, List, Optional
from datetime import datetime
from astrbot.api import logger

from .database import DatabaseManager
from .player import PlayerManager
from .items import ItemManager
from ..utils import XiuxianException


class MarketError(XiuxianException):
    """坊市相关异常"""
    pass


class ItemNotOwnedError(MarketError):
    """物品不属于该用户异常"""
    pass


class ItemNotTradableError(MarketError):
    """物品不可交易异常"""
    pass


class ListingNotFoundError(MarketError):
    """市场商品不存在异常"""
    pass


class InsufficientSpiritStoneError(MarketError):
    """灵石不足异常"""
    pass


class MarketSystem:
    """坊市交易系统类"""

    def __init__(self, db: DatabaseManager, player_mgr: PlayerManager, item_mgr: ItemManager):
        """
        初始化坊市系统

        Args:
            db: 数据库管理器
            player_mgr: 玩家管理器
            item_mgr: 物品管理器
        """
        self.db = db
        self.player_mgr = player_mgr
        self.item_mgr = item_mgr

        # 交易税率（5%）
        self.transaction_tax_rate = 0.05

    async def initialize(self):
        """初始化数据库表（在主程序中调用）"""
        await self._ensure_market_tables()
        await self._init_npc_items()

    async def _init_npc_items(self):
        """初始化NPC上架的基础物品"""
        # 检查是否已经初始化过
        existing = await self.db.fetchone(
            "SELECT id FROM market_items WHERE seller_id = 'npc' LIMIT 1"
        )

        if existing:
            return  # 已经初始化过，不重复添加

        logger.info("正在初始化NPC坊市物品...")

        npc_items = [
            # ===== 炼气期丹药 =====
            {
                "item_type": "pill",
                "item_id": "npc_pill_1",
                "item_name": "回春丹",
                "quality": "凡品",
                "description": "恢复500点生命值的基础丹药",
                "price": 50,
                "quantity": 999,
                "attributes": json.dumps({"hp_restore": 500})
            },
            {
                "item_type": "pill",
                "item_id": "npc_pill_2",
                "item_name": "回灵丹",
                "quality": "凡品",
                "description": "恢复300点法力值的基础丹药",
                "price": 50,
                "quantity": 999,
                "attributes": json.dumps({"mp_restore": 300})
            },
            {
                "item_type": "pill",
                "item_id": "npc_pill_3",
                "item_name": "聚气丹",
                "quality": "灵品",
                "description": "增加500修为的炼气期丹药",
                "price": 200,
                "quantity": 500,
                "attributes": json.dumps({"cultivation": 500})
            },
            {
                "item_type": "pill",
                "item_id": "npc_pill_4",
                "item_name": "固元丹",
                "quality": "灵品",
                "description": "增加800修为的炼气期丹药",
                "price": 350,
                "quantity": 300,
                "attributes": json.dumps({"cultivation": 800})
            },

            # ===== 筑基期丹药 =====
            {
                "item_type": "pill",
                "item_id": "npc_pill_5",
                "item_name": "大还丹",
                "quality": "灵品",
                "description": "恢复2000点生命值的高级丹药",
                "price": 400,
                "quantity": 200,
                "attributes": json.dumps({"hp_restore": 2000})
            },
            {
                "item_type": "pill",
                "item_id": "npc_pill_6",
                "item_name": "凝神丹",
                "quality": "灵品",
                "description": "恢复1500点法力值",
                "price": 350,
                "quantity": 200,
                "attributes": json.dumps({"mp_restore": 1500})
            },
            {
                "item_type": "pill",
                "item_id": "npc_pill_7",
                "item_name": "培元丹",
                "quality": "宝品",
                "description": "增加2000修为的筑基期丹药",
                "price": 800,
                "quantity": 150,
                "attributes": json.dumps({"cultivation": 2000})
            },
            {
                "item_type": "pill",
                "item_id": "npc_pill_8",
                "item_name": "筑基丹",
                "quality": "宝品",
                "description": "增加3000修为，帮助筑基",
                "price": 1500,
                "quantity": 80,
                "attributes": json.dumps({"cultivation": 3000})
            },

            # ===== 金丹期丹药 =====
            {
                "item_type": "pill",
                "item_id": "npc_pill_9",
                "item_name": "破障丹",
                "quality": "宝品",
                "description": "增加8000修为的金丹期丹药",
                "price": 3000,
                "quantity": 50,
                "attributes": json.dumps({"cultivation": 8000})
            },
            {
                "item_type": "pill",
                "item_id": "npc_pill_10",
                "item_name": "金丹",
                "quality": "仙品",
                "description": "增加12000修为的金丹期至宝",
                "price": 6000,
                "quantity": 30,
                "attributes": json.dumps({"cultivation": 12000})
            },
            {
                "item_type": "pill",
                "item_id": "npc_pill_11",
                "item_name": "九转金丹",
                "quality": "仙品",
                "description": "恢复5000点生命值和3000点法力值",
                "price": 5000,
                "quantity": 20,
                "attributes": json.dumps({"hp_restore": 5000, "mp_restore": 3000})
            },

            # ===== 元婴期丹药 =====
            {
                "item_type": "pill",
                "item_id": "npc_pill_12",
                "item_name": "天元丹",
                "quality": "仙品",
                "description": "增加20000修为的元婴期丹药",
                "price": 15000,
                "quantity": 20,
                "attributes": json.dumps({"cultivation": 20000})
            },
            {
                "item_type": "pill",
                "item_id": "npc_pill_13",
                "item_name": "元婴丹",
                "quality": "神品",
                "description": "增加30000修为的元婴期至宝",
                "price": 30000,
                "quantity": 10,
                "attributes": json.dumps({"cultivation": 30000})
            },
            {
                "item_type": "pill",
                "item_id": "npc_pill_14",
                "item_name": "涅槃丹",
                "quality": "神品",
                "description": "完全恢复生命值和法力值",
                "price": 25000,
                "quantity": 5,
                "attributes": json.dumps({"hp_restore": 99999, "mp_restore": 99999})
            },

            # ===== 属性提升丹药 =====
            {
                "item_type": "pill",
                "item_id": "npc_pill_15",
                "item_name": "洗髓丹",
                "quality": "宝品",
                "description": "提升体质+5",
                "price": 2000,
                "quantity": 30,
                "attributes": json.dumps({"constitution": 5})
            },
            {
                "item_type": "pill",
                "item_id": "npc_pill_16",
                "item_name": "通灵丹",
                "quality": "宝品",
                "description": "提升悟性+5",
                "price": 2500,
                "quantity": 25,
                "attributes": json.dumps({"comprehension": 5})
            },
            {
                "item_type": "pill",
                "item_id": "npc_pill_17",
                "item_name": "聚灵丹",
                "quality": "宝品",
                "description": "提升灵力+5",
                "price": 2200,
                "quantity": 25,
                "attributes": json.dumps({"spiritual_power": 5})
            },

            # ===== 炼丹材料 =====
            {
                "item_type": "material",
                "item_id": "npc_mat_1",
                "item_name": "灵草",
                "quality": "凡品",
                "description": "炼丹的基础材料",
                "price": 20,
                "quantity": 9999,
                "attributes": json.dumps({"type": "herb"})
            },
            {
                "item_type": "material",
                "item_id": "npc_mat_2",
                "item_name": "聚气草",
                "quality": "凡品",
                "description": "炼制聚气丹的主要材料",
                "price": 30,
                "quantity": 9999,
                "attributes": json.dumps({"type": "herb"})
            },
            {
                "item_type": "material",
                "item_id": "npc_mat_3",
                "item_name": "固元草",
                "quality": "凡品",
                "description": "炼制固元丹的主要材料",
                "price": 40,
                "quantity": 9999,
                "attributes": json.dumps({"type": "herb"})
            },
            {
                "item_type": "material",
                "item_id": "npc_mat_4",
                "item_name": "朱砂",
                "quality": "凡品",
                "description": "炼丹的辅助材料",
                "price": 25,
                "quantity": 9999,
                "attributes": json.dumps({"type": "mineral"})
            },
            {
                "item_type": "material",
                "item_id": "npc_mat_5",
                "item_name": "灵液",
                "quality": "灵品",
                "description": "炼丹的精华材料",
                "price": 80,
                "quantity": 5000,
                "attributes": json.dumps({"type": "liquid"})
            },
            {
                "item_type": "material",
                "item_id": "npc_mat_6",
                "item_name": "百年灵芝",
                "quality": "灵品",
                "description": "珍贵的药材",
                "price": 300,
                "quantity": 500,
                "attributes": json.dumps({"type": "herb"})
            },
            {
                "item_type": "material",
                "item_id": "npc_mat_7",
                "item_name": "兽骨",
                "quality": "凡品",
                "description": "妖兽骨骼，炼丹材料",
                "price": 50,
                "quantity": 2000,
                "attributes": json.dumps({"type": "bone"})
            },

            # ===== 炼器材料 =====
            {
                "item_type": "material",
                "item_id": "npc_mat_8",
                "item_name": "玄铁",
                "quality": "凡品",
                "description": "炼器的基础材料",
                "price": 30,
                "quantity": 9999,
                "attributes": json.dumps({"type": "metal"})
            },
            {
                "item_type": "material",
                "item_id": "npc_mat_9",
                "item_name": "精铁",
                "quality": "灵品",
                "description": "炼器的优质材料",
                "price": 100,
                "quantity": 5000,
                "attributes": json.dumps({"type": "metal"})
            },
            {
                "item_type": "material",
                "item_id": "npc_mat_10",
                "item_name": "寒铁",
                "quality": "宝品",
                "description": "珍贵的炼器材料",
                "price": 500,
                "quantity": 500,
                "attributes": json.dumps({"type": "metal"})
            },

            # ===== 其他材料 =====
            {
                "item_type": "material",
                "item_id": "npc_mat_11",
                "item_name": "灵石碎片",
                "quality": "灵品",
                "description": "蕴含灵力的石头碎片",
                "price": 100,
                "quantity": 2000,
                "attributes": json.dumps({"type": "spirit"})
            },
            {
                "item_type": "material",
                "item_id": "npc_mat_12",
                "item_name": "符纸",
                "quality": "凡品",
                "description": "绘制符箓的基础材料",
                "price": 10,
                "quantity": 9999,
                "attributes": json.dumps({"type": "paper"})
            },
            {
                "item_type": "material",
                "item_id": "npc_mat_13",
                "item_name": "朱砂墨",
                "quality": "凡品",
                "description": "绘制符箓的墨汁",
                "price": 20,
                "quantity": 9999,
                "attributes": json.dumps({"type": "ink"})
            },

            # ===== 消耗品 =====
            {
                "item_type": "consumable",
                "item_id": "npc_cons_1",
                "item_name": "传送符",
                "quality": "灵品",
                "description": "可以传送到随机地点",
                "price": 500,
                "quantity": 100,
                "attributes": json.dumps({"type": "teleport", "target_location": "随机地点"})
            },
            {
                "item_type": "consumable",
                "item_id": "npc_cons_2",
                "item_name": "护体符",
                "quality": "宝品",
                "description": "获得1000点护盾，持续3回合",
                "price": 800,
                "quantity": 50,
                "attributes": json.dumps({"type": "defense", "shield": 1000, "duration": 3})
            },
        ]

        for item in npc_items:
            listing_id = str(uuid.uuid4())
            await self.db.execute(
                """
                INSERT INTO market_items (
                    id, seller_id, item_type, item_id, item_name, quality,
                    description, price, quantity, attributes, status, listed_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    listing_id,
                    "npc",
                    item["item_type"],
                    item["item_id"],
                    item["item_name"],
                    item["quality"],
                    item["description"],
                    item["price"],
                    item["quantity"],
                    item["attributes"],
                    "active",
                    datetime.now().isoformat(),
                    datetime.now().isoformat()
                )
            )

        logger.info(f"NPC坊市物品初始化完成，共上架 {len(npc_items)} 种物品")

    async def list_item(self, user_id: str, item_type: str, item_id: str,
                       price: int, quantity: int = 1) -> Dict:
        """
        上架物品到坊市

        Args:
            user_id: 用户ID
            item_type: 物品类型 (equipment/pill/material/method)
            item_id: 物品ID
            price: 价格
            quantity: 数量（装备固定为1）

        Returns:
            上架结果字典

        Raises:
            ItemNotOwnedError: 物品不属于该用户
            ItemNotTradableError: 物品不可交易
            ValueError: 参数错误
        """
        # 验证价格
        if price <= 0:
            raise ValueError("价格必须大于0")

        if quantity <= 0:
            raise ValueError("数量必须大于0")

        # 获取玩家信息
        player = await self.player_mgr.get_player_or_error(user_id)

        # 根据类型验证物品所有权和可交易性
        item_name = ""
        quality = ""
        description = ""
        attributes = ""

        if item_type == "equipment":
            # 装备类型
            from .equipment import EquipmentSystem
            equipment_sys = EquipmentSystem(self.db, self.player_mgr)

            equipment = await equipment_sys.get_equipment_by_id(item_id, user_id)

            # 检查装备是否已绑定
            if equipment.is_bound:
                raise ItemNotTradableError("已绑定的装备无法交易")

            # 检查装备是否已装备
            if equipment.is_equipped:
                raise ItemNotTradableError("已装备的物品无法交易，请先卸下")

            item_name = equipment.get_display_name()
            quality = equipment.quality
            description = getattr(equipment, 'description', '') or f"{equipment.quality}{equipment.type}装备"
            # 将装备属性序列化为JSON
            attributes = json.dumps({
                'attack': equipment.attack,
                'defense': equipment.defense,
                'hp_bonus': equipment.hp_bonus,
                'mp_bonus': equipment.mp_bonus,
                'enhance_level': equipment.enhance_level
            }, ensure_ascii=False)
            quantity = 1  # 装备数量固定为1

        elif item_type == "method":
            # 功法类型
            from .cultivation_method import CultivationMethodSystem
            method_sys = CultivationMethodSystem(self.db, self.player_mgr)

            method = await method_sys.get_method_by_id(item_id, user_id)

            # 检查功法是否已装备
            if method.is_equipped:
                raise ItemNotTradableError("已装备的功法无法交易，请先卸下")

            item_name = method.get_display_name()
            quality = method.quality
            description = method.description or f"{method.quality}品{method.method_type}功法"
            # 将功法属性序列化为JSON
            attributes = json.dumps({
                'method_type': method.method_type,
                'element_type': method.element_type,
                'grade': method.grade,
                'cultivation_speed_bonus': method.cultivation_speed_bonus
            }, ensure_ascii=False)
            quantity = 1  # 功法数量固定为1

        elif item_type in ["pill", "material"]:
            # 丹药或材料（使用物品系统）
            # 检查物品数量
            item_data = await self.item_mgr.get_item(user_id, item_id)
            if not item_data:
                raise ItemNotOwnedError(f"未找到物品 {item_id}")

            if item_data['quantity'] < quantity:
                raise ValueError(f"物品数量不足，当前拥有 {item_data['quantity']}")

            item_name = item_data['name']
            quality = item_data.get('quality', '凡品')
            description = item_data.get('description', '') or item_data.get('effect', '')
            attributes = item_data.get('effect', '')

            # 扣除物品数量
            await self.item_mgr.remove_item(user_id, item_id, quantity)
        else:
            raise ValueError(f"不支持的物品类型: {item_type}")

        # 创建市场商品记录
        listing_id = str(uuid.uuid4())
        listing_data = {
            'id': listing_id,
            'seller_id': user_id,
            'item_type': item_type,
            'item_id': item_id,
            'item_name': item_name,
            'quality': quality,
            'description': description,
            'price': price,
            'quantity': quantity,
            'attributes': attributes,
            'status': 'active',
            'listed_at': datetime.now().isoformat(),
            'created_at': datetime.now().isoformat()
        }

        # 插入数据库（将在下一个任务中实现表结构）
        await self._save_listing(listing_data)

        logger.info(f"玩家 {player.name} 上架物品: {item_name} x{quantity}, 价格 {price}")

        return {
            'success': True,
            'listing_id': listing_id,
            'item_name': item_name,
            'price': price,
            'quantity': quantity
        }

    async def get_market_items(self, item_type: Optional[str] = None,
                              page: int = 1, page_size: int = 20) -> List[Dict]:
        """
        查询坊市物品列表

        Args:
            item_type: 物品类型筛选（可选）
            page: 页码（从1开始）
            page_size: 每页数量

        Returns:
            市场物品列表
        """
        offset = (page - 1) * page_size

        # 构建查询条件
        where_clause = "WHERE status = 'active'"
        params = []

        if item_type:
            where_clause += " AND item_type = ?"
            params.append(item_type)

        # 查询市场物品
        sql = f"""
            SELECT * FROM market_items
            {where_clause}
            ORDER BY listed_at DESC
            LIMIT ? OFFSET ?
        """
        params.extend([page_size, offset])

        results = await self.db.fetchall(sql, tuple(params))

        items = []
        for result in results:
            item_data = dict(result)
            items.append(item_data)

        return items

    async def purchase_item(self, buyer_id: str, listing_id: str) -> Dict:
        """
        购买市场物品

        Args:
            buyer_id: 买家用户ID
            listing_id: 市场商品ID

        Returns:
            购买结果字典

        Raises:
            ListingNotFoundError: 商品不存在或已售出
            InsufficientSpiritStoneError: 灵石不足
            ValueError: 不能购买自己的商品
        """
        # 查询市场商品
        listing = await self._get_listing(listing_id)
        if not listing:
            raise ListingNotFoundError(f"商品 {listing_id} 不存在")

        if listing['status'] != 'active':
            raise ListingNotFoundError("该商品已售出或已下架")

        # 检查是否购买自己的商品
        if listing['seller_id'] == buyer_id:
            raise ValueError("不能购买自己上架的商品")

        # 获取买家和卖家信息
        buyer = await self.player_mgr.get_player_or_error(buyer_id)
        seller = await self.player_mgr.get_player(listing['seller_id'])

        # 计算税费
        price = listing['price']
        tax = int(price * self.transaction_tax_rate)
        seller_receive = price - tax

        # 检查买家灵石
        if buyer.spirit_stone < price:
            raise InsufficientSpiritStoneError(
                f"灵石不足！需要 {price}，当前拥有 {buyer.spirit_stone}"
            )

        # 使用数据库事务确保一致性
        try:
            # 扣除买家灵石
            buyer.spirit_stone -= price
            await self.player_mgr.update_player(buyer)

            # 增加卖家灵石
            if seller:
                seller.spirit_stone += seller_receive
                await self.player_mgr.update_player(seller)

            # 转移物品到买家
            item_type = listing['item_type']
            item_id = listing['item_id']
            quantity = listing['quantity']

            if item_type == "equipment":
                # 转移装备所有权
                await self.db.execute(
                    "UPDATE equipment SET user_id = ? WHERE id = ?",
                    (buyer_id, item_id)
                )
            elif item_type == "method":
                # 转移功法所有权
                await self.db.execute(
                    "UPDATE cultivation_methods SET owner_id = ?, user_id = ? WHERE id = ?",
                    (buyer_id, buyer_id, item_id)
                )
            elif item_type in ["pill", "material"]:
                # 添加物品到买家背包
                # 解析物品属性（effect）
                item_effect = None
                if listing.get('attributes'):
                    try:
                        item_effect = json.loads(listing['attributes'])
                    except:
                        item_effect = None

                await self.item_mgr.add_item(
                    user_id=buyer_id,
                    item_name=listing['item_name'],
                    item_type=item_type,
                    quality=listing.get('quality', '凡品'),
                    quantity=quantity,
                    description=listing.get('description', ''),
                    effect=item_effect
                )

            # 更新商品状态
            await self.db.execute(
                "UPDATE market_items SET status = 'sold', sold_at = ? WHERE id = ?",
                (datetime.now().isoformat(), listing_id)
            )

            # 记录交易历史
            transaction_id = str(uuid.uuid4())
            transaction_data = {
                'id': transaction_id,
                'listing_id': listing_id,
                'seller_id': listing['seller_id'],
                'buyer_id': buyer_id,
                'item_type': item_type,
                'item_id': item_id,
                'price': price,
                'quantity': quantity,
                'tax': tax,
                'transaction_time': datetime.now().isoformat()
            }
            await self._save_transaction(transaction_data)

            logger.info(
                f"交易完成: {buyer.name} 从 {seller.name if seller else '未知'} "
                f"购买 {listing['item_name']} x{quantity}, 价格 {price}"
            )

            return {
                'success': True,
                'item_name': listing['item_name'],
                'quantity': quantity,
                'price': price,
                'tax': tax,
                'seller_receive': seller_receive,
                'buyer_remaining': buyer.spirit_stone
            }

        except Exception as e:
            logger.error(f"购买物品失败: {e}", exc_info=True)
            raise MarketError(f"交易失败: {str(e)}")

    async def cancel_listing(self, user_id: str, listing_id: str) -> Dict:
        """
        取消上架（下架）

        Args:
            user_id: 用户ID
            listing_id: 市场商品ID

        Returns:
            取消结果字典

        Raises:
            ListingNotFoundError: 商品不存在
            ValueError: 商品不属于该用户或已售出
        """
        # 查询市场商品
        listing = await self._get_listing(listing_id)
        if not listing:
            raise ListingNotFoundError(f"商品 {listing_id} 不存在")

        # 验证所有权
        if listing['seller_id'] != user_id:
            raise ValueError("只能下架自己的商品")

        if listing['status'] != 'active':
            raise ValueError("该商品已售出或已下架")

        # 退还物品
        item_type = listing['item_type']
        item_id = listing['item_id']
        quantity = listing['quantity']

        if item_type in ["pill", "material"]:
            # 退还丹药或材料
            # 解析物品属性（effect）
            item_effect = None
            if listing.get('attributes'):
                try:
                    item_effect = json.loads(listing['attributes'])
                except:
                    item_effect = None

            await self.item_mgr.add_item(
                user_id=user_id,
                item_name=listing['item_name'],
                item_type=item_type,
                quality=listing.get('quality', '凡品'),
                quantity=quantity,
                description=listing.get('description', ''),
                effect=item_effect
            )

        # 更新商品状态
        await self.db.execute(
            "UPDATE market_items SET status = 'cancelled' WHERE id = ?",
            (listing_id,)
        )

        player = await self.player_mgr.get_player_or_error(user_id)
        logger.info(f"玩家 {player.name} 下架物品: {listing['item_name']}")

        return {
            'success': True,
            'item_name': listing['item_name'],
            'quantity': quantity
        }

    async def get_transaction_history(self, user_id: str, limit: int = 10) -> List[Dict]:
        """
        查询交易历史

        Args:
            user_id: 用户ID
            limit: 限制返回数量

        Returns:
            交易历史列表
        """
        sql = """
            SELECT * FROM market_transactions
            WHERE seller_id = ? OR buyer_id = ?
            ORDER BY transaction_time DESC
            LIMIT ?
        """
        results = await self.db.fetchall(sql, (user_id, user_id, limit))

        transactions = []
        for result in results:
            trans_data = dict(result)
            transactions.append(trans_data)

        return transactions

    async def get_my_listings(self, user_id: str) -> List[Dict]:
        """
        查询我的上架物品

        Args:
            user_id: 用户ID

        Returns:
            上架物品列表
        """
        sql = """
            SELECT * FROM market_items
            WHERE seller_id = ? AND status = 'active'
            ORDER BY listed_at DESC
        """
        results = await self.db.fetchall(sql, (user_id,))

        listings = []
        for result in results:
            listing_data = dict(result)
            listings.append(listing_data)

        return listings

    # ========== 内部辅助方法 ==========

    async def _save_listing(self, listing_data: Dict):
        """保存市场商品记录"""
        columns = list(listing_data.keys())
        placeholders = ', '.join(['?' for _ in columns])
        values = list(listing_data.values())

        sql = f"INSERT INTO market_items ({', '.join(columns)}) VALUES ({placeholders})"
        await self.db.execute(sql, values)

    async def _get_listing(self, listing_id: str) -> Optional[Dict]:
        """获取市场商品信息"""
        result = await self.db.fetchone(
            "SELECT * FROM market_items WHERE id = ?",
            (listing_id,)
        )
        return dict(result) if result else None

    async def _save_transaction(self, transaction_data: Dict):
        """保存交易记录"""
        columns = list(transaction_data.keys())
        placeholders = ', '.join(['?' for _ in columns])
        values = list(transaction_data.values())

        sql = f"INSERT INTO market_transactions ({', '.join(columns)}) VALUES ({placeholders})"
        await self.db.execute(sql, values)

    async def _ensure_market_tables(self):
        """确保坊市数据库表存在"""
        # 创建market_items表
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS market_items (
                id TEXT PRIMARY KEY,
                seller_id TEXT NOT NULL,
                item_type TEXT NOT NULL,
                item_id TEXT NOT NULL,
                item_name TEXT NOT NULL,
                quality TEXT,
                description TEXT,
                price INTEGER NOT NULL,
                quantity INTEGER DEFAULT 1,
                attributes TEXT,
                status TEXT DEFAULT 'active',
                listed_at TEXT NOT NULL,
                created_at TEXT,
                sold_at TEXT
            )
        """)

        # 创建market_transactions表
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS market_transactions (
                id TEXT PRIMARY KEY,
                listing_id TEXT NOT NULL,
                seller_id TEXT NOT NULL,
                buyer_id TEXT NOT NULL,
                item_type TEXT NOT NULL,
                item_id TEXT NOT NULL,
                price INTEGER NOT NULL,
                quantity INTEGER NOT NULL,
                tax INTEGER DEFAULT 0,
                transaction_time TEXT NOT NULL
            )
        """)

        # 创建索引以提高查询性能
        # 市场物品索引
        await self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_market_items_type
            ON market_items(item_type, status)
        """)

        await self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_market_items_seller
            ON market_items(seller_id)
        """)

        # 交易记录索引
        await self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_transactions_buyer
            ON market_transactions(buyer_id)
        """)

        await self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_transactions_seller
            ON market_transactions(seller_id)
        """)

        logger.info("坊市数据库表和索引已初始化")
