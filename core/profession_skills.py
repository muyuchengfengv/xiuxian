"""
职业技能树系统
管理职业被动技能的学习和升级
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
import json
from astrbot.api import logger

from ..core.database import DatabaseManager
from ..core.player import PlayerManager
from ..core.profession import ProfessionManager, ProfessionNotFoundError


class SkillError(Exception):
    """技能系统异常"""
    pass


class SkillNotFoundError(SkillError):
    """技能不存在"""
    pass


class InsufficientSkillPointsError(SkillError):
    """技能点不足"""
    pass


class SkillAlreadyLearnedError(SkillError):
    """技能已学习"""
    pass


class ProfessionSkillManager:
    """职业技能管理器"""

    # 职业技能配置
    SKILL_TREE = {
        "alchemist": {
            "药性精通": {
                "description": "提升丹药效果",
                "max_level": 10,
                "required_rank": 1,
                "cost_points": 1,
                "effect_type": "pill_effect_bonus",
                "effect_per_level": 0.02  # 每级+2%
            },
            "高效炼丹": {
                "description": "减少材料消耗",
                "max_level": 10,
                "required_rank": 2,
                "cost_points": 1,
                "effect_type": "material_save_chance",
                "effect_per_level": 0.03  # 每级+3%几率节省材料
            },
            "批量炼制": {
                "description": "一次炼制多颗丹药",
                "max_level": 5,
                "required_rank": 3,
                "cost_points": 2,
                "effect_type": "batch_craft_count",
                "effect_per_level": 1  # 每级+1个额外数量
            },
            "丹劫感悟": {
                "description": "有几率引发丹劫,炼出极品丹",
                "max_level": 10,
                "required_rank": 4,
                "cost_points": 3,
                "effect_type": "high_quality_chance",
                "effect_per_level": 0.01  # 每级+1%极品几率
            }
        },
        "blacksmith": {
            "材料鉴定": {
                "description": "识别稀有材料品质",
                "max_level": 10,
                "required_rank": 1,
                "cost_points": 1,
                "effect_type": "material_identify",
                "effect_per_level": 0.1  # 每级+10%识别准确度
            },
            "灵纹精通": {
                "description": "提升装备属性",
                "max_level": 10,
                "required_rank": 2,
                "cost_points": 1,
                "effect_type": "equipment_attribute_bonus",
                "effect_per_level": 0.02  # 每级+2%属性
            },
            "装备强化精通": {
                "description": "强化成功率提升",
                "max_level": 10,
                "required_rank": 2,
                "cost_points": 1,
                "effect_type": "enhance_success_rate",
                "effect_per_level": 0.02  # 每级+2%成功率
            },
            "器灵觉醒": {
                "description": "炼制装备时有几率诞生器灵",
                "max_level": 5,
                "required_rank": 5,
                "cost_points": 3,
                "effect_type": "spirit_awaken_chance",
                "effect_per_level": 0.01  # 每级+1%觉醒几率
            }
        },
        "formation_master": {
            "快速布阵": {
                "description": "减少布阵时间",
                "max_level": 10,
                "required_rank": 1,
                "cost_points": 1,
                "effect_type": "deploy_time_reduction",
                "effect_per_level": 0.05  # 每级-5%时间
            },
            "阵法强化": {
                "description": "提升阵法威力",
                "max_level": 10,
                "required_rank": 2,
                "cost_points": 1,
                "effect_type": "formation_power_bonus",
                "effect_per_level": 0.03  # 每级+3%威力
            },
            "破阵精通": {
                "description": "破阵成功率提升",
                "max_level": 10,
                "required_rank": 2,
                "cost_points": 1,
                "effect_type": "break_formation_success",
                "effect_per_level": 0.03  # 每级+3%成功率
            },
            "阵法融合": {
                "description": "可以创造新阵法",
                "max_level": 5,
                "required_rank": 4,
                "cost_points": 3,
                "effect_type": "formation_fusion_unlock",
                "effect_per_level": 1  # 每级解锁一个融合槽位
            }
        },
        "talisman_master": {
            "符文简化": {
                "description": "降低制符难度",
                "max_level": 10,
                "required_rank": 1,
                "cost_points": 1,
                "effect_type": "craft_difficulty_reduction",
                "effect_per_level": 0.02  # 每级+2%成功率
            },
            "符箓强化": {
                "description": "提升符箓威力",
                "max_level": 10,
                "required_rank": 2,
                "cost_points": 1,
                "effect_type": "talisman_power_bonus",
                "effect_per_level": 0.03  # 每级+3%威力
            },
            "快速制符": {
                "description": "减少制作时间",
                "max_level": 10,
                "required_rank": 2,
                "cost_points": 1,
                "effect_type": "craft_time_reduction",
                "effect_per_level": 0.05  # 每级-5%时间
            },
            "符箓储存": {
                "description": "增加符箓携带上限",
                "max_level": 10,
                "required_rank": 3,
                "cost_points": 2,
                "effect_type": "talisman_capacity",
                "effect_per_level": 5  # 每级+5个携带上限
            }
        }
    }

    def __init__(
        self,
        db: DatabaseManager,
        player_mgr: PlayerManager,
        profession_mgr: ProfessionManager
    ):
        """
        初始化职业技能管理器

        Args:
            db: 数据库管理器
            player_mgr: 玩家管理器
            profession_mgr: 职业管理器
        """
        self.db = db
        self.player_mgr = player_mgr
        self.profession_mgr = profession_mgr

    async def learn_skill(
        self,
        user_id: str,
        profession_type: str,
        skill_name: str
    ) -> Dict[str, Any]:
        """
        学习职业技能

        Args:
            user_id: 玩家ID
            profession_type: 职业类型
            skill_name: 技能名称

        Returns:
            Dict: 学习结果

        Raises:
            ProfessionNotFoundError: 职业不存在
            SkillNotFoundError: 技能不存在
            SkillAlreadyLearnedError: 技能已学习
            InsufficientSkillPointsError: 技能点不足
        """
        # 获取职业
        profession = await self.profession_mgr.get_profession(user_id, profession_type)
        if not profession:
            raise ProfessionNotFoundError(f"未学习{profession_type}职业")

        # 检查技能是否存在
        if profession_type not in self.SKILL_TREE:
            raise SkillNotFoundError(f"职业类型{profession_type}不存在技能树")

        skill_config = self.SKILL_TREE[profession_type].get(skill_name)
        if not skill_config:
            raise SkillNotFoundError(f"技能{skill_name}不存在")

        # 检查品级要求
        if profession.rank < skill_config['required_rank']:
            raise SkillError(
                f"需要{skill_config['required_rank']}品才能学习该技能,当前{profession.rank}品"
            )

        # 检查是否已学习
        existing_skill = await self._get_skill(user_id, profession_type, skill_name)
        if existing_skill:
            raise SkillAlreadyLearnedError(f"已经学习了{skill_name}")

        # 检查技能点
        cost = skill_config['cost_points']
        if profession.skill_points < cost:
            raise InsufficientSkillPointsError(
                f"技能点不足,需要{cost}点,当前{profession.skill_points}点"
            )

        # 扣除技能点
        await self.db.execute(
            """
            UPDATE professions
            SET skill_points = skill_points - ?
            WHERE user_id = ? AND profession_type = ?
            """,
            (cost, user_id, profession_type)
        )

        # 创建技能记录
        await self.db.execute(
            """
            INSERT INTO profession_skills (
                user_id, profession_type, skill_name, skill_level,
                effect_type, effect_value, description, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                profession_type,
                skill_name,
                1,  # 初始等级
                skill_config['effect_type'],
                skill_config['effect_per_level'],
                skill_config['description'],
                datetime.now().isoformat()
            )
        )

        logger.info(f"玩家 {user_id} 学习了技能: {profession_type}.{skill_name}")

        return {
            'success': True,
            'skill_name': skill_name,
            'cost_points': cost,
            'remaining_points': profession.skill_points - cost,
            'initial_effect': skill_config['effect_per_level'],
            'message': f"成功学习技能: {skill_name}!"
        }

    async def upgrade_skill(
        self,
        user_id: str,
        profession_type: str,
        skill_name: str
    ) -> Dict[str, Any]:
        """
        升级职业技能

        Args:
            user_id: 玩家ID
            profession_type: 职业类型
            skill_name: 技能名称

        Returns:
            Dict: 升级结果
        """
        # 获取职业
        profession = await self.profession_mgr.get_profession(user_id, profession_type)
        if not profession:
            raise ProfessionNotFoundError(f"未学习{profession_type}职业")

        # 获取技能
        skill = await self._get_skill(user_id, profession_type, skill_name)
        if not skill:
            raise SkillNotFoundError(f"尚未学习{skill_name}")

        # 获取技能配置
        skill_config = self.SKILL_TREE[profession_type][skill_name]

        # 检查是否已满级
        if skill['skill_level'] >= skill_config['max_level']:
            raise SkillError(f"{skill_name}已达到最大等级")

        # 检查技能点(升级消耗1点)
        if profession.skill_points < 1:
            raise InsufficientSkillPointsError("技能点不足,需要1点")

        # 扣除技能点
        await self.db.execute(
            """
            UPDATE professions
            SET skill_points = skill_points - 1
            WHERE user_id = ? AND profession_type = ?
            """,
            (user_id, profession_type)
        )

        # 升级技能
        new_level = skill['skill_level'] + 1
        new_effect = skill_config['effect_per_level'] * new_level

        await self.db.execute(
            """
            UPDATE profession_skills
            SET skill_level = ?, effect_value = ?
            WHERE user_id = ? AND profession_type = ? AND skill_name = ?
            """,
            (new_level, new_effect, user_id, profession_type, skill_name)
        )

        logger.info(f"玩家 {user_id} 升级了技能: {profession_type}.{skill_name} → Lv.{new_level}")

        return {
            'success': True,
            'skill_name': skill_name,
            'old_level': skill['skill_level'],
            'new_level': new_level,
            'old_effect': skill['effect_value'],
            'new_effect': new_effect,
            'remaining_points': profession.skill_points - 1,
            'message': f"{skill_name} 升级到 Lv.{new_level}!"
        }

    async def get_player_skills(
        self,
        user_id: str,
        profession_type: str
    ) -> List[Dict[str, Any]]:
        """
        获取玩家已学习的技能列表

        Args:
            user_id: 玩家ID
            profession_type: 职业类型

        Returns:
            List[Dict]: 技能列表
        """
        rows = await self.db.fetchall(
            """
            SELECT * FROM profession_skills
            WHERE user_id = ? AND profession_type = ?
            ORDER BY skill_level DESC, skill_name
            """,
            (user_id, profession_type)
        )

        skills = []
        for row in rows:
            skill_data = dict(row)
            skills.append(skill_data)

        return skills

    async def get_available_skills(
        self,
        user_id: str,
        profession_type: str
    ) -> List[Dict[str, Any]]:
        """
        获取可学习的技能列表

        Args:
            user_id: 玩家ID
            profession_type: 职业类型

        Returns:
            List[Dict]: 可学习的技能列表
        """
        # 获取职业
        profession = await self.profession_mgr.get_profession(user_id, profession_type)
        if not profession:
            return []

        # 获取已学习的技能
        learned_skills = await self.get_player_skills(user_id, profession_type)
        learned_skill_names = {s['skill_name'] for s in learned_skills}

        # 获取可学习的技能
        available = []
        if profession_type in self.SKILL_TREE:
            for skill_name, skill_config in self.SKILL_TREE[profession_type].items():
                if skill_name not in learned_skill_names:
                    # 检查品级要求
                    if profession.rank >= skill_config['required_rank']:
                        available.append({
                            'skill_name': skill_name,
                            'description': skill_config['description'],
                            'required_rank': skill_config['required_rank'],
                            'cost_points': skill_config['cost_points'],
                            'max_level': skill_config['max_level'],
                            'effect_type': skill_config['effect_type'],
                            'effect_per_level': skill_config['effect_per_level'],
                            'can_learn': profession.skill_points >= skill_config['cost_points']
                        })

        return available

    async def get_skill_effects(
        self,
        user_id: str,
        profession_type: str
    ) -> Dict[str, float]:
        """
        获取所有技能的总效果

        Args:
            user_id: 玩家ID
            profession_type: 职业类型

        Returns:
            Dict: 效果类型 -> 效果值
        """
        skills = await self.get_player_skills(user_id, profession_type)

        effects = {}
        for skill in skills:
            effect_type = skill['effect_type']
            effect_value = skill['effect_value']

            if effect_type in effects:
                effects[effect_type] += effect_value
            else:
                effects[effect_type] = effect_value

        return effects

    async def format_skill_tree(
        self,
        user_id: str,
        profession_type: str
    ) -> str:
        """
        格式化技能树显示

        Args:
            user_id: 玩家ID
            profession_type: 职业类型

        Returns:
            str: 格式化的技能树文本
        """
        profession = await self.profession_mgr.get_profession(user_id, profession_type)
        if not profession:
            return "您还没有学习该职业"

        learned_skills = await self.get_player_skills(user_id, profession_type)
        available_skills = await self.get_available_skills(user_id, profession_type)

        # 创建技能名称到数据的映射
        learned_map = {s['skill_name']: s for s in learned_skills}

        lines = [
            f"🌟 {profession.get_full_title()} 技能树",
            "─" * 40,
            f"💎 可用技能点: {profession.skill_points}",
            ""
        ]

        # 显示已学习的技能
        if learned_skills:
            lines.append("📚 已学习技能:")
            lines.append("")
            for skill in learned_skills:
                skill_config = self.SKILL_TREE[profession_type][skill['skill_name']]
                lines.append(
                    f"  ✅ {skill['skill_name']} Lv.{skill['skill_level']}/{skill_config['max_level']}\n"
                    f"     {skill['description']}\n"
                    f"     效果: {self._format_effect(skill['effect_type'], skill['effect_value'])}"
                )
            lines.append("")

        # 显示可学习的技能
        if available_skills:
            lines.append("📖 可学习技能:")
            lines.append("")
            for skill in available_skills:
                can_afford = "🟢" if skill['can_learn'] else "🔴"
                lines.append(
                    f"  {can_afford} {skill['skill_name']} (消耗{skill['cost_points']}点)\n"
                    f"     {skill['description']}\n"
                    f"     需要: {skill['required_rank']}品 | 最大等级: {skill['max_level']}\n"
                    f"     效果: {self._format_effect(skill['effect_type'], skill['effect_per_level'])}/级"
                )
            lines.append("")

        lines.extend([
            "💡 使用 /学习技能 [技能名] 学习新技能",
            "💡 使用 /升级技能 [技能名] 升级已学技能"
        ])

        return "\n".join(lines)

    async def _get_skill(
        self,
        user_id: str,
        profession_type: str,
        skill_name: str
    ) -> Optional[Dict[str, Any]]:
        """获取技能记录"""
        row = await self.db.fetchone(
            """
            SELECT * FROM profession_skills
            WHERE user_id = ? AND profession_type = ? AND skill_name = ?
            """,
            (user_id, profession_type, skill_name)
        )
        return dict(row) if row else None

    def _format_effect(self, effect_type: str, effect_value: float) -> str:
        """格式化效果显示"""
        effect_names = {
            "pill_effect_bonus": f"+{effect_value*100:.0f}% 丹药效果",
            "material_save_chance": f"{effect_value*100:.0f}% 几率节省材料",
            "batch_craft_count": f"+{int(effect_value)} 批量数量",
            "high_quality_chance": f"+{effect_value*100:.1f}% 极品几率",
            "material_identify": f"+{effect_value*100:.0f}% 识别准确度",
            "equipment_attribute_bonus": f"+{effect_value*100:.0f}% 装备属性",
            "enhance_success_rate": f"+{effect_value*100:.0f}% 强化成功率",
            "spirit_awaken_chance": f"+{effect_value*100:.1f}% 器灵觉醒几率",
            "deploy_time_reduction": f"-{effect_value*100:.0f}% 布阵时间",
            "formation_power_bonus": f"+{effect_value*100:.0f}% 阵法威力",
            "break_formation_success": f"+{effect_value*100:.0f}% 破阵成功率",
            "formation_fusion_unlock": f"解锁{int(effect_value)}个融合槽位",
            "craft_difficulty_reduction": f"+{effect_value*100:.0f}% 制符成功率",
            "talisman_power_bonus": f"+{effect_value*100:.0f}% 符箓威力",
            "craft_time_reduction": f"-{effect_value*100:.0f}% 制作时间",
            "talisman_capacity": f"+{int(effect_value)} 携带上限"
        }
        return effect_names.get(effect_type, f"{effect_value}")
