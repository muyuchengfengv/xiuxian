"""
炼丹系统
实现丹药炼制、丹方管理等功能
"""

from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
import random
import json
from astrbot.api import logger

from ..core.database import DatabaseManager
from ..core.player import PlayerManager
from ..core.profession import ProfessionManager, ProfessionNotFoundError
from ..utils.exceptions import PlayerNotFoundError


class AlchemyError(Exception):
    """炼丹系统异常"""
    pass


class RecipeNotFoundError(AlchemyError):
    """丹方不存在"""
    pass


class InsufficientMaterialsError(AlchemyError):
    """材料不足"""
    pass


class InsufficientSpiritStoneError(AlchemyError):
    """灵石不足"""
    pass


class AlchemySystem:
    """炼丹系统"""

    # 丹药品质
    PILL_QUALITIES = {
        "废丹": {"effect": 0.0, "probability": 0.0},
        "下品": {"effect": 0.5, "probability": 0.4},
        "中品": {"effect": 1.0, "probability": 0.35},
        "上品": {"effect": 1.5, "probability": 0.2},
        "极品": {"effect": 2.0, "probability": 0.04},
        "神品": {"effect": 3.0, "probability": 0.01}
    }

    # 基础丹方配置
    BASE_RECIPES = [
        {
            "name": "回血丹",
            "rank": 1,
            "description": "恢复500点生命值的基础丹药",
            "recipe_type": "alchemy",
            "materials": json.dumps([
                {"name": "灵草", "quantity": 3},
                {"name": "朱砂", "quantity": 1}
            ]),
            "output_name": "回血丹",
            "output_quality": "中品",
            "base_success_rate": 60,
            "spirit_stone_cost": 100,
            "effect": json.dumps({"hp_restore": 500})
        },
        {
            "name": "回灵丹",
            "rank": 1,
            "description": "恢复300点法力值的基础丹药",
            "recipe_type": "alchemy",
            "materials": json.dumps([
                {"name": "灵草", "quantity": 2},
                {"name": "灵液", "quantity": 2}
            ]),
            "output_name": "回灵丹",
            "output_quality": "中品",
            "base_success_rate": 60,
            "spirit_stone_cost": 100,
            "effect": json.dumps({"mp_restore": 300})
        },
        {
            "name": "筑基丹",
            "rank": 2,
            "description": "帮助突破筑基期的珍贵丹药",
            "recipe_type": "alchemy",
            "materials": json.dumps([
                {"name": "筑基草", "quantity": 5},
                {"name": "妖兽内丹", "quantity": 1},
                {"name": "灵液", "quantity": 3}
            ]),
            "output_name": "筑基丹",
            "output_quality": "中品",
            "base_success_rate": 50,
            "spirit_stone_cost": 500,
            "effect": json.dumps({"cultivation": 2000, "breakthrough_bonus": 0.1})
        }
    ]

    def __init__(
        self,
        db: DatabaseManager,
        player_mgr: PlayerManager,
        profession_mgr: ProfessionManager
    ):
        """
        初始化炼丹系统

        Args:
            db: 数据库管理器
            player_mgr: 玩家管理器
            profession_mgr: 职业管理器
        """
        self.db = db
        self.player_mgr = player_mgr
        self.profession_mgr = profession_mgr

    async def init_base_recipes(self):
        """初始化基础丹方"""
        for recipe_data in self.BASE_RECIPES:
            # 检查是否已存在
            row = await self.db.fetchone(
                """
                SELECT id FROM recipes
                WHERE name = ? AND recipe_type = 'alchemy' AND user_id IS NULL
                """,
                (recipe_data['name'],)
            )

            if not row:
                # 插入丹方
                await self.db.execute(
                    """
                    INSERT INTO recipes (
                        user_id, recipe_type, name, rank, description,
                        materials, output_name, output_quality,
                        base_success_rate, source, is_ai_generated
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        None,  # 公共丹方
                        recipe_data['recipe_type'],
                        recipe_data['name'],
                        recipe_data['rank'],
                        recipe_data['description'],
                        recipe_data['materials'],
                        recipe_data['output_name'],
                        recipe_data['output_quality'],
                        recipe_data['base_success_rate'],
                        "系统预设",
                        0
                    )
                )

        logger.info("基础丹方初始化完成")

    async def refine_pill(
        self,
        user_id: str,
        recipe_id: int
    ) -> Dict[str, Any]:
        """
        炼制丹药

        Args:
            user_id: 玩家ID
            recipe_id: 丹方ID

        Returns:
            Dict: 炼制结果

        Raises:
            PlayerNotFoundError: 玩家不存在
            ProfessionNotFoundError: 未学习炼丹师
            RecipeNotFoundError: 丹方不存在
            InsufficientMaterialsError: 材料不足
            InsufficientSpiritStoneError: 灵石不足
        """
        # 获取玩家信息
        player = await self.player_mgr.get_player_or_error(user_id)

        # 获取炼丹师职业
        profession = await self.profession_mgr.get_profession(user_id, "alchemist")
        if not profession:
            raise ProfessionNotFoundError("尚未学习炼丹师职业")

        # 获取丹方
        recipe = await self._get_recipe(recipe_id)
        if not recipe:
            raise RecipeNotFoundError(f"丹方不存在: {recipe_id}")

        # 检查品级
        if recipe['rank'] > profession.rank:
            raise AlchemyError(f"丹方需要{recipe['rank']}品炼丹师,当前仅{profession.rank}品")

        # 解析材料需求
        materials_required = json.loads(recipe['materials'])

        # TODO: 检查材料是否足够 (需要物品系统)
        # 这里先简化处理,假设材料充足

        # 检查灵石
        spirit_stone_cost = 100  # 基础消耗
        if player.spirit_stone < spirit_stone_cost:
            raise InsufficientSpiritStoneError(f"灵石不足,需要{spirit_stone_cost}灵石")

        # 计算成功率
        base_success_rate = recipe['base_success_rate'] / 100.0
        success_rate = profession.get_success_rate()

        # 灵根加成
        if player.spirit_root_type in ["火", "木", "光"]:
            if player.spirit_root_type == "火":
                success_rate += 0.25  # 火系+25%
            elif player.spirit_root_type == "木":
                success_rate += 0.20  # 木系+20%
            elif player.spirit_root_type == "光":
                success_rate += 0.30  # 光系+30%

        # 限制最高成功率
        success_rate = min(0.95, success_rate)

        # 判断是否成功
        success = random.random() < success_rate

        if not success:
            # 炼制失败
            await self.player_mgr.add_spirit_stone(user_id, -spirit_stone_cost)

            # 记录炼制日志
            await self._log_crafting(
                user_id=user_id,
                recipe_id=recipe_id,
                success=False,
                output_quality="废丹",
                materials_used=json.dumps(materials_required),
                spirit_stone_cost=spirit_stone_cost,
                experience_gained=10
            )

            # 添加少量经验
            await self.profession_mgr.add_experience(user_id, "alchemist", 10)

            return {
                'success': False,
                'quality': "废丹",
                'pill_name': recipe['output_name'],
                'spirit_stone_cost': spirit_stone_cost,
                'experience_gained': 10,
                'message': f"炼制失败,丹药炸炉了!"
            }

        # 炼制成功,确定品质
        quality = self._determine_quality(success_rate, profession)

        # 消耗灵石
        await self.player_mgr.add_spirit_stone(user_id, -spirit_stone_cost)

        # TODO: 添加丹药到背包 (需要物品系统)

        # 获得经验
        exp_gain = self._calculate_experience(recipe['rank'], quality)
        await self.profession_mgr.add_experience(user_id, "alchemist", exp_gain)

        # 获得声望
        reputation_gain = recipe['rank'] * 10
        if quality in ["极品", "神品"]:
            reputation_gain *= 2
        await self.profession_mgr.add_reputation(user_id, "alchemist", reputation_gain)

        # 记录炼制日志
        await self._log_crafting(
            user_id=user_id,
            recipe_id=recipe_id,
            success=True,
            output_quality=quality,
            materials_used=json.dumps(materials_required),
            spirit_stone_cost=spirit_stone_cost,
            experience_gained=exp_gain
        )

        logger.info(f"玩家 {user_id} 炼制了 {quality} {recipe['output_name']}")

        return {
            'success': True,
            'quality': quality,
            'pill_name': recipe['output_name'],
            'spirit_stone_cost': spirit_stone_cost,
            'experience_gained': exp_gain,
            'reputation_gained': reputation_gain,
            'message': f"炼制成功!获得了{quality}{recipe['output_name']}!"
        }

    async def get_available_recipes(self, user_id: str) -> List[Dict[str, Any]]:
        """
        获取可用的丹方列表

        Args:
            user_id: 玩家ID

        Returns:
            List[Dict]: 丹方列表
        """
        # 获取炼丹师职业
        profession = await self.profession_mgr.get_profession(user_id, "alchemist")
        max_rank = profession.rank if profession else 1

        # 查询公共丹方和玩家拥有的丹方
        rows = await self.db.fetchall(
            """
            SELECT * FROM recipes
            WHERE recipe_type = 'alchemy'
            AND (user_id IS NULL OR user_id = ?)
            AND rank <= ?
            ORDER BY rank, name
            """,
            (user_id, max_rank)
        )

        recipes = []
        for row in rows:
            recipe_data = dict(row)
            recipes.append(recipe_data)

        return recipes

    async def format_recipe_list(self, user_id: str) -> str:
        """
        格式化丹方列表显示

        Args:
            user_id: 玩家ID

        Returns:
            str: 格式化的丹方列表
        """
        recipes = await self.get_available_recipes(user_id)
        profession = await self.profession_mgr.get_profession(user_id, "alchemist")

        if not profession:
            return (
                "📜 炼丹师丹方\n"
                "─" * 40 + "\n\n"
                "您还没有学习炼丹师职业\n\n"
                "💡 使用 /学习职业 炼丹师 学习炼丹"
            )

        lines = [
            f"📜 炼丹师丹方 ({profession.get_full_title()})",
            "─" * 40,
            ""
        ]

        if not recipes:
            lines.append("目前没有可用的丹方")
        else:
            for i, recipe in enumerate(recipes, 1):
                rank_color = "🟢" if recipe['rank'] <= profession.rank else "🔴"
                lines.append(
                    f"{i}. {rank_color} {recipe['name']} ({recipe['rank']}品)\n"
                    f"   {recipe['description']}\n"
                    f"   成功率: {recipe['base_success_rate']}%"
                )

        lines.extend([
            "",
            "💡 使用 /炼丹 [编号] 炼制丹药",
            "💡 使用 /丹方详情 [编号] 查看详细信息"
        ])

        return "\n".join(lines)

    async def _get_recipe(self, recipe_id: int) -> Optional[Dict[str, Any]]:
        """获取丹方信息"""
        row = await self.db.fetchone(
            "SELECT * FROM recipes WHERE id = ? AND recipe_type = 'alchemy'",
            (recipe_id,)
        )
        return dict(row) if row else None

    def _determine_quality(self, success_rate: float, profession) -> str:
        """
        确定丹药品质

        Args:
            success_rate: 成功率
            profession: 职业对象

        Returns:
            str: 品质
        """
        # 基础概率
        probabilities = {
            "神品": 0.01,
            "极品": 0.04,
            "上品": 0.20,
            "中品": 0.35,
            "下品": 0.40
        }

        # 品级加成
        rank_bonus = (profession.rank - 1) * 0.05
        probabilities["极品"] += rank_bonus * 0.3
        probabilities["上品"] += rank_bonus * 0.5
        probabilities["中品"] += rank_bonus * 0.2

        # 成功率加成
        if success_rate > 0.8:
            probabilities["神品"] += 0.02
            probabilities["极品"] += 0.06

        # 归一化
        total = sum(probabilities.values())
        probabilities = {k: v/total for k, v in probabilities.items()}

        # 随机选择
        rand = random.random()
        cumulative = 0.0

        for quality in ["神品", "极品", "上品", "中品", "下品"]:
            cumulative += probabilities.get(quality, 0)
            if rand <= cumulative:
                return quality

        return "中品"

    def _calculate_experience(self, rank: int, quality: str) -> int:
        """
        计算获得的经验

        Args:
            rank: 丹药品级
            quality: 丹药品质

        Returns:
            int: 经验值
        """
        base_exp = rank * 50

        quality_multiplier = {
            "下品": 1.0,
            "中品": 1.5,
            "上品": 2.0,
            "极品": 3.0,
            "神品": 5.0
        }

        return int(base_exp * quality_multiplier.get(quality, 1.0))

    async def _log_crafting(
        self,
        user_id: str,
        recipe_id: int,
        success: bool,
        output_quality: str,
        materials_used: str,
        spirit_stone_cost: int,
        experience_gained: int
    ):
        """记录炼制日志"""
        await self.db.execute(
            """
            INSERT INTO crafting_logs (
                user_id, craft_type, recipe_id, success,
                output_quality, materials_used, spirit_stone_cost,
                experience_gained, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                "alchemy",
                recipe_id,
                success,
                output_quality,
                materials_used,
                spirit_stone_cost,
                experience_gained,
                datetime.now().isoformat()
            )
        )
