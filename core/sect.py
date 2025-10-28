"""
宗门系统
负责宗门的创建、管理、成员管理、建筑升级等功能
"""

import uuid
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from astrbot.api import logger

from .database import DatabaseManager
from .player import PlayerManager
from ..models.sect_model import Sect, SectMember
from ..utils import XiuxianException


class SectError(XiuxianException):
    """宗门相关异常"""
    pass


class SectNotFoundError(SectError):
    """宗门不存在异常"""
    pass


class SectNameExistsError(SectError):
    """宗门名称已存在异常"""
    pass


class NotSectMemberError(SectError):
    """不是宗门成员异常"""
    pass


class AlreadyInSectError(SectError):
    """已加入宗门异常"""
    pass


class InsufficientPermissionError(SectError):
    """权限不足异常"""
    pass


class InsufficientResourceError(SectError):
    """资源不足异常"""
    pass


class SectFullError(SectError):
    """宗门已满异常"""
    pass


class SectSystem:
    """宗门系统类"""

    # 宗门建筑配置
    BUILDINGS = {
        "大殿": {
            "name": "宗门大殿",
            "description": "宗门核心建筑，提升宗门等级上限",
            "max_level": 10,
            "upgrade_cost_base": 1000
        },
        "藏经阁": {
            "name": "藏经阁",
            "description": "储存功法的地方，提升功法获取率",
            "max_level": 10,
            "upgrade_cost_base": 800
        },
        "练功房": {
            "name": "练功房",
            "description": "供弟子修炼的地方，提升修炼效率",
            "max_level": 10,
            "upgrade_cost_base": 600
        },
        "炼丹房": {
            "name": "炼丹房",
            "description": "炼制丹药的地方，提升丹药品质",
            "max_level": 10,
            "upgrade_cost_base": 700
        },
        "炼器房": {
            "name": "炼器房",
            "description": "炼制装备的地方，提升装备品质",
            "max_level": 10,
            "upgrade_cost_base": 700
        }
    }

    # 职位权限配置
    POSITIONS = {
        "宗主": {
            "level": 5,
            "permissions": ["manage_all", "upgrade_building", "declare_war", "manage_members", "set_announcement"]
        },
        "长老": {
            "level": 4,
            "permissions": ["upgrade_building", "manage_members", "set_announcement"]
        },
        "执事": {
            "level": 3,
            "permissions": ["manage_members"]
        },
        "精英弟子": {
            "level": 2,
            "permissions": []
        },
        "弟子": {
            "level": 1,
            "permissions": []
        }
    }

    def __init__(self, db: DatabaseManager, player_mgr: PlayerManager):
        """
        初始化宗门系统

        Args:
            db: 数据库管理器
            player_mgr: 玩家管理器
        """
        self.db = db
        self.player_mgr = player_mgr

    async def create_sect(self, user_id: str, name: str, description: str,
                         sect_type: str = "正派", sect_style: str = "剑修") -> Sect:
        """
        创建宗门

        Args:
            user_id: 创建者ID
            name: 宗门名称
            description: 宗门描述
            sect_type: 宗门类型
            sect_style: 宗门风格

        Returns:
            创建的宗门对象

        Raises:
            AlreadyInSectError: 已加入宗门
            SectNameExistsError: 宗门名称已存在
        """
        # 检查玩家是否已加入宗门
        current_sect = await self.get_player_sect(user_id)
        if current_sect:
            raise AlreadyInSectError(f"道友已加入宗门 {current_sect.name}，无法创建新宗门")

        # 检查宗门名称是否存在
        if await self._sect_name_exists(name):
            raise SectNameExistsError(f"宗门名称 {name} 已被使用")

        # 获取玩家信息
        player = await self.player_mgr.get_player_or_error(user_id)

        # 创建宗门
        sect = Sect(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            sect_type=sect_type,
            sect_style=sect_style,
            leader_id=user_id,
            member_count=1,
            max_members=20,
            buildings={
                "大殿": 1,
                "藏经阁": 0,
                "练功房": 0,
                "炼丹房": 0,
                "炼器房": 0
            }
        )

        # 保存宗门
        await self._save_sect(sect)

        # 添加创建者为宗主
        member = SectMember(
            user_id=user_id,
            sect_id=sect.id,
            position="宗主",
            position_level=5
        )
        await self._save_member(member)

        # 添加初始基础功法（练气-元婴期）
        await self._init_sect_base_methods(sect.id)

        logger.info(f"玩家 {player.name} 创建宗门: {name}")

        return sect

    async def _init_sect_base_methods(self, sect_id: str):
        """为新宗门初始化基础功法"""
        import json

        base_methods = [
            # 练气期功法
            {
                "method_id": f"sect_base_qi_{sect_id}",
                "method_name": "基础练气诀",
                "method_type": "心法",
                "method_quality": "凡品",
                "required_contribution": 0,
                "required_position": "弟子",
                "description": "最基础的练气功法"
            },
            # 筑基期功法
            {
                "method_id": f"sect_base_foundation_{sect_id}",
                "method_name": "筑基心法",
                "method_type": "心法",
                "method_quality": "灵品",
                "required_contribution": 100,
                "required_position": "弟子",
                "description": "筑基期修炼功法"
            },
            # 金丹期功法
            {
                "method_id": f"sect_base_golden_{sect_id}",
                "method_name": "金丹真诀",
                "method_type": "心法",
                "method_quality": "灵品",
                "required_contribution": 300,
                "required_position": "精英弟子",
                "description": "金丹期修炼功法"
            },
            # 元婴期功法
            {
                "method_id": f"sect_base_nascent_{sect_id}",
                "method_name": "元婴神功",
                "method_type": "心法",
                "method_quality": "宝品",
                "required_contribution": 500,
                "required_position": "执事",
                "description": "元婴期修炼功法"
            },
            # 基础剑法
            {
                "method_id": f"sect_base_sword_{sect_id}",
                "method_name": "基础剑诀",
                "method_type": "剑法",
                "method_quality": "凡品",
                "required_contribution": 50,
                "required_position": "弟子",
                "description": "最基础的剑法"
            },
            # 基础掌法
            {
                "method_id": f"sect_base_palm_{sect_id}",
                "method_name": "基础掌法",
                "method_type": "掌法",
                "method_quality": "凡品",
                "required_contribution": 50,
                "required_position": "弟子",
                "description": "最基础的掌法"
            },
        ]

        await self._ensure_sect_methods_table()

        for method in base_methods:
            required_position_level = self.POSITIONS.get(method["required_position"], {}).get("level", 1)

            await self.db.execute(
                """
                INSERT INTO sect_methods (
                    sect_id, method_id, method_name, method_type, method_quality,
                    required_contribution, required_position, required_position_level,
                    donated_by, added_at, learn_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    sect_id,
                    method["method_id"],
                    method["method_name"],
                    method["method_type"],
                    method["method_quality"],
                    method["required_contribution"],
                    method["required_position"],
                    required_position_level,
                    None,  # 系统初始化，无捐献者
                    datetime.now().isoformat(),
                    0
                )
            )

        logger.info(f"宗门 {sect_id} 初始化 {len(base_methods)} 个基础功法")

    async def join_sect(self, user_id: str, sect_id: str) -> SectMember:
        """
        加入宗门

        Args:
            user_id: 用户ID
            sect_id: 宗门ID

        Returns:
            成员对象

        Raises:
            AlreadyInSectError: 已加入宗门
            SectNotFoundError: 宗门不存在
            SectFullError: 宗门已满
        """
        # 检查是否已加入宗门
        current_sect = await self.get_player_sect(user_id)
        if current_sect:
            raise AlreadyInSectError(f"道友已加入宗门 {current_sect.name}")

        # 获取宗门
        sect = await self.get_sect_by_id(sect_id)

        # 检查宗门是否可以招募
        if not sect.can_recruit():
            if sect.member_count >= sect.max_members:
                raise SectFullError(f"宗门 {sect.name} 已满员")
            else:
                raise SectError(f"宗门 {sect.name} 当前不招募新成员")

        # 添加成员
        member = SectMember(
            user_id=user_id,
            sect_id=sect_id,
            position="弟子",
            position_level=1
        )
        await self._save_member(member)

        # 更新宗门成员数
        sect.member_count += 1
        await self._update_sect(sect)

        player = await self.player_mgr.get_player_or_error(user_id)
        logger.info(f"玩家 {player.name} 加入宗门: {sect.name}")

        return member

    async def leave_sect(self, user_id: str) -> Sect:
        """
        离开宗门

        Args:
            user_id: 用户ID

        Returns:
            离开的宗门对象

        Raises:
            NotSectMemberError: 不是宗门成员
            SectError: 宗主无法离开
        """
        # 获取成员信息
        member = await self.get_sect_member(user_id)
        if not member:
            raise NotSectMemberError("道友尚未加入任何宗门")

        # 宗主不能直接离开
        if member.position == "宗主":
            raise SectError("宗主无法离开宗门，请先转让宗主或解散宗门")

        # 获取宗门信息
        sect = await self.get_sect_by_id(member.sect_id)

        # 删除成员记录
        await self._delete_member(user_id)

        # 更新宗门成员数
        sect.member_count -= 1
        await self._update_sect(sect)

        player = await self.player_mgr.get_player_or_error(user_id)
        logger.info(f"玩家 {player.name} 离开宗门: {sect.name}")

        return sect

    async def kick_member(self, operator_id: str, target_id: str) -> SectMember:
        """
        踢出成员

        Args:
            operator_id: 操作者ID
            target_id: 目标ID

        Returns:
            被踢出的成员对象

        Raises:
            InsufficientPermissionError: 权限不足
        """
        # 检查操作者权限
        operator_member = await self.get_sect_member(operator_id)
        if not operator_member or not operator_member.can_manage_members():
            raise InsufficientPermissionError("权限不足，无法踢出成员")

        # 获取目标成员
        target_member = await self.get_sect_member(target_id)
        if not target_member:
            raise NotSectMemberError("目标玩家不在宗门中")

        # 检查是否在同一宗门
        if operator_member.sect_id != target_member.sect_id:
            raise SectError("只能踢出本宗门成员")

        # 不能踢出宗主
        if target_member.position == "宗主":
            raise SectError("无法踢出宗主")

        # 检查职位等级（只能踢出低于自己的）
        if target_member.position_level >= operator_member.position_level:
            raise InsufficientPermissionError("无法踢出职位高于或等于自己的成员")

        # 删除成员
        await self._delete_member(target_id)

        # 更新宗门成员数
        sect = await self.get_sect_by_id(target_member.sect_id)
        sect.member_count -= 1
        await self._update_sect(sect)

        logger.info(f"成员 {target_id} 被踢出宗门 {sect.name}")

        return target_member

    async def promote_member(self, operator_id: str, target_id: str, new_position: str) -> SectMember:
        """
        晋升成员

        Args:
            operator_id: 操作者ID
            target_id: 目标ID
            new_position: 新职位

        Returns:
            晋升后的成员对象

        Raises:
            InsufficientPermissionError: 权限不足
        """
        # 检查操作者权限
        operator_member = await self.get_sect_member(operator_id)
        if not operator_member or not operator_member.can_manage_members():
            raise InsufficientPermissionError("权限不足，无法晋升成员")

        # 获取目标成员
        target_member = await self.get_sect_member(target_id)
        if not target_member:
            raise NotSectMemberError("目标玩家不在宗门中")

        # 检查新职位
        if new_position not in self.POSITIONS:
            raise ValueError(f"无效的职位: {new_position}")

        new_level = self.POSITIONS[new_position]["level"]

        # 只有宗主可以任命长老及以上职位
        if new_level >= 4 and operator_member.position != "宗主":
            raise InsufficientPermissionError("只有宗主可以任命长老及以上职位")

        # 不能晋升到宗主
        if new_position == "宗主":
            raise SectError("无法直接晋升为宗主，请使用转让功能")

        # 更新职位
        target_member.position = new_position
        target_member.position_level = new_level
        await self._update_member(target_member)

        logger.info(f"成员 {target_id} 晋升为 {new_position}")

        return target_member

    async def upgrade_building(self, operator_id: str, building_name: str) -> Tuple[Sect, int]:
        """
        升级建筑

        Args:
            operator_id: 操作者ID
            building_name: 建筑名称

        Returns:
            (更新后的宗门对象, 新等级)

        Raises:
            InsufficientPermissionError: 权限不足
            InsufficientResourceError: 资源不足
        """
        # 检查操作者权限
        member = await self.get_sect_member(operator_id)
        if not member or not member.can_upgrade_buildings():
            raise InsufficientPermissionError("权限不足，无法升级建筑")

        # 获取宗门
        sect = await self.get_sect_by_id(member.sect_id)

        # 检查建筑是否存在
        if building_name not in self.BUILDINGS:
            raise ValueError(f"建筑不存在: {building_name}")

        building_config = self.BUILDINGS[building_name]
        current_level = sect.get_building_level(building_name)

        # 检查是否已满级
        if current_level >= building_config["max_level"]:
            raise SectError(f"{building_config['name']} 已达最高等级")

        # 计算升级费用
        upgrade_cost = building_config["upgrade_cost_base"] * (current_level + 1)

        # 检查灵石是否足够
        if sect.spirit_stone < upgrade_cost:
            raise InsufficientResourceError(f"灵石不足，需要 {upgrade_cost} 灵石")

        # 扣除灵石并升级
        sect.spirit_stone -= upgrade_cost
        sect.upgrade_building(building_name)
        await self._update_sect(sect)

        new_level = sect.get_building_level(building_name)
        logger.info(f"宗门 {sect.name} 升级 {building_name} 到 {new_level} 级")

        return sect, new_level

    async def donate_spirit_stone(self, user_id: str, amount: int) -> Tuple[Sect, int]:
        """
        捐献灵石

        Args:
            user_id: 用户ID
            amount: 捐献数量

        Returns:
            (宗门对象, 获得的贡献度)

        Raises:
            NotSectMemberError: 不是宗门成员
        """
        # 获取成员信息
        member = await self.get_sect_member(user_id)
        if not member:
            raise NotSectMemberError("道友尚未加入任何宗门")

        # 获取宗门
        sect = await self.get_sect_by_id(member.sect_id)

        # TODO: 从玩家背包扣除灵石（需要实现灵石系统）

        # 增加宗门灵石
        sect.spirit_stone += amount

        # 计算贡献度（1灵石=1贡献）
        contribution = amount
        member.contribution += contribution
        member.total_contribution += contribution
        sect.contribution += contribution

        # 增加宗门经验
        experience = amount // 10  # 10灵石=1经验
        leveled_up = sect.add_experience(experience)

        await self._update_sect(sect)
        await self._update_member(member)

        player = await self.player_mgr.get_player_or_error(user_id)
        logger.info(f"玩家 {player.name} 向宗门 {sect.name} 捐献 {amount} 灵石")

        if leveled_up:
            logger.info(f"宗门 {sect.name} 升级到 {sect.level} 级！")

        return sect, contribution

    async def get_sect_by_id(self, sect_id: str) -> Sect:
        """根据ID获取宗门"""
        await self._ensure_sects_table()

        result = await self.db.fetchone(
            "SELECT * FROM sects WHERE id = ?",
            (sect_id,)
        )

        if result is None:
            raise SectNotFoundError(sect_id)

        sect_data = dict(result)
        return Sect.from_dict(sect_data)

    async def get_sect_by_name(self, name: str) -> Optional[Sect]:
        """根据名称获取宗门"""
        await self._ensure_sects_table()

        result = await self.db.fetchone(
            "SELECT * FROM sects WHERE name = ?",
            (name,)
        )

        if result is None:
            return None

        sect_data = dict(result)
        return Sect.from_dict(sect_data)

    async def get_player_sect(self, user_id: str) -> Optional[Sect]:
        """获取玩家所在宗门"""
        member = await self.get_sect_member(user_id)
        if not member:
            return None

        return await self.get_sect_by_id(member.sect_id)

    async def get_sect_member(self, user_id: str) -> Optional[SectMember]:
        """获取成员信息"""
        await self._ensure_members_table()

        result = await self.db.fetchone(
            "SELECT * FROM sect_members WHERE user_id = ?",
            (user_id,)
        )

        if result is None:
            return None

        member_data = dict(result)
        return SectMember.from_dict(member_data)

    async def get_sect_members(self, sect_id: str) -> List[SectMember]:
        """获取宗门所有成员"""
        await self._ensure_members_table()

        results = await self.db.fetchall(
            "SELECT * FROM sect_members WHERE sect_id = ? ORDER BY position_level DESC, total_contribution DESC",
            (sect_id,)
        )

        members = []
        for result in results:
            member_data = dict(result)
            member = SectMember.from_dict(member_data)
            members.append(member)

        return members

    async def get_all_sects(self, limit: int = 50) -> List[Sect]:
        """获取所有宗门"""
        await self._ensure_sects_table()

        results = await self.db.fetchall(
            "SELECT * FROM sects ORDER BY power DESC, level DESC LIMIT ?",
            (limit,)
        )

        sects = []
        for result in results:
            sect_data = dict(result)
            sect = Sect.from_dict(sect_data)
            sects.append(sect)

        return sects

    # ========== 宗门建筑加成系统 ==========

    async def get_sect_bonuses(self, sect_id: str) -> Dict[str, float]:
        """
        计算宗门建筑加成

        Args:
            sect_id: 宗门ID

        Returns:
            加成字典，包含各类型加成系数

        Raises:
            SectNotFoundError: 宗门不存在
        """
        # 获取宗门信息
        sect = await self.get_sect_by_id(sect_id)

        # 建筑加成配置
        bonuses = {
            "cultivation_bonus": 0.0,  # 修炼效率加成
            "alchemy_bonus": 0.0,      # 炼丹成功率加成
            "refining_bonus": 0.0,     # 炼器成功率加成
            "formation_bonus": 0.0,    # 阵法效果加成
            "talisman_bonus": 0.0,     # 符箓效果加成
            "method_quality_bonus": 0.0  # 功法品质加成
        }

        # 练功房：修炼效率加成 +10%/级
        practice_room_level = sect.get_building_level("练功房")
        if practice_room_level > 0:
            bonuses["cultivation_bonus"] = practice_room_level * 0.10

        # 炼丹房：炼丹成功率加成 +8%/级
        alchemy_room_level = sect.get_building_level("炼丹房")
        if alchemy_room_level > 0:
            bonuses["alchemy_bonus"] = alchemy_room_level * 0.08

        # 炼器房：炼器成功率加成 +8%/级
        refining_room_level = sect.get_building_level("炼器房")
        if refining_room_level > 0:
            bonuses["refining_bonus"] = refining_room_level * 0.08

        # 藏经阁：功法品质加成 +5%/级
        library_level = sect.get_building_level("藏经阁")
        if library_level > 0:
            bonuses["method_quality_bonus"] = library_level * 0.05

        return bonuses

    async def apply_sect_bonus(self, user_id: str, bonus_type: str, base_value: float) -> Tuple[float, float]:
        """
        应用宗门加成到数值

        Args:
            user_id: 用户ID
            bonus_type: 加成类型（cultivation_bonus, alchemy_bonus等）
            base_value: 基础值

        Returns:
            (加成后的值, 加成系数)

        Raises:
            ValueError: 无效的加成类型
        """
        # 获取玩家所在宗门
        sect = await self.get_player_sect(user_id)

        # 如果玩家没有宗门，返回原值
        if not sect:
            return base_value, 0.0

        # 获取宗门加成
        bonuses = await self.get_sect_bonuses(sect.id)

        # 检查加成类型是否有效
        if bonus_type not in bonuses:
            raise ValueError(f"无效的加成类型: {bonus_type}")

        # 获取对应的加成系数
        bonus_rate = bonuses[bonus_type]

        # 计算加成后的值
        bonus_value = base_value * (1 + bonus_rate)

        return bonus_value, bonus_rate

    async def get_member_bonuses(self, user_id: str) -> Dict:
        """
        获取成员的宗门加成信息（用于显示）

        Args:
            user_id: 用户ID

        Returns:
            加成信息字典
        """
        # 获取玩家所在宗门
        sect = await self.get_player_sect(user_id)

        if not sect:
            return {
                "has_sect": False,
                "sect_name": None,
                "bonuses": {}
            }

        # 获取宗门加成
        bonuses = await self.get_sect_bonuses(sect.id)

        # 格式化加成信息
        bonus_display = {}
        if bonuses["cultivation_bonus"] > 0:
            bonus_display["修炼效率"] = f"+{bonuses['cultivation_bonus']*100:.0f}%"
        if bonuses["alchemy_bonus"] > 0:
            bonus_display["炼丹成功率"] = f"+{bonuses['alchemy_bonus']*100:.0f}%"
        if bonuses["refining_bonus"] > 0:
            bonus_display["炼器成功率"] = f"+{bonuses['refining_bonus']*100:.0f}%"
        if bonuses["method_quality_bonus"] > 0:
            bonus_display["功法品质"] = f"+{bonuses['method_quality_bonus']*100:.0f}%"

        return {
            "has_sect": True,
            "sect_name": sect.name,
            "sect_level": sect.level,
            "bonuses": bonus_display,
            "raw_bonuses": bonuses
        }

    # ========== 宗门任务系统 ==========

    async def init_base_tasks(self):
        """初始化基础任务"""
        import json

        base_tasks = [
            # 每日任务
            {
                "id": "daily_cultivate",
                "task_type": "daily",
                "task_name": "每日修炼",
                "task_description": "完成3次修炼",
                "requirements": json.dumps({"type": "cultivation", "amount": 3}),
                "contribution_reward": 50,
                "spirit_stone_reward": 100,
                "exp_reward": 50
            },
            {
                "id": "daily_combat",
                "task_type": "daily",
                "task_name": "斩妖除魔",
                "task_description": "挑战5次妖兽",
                "requirements": json.dumps({"type": "combat", "amount": 5}),
                "contribution_reward": 80,
                "spirit_stone_reward": 200,
                "exp_reward": 100
            },
            {
                "id": "daily_donate",
                "task_type": "daily",
                "task_name": "资源捐献",
                "task_description": "向宗门捐献500灵石",
                "requirements": json.dumps({"type": "donate", "amount": 500}),
                "contribution_reward": 100,
                "spirit_stone_reward": 0,
                "exp_reward": 50
            },
            # 每周任务
            {
                "id": "weekly_alchemy",
                "task_type": "weekly",
                "task_name": "炼丹大师",
                "task_description": "成功炼制10颗丹药",
                "requirements": json.dumps({"type": "alchemy", "amount": 10}),
                "contribution_reward": 300,
                "spirit_stone_reward": 1000,
                "exp_reward": 500
            },
            {
                "id": "weekly_refining",
                "task_type": "weekly",
                "task_name": "炼器宗师",
                "task_description": "成功炼制5件装备",
                "requirements": json.dumps({"type": "refining", "amount": 5}),
                "contribution_reward": 300,
                "spirit_stone_reward": 1000,
                "exp_reward": 500
            },
            {
                "id": "weekly_contribution",
                "task_type": "weekly",
                "task_name": "宗门之柱",
                "task_description": "获得500宗门贡献度",
                "requirements": json.dumps({"type": "contribution", "amount": 500}),
                "contribution_reward": 500,
                "spirit_stone_reward": 2000,
                "exp_reward": 1000
            }
        ]

        await self._ensure_sect_tasks_table()

        for task_data in base_tasks:
            # 检查任务是否存在
            existing = await self.db.fetchone(
                "SELECT id FROM sect_tasks WHERE id = ?",
                (task_data['id'],)
            )

            if not existing:
                # 插入任务
                await self.db.execute(
                    """
                    INSERT INTO sect_tasks (
                        id, task_type, task_name, task_description, requirements,
                        contribution_reward, spirit_stone_reward, exp_reward, is_active
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        task_data['id'],
                        task_data['task_type'],
                        task_data['task_name'],
                        task_data['task_description'],
                        task_data['requirements'],
                        task_data['contribution_reward'],
                        task_data['spirit_stone_reward'],
                        task_data['exp_reward'],
                        1
                    )
                )

        logger.info("宗门基础任务初始化完成")

    async def get_available_tasks(self, user_id: str, task_type: Optional[str] = None) -> List[Dict]:
        """
        获取可接取的任务列表

        Args:
            user_id: 用户ID
            task_type: 任务类型（daily/weekly），None表示所有类型

        Returns:
            可接取的任务列表

        Raises:
            NotSectMemberError: 不是宗门成员
        """
        import json
        from datetime import datetime, timedelta

        # 检查是否是宗门成员
        member = await self.get_sect_member(user_id)
        if not member:
            raise NotSectMemberError("道友尚未加入任何宗门")

        await self._ensure_sect_tasks_table()

        # 获取所有活跃任务
        query = "SELECT * FROM sect_tasks WHERE is_active = 1"
        params = []

        if task_type:
            query += " AND task_type = ?"
            params.append(task_type)

        all_tasks = await self.db.fetchall(query, tuple(params))

        # 获取今天的日期（用于每日任务）
        today = datetime.now().date().isoformat()

        # 获取本周开始日期（用于每周任务）
        today_dt = datetime.now()
        week_start = (today_dt - timedelta(days=today_dt.weekday())).date().isoformat()

        available_tasks = []
        for task in all_tasks:
            task_data = dict(task)

            # 检查玩家是否已接取此任务
            if task_data['task_type'] == 'daily':
                # 每日任务：检查今天是否已接取
                existing = await self.db.fetchone(
                    """
                    SELECT id, status, progress, target FROM sect_member_tasks
                    WHERE user_id = ? AND task_id = ? AND date(accepted_at) = ?
                    """,
                    (user_id, task_data['id'], today)
                )
            else:  # weekly
                # 每周任务：检查本周是否已接取
                existing = await self.db.fetchone(
                    """
                    SELECT id, status, progress, target FROM sect_member_tasks
                    WHERE user_id = ? AND task_id = ? AND date(accepted_at) >= ?
                    """,
                    (user_id, task_data['id'], week_start)
                )

            # 解析任务要求
            requirements = json.loads(task_data['requirements'])

            task_info = {
                "task_id": task_data['id'],
                "task_type": task_data['task_type'],
                "task_name": task_data['task_name'],
                "task_description": task_data['task_description'],
                "requirements": requirements,
                "contribution_reward": task_data['contribution_reward'],
                "spirit_stone_reward": task_data['spirit_stone_reward'],
                "exp_reward": task_data['exp_reward'],
                "is_accepted": existing is not None,
                "status": dict(existing)['status'] if existing else None,
                "progress": dict(existing)['progress'] if existing else 0,
                "target": requirements['amount']
            }

            available_tasks.append(task_info)

        return available_tasks

    async def accept_task(self, user_id: str, task_id: str) -> Dict:
        """
        接取宗门任务

        Args:
            user_id: 用户ID
            task_id: 任务ID

        Returns:
            任务信息字典

        Raises:
            NotSectMemberError: 不是宗门成员
            SectError: 任务相关错误
        """
        import json

        # 检查是否是宗门成员
        member = await self.get_sect_member(user_id)
        if not member:
            raise NotSectMemberError("道友尚未加入任何宗门")

        await self._ensure_sect_tasks_table()

        # 获取任务信息
        task = await self.db.fetchone(
            "SELECT * FROM sect_tasks WHERE id = ? AND is_active = 1",
            (task_id,)
        )

        if not task:
            raise SectError(f"任务不存在或已禁用: {task_id}")

        task_data = dict(task)

        # 检查是否已接取
        from datetime import datetime, timedelta
        today = datetime.now().date().isoformat()
        today_dt = datetime.now()
        week_start = (today_dt - timedelta(days=today_dt.weekday())).date().isoformat()

        if task_data['task_type'] == 'daily':
            existing = await self.db.fetchone(
                """
                SELECT id FROM sect_member_tasks
                WHERE user_id = ? AND task_id = ? AND date(accepted_at) = ?
                """,
                (user_id, task_id, today)
            )
        else:  # weekly
            existing = await self.db.fetchone(
                """
                SELECT id FROM sect_member_tasks
                WHERE user_id = ? AND task_id = ? AND date(accepted_at) >= ?
                """,
                (user_id, task_id, week_start)
            )

        if existing:
            raise SectError(f"您已接取过此任务")

        # 解析任务要求
        requirements = json.loads(task_data['requirements'])
        target = requirements['amount']

        # 创建任务记录
        member_task_id = str(uuid.uuid4())
        await self.db.execute(
            """
            INSERT INTO sect_member_tasks (
                id, sect_id, user_id, task_id, progress, target,
                status, accepted_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                member_task_id,
                member.sect_id,
                user_id,
                task_id,
                0,
                target,
                'active',
                datetime.now().isoformat()
            )
        )

        logger.info(f"玩家 {user_id} 接取宗门任务: {task_data['task_name']}")

        return {
            "success": True,
            "task_id": task_id,
            "task_name": task_data['task_name'],
            "task_description": task_data['task_description'],
            "target": target,
            "progress": 0
        }

    async def update_task_progress(self, user_id: str, task_type_filter: str, amount: int = 1) -> List[Dict]:
        """
        更新任务进度（由其他系统调用）

        Args:
            user_id: 用户ID
            task_type_filter: 任务类型过滤（cultivation/combat/donate/alchemy/refining/contribution）
            amount: 进度增加量

        Returns:
            更新后的任务列表
        """
        import json

        # 检查是否是宗门成员
        member = await self.get_sect_member(user_id)
        if not member:
            return []  # 不是宗门成员，静默返回

        await self._ensure_sect_tasks_table()

        # 查询所有进行中的任务
        active_tasks = await self.db.fetchall(
            """
            SELECT mt.*, t.requirements, t.task_name
            FROM sect_member_tasks mt
            JOIN sect_tasks t ON mt.task_id = t.id
            WHERE mt.user_id = ? AND mt.status = 'active'
            """,
            (user_id,)
        )

        updated_tasks = []
        for task in active_tasks:
            task_data = dict(task)
            requirements = json.loads(task_data['requirements'])

            # 检查任务类型是否匹配
            if requirements['type'] != task_type_filter:
                continue

            # 更新进度
            new_progress = task_data['progress'] + amount
            target = task_data['target']

            # 检查是否完成
            if new_progress >= target:
                new_progress = target
                new_status = 'completed'
                completed_at = datetime.now().isoformat()

                await self.db.execute(
                    """
                    UPDATE sect_member_tasks
                    SET progress = ?, status = ?, completed_at = ?
                    WHERE id = ?
                    """,
                    (new_progress, new_status, completed_at, task_data['id'])
                )

                logger.info(f"玩家 {user_id} 完成宗门任务: {task_data['task_name']}")
            else:
                await self.db.execute(
                    """
                    UPDATE sect_member_tasks
                    SET progress = ?
                    WHERE id = ?
                    """,
                    (new_progress, task_data['id'])
                )

            updated_tasks.append({
                "task_id": task_data['task_id'],
                "task_name": task_data['task_name'],
                "progress": new_progress,
                "target": target,
                "completed": new_progress >= target
            })

        return updated_tasks

    async def complete_task(self, user_id: str, member_task_id: str) -> Dict:
        """
        完成并领取任务奖励

        Args:
            user_id: 用户ID
            member_task_id: 成员任务ID

        Returns:
            奖励信息字典

        Raises:
            NotSectMemberError: 不是宗门成员
            SectError: 任务相关错误
        """
        # 检查是否是宗门成员
        member = await self.get_sect_member(user_id)
        if not member:
            raise NotSectMemberError("道友尚未加入任何宗门")

        await self._ensure_sect_tasks_table()

        # 获取任务信息
        task_result = await self.db.fetchone(
            """
            SELECT mt.*, t.task_name, t.contribution_reward,
                   t.spirit_stone_reward, t.exp_reward
            FROM sect_member_tasks mt
            JOIN sect_tasks t ON mt.task_id = t.id
            WHERE mt.id = ? AND mt.user_id = ?
            """,
            (member_task_id, user_id)
        )

        if not task_result:
            raise SectError("任务不存在或不属于您")

        task_data = dict(task_result)

        # 检查任务状态
        if task_data['status'] != 'completed':
            raise SectError(f"任务尚未完成（进度：{task_data['progress']}/{task_data['target']}）")

        if task_data.get('claimed_at'):
            raise SectError("任务奖励已领取")

        # 发放奖励
        rewards = {
            "contribution": task_data['contribution_reward'],
            "spirit_stone": task_data['spirit_stone_reward'],
            "exp": task_data['exp_reward']
        }

        # 增加贡献度
        if rewards['contribution'] > 0:
            member.contribution += rewards['contribution']
            member.total_contribution += rewards['contribution']
            await self._update_member(member)

        # 增加灵石（需要通过player_mgr）
        if rewards['spirit_stone'] > 0:
            await self.player_mgr.add_spirit_stone(user_id, rewards['spirit_stone'])

        # 增加经验（需要通过player_mgr）
        if rewards['exp'] > 0:
            player = await self.player_mgr.get_player_or_error(user_id)
            player.experience += rewards['exp']
            await self.player_mgr.update_player(player)

        # 标记为已领取
        await self.db.execute(
            """
            UPDATE sect_member_tasks
            SET claimed_at = ?
            WHERE id = ?
            """,
            (datetime.now().isoformat(), member_task_id)
        )

        logger.info(f"玩家 {user_id} 领取宗门任务奖励: {task_data['task_name']}")

        return {
            "success": True,
            "task_name": task_data['task_name'],
            "rewards": rewards
        }

    async def get_member_tasks(self, user_id: str, status_filter: Optional[str] = None) -> List[Dict]:
        """
        获取成员的任务列表

        Args:
            user_id: 用户ID
            status_filter: 状态过滤（active/completed/claimed）

        Returns:
            任务列表

        Raises:
            NotSectMemberError: 不是宗门成员
        """
        import json

        # 检查是否是宗门成员
        member = await self.get_sect_member(user_id)
        if not member:
            raise NotSectMemberError("道友尚未加入任何宗门")

        await self._ensure_sect_tasks_table()

        # 构建查询
        query = """
            SELECT mt.*, t.task_name, t.task_description, t.task_type,
                   t.requirements, t.contribution_reward, t.spirit_stone_reward,
                   t.exp_reward
            FROM sect_member_tasks mt
            JOIN sect_tasks t ON mt.task_id = t.id
            WHERE mt.user_id = ?
        """
        params = [user_id]

        if status_filter:
            query += " AND mt.status = ?"
            params.append(status_filter)

        query += " ORDER BY mt.accepted_at DESC"

        results = await self.db.fetchall(query, tuple(params))

        tasks = []
        for result in results:
            task_data = dict(result)
            requirements = json.loads(task_data['requirements'])

            task_info = {
                "id": task_data['id'],
                "task_id": task_data['task_id'],
                "task_name": task_data['task_name'],
                "task_description": task_data['task_description'],
                "task_type": task_data['task_type'],
                "requirements_type": requirements['type'],
                "progress": task_data['progress'],
                "target": task_data['target'],
                "status": task_data['status'],
                "contribution_reward": task_data['contribution_reward'],
                "spirit_stone_reward": task_data['spirit_stone_reward'],
                "exp_reward": task_data['exp_reward'],
                "accepted_at": task_data['accepted_at'],
                "completed_at": task_data.get('completed_at'),
                "claimed_at": task_data.get('claimed_at'),
                "can_claim": task_data['status'] == 'completed' and not task_data.get('claimed_at')
            }

            tasks.append(task_info)

        return tasks

    # ========== 宗门功法库系统 ==========

    async def add_sect_method(self, sect_id: str, method_id: str, method_name: str,
                             method_type: str, method_quality: str,
                             required_contribution: int = 0,
                             required_position: str = "弟子",
                             donated_by: Optional[str] = None) -> Dict:
        """
        添加功法到宗门库

        Args:
            sect_id: 宗门ID
            method_id: 功法ID
            method_name: 功法名称
            method_type: 功法类型
            method_quality: 功法品质
            required_contribution: 需要的贡献度
            required_position: 需要的职位
            donated_by: 捐献者ID(可选)

        Returns:
            添加结果字典

        Raises:
            SectNotFoundError: 宗门不存在
        """
        # 验证宗门存在
        sect = await self.get_sect_by_id(sect_id)

        # 确保表存在
        await self._ensure_sect_methods_table()

        # 检查功法是否已存在
        existing = await self.db.fetchone(
            "SELECT id FROM sect_methods WHERE sect_id = ? AND method_id = ?",
            (sect_id, method_id)
        )

        if existing:
            raise SectError(f"功法 {method_name} 已在宗门库中")

        # 获取职位等级
        required_position_level = self.POSITIONS.get(required_position, {}).get("level", 1)

        # 插入功法记录
        await self.db.execute(
            """
            INSERT INTO sect_methods (
                sect_id, method_id, method_name, method_type, method_quality,
                required_contribution, required_position, required_position_level,
                donated_by, added_at, learn_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (sect_id, method_id, method_name, method_type, method_quality,
             required_contribution, required_position, required_position_level,
             donated_by, datetime.now().isoformat(), 0)
        )

        logger.info(f"宗门 {sect.name} 添加功法: {method_name}")

        return {
            "method_id": method_id,
            "method_name": method_name,
            "required_contribution": required_contribution,
            "required_position": required_position
        }

    async def get_sect_methods(self, sect_id: str, user_id: Optional[str] = None) -> List[Dict]:
        """
        查询宗门功法库

        Args:
            sect_id: 宗门ID
            user_id: 用户ID(可选，用于标记已学习状态)

        Returns:
            功法列表

        Raises:
            SectNotFoundError: 宗门不存在
        """
        # 验证宗门存在
        sect = await self.get_sect_by_id(sect_id)

        # 确保表存在
        await self._ensure_sect_methods_table()

        # 查询宗门所有功法
        results = await self.db.fetchall(
            """
            SELECT * FROM sect_methods
            WHERE sect_id = ?
            ORDER BY required_position_level DESC, required_contribution DESC
            """,
            (sect_id,)
        )

        methods = []
        for result in results:
            method_data = dict(result)

            # 如果提供了user_id，检查玩家是否已学习此功法
            learned = False
            if user_id:
                # 检查玩家是否拥有此功法
                learned_result = await self.db.fetchone(
                    "SELECT id FROM cultivation_methods WHERE user_id = ? AND id = ?",
                    (user_id, method_data['method_id'])
                )
                learned = learned_result is not None

            method_info = {
                "id": method_data['id'],
                "method_id": method_data['method_id'],
                "method_name": method_data['method_name'],
                "method_type": method_data['method_type'],
                "method_quality": method_data['method_quality'],
                "required_contribution": method_data['required_contribution'],
                "required_position": method_data['required_position'],
                "required_position_level": method_data['required_position_level'],
                "donated_by": method_data.get('donated_by'),
                "added_at": method_data['added_at'],
                "learn_count": method_data['learn_count'],
                "learned": learned
            }
            methods.append(method_info)

        return methods

    async def learn_sect_method(self, user_id: str, sect_method_id: int, method_sys) -> Dict:
        """
        学习宗门功法

        Args:
            user_id: 用户ID
            sect_method_id: 宗门功法记录ID
            method_sys: 功法系统实例

        Returns:
            学习结果字典

        Raises:
            NotSectMemberError: 不是宗门成员
            SectError: 各种宗门相关错误
        """
        # 获取成员信息
        member = await self.get_sect_member(user_id)
        if not member:
            raise NotSectMemberError("道友尚未加入任何宗门")

        # 确保表存在
        await self._ensure_sect_methods_table()

        # 获取宗门功法信息
        method_data = await self.db.fetchone(
            "SELECT * FROM sect_methods WHERE id = ? AND sect_id = ?",
            (sect_method_id, member.sect_id)
        )

        if not method_data:
            raise SectError("功法不存在或不属于您的宗门")

        method_data = dict(method_data)

        # 检查是否已学习
        learned = await self.db.fetchone(
            "SELECT id FROM cultivation_methods WHERE user_id = ? AND source_id = ?",
            (user_id, method_data['method_id'])
        )

        if learned:
            raise SectError(f"您已经学习过 {method_data['method_name']}")

        # 检查贡献度要求
        if member.contribution < method_data['required_contribution']:
            raise InsufficientResourceError(
                f"贡献度不足，需要 {method_data['required_contribution']}，"
                f"当前 {member.contribution}"
            )

        # 检查职位要求
        if member.position_level < method_data['required_position_level']:
            raise InsufficientPermissionError(
                f"职位不足，需要 {method_data['required_position']} 及以上职位"
            )

        # 生成功法副本到玩家背包
        # 注意：这里使用method_sys来生成功法
        new_method = await method_sys.generate_method(
            user_id,
            method_type=method_data['method_type'],
            quality=method_data['method_quality']
        )

        # 设置功法来源
        new_method.source = "宗门"
        new_method.source_id = method_data['method_id']

        # 保存功法（需要调用method_sys的保存方法）
        # 由于我们已经在generate_method中生成了功法，它应该已经保存了

        # 扣除贡献度（可选，根据宗门设置）
        contribution_cost = method_data['required_contribution'] // 2  # 消耗一半贡献度
        member.contribution -= contribution_cost
        await self._update_member(member)

        # 更新功法学习次数
        await self.db.execute(
            "UPDATE sect_methods SET learn_count = learn_count + 1 WHERE id = ?",
            (sect_method_id,)
        )

        logger.info(f"玩家 {user_id} 学习宗门功法: {method_data['method_name']}")

        return {
            "success": True,
            "method_id": new_method.id,
            "method_name": method_data['method_name'],
            "method_type": method_data['method_type'],
            "method_quality": method_data['method_quality'],
            "contribution_cost": contribution_cost,
            "remaining_contribution": member.contribution
        }

    async def donate_method_to_sect(self, user_id: str, method_id: str, method_sys,
                                   contribution_reward: Optional[int] = None) -> Dict:
        """
        捐献功法到宗门

        Args:
            user_id: 用户ID
            method_id: 功法ID
            method_sys: 功法系统实例
            contribution_reward: 贡献度奖励(可选，默认根据功法品质计算)

        Returns:
            捐献结果字典

        Raises:
            NotSectMemberError: 不是宗门成员
            SectError: 各种宗门相关错误
        """
        # 获取成员信息
        member = await self.get_sect_member(user_id)
        if not member:
            raise NotSectMemberError("道友尚未加入任何宗门")

        # 获取宗门信息
        sect = await self.get_sect_by_id(member.sect_id)

        # 获取功法信息
        methods = await method_sys.get_player_methods(user_id)
        method = None
        for m in methods:
            if m.id == method_id:
                method = m
                break

        if not method:
            raise SectError("功法不存在或不属于您")

        # 检查功法是否已装备
        if method.is_equipped:
            raise SectError("已装备的功法无法捐献，请先卸下")

        # 检查功法是否绑定
        if method.is_bound:
            raise SectError("绑定的功法无法捐献")

        # 计算贡献度奖励
        if contribution_reward is None:
            # 根据品质计算奖励
            quality_rewards = {
                "凡品": 50,
                "灵品": 100,
                "宝品": 200,
                "仙品": 500,
                "神品": 1000,
                "道品": 2000
            }
            contribution_reward = quality_rewards.get(method.quality, 50)

        # 计算学习要求
        quality_contributions = {
            "凡品": 0,
            "灵品": 50,
            "宝品": 100,
            "仙品": 200,
            "神品": 500,
            "道品": 1000
        }
        required_contribution = quality_contributions.get(method.quality, 0)

        quality_positions = {
            "凡品": "弟子",
            "灵品": "弟子",
            "宝品": "精英弟子",
            "仙品": "执事",
            "神品": "长老",
            "道品": "宗主"
        }
        required_position = quality_positions.get(method.quality, "弟子")

        # 添加功法到宗门库
        await self.add_sect_method(
            sect_id=sect.id,
            method_id=method.id,
            method_name=method.name,
            method_type=method.method_type,
            method_quality=method.quality,
            required_contribution=required_contribution,
            required_position=required_position,
            donated_by=user_id
        )

        # 删除玩家的功法（转移到宗门）
        await self.db.execute(
            "DELETE FROM cultivation_methods WHERE id = ? AND user_id = ?",
            (method_id, user_id)
        )

        # 增加玩家贡献度
        member.contribution += contribution_reward
        member.total_contribution += contribution_reward
        await self._update_member(member)

        logger.info(f"玩家 {user_id} 向宗门 {sect.name} 捐献功法: {method.name}")

        return {
            "success": True,
            "method_name": method.name,
            "method_quality": method.quality,
            "contribution_reward": contribution_reward,
            "total_contribution": member.total_contribution
        }

    async def _sect_name_exists(self, name: str) -> bool:
        """检查宗门名称是否存在"""
        sect = await self.get_sect_by_name(name)
        return sect is not None

    async def _save_sect(self, sect: Sect):
        """保存宗门到数据库"""
        await self._ensure_sects_table()

        sect_data = sect.to_dict()
        columns = list(sect_data.keys())
        placeholders = ', '.join(['?' for _ in columns])
        values = list(sect_data.values())

        sql = f"INSERT INTO sects ({', '.join(columns)}) VALUES ({placeholders})"
        await self.db.execute(sql, values)

    async def _update_sect(self, sect: Sect):
        """更新宗门信息"""
        sect.last_active_at = datetime.now()
        sect_data = sect.to_dict()

        set_clause = ', '.join([f"{key} = ?" for key in sect_data.keys() if key != 'id'])
        values = [value for key, value in sect_data.items() if key != 'id']
        values.append(sect.id)

        sql = f"UPDATE sects SET {set_clause} WHERE id = ?"
        await self.db.execute(sql, tuple(values))

    async def _save_member(self, member: SectMember):
        """保存成员到数据库"""
        await self._ensure_members_table()

        member_data = member.to_dict()
        columns = list(member_data.keys())
        placeholders = ', '.join(['?' for _ in columns])
        values = list(member_data.values())

        sql = f"INSERT INTO sect_members ({', '.join(columns)}) VALUES ({placeholders})"
        await self.db.execute(sql, values)

    async def _update_member(self, member: SectMember):
        """更新成员信息"""
        member.last_active_at = datetime.now()
        member_data = member.to_dict()

        set_clause = ', '.join([f"{key} = ?" for key in member_data.keys() if key != 'id'])
        values = [value for key, value in member_data.items() if key != 'id']
        values.append(member.id)

        sql = f"UPDATE sect_members SET {set_clause} WHERE id = ?"
        await self.db.execute(sql, tuple(values))

    async def _delete_member(self, user_id: str):
        """删除成员"""
        await self.db.execute(
            "DELETE FROM sect_members WHERE user_id = ?",
            (user_id,)
        )

    async def _ensure_sects_table(self):
        """确保宗门表存在"""
        sql = """
        CREATE TABLE IF NOT EXISTS sects (
            id TEXT PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            description TEXT,
            announcement TEXT,
            sect_type TEXT NOT NULL,
            sect_style TEXT NOT NULL,
            level INTEGER DEFAULT 1,
            experience INTEGER DEFAULT 0,
            max_experience INTEGER DEFAULT 1000,
            spirit_stone INTEGER DEFAULT 0,
            contribution INTEGER DEFAULT 0,
            reputation INTEGER DEFAULT 0,
            power INTEGER DEFAULT 0,
            leader_id TEXT NOT NULL,
            member_count INTEGER DEFAULT 0,
            max_members INTEGER DEFAULT 20,
            buildings TEXT,
            sect_skills TEXT,
            is_recruiting INTEGER DEFAULT 1,
            join_requirement TEXT,
            in_war INTEGER DEFAULT 0,
            war_target_id TEXT,
            war_score INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            last_active_at TEXT NOT NULL
        )
        """
        await self.db.execute(sql)

    async def _ensure_members_table(self):
        """确保成员表存在"""
        sql = """
        CREATE TABLE IF NOT EXISTS sect_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT UNIQUE NOT NULL,
            sect_id TEXT NOT NULL,
            position TEXT NOT NULL,
            position_level INTEGER NOT NULL,
            contribution INTEGER DEFAULT 0,
            total_contribution INTEGER DEFAULT 0,
            activity INTEGER DEFAULT 0,
            last_active_at TEXT NOT NULL,
            joined_at TEXT NOT NULL
        )
        """
        await self.db.execute(sql)

    async def _ensure_sect_methods_table(self):
        """确保宗门功法表存在"""
        sql = """
        CREATE TABLE IF NOT EXISTS sect_methods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sect_id TEXT NOT NULL,
            method_id TEXT NOT NULL,
            method_name TEXT NOT NULL,
            method_type TEXT NOT NULL,
            method_quality TEXT NOT NULL,
            required_contribution INTEGER DEFAULT 0,
            required_position TEXT DEFAULT '弟子',
            required_position_level INTEGER DEFAULT 1,
            donated_by TEXT,
            added_at TEXT NOT NULL,
            learn_count INTEGER DEFAULT 0,
            UNIQUE(sect_id, method_id)
        )
        """
        await self.db.execute(sql)

        # 创建索引
        await self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_sect_methods_sect
            ON sect_methods(sect_id)
        """)

    async def _ensure_sect_tasks_table(self):
        """确保宗门任务表存在"""
        # 任务模板表
        sql = """
        CREATE TABLE IF NOT EXISTS sect_tasks (
            id TEXT PRIMARY KEY,
            task_type TEXT NOT NULL,
            task_name TEXT NOT NULL,
            task_description TEXT,
            requirements TEXT NOT NULL,
            contribution_reward INTEGER DEFAULT 0,
            spirit_stone_reward INTEGER DEFAULT 0,
            exp_reward INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1
        )
        """
        await self.db.execute(sql)

        # 成员任务进度表
        sql = """
        CREATE TABLE IF NOT EXISTS sect_member_tasks (
            id TEXT PRIMARY KEY,
            sect_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            task_id TEXT NOT NULL,
            progress INTEGER DEFAULT 0,
            target INTEGER NOT NULL,
            status TEXT DEFAULT 'active',
            accepted_at TEXT NOT NULL,
            completed_at TEXT,
            claimed_at TEXT,
            UNIQUE(user_id, task_id, accepted_at)
        )
        """
        await self.db.execute(sql)

        # 创建索引
        await self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_sect_member_tasks_user
            ON sect_member_tasks(user_id, status)
        """)

        await self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_sect_member_tasks_sect
            ON sect_member_tasks(sect_id, status)
        """)