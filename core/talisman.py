"""
符箓系统
实现符箓制作、使用、管理等功能
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import random
import json
from astrbot.api import logger

from ..core.database import DatabaseManager
from ..core.player import PlayerManager
from ..core.profession import ProfessionManager, ProfessionNotFoundError
from ..utils.exceptions import PlayerNotFoundError


class TalismanError(Exception):
    """符箓系统异常"""
    pass


class TalismanPatternNotFoundError(TalismanError):
    """符箓配方不存在"""
    pass


class InsufficientMaterialsError(TalismanError):
    """材料不足"""
    pass


class InsufficientSpiritStoneError(TalismanError):
    """灵石不足"""
    pass


class TalismanSystem:
    """符箓系统"""

    # 符箓类型
    TALISMAN_TYPES = {
        "attack": {
            "name": "攻击符箓",
            "description": "造成伤害的符箓",
            "icon": "⚔️"
        },
        "defense": {
            "name": "防御符箓",
            "description": "提供防护的符箓",
            "icon": "🛡️"
        },
        "assist": {
            "name": "辅助符箓",
            "description": "提供增益效果的符箓",
            "icon": "✨"
        },
        "healing": {
            "name": "治疗符箓",
            "description": "恢复生命或法力的符箓",
            "icon": "💚"
        },
        "special": {
            "name": "特殊符箓",
            "description": "具有特殊效果的符箓",
            "icon": "🎴"
        }
    }

    # 基础符箓配置
    BASE_TALISMANS = [
        {
            "name": "火球符",
            "rank": 1,
            "talisman_type": "attack",
            "description": "释放火球攻击敌人,造成100点火系伤害",
            "materials": json.dumps([
                {"name": "符纸", "quantity": 1},
                {"name": "朱砂", "quantity": 1}
            ]),
            "base_success_rate": 75,
            "spirit_stone_cost": 50,
            "effects": json.dumps({
                "damage": 100,
                "element": "fire",
                "target": "single"
            }),
            "cooldown_seconds": 0,
            "duration_days": 30
        },
        {
            "name": "护身符",
            "rank": 1,
            "talisman_type": "defense",
            "description": "临时提供护盾,吸收200点伤害",
            "materials": json.dumps([
                {"name": "符纸", "quantity": 1},
                {"name": "朱砂", "quantity": 1},
                {"name": "灵兽血", "quantity": 1}
            ]),
            "base_success_rate": 70,
            "spirit_stone_cost": 80,
            "effects": json.dumps({
                "shield": 200,
                "duration": 300
            }),
            "cooldown_seconds": 0,
            "duration_days": 30
        },
        {
            "name": "神行符",
            "rank": 1,
            "talisman_type": "assist",
            "description": "提升移动速度50%,持续5分钟",
            "materials": json.dumps([
                {"name": "符纸", "quantity": 1},
                {"name": "疾风草", "quantity": 2}
            ]),
            "base_success_rate": 80,
            "spirit_stone_cost": 60,
            "effects": json.dumps({
                "speed_boost": 0.5,
                "duration": 300
            }),
            "cooldown_seconds": 0,
            "duration_days": 30
        },
        {
            "name": "疗伤符",
            "rank": 1,
            "talisman_type": "healing",
            "description": "立即恢复500点生命值",
            "materials": json.dumps([
                {"name": "符纸", "quantity": 1},
                {"name": "回春草", "quantity": 3}
            ]),
            "base_success_rate": 70,
            "spirit_stone_cost": 100,
            "effects": json.dumps({
                "hp_restore": 500
            }),
            "cooldown_seconds": 0,
            "duration_days": 30
        },
        {
            "name": "五雷符",
            "rank": 2,
            "talisman_type": "attack",
            "description": "召唤五道天雷,造成500点雷系伤害",
            "materials": json.dumps([
                {"name": "灵符纸", "quantity": 1},
                {"name": "妖兽精血", "quantity": 2},
                {"name": "雷霆石", "quantity": 1}
            ]),
            "base_success_rate": 60,
            "spirit_stone_cost": 200,
            "effects": json.dumps({
                "damage": 500,
                "element": "thunder",
                "target": "area",
                "count": 5
            }),
            "cooldown_seconds": 0,
            "duration_days": 30
        },
        {
            "name": "金刚符",
            "rank": 2,
            "talisman_type": "defense",
            "description": "提升防御力50%,持续10分钟",
            "materials": json.dumps([
                {"name": "灵符纸", "quantity": 1},
                {"name": "金刚石粉", "quantity": 3}
            ]),
            "base_success_rate": 65,
            "spirit_stone_cost": 150,
            "effects": json.dumps({
                "defense_boost": 0.5,
                "duration": 600
            }),
            "cooldown_seconds": 0,
            "duration_days": 30
        },
        {
            "name": "传送符",
            "rank": 2,
            "talisman_type": "special",
            "description": "瞬间传送到指定地点",
            "materials": json.dumps([
                {"name": "灵符纸", "quantity": 1},
                {"name": "空间石", "quantity": 1},
                {"name": "灵液", "quantity": 5}
            ]),
            "base_success_rate": 50,
            "spirit_stone_cost": 300,
            "effects": json.dumps({
                "teleport": True
            }),
            "cooldown_seconds": 3600,  # 1小时冷却
            "duration_days": 60
        },
        {
            "name": "替身符",
            "rank": 3,
            "talisman_type": "special",
            "description": "抵挡一次致命伤害",
            "materials": json.dumps([
                {"name": "金符纸", "quantity": 1},
                {"name": "替身草", "quantity": 1},
                {"name": "凤凰羽", "quantity": 1}
            ]),
            "base_success_rate": 45,
            "spirit_stone_cost": 500,
            "effects": json.dumps({
                "revive": True,
                "hp_percent": 0.5
            }),
            "cooldown_seconds": 0,
            "duration_days": 90
        },
        {
            "name": "万剑符",
            "rank": 3,
            "talisman_type": "attack",
            "description": "召唤万剑齐发,造成大范围1000点伤害",
            "materials": json.dumps([
                {"name": "金符纸", "quantity": 1},
                {"name": "剑气石", "quantity": 10},
                {"name": "妖兽精血", "quantity": 5}
            ]),
            "base_success_rate": 40,
            "spirit_stone_cost": 800,
            "effects": json.dumps({
                "damage": 1000,
                "element": "metal",
                "target": "large_area",
                "visual": "sword_rain"
            }),
            "cooldown_seconds": 0,
            "duration_days": 90
        }
    ]

    def __init__(
        self,
        db: DatabaseManager,
        player_mgr: PlayerManager,
        profession_mgr: ProfessionManager
    ):
        """
        初始化符箓系统

        Args:
            db: 数据库管理器
            player_mgr: 玩家管理器
            profession_mgr: 职业管理器
        """
        self.db = db
        self.player_mgr = player_mgr
        self.profession_mgr = profession_mgr

    async def init_base_talismans(self):
        """初始化基础符箓配方"""
        for talisman_data in self.BASE_TALISMANS:
            # 检查是否已存在
            row = await self.db.fetchone(
                """
                SELECT id FROM recipes
                WHERE name = ? AND recipe_type = 'talisman' AND user_id IS NULL
                """,
                (talisman_data['name'],)
            )

            if not row:
                # 插入符箓配方
                await self.db.execute(
                    """
                    INSERT INTO recipes (
                        user_id, recipe_type, name, rank, description,
                        materials, output_name, base_success_rate,
                        special_requirements, source, is_ai_generated
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        None,  # 公共符箓
                        'talisman',
                        talisman_data['name'],
                        talisman_data['rank'],
                        talisman_data['description'],
                        talisman_data['materials'],
                        talisman_data['name'],
                        talisman_data['base_success_rate'],
                        json.dumps({
                            "talisman_type": talisman_data['talisman_type'],
                            "spirit_stone_cost": talisman_data['spirit_stone_cost'],
                            "effects": talisman_data['effects'],
                            "cooldown_seconds": talisman_data['cooldown_seconds'],
                            "duration_days": talisman_data['duration_days']
                        }),
                        "系统预设",
                        0
                    )
                )

        logger.info("基础符箓配方初始化完成")

    async def craft_talisman(
        self,
        user_id: str,
        talisman_id: int,
        quantity: int = 1
    ) -> Dict[str, Any]:
        """
        制作符箓

        Args:
            user_id: 玩家ID
            talisman_id: 符箓配方ID
            quantity: 制作数量

        Returns:
            Dict: 制作结果

        Raises:
            PlayerNotFoundError: 玩家不存在
            ProfessionNotFoundError: 未学习符箓师
            TalismanPatternNotFoundError: 符箓配方不存在
            InsufficientMaterialsError: 材料不足
            InsufficientSpiritStoneError: 灵石不足
        """
        # 获取玩家信息
        player = await self.player_mgr.get_player_or_error(user_id)

        # 获取符箓师职业
        profession = await self.profession_mgr.get_profession(user_id, "talisman_master")
        if not profession:
            raise ProfessionNotFoundError("尚未学习符箓师职业")

        # 获取符箓配方
        talisman = await self._get_talisman_pattern(talisman_id)
        if not talisman:
            raise TalismanPatternNotFoundError(f"符箓配方不存在: {talisman_id}")

        # 检查品级
        if talisman['rank'] > profession.rank:
            raise TalismanError(f"符箓需要{talisman['rank']}品符箓师,当前仅{profession.rank}品")

        # 解析材料需求和特殊要求
        materials_required = json.loads(talisman['materials'])
        special_req = json.loads(talisman.get('special_requirements', '{}'))

        talisman_type = special_req.get('talisman_type', 'attack')
        spirit_stone_cost = special_req.get('spirit_stone_cost', 50) * quantity

        # TODO: 检查材料是否足够 (需要物品系统)

        # 检查灵石
        if player.spirit_stone < spirit_stone_cost:
            raise InsufficientSpiritStoneError(f"灵石不足,需要{spirit_stone_cost}灵石")

        # 计算成功率
        base_success_rate = talisman['base_success_rate'] / 100.0
        success_rate = profession.get_success_rate()

        # 灵根加成
        if player.spirit_root_type in ["风", "雷", "暗"]:
            if player.spirit_root_type == "风":
                success_rate += 0.25  # 风系+25%
            elif player.spirit_root_type == "雷":
                success_rate += 0.30  # 雷系+30%
            elif player.spirit_root_type == "暗":
                success_rate += 0.25  # 暗系+25%

        # 批量制作降低成功率
        if quantity > 1:
            success_rate -= (quantity - 1) * 0.05
            success_rate = max(0.3, success_rate)

        # 限制最高成功率
        success_rate = min(0.95, success_rate)

        # 制作每个符箓
        success_count = 0
        failed_count = 0

        for _ in range(quantity):
            if random.random() < success_rate:
                success_count += 1
            else:
                failed_count += 1

        # 消耗灵石
        await self.player_mgr.add_spirit_stone(user_id, -spirit_stone_cost)

        # TODO: 添加符箓到背包 (需要物品系统)
        # 这里暂时存储到items表
        if success_count > 0:
            # 检查是否已有该符箓
            existing = await self.db.fetchone(
                """
                SELECT id, quantity FROM items
                WHERE user_id = ? AND item_type = 'talisman' AND item_name = ?
                """,
                (user_id, talisman['name'])
            )

            if existing:
                # 更新数量
                new_quantity = existing['quantity'] + success_count
                await self.db.execute(
                    "UPDATE items SET quantity = ? WHERE id = ?",
                    (new_quantity, existing['id'])
                )
            else:
                # 创建新符箓
                expires_at = datetime.now() + timedelta(days=special_req.get('duration_days', 30))
                await self.db.execute(
                    """
                    INSERT INTO items (
                        user_id, item_type, item_name, quality, quantity,
                        description, effect, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user_id,
                        'talisman',
                        talisman['name'],
                        f"{talisman['rank']}品",
                        success_count,
                        talisman['description'],
                        special_req.get('effects', '{}'),
                        datetime.now().isoformat()
                    )
                )

        # 获得经验
        exp_gain = self._calculate_experience(talisman['rank'], success_count, failed_count)
        await self.profession_mgr.add_experience(user_id, "talisman_master", exp_gain)

        # 获得声望
        if success_count > 0:
            reputation_gain = talisman['rank'] * 10 * success_count
            if talisman_type == "special":
                reputation_gain *= 2
            await self.profession_mgr.add_reputation(user_id, "talisman_master", reputation_gain)
        else:
            reputation_gain = 0

        logger.info(f"玩家 {user_id} 制作了 {success_count}/{quantity} 张 {talisman['name']}")

        return {
            'success': success_count > 0,
            'talisman_name': talisman['name'],
            'talisman_type': self.TALISMAN_TYPES[talisman_type]['name'],
            'total_quantity': quantity,
            'success_count': success_count,
            'failed_count': failed_count,
            'spirit_stone_cost': spirit_stone_cost,
            'experience_gained': exp_gain,
            'reputation_gained': reputation_gain,
            'message': self._craft_message(talisman['name'], success_count, failed_count)
        }

    async def use_talisman(
        self,
        user_id: str,
        talisman_name: str,
        target_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        使用符箓

        Args:
            user_id: 玩家ID
            talisman_name: 符箓名称
            target_id: 目标ID (可选)

        Returns:
            Dict: 使用结果
        """
        # 获取玩家信息
        player = await self.player_mgr.get_player_or_error(user_id)

        # 检查是否拥有该符箓
        talisman_item = await self.db.fetchone(
            """
            SELECT * FROM items
            WHERE user_id = ? AND item_type = 'talisman' AND item_name = ? AND quantity > 0
            """,
            (user_id, talisman_name)
        )

        if not talisman_item:
            raise TalismanError(f"您没有{talisman_name}或数量不足")

        # 解析符箓效果
        effects = json.loads(talisman_item['effect'])

        # 根据符箓类型执行效果
        result = {
            'talisman_name': talisman_name,
            'effects_applied': []
        }

        # 攻击符箓
        if 'damage' in effects:
            damage = effects['damage']
            element = effects.get('element', 'physical')
            target = effects.get('target', 'single')

            # 这里可以对目标造成伤害
            result['effects_applied'].append(
                f"造成{damage}点{element}系伤害 (目标类型: {target})"
            )

        # 防御符箓
        if 'shield' in effects:
            shield = effects['shield']
            duration = effects.get('duration', 300)
            result['effects_applied'].append(
                f"获得{shield}点护盾,持续{duration}秒"
            )

        if 'defense_boost' in effects:
            boost = effects['defense_boost']
            duration = effects.get('duration', 300)
            result['effects_applied'].append(
                f"防御力提升{int(boost*100)}%,持续{duration}秒"
            )

        # 治疗符箓
        if 'hp_restore' in effects:
            hp = effects['hp_restore']
            await self.player_mgr.modify_hp(user_id, hp)
            result['effects_applied'].append(f"恢复{hp}点生命值")

        # 辅助符箓
        if 'speed_boost' in effects:
            boost = effects['speed_boost']
            duration = effects.get('duration', 300)
            result['effects_applied'].append(
                f"移动速度提升{int(boost*100)}%,持续{duration}秒"
            )

        # 特殊符箓
        if effects.get('teleport'):
            result['effects_applied'].append("可以传送到指定地点")

        if effects.get('revive'):
            hp_percent = effects.get('hp_percent', 0.5)
            result['effects_applied'].append(
                f"死亡时复活并恢复{int(hp_percent*100)}%生命值"
            )

        # 消耗符箓
        new_quantity = talisman_item['quantity'] - 1
        if new_quantity > 0:
            await self.db.execute(
                "UPDATE items SET quantity = ? WHERE id = ?",
                (new_quantity, talisman_item['id'])
            )
        else:
            await self.db.execute(
                "DELETE FROM items WHERE id = ?",
                (talisman_item['id'],)
            )

        logger.info(f"玩家 {user_id} 使用了 {talisman_name}")

        result['message'] = f"成功使用{talisman_name}!"
        return result

    async def get_available_talismans(self, user_id: str) -> List[Dict[str, Any]]:
        """
        获取可用的符箓配方列表

        Args:
            user_id: 玩家ID

        Returns:
            List[Dict]: 符箓配方列表
        """
        # 获取符箓师职业
        profession = await self.profession_mgr.get_profession(user_id, "talisman_master")
        max_rank = profession.rank if profession else 1

        # 查询公共符箓和玩家拥有的符箓
        rows = await self.db.fetchall(
            """
            SELECT * FROM recipes
            WHERE recipe_type = 'talisman'
            AND (user_id IS NULL OR user_id = ?)
            AND rank <= ?
            ORDER BY rank, name
            """,
            (user_id, max_rank)
        )

        talismans = []
        for row in rows:
            talisman_data = dict(row)
            talismans.append(talisman_data)

        return talismans

    async def get_player_talismans(self, user_id: str) -> List[Dict[str, Any]]:
        """
        获取玩家拥有的符箓

        Args:
            user_id: 玩家ID

        Returns:
            List[Dict]: 符箓列表
        """
        rows = await self.db.fetchall(
            """
            SELECT * FROM items
            WHERE user_id = ? AND item_type = 'talisman' AND quantity > 0
            ORDER BY item_name
            """,
            (user_id,)
        )

        talismans = []
        for row in rows:
            talisman_data = dict(row)
            talismans.append(talisman_data)

        return talismans

    async def format_talisman_list(self, user_id: str) -> str:
        """
        格式化符箓配方列表显示

        Args:
            user_id: 玩家ID

        Returns:
            str: 格式化的符箓列表
        """
        talismans = await self.get_available_talismans(user_id)
        profession = await self.profession_mgr.get_profession(user_id, "talisman_master")

        if not profession:
            return (
                "📜 符箓师符箓\n"
                "─" * 40 + "\n\n"
                "您还没有学习符箓师职业\n\n"
                "💡 使用 /学习职业 符箓师 学习符箓"
            )

        lines = [
            f"📜 符箓师符箓 ({profession.get_full_title()})",
            "─" * 40,
            ""
        ]

        if not talismans:
            lines.append("目前没有可用的符箓配方")
        else:
            for i, talisman in enumerate(talismans, 1):
                rank_color = "🟢" if talisman['rank'] <= profession.rank else "🔴"
                special_req = json.loads(talisman.get('special_requirements', '{}'))
                talisman_type = special_req.get('talisman_type', 'attack')
                type_icon = self.TALISMAN_TYPES.get(talisman_type, {}).get('icon', '🎴')

                lines.append(
                    f"{i}. {rank_color} {type_icon} {talisman['name']} ({talisman['rank']}品)\n"
                    f"   {talisman['description']}\n"
                    f"   成功率: {talisman['base_success_rate']}%"
                )

        lines.extend([
            "",
            "💡 使用 /制符 [编号] [数量] 制作符箓",
            "💡 使用 /符箓详情 [编号] 查看详细信息"
        ])

        return "\n".join(lines)

    async def format_player_talismans(self, user_id: str) -> str:
        """
        格式化玩家符箓列表显示

        Args:
            user_id: 玩家ID

        Returns:
            str: 格式化的符箓列表
        """
        talismans = await self.get_player_talismans(user_id)

        lines = [
            "🎴 我的符箓",
            "─" * 40,
            ""
        ]

        if not talismans:
            lines.append("您还没有任何符箓")
        else:
            for i, talisman in enumerate(talismans, 1):
                lines.append(
                    f"{i}. {talisman['item_name']} ×{talisman['quantity']}\n"
                    f"   {talisman['description']}"
                )

        lines.extend([
            "",
            "💡 使用 /使用符箓 [符箓名] 使用符箓"
        ])

        return "\n".join(lines)

    async def _get_talisman_pattern(self, talisman_id: int) -> Optional[Dict[str, Any]]:
        """获取符箓配方信息"""
        row = await self.db.fetchone(
            "SELECT * FROM recipes WHERE id = ? AND recipe_type = 'talisman'",
            (talisman_id,)
        )
        return dict(row) if row else None

    def _calculate_experience(self, rank: int, success_count: int, failed_count: int) -> int:
        """
        计算获得的经验

        Args:
            rank: 符箓品级
            success_count: 成功数量
            failed_count: 失败数量

        Returns:
            int: 经验值
        """
        base_exp = rank * 40
        success_exp = success_count * base_exp
        failed_exp = failed_count * (base_exp // 4)  # 失败也给1/4经验
        return success_exp + failed_exp

    def _craft_message(self, talisman_name: str, success: int, failed: int) -> str:
        """生成制作消息"""
        total = success + failed

        if failed == 0:
            return f"完美制作!成功制作{success}张{talisman_name}!"
        elif success == 0:
            return f"制作失败!{total}张符箓全部失败了..."
        else:
            return f"制作完成!成功{success}张,失败{failed}张{talisman_name}"
