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

        logger.info(f"玩家 {player.name} 创建宗门: {name}")

        return sect

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