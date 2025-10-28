"""
炼器系统
实现装备炼制、强化、改造等功能
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
import random
import json
from astrbot.api import logger

from ..core.database import DatabaseManager
from ..core.player import PlayerManager
from ..core.profession import ProfessionManager, ProfessionNotFoundError
from ..utils.exceptions import PlayerNotFoundError


class RefiningError(Exception):
    """炼器系统异常"""
    pass


class BlueprintNotFoundError(RefiningError):
    """图纸不存在"""
    pass


class InsufficientMaterialsError(RefiningError):
    """材料不足"""
    pass


class InsufficientSpiritStoneError(RefiningError):
    """灵石不足"""
    pass


class RefiningSystem:
    """炼器系统"""

    # 装备品质
    EQUIPMENT_QUALITIES = {
        "凡品": {"attribute_multiplier": 1.0, "probability": 0.4},
        "灵品": {"attribute_multiplier": 1.5, "probability": 0.35},
        "宝品": {"attribute_multiplier": 2.0, "probability": 0.2},
        "仙品": {"attribute_multiplier": 3.0, "probability": 0.04},
        "神品": {"attribute_multiplier": 5.0, "probability": 0.01}
    }

    # 基础图纸配置（大幅扩充至28种）
    BASE_BLUEPRINTS = [
        # ========== 炼气期装备 (Rank 1) ==========
        {
            "name": "玄铁剑",
            "rank": 1,
            "description": "用玄铁打造的基础长剑",
            "recipe_type": "refining",
            "materials": json.dumps([
                {"name": "玄铁", "quantity": 5},
                {"name": "精金", "quantity": 2}
            ]),
            "output_name": "玄铁剑",
            "output_quality": "灵品",
            "base_success_rate": 70,
            "equipment_type": "weapon",
            "base_attributes": json.dumps({
                "attack": 50,
                "defense": 0
            })
        },
        {
            "name": "护体战袍",
            "rank": 1,
            "description": "基础的防护战袍",
            "recipe_type": "refining",
            "materials": json.dumps([
                {"name": "灵兽皮", "quantity": 3},
                {"name": "精金", "quantity": 1}
            ]),
            "output_name": "护体战袍",
            "output_quality": "灵品",
            "base_success_rate": 70,
            "equipment_type": "armor",
            "base_attributes": json.dumps({
                "attack": 0,
                "defense": 30,
                "hp_bonus": 200
            })
        },
        {
            "name": "灵玉佩",
            "rank": 1,
            "description": "普通的灵玉饰品",
            "recipe_type": "refining",
            "materials": json.dumps([
                {"name": "灵玉", "quantity": 2},
                {"name": "银丝", "quantity": 1}
            ]),
            "output_name": "灵玉佩",
            "output_quality": "灵品",
            "base_success_rate": 65,
            "equipment_type": "accessory",
            "base_attributes": json.dumps({
                "attack": 10,
                "defense": 10,
                "mp_bonus": 50
            })
        },

        # ========== 筑基期装备 (Rank 2) ==========
        {
            "name": "青锋剑",
            "rank": 2,
            "description": "筑基期修士常用的法剑",
            "recipe_type": "refining",
            "materials": json.dumps([
                {"name": "寒铁", "quantity": 10},
                {"name": "秘银", "quantity": 5},
                {"name": "灵石", "quantity": 20}
            ]),
            "output_name": "青锋剑",
            "output_quality": "宝品",
            "base_success_rate": 60,
            "equipment_type": "weapon",
            "base_attributes": json.dumps({
                "attack": 150,
                "defense": 0,
                "hp_bonus": 100
            })
        },
        {
            "name": "流云甲",
            "rank": 2,
            "description": "轻若云朵的防护甲胄",
            "recipe_type": "refining",
            "materials": json.dumps([
                {"name": "二阶兽皮", "quantity": 8},
                {"name": "秘银", "quantity": 3},
                {"name": "云纹石", "quantity": 5}
            ]),
            "output_name": "流云甲",
            "output_quality": "宝品",
            "base_success_rate": 60,
            "equipment_type": "armor",
            "base_attributes": json.dumps({
                "attack": 0,
                "defense": 100,
                "hp_bonus": 800
            })
        },
        {
            "name": "聚灵戒指",
            "rank": 2,
            "description": "能够聚集灵气的法戒",
            "recipe_type": "refining",
            "materials": json.dumps([
                {"name": "灵玉", "quantity": 5},
                {"name": "秘银", "quantity": 2},
                {"name": "灵石", "quantity": 30}
            ]),
            "output_name": "聚灵戒指",
            "output_quality": "宝品",
            "base_success_rate": 55,
            "equipment_type": "accessory",
            "base_attributes": json.dumps({
                "attack": 30,
                "defense": 30,
                "mp_bonus": 300
            })
        },

        # ========== 金丹期装备 (Rank 3) ==========
        {
            "name": "赤炎剑",
            "rank": 3,
            "description": "蕴含火焰之力的金丹期法剑",
            "recipe_type": "refining",
            "materials": json.dumps([
                {"name": "赤炎铁", "quantity": 20},
                {"name": "火晶石", "quantity": 10},
                {"name": "三阶妖丹", "quantity": 2},
                {"name": "秘银", "quantity": 10}
            ]),
            "output_name": "赤炎剑",
            "output_quality": "仙品",
            "base_success_rate": 50,
            "equipment_type": "weapon",
            "base_attributes": json.dumps({
                "attack": 400,
                "defense": 0,
                "hp_bonus": 300,
                "special": "火焰伤害+20%"
            })
        },
        {
            "name": "金刚战甲",
            "rank": 3,
            "description": "坚如金刚的金丹期防具",
            "recipe_type": "refining",
            "materials": json.dumps([
                {"name": "金刚石", "quantity": 15},
                {"name": "三阶兽皮", "quantity": 12},
                {"name": "精金", "quantity": 10}
            ]),
            "output_name": "金刚战甲",
            "output_quality": "仙品",
            "base_success_rate": 50,
            "equipment_type": "armor",
            "base_attributes": json.dumps({
                "attack": 0,
                "defense": 300,
                "hp_bonus": 2000
            })
        },
        {
            "name": "紫金冠",
            "rank": 3,
            "description": "提升神识的紫金法冠",
            "recipe_type": "refining",
            "materials": json.dumps([
                {"name": "紫金", "quantity": 8},
                {"name": "灵玉", "quantity": 10},
                {"name": "神识石", "quantity": 5}
            ]),
            "output_name": "紫金冠",
            "output_quality": "仙品",
            "base_success_rate": 45,
            "equipment_type": "accessory",
            "base_attributes": json.dumps({
                "attack": 80,
                "defense": 80,
                "mp_bonus": 1000
            })
        },

        # ========== 元婴期装备 (Rank 4) ==========
        {
            "name": "龙吟剑",
            "rank": 4,
            "description": "剑鸣如龙的元婴期至宝",
            "recipe_type": "refining",
            "materials": json.dumps([
                {"name": "龙鳞铁", "quantity": 30},
                {"name": "龙晶", "quantity": 15},
                {"name": "四阶妖丹", "quantity": 5},
                {"name": "万年寒铁", "quantity": 10}
            ]),
            "output_name": "龙吟剑",
            "output_quality": "神品",
            "base_success_rate": 40,
            "equipment_type": "weapon",
            "base_attributes": json.dumps({
                "attack": 1000,
                "defense": 100,
                "hp_bonus": 1000,
                "special": "攻击附带龙威"
            })
        },
        {
            "name": "玄龟甲",
            "rank": 4,
            "description": "防御无双的玄龟之甲",
            "recipe_type": "refining",
            "materials": json.dumps([
                {"name": "玄龟甲片", "quantity": 20},
                {"name": "四阶兽皮", "quantity": 15},
                {"name": "防御符文", "quantity": 10}
            ]),
            "output_name": "玄龟甲",
            "output_quality": "神品",
            "base_success_rate": 40,
            "equipment_type": "armor",
            "base_attributes": json.dumps({
                "attack": 0,
                "defense": 800,
                "hp_bonus": 5000
            })
        },
        {
            "name": "元婴镜",
            "rank": 4,
            "description": "映照元婴的神秘法宝",
            "recipe_type": "refining",
            "materials": json.dumps([
                {"name": "神玉", "quantity": 20},
                {"name": "镜心石", "quantity": 10},
                {"name": "元婴精华", "quantity": 3}
            ]),
            "output_name": "元婴镜",
            "output_quality": "神品",
            "base_success_rate": 35,
            "equipment_type": "accessory",
            "base_attributes": json.dumps({
                "attack": 200,
                "defense": 200,
                "mp_bonus": 3000,
                "special": "反射法术伤害10%"
            })
        },

        # ========== 化神期装备 (Rank 5) ==========
        {
            "name": "神魔剑",
            "rank": 5,
            "description": "化神期顶尖武器，集神魔之力于一身",
            "recipe_type": "refining",
            "materials": json.dumps([
                {"name": "神魔铁", "quantity": 50},
                {"name": "神性结晶", "quantity": 20},
                {"name": "五阶妖丹", "quantity": 10},
                {"name": "混沌石", "quantity": 5}
            ]),
            "output_name": "神魔剑",
            "output_quality": "道品",
            "base_success_rate": 30,
            "equipment_type": "weapon",
            "base_attributes": json.dumps({
                "attack": 2500,
                "defense": 300,
                "hp_bonus": 3000,
                "special": "攻击附带神魔之力"
            })
        },
        {
            "name": "化神袍",
            "rank": 5,
            "description": "融合神性的化神期法袍",
            "recipe_type": "refining",
            "materials": json.dumps([
                {"name": "神兽皮", "quantity": 30},
                {"name": "神性丝线", "quantity": 50},
                {"name": "防御符文", "quantity": 20}
            ]),
            "output_name": "化神袍",
            "output_quality": "道品",
            "base_success_rate": 30,
            "equipment_type": "armor",
            "base_attributes": json.dumps({
                "attack": 200,
                "defense": 2000,
                "hp_bonus": 10000,
                "mp_bonus": 2000
            })
        },
        {
            "name": "混沌珠",
            "rank": 5,
            "description": "蕴含混沌之力的至宝",
            "recipe_type": "refining",
            "materials": json.dumps([
                {"name": "混沌石", "quantity": 10},
                {"name": "神玉", "quantity": 30},
                {"name": "天地本源", "quantity": 3}
            ]),
            "output_name": "混沌珠",
            "output_quality": "道品",
            "base_success_rate": 25,
            "equipment_type": "accessory",
            "base_attributes": json.dumps({
                "attack": 500,
                "defense": 500,
                "mp_bonus": 8000,
                "special": "法力恢复速度+50%"
            })
        },

        # ========== 炼虚期装备 (Rank 6) ==========
        {
            "name": "虚空剑",
            "rank": 6,
            "description": "可切割虚空的炼虚期神兵",
            "recipe_type": "refining",
            "materials": json.dumps([
                {"name": "虚空铁", "quantity": 80},
                {"name": "虚空结晶", "quantity": 40},
                {"name": "六阶妖丹", "quantity": 15},
                {"name": "混沌精华", "quantity": 10}
            ]),
            "output_name": "虚空剑",
            "output_quality": "先天灵宝",
            "base_success_rate": 25,
            "equipment_type": "weapon",
            "base_attributes": json.dumps({
                "attack": 6000,
                "defense": 500,
                "hp_bonus": 5000,
                "special": "攻击无视30%防御"
            })
        },
        {
            "name": "星辰甲",
            "rank": 6,
            "description": "凝聚星辰之力的防具",
            "recipe_type": "refining",
            "materials": json.dumps([
                {"name": "星辰铁", "quantity": 60},
                {"name": "星核", "quantity": 20},
                {"name": "虚空结晶", "quantity": 30}
            ]),
            "output_name": "星辰甲",
            "output_quality": "先天灵宝",
            "base_success_rate": 25,
            "equipment_type": "armor",
            "base_attributes": json.dumps({
                "attack": 500,
                "defense": 5000,
                "hp_bonus": 20000,
                "special": "受到攻击时反震20%伤害"
            })
        },

        # ========== 合体期装备 (Rank 7) ==========
        {
            "name": "太极剑",
            "rank": 7,
            "description": "阴阳合一的合体期至宝",
            "recipe_type": "refining",
            "materials": json.dumps([
                {"name": "阴阳铁", "quantity": 100},
                {"name": "太极石", "quantity": 50},
                {"name": "七阶妖丹", "quantity": 20},
                {"name": "天地本源", "quantity": 15}
            ]),
            "output_name": "太极剑",
            "output_quality": "后天至宝",
            "base_success_rate": 20,
            "equipment_type": "weapon",
            "base_attributes": json.dumps({
                "attack": 15000,
                "defense": 1000,
                "hp_bonus": 10000,
                "mp_bonus": 5000,
                "special": "阴阳两仪，攻守兼备"
            })
        },
        {
            "name": "乾坤甲",
            "rank": 7,
            "description": "包罗乾坤的防御至宝",
            "recipe_type": "refining",
            "materials": json.dumps([
                {"name": "乾坤石", "quantity": 80},
                {"name": "天地本源", "quantity": 20},
                {"name": "混沌精华", "quantity": 30}
            ]),
            "output_name": "乾坤甲",
            "output_quality": "后天至宝",
            "base_success_rate": 20,
            "equipment_type": "armor",
            "base_attributes": json.dumps({
                "attack": 1000,
                "defense": 12000,
                "hp_bonus": 50000,
                "special": "可吸收50%伤害转化为法力"
            })
        },

        # ========== 大乘期装备 (Rank 8) ==========
        {
            "name": "弑仙剑",
            "rank": 8,
            "description": "传说中可弑仙的神剑",
            "recipe_type": "refining",
            "materials": json.dumps([
                {"name": "弑仙铁", "quantity": 150},
                {"name": "仙晶", "quantity": 80},
                {"name": "八阶妖丹", "quantity": 30},
                {"name": "鸿蒙紫气", "quantity": 10}
            ]),
            "output_name": "弑仙剑",
            "output_quality": "先天至宝",
            "base_success_rate": 15,
            "equipment_type": "weapon",
            "base_attributes": json.dumps({
                "attack": 35000,
                "defense": 2000,
                "hp_bonus": 20000,
                "special": "对仙人造成额外50%伤害"
            })
        },
        {
            "name": "不灭金身",
            "rank": 8,
            "description": "不灭不坏的金身护甲",
            "recipe_type": "refining",
            "materials": json.dumps([
                {"name": "不灭金", "quantity": 120},
                {"name": "金身舍利", "quantity": 30},
                {"name": "鸿蒙紫气", "quantity": 15}
            ]),
            "output_name": "不灭金身",
            "output_quality": "先天至宝",
            "base_success_rate": 15,
            "equipment_type": "armor",
            "base_attributes": json.dumps({
                "attack": 2000,
                "defense": 30000,
                "hp_bonus": 100000,
                "special": "濒死时触发不灭金身，恢复50%生命值"
            })
        },

        # ========== 渡劫期装备 (Rank 9) ==========
        {
            "name": "开天斧",
            "rank": 9,
            "description": "开天辟地的混沌神兵",
            "recipe_type": "refining",
            "materials": json.dumps([
                {"name": "混沌神铁", "quantity": 200},
                {"name": "开天石", "quantity": 100},
                {"name": "九阶妖丹", "quantity": 50},
                {"name": "鸿蒙紫气", "quantity": 30},
                {"name": "天道碎片", "quantity": 5}
            ]),
            "output_name": "开天斧",
            "output_quality": "混沌灵宝",
            "base_success_rate": 10,
            "equipment_type": "weapon",
            "base_attributes": json.dumps({
                "attack": 80000,
                "defense": 5000,
                "hp_bonus": 50000,
                "mp_bonus": 20000,
                "special": "破天之力，无视一切防御"
            })
        },
        {
            "name": "混沌钟",
            "rank": 9,
            "description": "镇压一切的混沌至宝",
            "recipe_type": "refining",
            "materials": json.dumps([
                {"name": "混沌铜", "quantity": 200},
                {"name": "时空石", "quantity": 100},
                {"name": "天道碎片", "quantity": 10}
            ]),
            "output_name": "混沌钟",
            "output_quality": "混沌灵宝",
            "base_success_rate": 8,
            "equipment_type": "accessory",
            "base_attributes": json.dumps({
                "attack": 10000,
                "defense": 50000,
                "hp_bonus": 200000,
                "mp_bonus": 100000,
                "special": "免疫一切控制效果，镇压万物"
            })
        }
    ]

    def __init__(
        self,
        db: DatabaseManager,
        player_mgr: PlayerManager,
        profession_mgr: ProfessionManager
    ):
        """
        初始化炼器系统

        Args:
            db: 数据库管理器
            player_mgr: 玩家管理器
            profession_mgr: 职业管理器
        """
        self.db = db
        self.player_mgr = player_mgr
        self.profession_mgr = profession_mgr
        self.sect_sys = None  # 宗门系统（可选）

    def set_sect_system(self, sect_sys):
        """
        设置宗门系统（用于加成计算）

        Args:
            sect_sys: 宗门系统实例
        """
        self.sect_sys = sect_sys

    async def init_base_blueprints(self):
        """初始化基础图纸"""
        for blueprint_data in self.BASE_BLUEPRINTS:
            # 检查是否已存在
            row = await self.db.fetchone(
                """
                SELECT id FROM recipes
                WHERE name = ? AND recipe_type = 'refining' AND user_id IS NULL
                """,
                (blueprint_data['name'],)
            )

            if not row:
                # 插入图纸
                await self.db.execute(
                    """
                    INSERT INTO recipes (
                        user_id, recipe_type, name, rank, description,
                        materials, output_name, output_quality,
                        base_success_rate, special_requirements, source, is_ai_generated
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        None,  # 公共图纸
                        blueprint_data['recipe_type'],
                        blueprint_data['name'],
                        blueprint_data['rank'],
                        blueprint_data['description'],
                        blueprint_data['materials'],
                        blueprint_data['output_name'],
                        blueprint_data['output_quality'],
                        blueprint_data['base_success_rate'],
                        json.dumps({
                            "equipment_type": blueprint_data['equipment_type'],
                            "base_attributes": blueprint_data['base_attributes']
                        }),
                        "系统预设",
                        0
                    )
                )

        logger.info("基础图纸初始化完成")

    async def refine_equipment(
        self,
        user_id: str,
        blueprint_id: int
    ) -> Dict[str, Any]:
        """
        炼制装备

        Args:
            user_id: 玩家ID
            blueprint_id: 图纸ID

        Returns:
            Dict: 炼制结果

        Raises:
            PlayerNotFoundError: 玩家不存在
            ProfessionNotFoundError: 未学习炼器师
            BlueprintNotFoundError: 图纸不存在
            InsufficientMaterialsError: 材料不足
            InsufficientSpiritStoneError: 灵石不足
        """
        # 获取玩家信息
        player = await self.player_mgr.get_player_or_error(user_id)

        # 获取炼器师职业
        profession = await self.profession_mgr.get_profession(user_id, "blacksmith")
        if not profession:
            raise ProfessionNotFoundError("尚未学习炼器师职业")

        # 获取图纸
        blueprint = await self._get_blueprint(blueprint_id)
        if not blueprint:
            raise BlueprintNotFoundError(f"图纸不存在: {blueprint_id}")

        # 检查品级
        if blueprint['rank'] > profession.rank:
            raise RefiningError(f"图纸需要{blueprint['rank']}品炼器师,当前仅{profession.rank}品")

        # 解析材料需求
        materials_required = json.loads(blueprint['materials'])

        # TODO: 检查材料是否足够 (需要物品系统)

        # 检查灵石
        spirit_stone_cost = 200  # 炼器比炼丹贵
        if player.spirit_stone < spirit_stone_cost:
            raise InsufficientSpiritStoneError(f"灵石不足,需要{spirit_stone_cost}灵石")

        # 计算成功率
        success_rate = profession.get_success_rate()

        # 灵根加成
        if player.spirit_root_type in ["金", "火", "冰"]:
            if player.spirit_root_type == "金":
                success_rate += 0.30  # 金系+30%
            elif player.spirit_root_type == "火":
                success_rate += 0.20  # 火系+20%
            elif player.spirit_root_type == "冰":
                success_rate += 0.20  # 冰系+20%

        # 应用宗门加成
        sect_bonus_rate = 0.0
        if self.sect_sys:
            try:
                success_rate, sect_bonus_rate = await self.sect_sys.apply_sect_bonus(
                    user_id, "refining_bonus", success_rate
                )
            except Exception as e:
                # 如果宗门加成失败，记录日志但不影响炼器
                logger.warning(f"应用宗门加成失败: {e}")

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
                blueprint_id=blueprint_id,
                success=False,
                output_quality="损毁",
                materials_used=json.dumps(materials_required),
                spirit_stone_cost=spirit_stone_cost,
                experience_gained=15
            )

            # 添加少量经验
            await self.profession_mgr.add_experience(user_id, "blacksmith", 15)

            return {
                'success': False,
                'quality': "损毁",
                'equipment_name': blueprint['output_name'],
                'spirit_stone_cost': spirit_stone_cost,
                'experience_gained': 15,
                'message': f"炼制失败,装备在淬火时损毁了!"
            }

        # 炼制成功,确定品质
        quality = self._determine_quality(success_rate, profession)

        # 解析基础属性
        special_req = json.loads(blueprint.get('special_requirements', '{}'))
        base_attrs = json.loads(special_req.get('base_attributes', '{}'))
        equipment_type = special_req.get('equipment_type', 'weapon')

        # 计算最终属性
        quality_multiplier = self.EQUIPMENT_QUALITIES[quality]['attribute_multiplier']
        final_attributes = {
            key: int(value * quality_multiplier)
            for key, value in base_attrs.items()
        }

        # 消耗灵石
        await self.player_mgr.add_spirit_stone(user_id, -spirit_stone_cost)

        # TODO: 添加装备到背包 (需要物品系统)
        # 这里我们可以使用现有的equipment系统创建装备
        from ..core.equipment import EquipmentSystem
        equipment_sys = EquipmentSystem(self.db, self.player_mgr)

        # 创建装备(简化处理)
        equipment = await equipment_sys.create_equipment(user_id, equipment_type)
        # 更新装备属性
        await self.db.execute(
            """
            UPDATE equipment
            SET name = ?, quality = ?, attack = ?, defense = ?, hp_bonus = ?, mp_bonus = ?
            WHERE id = ?
            """,
            (
                f"{quality}{blueprint['output_name']}",
                quality,
                final_attributes.get('attack', 0),
                final_attributes.get('defense', 0),
                final_attributes.get('hp_bonus', 0),
                final_attributes.get('mp_bonus', 0),
                equipment.id
            )
        )

        # 获得经验
        exp_gain = self._calculate_experience(blueprint['rank'], quality)
        await self.profession_mgr.add_experience(user_id, "blacksmith", exp_gain)

        # 获得声望
        reputation_gain = blueprint['rank'] * 15
        if quality in ["仙品", "神品"]:
            reputation_gain *= 2
        await self.profession_mgr.add_reputation(user_id, "blacksmith", reputation_gain)

        # 记录炼制日志
        await self._log_crafting(
            user_id=user_id,
            blueprint_id=blueprint_id,
            success=True,
            output_quality=quality,
            output_item_id=equipment.id,
            materials_used=json.dumps(materials_required),
            spirit_stone_cost=spirit_stone_cost,
            experience_gained=exp_gain
        )

        logger.info(f"玩家 {user_id} 炼制了 {quality} {blueprint['output_name']}")

        return {
            'success': True,
            'quality': quality,
            'equipment_name': blueprint['output_name'],
            'equipment_id': equipment.id,
            'attributes': final_attributes,
            'spirit_stone_cost': spirit_stone_cost,
            'experience_gained': exp_gain,
            'reputation_gained': reputation_gain,
            'message': f"炼制成功!获得了{quality}{blueprint['output_name']}!"
        }

    async def enhance_equipment(
        self,
        user_id: str,
        equipment_id: int
    ) -> Dict[str, Any]:
        """
        强化装备

        Args:
            user_id: 玩家ID
            equipment_id: 装备ID

        Returns:
            Dict: 强化结果
        """
        # 获取炼器师职业
        profession = await self.profession_mgr.get_profession(user_id, "blacksmith")
        if not profession:
            raise ProfessionNotFoundError("尚未学习炼器师职业")

        # 获取装备信息
        equipment_row = await self.db.fetchone(
            "SELECT * FROM equipment WHERE id = ? AND user_id = ?",
            (equipment_id, user_id)
        )

        if not equipment_row:
            raise RefiningError("装备不存在或不属于您")

        equipment = dict(equipment_row)
        current_level = equipment['enhance_level']

        # 强化上限
        if current_level >= 20:
            raise RefiningError("装备已达到最大强化等级(+20)")

        # 计算强化成功率
        base_rate = 1.0 - (current_level * 0.05)  # 每级降低5%成功率
        success_rate = max(0.3, base_rate + profession.success_rate_bonus)

        # 强化消耗
        spirit_stone_cost = (current_level + 1) * 100

        # 检查灵石
        player = await self.player_mgr.get_player_or_error(user_id)
        if player.spirit_stone < spirit_stone_cost:
            raise InsufficientSpiritStoneError(f"灵石不足,需要{spirit_stone_cost}灵石")

        # 消耗灵石
        await self.player_mgr.add_spirit_stone(user_id, -spirit_stone_cost)

        # 判断是否成功
        success = random.random() < success_rate

        if success:
            # 强化成功
            new_level = current_level + 1
            await self.db.execute(
                "UPDATE equipment SET enhance_level = ? WHERE id = ?",
                (new_level, equipment_id)
            )

            # 获得经验
            exp_gain = (current_level + 1) * 20
            await self.profession_mgr.add_experience(user_id, "blacksmith", exp_gain)

            logger.info(f"玩家 {user_id} 强化装备 {equipment_id} 到 +{new_level}")

            return {
                'success': True,
                'old_level': current_level,
                'new_level': new_level,
                'spirit_stone_cost': spirit_stone_cost,
                'experience_gained': exp_gain,
                'message': f"强化成功!装备达到+{new_level}!"
            }
        else:
            # 强化失败
            # 有几率装备等级回退
            if current_level > 0 and random.random() < 0.3:
                new_level = max(0, current_level - 1)
                await self.db.execute(
                    "UPDATE equipment SET enhance_level = ? WHERE id = ?",
                    (new_level, equipment_id)
                )
                message = f"强化失败,装备等级从+{current_level}回退到+{new_level}"
            else:
                message = "强化失败,装备等级未变化"

            return {
                'success': False,
                'old_level': current_level,
                'new_level': current_level,
                'spirit_stone_cost': spirit_stone_cost,
                'message': message
            }

    async def get_available_blueprints(self, user_id: str) -> List[Dict[str, Any]]:
        """
        获取可用的图纸列表

        Args:
            user_id: 玩家ID

        Returns:
            List[Dict]: 图纸列表
        """
        # 获取炼器师职业
        profession = await self.profession_mgr.get_profession(user_id, "blacksmith")
        max_rank = profession.rank if profession else 1

        # 查询公共图纸和玩家拥有的图纸
        rows = await self.db.fetchall(
            """
            SELECT * FROM recipes
            WHERE recipe_type = 'refining'
            AND (user_id IS NULL OR user_id = ?)
            AND rank <= ?
            ORDER BY rank, name
            """,
            (user_id, max_rank)
        )

        blueprints = []
        for row in rows:
            blueprint_data = dict(row)
            blueprints.append(blueprint_data)

        return blueprints

    async def format_blueprint_list(self, user_id: str) -> str:
        """
        格式化图纸列表显示

        Args:
            user_id: 玩家ID

        Returns:
            str: 格式化的图纸列表
        """
        blueprints = await self.get_available_blueprints(user_id)
        profession = await self.profession_mgr.get_profession(user_id, "blacksmith")

        if not profession:
            return (
                "📜 炼器师图纸\n"
                "─" * 40 + "\n\n"
                "您还没有学习炼器师职业\n\n"
                "💡 使用 /学习职业 炼器师 学习炼器"
            )

        lines = [
            f"📜 炼器师图纸 ({profession.get_full_title()})",
            "─" * 40,
            ""
        ]

        if not blueprints:
            lines.append("目前没有可用的图纸")
        else:
            for i, blueprint in enumerate(blueprints, 1):
                rank_color = "🟢" if blueprint['rank'] <= profession.rank else "🔴"
                lines.append(
                    f"{i}. {rank_color} {blueprint['name']} ({blueprint['rank']}品)\n"
                    f"   {blueprint['description']}\n"
                    f"   成功率: {blueprint['base_success_rate']}%"
                )

        lines.extend([
            "",
            "💡 使用 /炼器 [编号] 炼制装备",
            "💡 使用 /图纸详情 [编号] 查看详细信息",
            "💡 使用 /强化装备 [装备编号] 强化装备"
        ])

        return "\n".join(lines)

    async def _get_blueprint(self, blueprint_id: int) -> Optional[Dict[str, Any]]:
        """获取图纸信息"""
        row = await self.db.fetchone(
            "SELECT * FROM recipes WHERE id = ? AND recipe_type = 'refining'",
            (blueprint_id,)
        )
        return dict(row) if row else None

    def _determine_quality(self, success_rate: float, profession) -> str:
        """
        确定装备品质

        Args:
            success_rate: 成功率
            profession: 职业对象

        Returns:
            str: 品质
        """
        # 基础概率
        probabilities = {
            "神品": 0.01,
            "仙品": 0.04,
            "宝品": 0.20,
            "灵品": 0.35,
            "凡品": 0.40
        }

        # 品级加成
        rank_bonus = (profession.rank - 1) * 0.05
        probabilities["仙品"] += rank_bonus * 0.3
        probabilities["宝品"] += rank_bonus * 0.5
        probabilities["灵品"] += rank_bonus * 0.2

        # 成功率加成
        if success_rate > 0.8:
            probabilities["神品"] += 0.02
            probabilities["仙品"] += 0.06

        # 归一化
        total = sum(probabilities.values())
        probabilities = {k: v/total for k, v in probabilities.items()}

        # 随机选择
        rand = random.random()
        cumulative = 0.0

        for quality in ["神品", "仙品", "宝品", "灵品", "凡品"]:
            cumulative += probabilities.get(quality, 0)
            if rand <= cumulative:
                return quality

        return "灵品"

    def _calculate_experience(self, rank: int, quality: str) -> int:
        """
        计算获得的经验

        Args:
            rank: 装备品级
            quality: 装备品质

        Returns:
            int: 经验值
        """
        base_exp = rank * 60

        quality_multiplier = {
            "凡品": 1.0,
            "灵品": 1.5,
            "宝品": 2.0,
            "仙品": 3.0,
            "神品": 5.0
        }

        return int(base_exp * quality_multiplier.get(quality, 1.0))

    async def _log_crafting(
        self,
        user_id: str,
        blueprint_id: int,
        success: bool,
        output_quality: str,
        materials_used: str,
        spirit_stone_cost: int,
        experience_gained: int,
        output_item_id: Optional[int] = None
    ):
        """记录炼制日志"""
        await self.db.execute(
            """
            INSERT INTO crafting_logs (
                user_id, craft_type, recipe_id, success,
                output_quality, output_item_id, materials_used,
                spirit_stone_cost, experience_gained, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                "refining",
                blueprint_id,
                success,
                output_quality,
                output_item_id,
                materials_used,
                spirit_stone_cost,
                experience_gained,
                datetime.now().isoformat()
            )
        )
