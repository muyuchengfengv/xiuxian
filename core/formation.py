"""
阵法系统
实现阵法布置、破阵、管理等功能
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


class FormationError(Exception):
    """阵法系统异常"""
    pass


class FormationPatternNotFoundError(FormationError):
    """阵法配方不存在"""
    pass


class InsufficientMaterialsError(FormationError):
    """材料不足"""
    pass


class InsufficientSpiritStoneError(FormationError):
    """灵石不足"""
    pass


class FormationAlreadyExistsError(FormationError):
    """该位置已有阵法"""
    pass


class FormationSystem:
    """阵法系统"""

    # 阵法类型
    FORMATION_TYPES = {
        "assist": {
            "name": "辅助阵法",
            "description": "提升修炼速度或恢复能力的阵法",
            "icon": "💫"
        },
        "defense": {
            "name": "防御阵法",
            "description": "提升防御力或创建护盾的阵法",
            "icon": "🛡️"
        },
        "attack": {
            "name": "攻击阵法",
            "description": "对敌人造成伤害的阵法",
            "icon": "⚔️"
        },
        "control": {
            "name": "控制阵法",
            "description": "困住或限制敌人的阵法",
            "icon": "🔗"
        },
        "compound": {
            "name": "复合阵法",
            "description": "结合多种效果的复杂阵法",
            "icon": "✨"
        }
    }

    # 基础阵法配置（扩充至20种）
    BASE_FORMATIONS = [
        # ========== 炼气期阵法 (Rank 1) ==========
        {
            "name": "聚灵阵",
            "rank": 1,
            "formation_type": "assist",
            "description": "聚集周围灵气,提升修炼速度50%",
            "materials": json.dumps([
                {"name": "阵旗", "quantity": 4},
                {"name": "灵石", "quantity": 10}
            ]),
            "base_success_rate": 70,
            "spirit_stone_cost": 200,
            "duration_hours": 24,
            "range_meters": 10,
            "effects": json.dumps({
                "cultivation_speed": 0.5,
                "mp_recovery": 0.2
            })
        },
        {
            "name": "护体阵",
            "rank": 1,
            "formation_type": "defense",
            "description": "创建防御护盾,提升防御力30%",
            "materials": json.dumps([
                {"name": "阵旗", "quantity": 4},
                {"name": "灵石", "quantity": 15}
            ]),
            "base_success_rate": 65,
            "spirit_stone_cost": 250,
            "duration_hours": 12,
            "range_meters": 5,
            "effects": json.dumps({
                "defense_bonus": 0.3,
                "damage_reduction": 0.15
            })
        },

        # ========== 筑基期阵法 (Rank 2) ==========
        {
            "name": "五行杀阵",
            "rank": 2,
            "formation_type": "attack",
            "description": "调动五行之力攻击敌人",
            "materials": json.dumps([
                {"name": "阵旗", "quantity": 5},
                {"name": "五行石", "quantity": 5},
                {"name": "灵石", "quantity": 30}
            ]),
            "base_success_rate": 55,
            "spirit_stone_cost": 500,
            "duration_hours": 6,
            "range_meters": 15,
            "effects": json.dumps({
                "damage_per_hour": 100,
                "attack_frequency": 10
            })
        },
        {
            "name": "困龙阵",
            "rank": 2,
            "formation_type": "control",
            "description": "困住敌人,限制其行动",
            "materials": json.dumps([
                {"name": "阵旗", "quantity": 8},
                {"name": "困龙索", "quantity": 1},
                {"name": "灵石", "quantity": 40}
            ]),
            "base_success_rate": 50,
            "spirit_stone_cost": 600,
            "duration_hours": 4,
            "range_meters": 12,
            "effects": json.dumps({
                "trap_duration": 120,  # 分钟
                "escape_difficulty": 0.7
            })
        },

        # ========== 金丹期阵法 (Rank 3) ==========
        {
            "name": "八卦玄天阵",
            "rank": 3,
            "formation_type": "compound",
            "description": "八卦演天,攻防兼备的复合大阵",
            "materials": json.dumps([
                {"name": "八卦阵盘", "quantity": 1},
                {"name": "阵旗", "quantity": 8},
                {"name": "天罡石", "quantity": 8},
                {"name": "灵石", "quantity": 100}
            ]),
            "base_success_rate": 40,
            "spirit_stone_cost": 1000,
            "duration_hours": 48,
            "range_meters": 30,
            "effects": json.dumps({
                "defense_bonus": 0.5,
                "attack_bonus": 0.3,
                "cultivation_speed": 0.3,
                "damage_per_hour": 150
            })
        },
        {
            "name": "九天雷霆阵",
            "rank": 3,
            "formation_type": "attack",
            "description": "引动九天雷霆,对敌人造成持续雷击伤害",
            "materials": json.dumps([
                {"name": "雷晶石", "quantity": 10},
                {"name": "阵旗", "quantity": 9},
                {"name": "灵石", "quantity": 120}
            ]),
            "base_success_rate": 45,
            "spirit_stone_cost": 1500,
            "duration_hours": 12,
            "range_meters": 25,
            "effects": json.dumps({
                "damage_per_hour": 300,
                "attack_frequency": 15,
                "thunder_damage": True
            })
        },
        {
            "name": "四象护山阵",
            "rank": 3,
            "formation_type": "defense",
            "description": "青龙白虎朱雀玄武,四象守护提升防御100%",
            "materials": json.dumps([
                {"name": "四象石", "quantity": 4},
                {"name": "阵旗", "quantity": 12},
                {"name": "灵石", "quantity": 150}
            ]),
            "base_success_rate": 50,
            "spirit_stone_cost": 1800,
            "duration_hours": 72,
            "range_meters": 50,
            "effects": json.dumps({
                "defense_bonus": 1.0,
                "damage_reduction": 0.4,
                "hp_regeneration": 50
            })
        },

        # ========== 元婴期阵法 (Rank 4) ==========
        {
            "name": "万剑归宗阵",
            "rank": 4,
            "formation_type": "attack",
            "description": "凝聚万千剑气,对敌人造成毁灭性打击",
            "materials": json.dumps([
                {"name": "剑石", "quantity": 100},
                {"name": "阵旗", "quantity": 15},
                {"name": "四阶妖丹", "quantity": 2},
                {"name": "灵石", "quantity": 300}
            ]),
            "base_success_rate": 40,
            "spirit_stone_cost": 3000,
            "duration_hours": 24,
            "range_meters": 40,
            "effects": json.dumps({
                "damage_per_hour": 800,
                "attack_frequency": 20,
                "sword_rain": True
            })
        },
        {
            "name": "天罡北斗阵",
            "rank": 4,
            "formation_type": "assist",
            "description": "引动北斗星力,大幅提升修炼速度和恢复能力",
            "materials": json.dumps([
                {"name": "北斗星石", "quantity": 7},
                {"name": "阵旗", "quantity": 20},
                {"name": "天罡石", "quantity": 15},
                {"name": "灵石", "quantity": 400}
            ]),
            "base_success_rate": 38,
            "spirit_stone_cost": 4000,
            "duration_hours": 120,
            "range_meters": 60,
            "effects": json.dumps({
                "cultivation_speed": 1.5,
                "mp_recovery": 0.8,
                "hp_regeneration": 100
            })
        },
        {
            "name": "封魔镇灵阵",
            "rank": 4,
            "formation_type": "control",
            "description": "封印妖魔,镇压一切邪魔外道",
            "materials": json.dumps([
                {"name": "封魔石", "quantity": 20},
                {"name": "阵旗", "quantity": 18},
                {"name": "镇灵符", "quantity": 12},
                {"name": "灵石", "quantity": 350}
            ]),
            "base_success_rate": 35,
            "spirit_stone_cost": 3500,
            "duration_hours": 48,
            "range_meters": 35,
            "effects": json.dumps({
                "trap_duration": 360,
                "escape_difficulty": 0.85,
                "seal_power": True
            })
        },

        # ========== 化神期阵法 (Rank 5) ==========
        {
            "name": "九龙焚天阵",
            "rank": 5,
            "formation_type": "attack",
            "description": "九龙齐出,焚天煮海的超级攻击大阵",
            "materials": json.dumps([
                {"name": "龙晶", "quantity": 9},
                {"name": "阵旗", "quantity": 27},
                {"name": "五阶妖丹", "quantity": 5},
                {"name": "神性结晶", "quantity": 3},
                {"name": "灵石", "quantity": 800}
            ]),
            "base_success_rate": 30,
            "spirit_stone_cost": 8000,
            "duration_hours": 36,
            "range_meters": 80,
            "effects": json.dumps({
                "damage_per_hour": 2000,
                "attack_frequency": 30,
                "fire_damage": True,
                "area_damage": True
            })
        },
        {
            "name": "混元太极阵",
            "rank": 5,
            "formation_type": "compound",
            "description": "阴阳合一,混元太极的至高复合阵法",
            "materials": json.dumps([
                {"name": "太极石", "quantity": 2},
                {"name": "阵旗", "quantity": 30},
                {"name": "混沌石", "quantity": 5},
                {"name": "神性精华", "quantity": 8},
                {"name": "灵石", "quantity": 1000}
            ]),
            "base_success_rate": 25,
            "spirit_stone_cost": 10000,
            "duration_hours": 168,
            "range_meters": 100,
            "effects": json.dumps({
                "defense_bonus": 1.5,
                "attack_bonus": 1.0,
                "cultivation_speed": 1.0,
                "damage_per_hour": 500,
                "balance_power": True
            })
        },
        {
            "name": "虚空幻境阵",
            "rank": 5,
            "formation_type": "control",
            "description": "构建虚空幻境,困住敌人于无尽迷宫",
            "materials": json.dumps([
                {"name": "虚空结晶", "quantity": 15},
                {"name": "阵旗", "quantity": 24},
                {"name": "幻境石", "quantity": 10},
                {"name": "灵石", "quantity": 700}
            ]),
            "base_success_rate": 28,
            "spirit_stone_cost": 7000,
            "duration_hours": 72,
            "range_meters": 50,
            "effects": json.dumps({
                "trap_duration": 600,
                "escape_difficulty": 0.9,
                "illusion_power": True,
                "confusion": True
            })
        },

        # ========== 炼虚期阵法 (Rank 6) ==========
        {
            "name": "星辰灭世阵",
            "rank": 6,
            "formation_type": "attack",
            "description": "引动星辰之力,毁天灭地的恐怖阵法",
            "materials": json.dumps([
                {"name": "星核", "quantity": 12},
                {"name": "阵旗", "quantity": 36},
                {"name": "六阶妖丹", "quantity": 10},
                {"name": "虚空结晶", "quantity": 20},
                {"name": "灵石", "quantity": 2000}
            ]),
            "base_success_rate": 25,
            "spirit_stone_cost": 20000,
            "duration_hours": 48,
            "range_meters": 150,
            "effects": json.dumps({
                "damage_per_hour": 5000,
                "attack_frequency": 40,
                "star_power": True,
                "massive_damage": True
            })
        },
        {
            "name": "万法归元阵",
            "rank": 6,
            "formation_type": "assist",
            "description": "万法归元,极致提升修炼和恢复效率",
            "materials": json.dumps([
                {"name": "归元石", "quantity": 50},
                {"name": "阵旗", "quantity": 40},
                {"name": "混沌精华", "quantity": 15},
                {"name": "灵石", "quantity": 2500}
            ]),
            "base_success_rate": 22,
            "spirit_stone_cost": 25000,
            "duration_hours": 240,
            "range_meters": 120,
            "effects": json.dumps({
                "cultivation_speed": 2.5,
                "mp_recovery": 1.5,
                "hp_regeneration": 300,
                "enlightenment": True
            })
        },

        # ========== 合体期阵法 (Rank 7) ==========
        {
            "name": "天地同寿阵",
            "rank": 7,
            "formation_type": "defense",
            "description": "天地庇护,防御力与天地同寿",
            "materials": json.dumps([
                {"name": "天地本源", "quantity": 10},
                {"name": "阵旗", "quantity": 49},
                {"name": "七阶妖丹", "quantity": 15},
                {"name": "不灭金", "quantity": 20},
                {"name": "灵石", "quantity": 5000}
            ]),
            "base_success_rate": 20,
            "spirit_stone_cost": 50000,
            "duration_hours": 360,
            "range_meters": 200,
            "effects": json.dumps({
                "defense_bonus": 3.0,
                "damage_reduction": 0.7,
                "hp_regeneration": 500,
                "immortal_shield": True
            })
        },
        {
            "name": "阴阳颠倒阵",
            "rank": 7,
            "formation_type": "compound",
            "description": "颠倒阴阳,逆转乾坤的禁忌大阵",
            "materials": json.dumps([
                {"name": "阴阳石", "quantity": 2},
                {"name": "阵旗", "quantity": 50},
                {"name": "乾坤石", "quantity": 10},
                {"name": "天地本源", "quantity": 15},
                {"name": "灵石", "quantity": 6000}
            ]),
            "base_success_rate": 18,
            "spirit_stone_cost": 60000,
            "duration_hours": 144,
            "range_meters": 180,
            "effects": json.dumps({
                "defense_bonus": 2.0,
                "attack_bonus": 2.5,
                "damage_per_hour": 3000,
                "reverse_power": True,
                "chaos_control": True
            })
        },

        # ========== 大乘期阵法 (Rank 8) ==========
        {
            "name": "诛仙剑阵",
            "rank": 8,
            "formation_type": "attack",
            "description": "传说中的诛仙剑阵,四剑合一斩仙屠神",
            "materials": json.dumps([
                {"name": "诛仙剑气", "quantity": 4},
                {"name": "阵旗", "quantity": 64},
                {"name": "八阶妖丹", "quantity": 20},
                {"name": "仙晶", "quantity": 50},
                {"name": "鸿蒙紫气", "quantity": 5},
                {"name": "灵石", "quantity": 15000}
            ]),
            "base_success_rate": 15,
            "spirit_stone_cost": 150000,
            "duration_hours": 72,
            "range_meters": 300,
            "effects": json.dumps({
                "damage_per_hour": 15000,
                "attack_frequency": 60,
                "immortal_slaying": True,
                "unstoppable": True
            })
        },
        {
            "name": "周天星斗大阵",
            "rank": 8,
            "formation_type": "compound",
            "description": "演化周天星斗,攻防兼备的终极大阵",
            "materials": json.dumps([
                {"name": "星辰本源", "quantity": 365},
                {"name": "阵旗", "quantity": 72},
                {"name": "仙晶", "quantity": 100},
                {"name": "鸿蒙紫气", "quantity": 10},
                {"name": "灵石", "quantity": 20000}
            ]),
            "base_success_rate": 12,
            "spirit_stone_cost": 200000,
            "duration_hours": 720,
            "range_meters": 500,
            "effects": json.dumps({
                "defense_bonus": 5.0,
                "attack_bonus": 4.0,
                "cultivation_speed": 3.0,
                "damage_per_hour": 8000,
                "star_formation": True
            })
        },

        # ========== 渡劫期阵法 (Rank 9) ==========
        {
            "name": "都天神煞大阵",
            "rank": 9,
            "formation_type": "attack",
            "description": "十二都天神煞,可匹敌圣人的恐怖杀阵",
            "materials": json.dumps([
                {"name": "都天精血", "quantity": 12},
                {"name": "阵旗", "quantity": 108},
                {"name": "九阶妖丹", "quantity": 30},
                {"name": "鸿蒙紫气", "quantity": 20},
                {"name": "天道碎片", "quantity": 3},
                {"name": "灵石", "quantity": 50000}
            ]),
            "base_success_rate": 10,
            "spirit_stone_cost": 500000,
            "duration_hours": 120,
            "range_meters": 1000,
            "effects": json.dumps({
                "damage_per_hour": 50000,
                "attack_frequency": 100,
                "divine_power": True,
                "saint_level": True
            })
        },
        {
            "name": "混沌开天阵",
            "rank": 9,
            "formation_type": "compound",
            "description": "混沌演化,开天辟地的至高阵法",
            "materials": json.dumps([
                {"name": "混沌本源", "quantity": 1},
                {"name": "阵旗", "quantity": 81},
                {"name": "开天石", "quantity": 50},
                {"name": "鸿蒙紫气", "quantity": 30},
                {"name": "天道碎片", "quantity": 10},
                {"name": "灵石", "quantity": 100000}
            ]),
            "base_success_rate": 8,
            "spirit_stone_cost": 1000000,
            "duration_hours": 1440,
            "range_meters": 2000,
            "effects": json.dumps({
                "defense_bonus": 10.0,
                "attack_bonus": 10.0,
                "cultivation_speed": 5.0,
                "damage_per_hour": 20000,
                "creation_power": True,
                "supreme_formation": True
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
        初始化阵法系统

        Args:
            db: 数据库管理器
            player_mgr: 玩家管理器
            profession_mgr: 职业管理器
        """
        self.db = db
        self.player_mgr = player_mgr
        self.profession_mgr = profession_mgr

    async def init_base_formations(self):
        """初始化基础阵法"""
        for formation_data in self.BASE_FORMATIONS:
            # 检查是否已存在
            row = await self.db.fetchone(
                """
                SELECT id FROM recipes
                WHERE name = ? AND recipe_type = 'formation' AND user_id IS NULL
                """,
                (formation_data['name'],)
            )

            if not row:
                # 插入阵法配方
                await self.db.execute(
                    """
                    INSERT INTO recipes (
                        user_id, recipe_type, name, rank, description,
                        materials, output_name, base_success_rate,
                        special_requirements, source, is_ai_generated
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        None,  # 公共阵法
                        'formation',
                        formation_data['name'],
                        formation_data['rank'],
                        formation_data['description'],
                        formation_data['materials'],
                        formation_data['name'],
                        formation_data['base_success_rate'],
                        json.dumps({
                            "formation_type": formation_data['formation_type'],
                            "duration_hours": formation_data['duration_hours'],
                            "range_meters": formation_data['range_meters'],
                            "spirit_stone_cost": formation_data['spirit_stone_cost'],
                            "effects": formation_data['effects']
                        }),
                        "系统预设",
                        0
                    )
                )

        logger.info("基础阵法初始化完成")

    async def deploy_formation(
        self,
        user_id: str,
        formation_id: int,
        location: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        布置阵法

        Args:
            user_id: 玩家ID
            formation_id: 阵法配方ID
            location: 布阵位置

        Returns:
            Dict: 布阵结果

        Raises:
            PlayerNotFoundError: 玩家不存在
            ProfessionNotFoundError: 未学习阵法师
            FormationPatternNotFoundError: 阵法配方不存在
            InsufficientMaterialsError: 材料不足
            InsufficientSpiritStoneError: 灵石不足
            FormationAlreadyExistsError: 该位置已有阵法
        """
        # 获取玩家信息
        player = await self.player_mgr.get_player_or_error(user_id)

        # 获取阵法师职业
        profession = await self.profession_mgr.get_profession(user_id, "formation_master")
        if not profession:
            raise ProfessionNotFoundError("尚未学习阵法师职业")

        # 获取阵法配方
        formation = await self._get_formation_pattern(formation_id)
        if not formation:
            raise FormationPatternNotFoundError(f"阵法配方不存在: {formation_id}")

        # 检查品级
        if formation['rank'] > profession.rank:
            raise FormationError(f"阵法需要{formation['rank']}品阵法师,当前仅{profession.rank}品")

        # 解析材料需求
        materials_required = json.loads(formation['materials'])
        special_req = json.loads(formation.get('special_requirements', '{}'))

        # 获取阵法信息
        formation_type = special_req.get('formation_type', 'assist')
        duration_hours = special_req.get('duration_hours', 24)
        range_meters = special_req.get('range_meters', 10)
        spirit_stone_cost = special_req.get('spirit_stone_cost', 200)
        effects_str = special_req.get('effects', '{}')

        # TODO: 检查材料是否足够 (需要物品系统)

        # 检查灵石
        if player.spirit_stone < spirit_stone_cost:
            raise InsufficientSpiritStoneError(f"灵石不足,需要{spirit_stone_cost}灵石")

        # 如果没有指定位置,使用玩家当前位置
        if not location:
            location = player.current_location

        # 检查该位置是否已有活跃阵法
        existing = await self._get_active_formation_at_location(location, user_id)
        if existing:
            raise FormationAlreadyExistsError(f"该位置已有活跃阵法: {existing['formation_name']}")

        # 计算成功率
        base_success_rate = formation['base_success_rate'] / 100.0
        success_rate = profession.get_success_rate()

        # 灵根加成
        if player.spirit_root_type in ["水", "土", "五行均衡"]:
            if player.spirit_root_type == "水":
                success_rate += 0.15  # 水系+15%
            elif player.spirit_root_type == "土":
                success_rate += 0.20  # 土系+20%
            else:
                success_rate += 0.20  # 五行均衡+20%

        # 限制最高成功率
        success_rate = min(0.95, success_rate)

        # 判断是否成功
        success = random.random() < success_rate

        if not success:
            # 布阵失败
            await self.player_mgr.add_spirit_stone(user_id, -spirit_stone_cost // 2)  # 失败只消耗一半

            # 添加少量经验
            await self.profession_mgr.add_experience(user_id, "formation_master", 20)

            return {
                'success': False,
                'formation_name': formation['name'],
                'spirit_stone_cost': spirit_stone_cost // 2,
                'experience_gained': 20,
                'message': f"布阵失败,阵法构建时能量紊乱,阵法崩溃了!"
            }

        # 布阵成功
        # 消耗灵石
        await self.player_mgr.add_spirit_stone(user_id, -spirit_stone_cost)

        # 计算阵法强度(基于品级和成功率)
        strength = profession.rank + int(success_rate * 10)

        # 计算过期时间
        expires_at = datetime.now() + timedelta(hours=duration_hours)

        # 创建活跃阵法记录
        await self.db.execute(
            """
            INSERT INTO active_formations (
                user_id, formation_name, location_id, formation_type,
                strength, range, effects, energy_cost, is_active,
                created_at, expires_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                formation['name'],
                location,  # 简化处理,直接用位置名
                formation_type,
                strength,
                range_meters,
                effects_str,
                10,  # 每小时能量消耗
                1,  # 激活状态
                datetime.now().isoformat(),
                expires_at.isoformat()
            )
        )

        # 获得经验
        exp_gain = self._calculate_experience(formation['rank'], duration_hours)
        await self.profession_mgr.add_experience(user_id, "formation_master", exp_gain)

        # 获得声望
        reputation_gain = formation['rank'] * 20
        if formation_type == "compound":
            reputation_gain *= 2  # 复合阵法双倍声望
        await self.profession_mgr.add_reputation(user_id, "formation_master", reputation_gain)

        logger.info(f"玩家 {user_id} 在 {location} 布置了 {formation['name']}")

        return {
            'success': True,
            'formation_name': formation['name'],
            'formation_type': self.FORMATION_TYPES[formation_type]['name'],
            'location': location,
            'strength': strength,
            'range': range_meters,
            'duration_hours': duration_hours,
            'expires_at': expires_at.strftime("%Y-%m-%d %H:%M:%S"),
            'spirit_stone_cost': spirit_stone_cost,
            'experience_gained': exp_gain,
            'reputation_gained': reputation_gain,
            'message': f"布阵成功!{formation['name']}已在{location}激活!"
        }

    async def break_formation(
        self,
        user_id: str,
        formation_id: int,
        method: str = "force"
    ) -> Dict[str, Any]:
        """
        破解阵法

        Args:
            user_id: 玩家ID
            formation_id: 活跃阵法ID
            method: 破阵方法 (force/skill/counter/expert)

        Returns:
            Dict: 破阵结果
        """
        # 获取玩家信息
        player = await self.player_mgr.get_player_or_error(user_id)

        # 获取阵法
        formation = await self._get_active_formation(formation_id)
        if not formation:
            raise FormationError("阵法不存在或已失效")

        if not formation['is_active']:
            raise FormationError("阵法已被撤销")

        # 计算破阵成功率
        success_rate = 0.3  # 基础成功率

        if method == "force":
            # 强行破阵 - 基于战力
            success_rate += player.attack * 0.001
        elif method == "skill":
            # 技巧破阵 - 基于悟性
            success_rate += player.comprehension * 0.01
        elif method == "expert":
            # 阵法师破阵 - 需要阵法师职业
            profession = await self.profession_mgr.get_profession(user_id, "formation_master")
            if profession:
                success_rate += profession.rank * 0.15
                success_rate += profession.success_rate_bonus
            else:
                raise FormationError("需要阵法师职业才能使用专家破阵")

        # 阵法强度影响
        success_rate -= formation['strength'] * 0.05

        # 限制成功率范围
        success_rate = max(0.1, min(0.9, success_rate))

        # 判断是否成功
        success = random.random() < success_rate

        if success:
            # 破阵成功
            await self.db.execute(
                "UPDATE active_formations SET is_active = 0 WHERE id = ?",
                (formation_id,)
            )

            # 如果是阵法师破阵,获得经验和声望
            if method == "expert":
                profession = await self.profession_mgr.get_profession(user_id, "formation_master")
                if profession:
                    exp_gain = formation['strength'] * 30
                    await self.profession_mgr.add_experience(user_id, "formation_master", exp_gain)
                    await self.profession_mgr.add_reputation(user_id, "formation_master", 50)

            logger.info(f"玩家 {user_id} 破解了阵法 {formation_id}")

            return {
                'success': True,
                'formation_name': formation['formation_name'],
                'method': method,
                'message': f"成功破解{formation['formation_name']}!"
            }
        else:
            # 破阵失败
            # 可能受到反噬
            if method == "force" and random.random() < 0.3:
                damage = formation['strength'] * 50
                await self.player_mgr.modify_hp(user_id, -damage)
                return {
                    'success': False,
                    'formation_name': formation['formation_name'],
                    'damage': damage,
                    'message': f"破阵失败!受到阵法反噬,损失{damage}点生命值!"
                }

            return {
                'success': False,
                'formation_name': formation['formation_name'],
                'message': f"破阵失败,阵法依然坚固!"
            }

    async def cancel_formation(self, user_id: str, formation_id: int) -> bool:
        """
        撤销自己布置的阵法

        Args:
            user_id: 玩家ID
            formation_id: 活跃阵法ID

        Returns:
            bool: 是否成功
        """
        # 检查阵法是否属于该玩家
        formation = await self._get_active_formation(formation_id)
        if not formation:
            raise FormationError("阵法不存在")

        if formation['user_id'] != user_id:
            raise FormationError("只能撤销自己布置的阵法")

        # 撤销阵法
        await self.db.execute(
            "UPDATE active_formations SET is_active = 0 WHERE id = ?",
            (formation_id,)
        )

        logger.info(f"玩家 {user_id} 撤销了阵法 {formation_id}")
        return True

    async def get_available_formations(self, user_id: str) -> List[Dict[str, Any]]:
        """
        获取可用的阵法配方列表

        Args:
            user_id: 玩家ID

        Returns:
            List[Dict]: 阵法配方列表
        """
        # 获取阵法师职业
        profession = await self.profession_mgr.get_profession(user_id, "formation_master")
        max_rank = profession.rank if profession else 1

        # 查询公共阵法和玩家拥有的阵法
        rows = await self.db.fetchall(
            """
            SELECT * FROM recipes
            WHERE recipe_type = 'formation'
            AND (user_id IS NULL OR user_id = ?)
            AND rank <= ?
            ORDER BY rank, name
            """,
            (user_id, max_rank)
        )

        formations = []
        for row in rows:
            formation_data = dict(row)
            formations.append(formation_data)

        return formations

    async def get_active_formations(
        self,
        user_id: Optional[str] = None,
        location: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        获取活跃的阵法列表

        Args:
            user_id: 玩家ID (可选)
            location: 位置 (可选)

        Returns:
            List[Dict]: 活跃阵法列表
        """
        query = "SELECT * FROM active_formations WHERE is_active = 1"
        params = []

        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)

        if location:
            query += " AND location_id = ?"
            params.append(location)

        query += " ORDER BY created_at DESC"

        rows = await self.db.fetchall(query, tuple(params))

        formations = []
        for row in rows:
            formation_data = dict(row)
            # 检查是否过期
            if datetime.fromisoformat(formation_data['expires_at']) < datetime.now():
                # 标记为失效
                await self.db.execute(
                    "UPDATE active_formations SET is_active = 0 WHERE id = ?",
                    (formation_data['id'],)
                )
                continue
            formations.append(formation_data)

        return formations

    async def format_formation_list(self, user_id: str) -> str:
        """
        格式化阵法配方列表显示

        Args:
            user_id: 玩家ID

        Returns:
            str: 格式化的阵法列表
        """
        formations = await self.get_available_formations(user_id)
        profession = await self.profession_mgr.get_profession(user_id, "formation_master")

        if not profession:
            return (
                "📜 阵法师阵法\n"
                "─" * 40 + "\n\n"
                "您还没有学习阵法师职业\n\n"
                "💡 使用 /学习职业 阵法师 学习阵法"
            )

        lines = [
            f"📜 阵法师阵法 ({profession.get_full_title()})",
            "─" * 40,
            ""
        ]

        if not formations:
            lines.append("目前没有可用的阵法")
        else:
            for i, formation in enumerate(formations, 1):
                rank_color = "🟢" if formation['rank'] <= profession.rank else "🔴"
                special_req = json.loads(formation.get('special_requirements', '{}'))
                formation_type = special_req.get('formation_type', 'assist')
                type_icon = self.FORMATION_TYPES.get(formation_type, {}).get('icon', '📍')

                lines.append(
                    f"{i}. {rank_color} {type_icon} {formation['name']} ({formation['rank']}品)\n"
                    f"   {formation['description']}\n"
                    f"   成功率: {formation['base_success_rate']}%"
                )

        lines.extend([
            "",
            "💡 使用 /布阵 [编号] 布置阵法",
            "💡 使用 /阵法详情 [编号] 查看详细信息",
            "💡 使用 /查看阵法 查看当前位置的活跃阵法"
        ])

        return "\n".join(lines)

    async def format_active_formations(
        self,
        user_id: str,
        location: Optional[str] = None
    ) -> str:
        """
        格式化活跃阵法列表显示

        Args:
            user_id: 玩家ID
            location: 位置 (可选)

        Returns:
            str: 格式化的活跃阵法列表
        """
        if not location:
            player = await self.player_mgr.get_player_or_error(user_id)
            location = player.current_location

        formations = await self.get_active_formations(location=location)

        lines = [
            f"📍 当前位置活跃阵法 ({location})",
            "─" * 40,
            ""
        ]

        if not formations:
            lines.append("该位置没有活跃的阵法")
        else:
            for i, formation in enumerate(formations, 1):
                type_icon = self.FORMATION_TYPES.get(formation['formation_type'], {}).get('icon', '📍')
                expires_at = datetime.fromisoformat(formation['expires_at'])
                time_left = expires_at - datetime.now()
                hours_left = int(time_left.total_seconds() / 3600)

                lines.append(
                    f"{i}. {type_icon} {formation['formation_name']}\n"
                    f"   强度: {formation['strength']} | 范围: {formation['range']}米\n"
                    f"   剩余时间: {hours_left}小时\n"
                    f"   布阵者: {'我' if formation['user_id'] == user_id else '其他修士'}"
                )

        lines.extend([
            "",
            "💡 使用 /破阵 [编号] [方法] 破解阵法",
            "💡 破阵方法: force(强行) skill(技巧) expert(专家)"
        ])

        return "\n".join(lines)

    async def _get_formation_pattern(self, formation_id: int) -> Optional[Dict[str, Any]]:
        """获取阵法配方信息"""
        row = await self.db.fetchone(
            "SELECT * FROM recipes WHERE id = ? AND recipe_type = 'formation'",
            (formation_id,)
        )
        return dict(row) if row else None

    async def _get_active_formation(self, formation_id: int) -> Optional[Dict[str, Any]]:
        """获取活跃阵法信息"""
        row = await self.db.fetchone(
            "SELECT * FROM active_formations WHERE id = ?",
            (formation_id,)
        )
        return dict(row) if row else None

    async def _get_active_formation_at_location(
        self,
        location: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """获取指定位置的活跃阵法"""
        row = await self.db.fetchone(
            """
            SELECT * FROM active_formations
            WHERE location_id = ? AND user_id = ? AND is_active = 1
            """,
            (location, user_id)
        )
        return dict(row) if row else None

    def _calculate_experience(self, rank: int, duration_hours: int) -> int:
        """
        计算获得的经验

        Args:
            rank: 阵法品级
            duration_hours: 持续时间

        Returns:
            int: 经验值
        """
        base_exp = rank * 80
        duration_bonus = min(duration_hours / 24, 3.0)  # 最多3倍
        return int(base_exp * duration_bonus)
