"""
探索队伍管理系统
支持多人组队探索
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from astrbot.api import logger

from .database import DatabaseManager
from ..utils import XiuxianException


class ExplorationTeamError(XiuxianException):
    """探索队伍相关异常"""
    pass


class ExplorationTeamManager:
    """探索队伍管理器"""

    def __init__(self, db: DatabaseManager):
        self.db = db
        # 内存中的邀请数据 {team_id: {user_id: expire_time}}
        self._pending_invites = {}

    async def create_team(self, leader_id: str, location_id: int) -> str:
        """
        创建探索队伍

        Args:
            leader_id: 队长ID
            location_id: 探索地点ID

        Returns:
            队伍ID
        """
        team_id = str(uuid.uuid4())

        await self.db.execute("""
            INSERT INTO exploration_teams (
                id, leader_id, location_id, status
            ) VALUES (?, ?, ?, 'waiting')
        """, (team_id, leader_id, location_id))

        # 添加队长作为成员
        await self.db.execute("""
            INSERT INTO team_members (
                team_id, user_id, status, joined_at
            ) VALUES (?, ?, 'joined', ?)
        """, (team_id, leader_id, datetime.now().isoformat()))

        logger.info(f"创建探索队伍: {team_id}, 队长: {leader_id}")
        return team_id

    async def invite_member(self, team_id: str, user_id: str, inviter_id: str) -> bool:
        """
        邀请成员加入队伍

        Args:
            team_id: 队伍ID
            user_id: 被邀请玩家ID
            inviter_id: 邀请者ID

        Returns:
            是否成功邀请
        """
        # 检查队伍是否存在
        team = await self.get_team(team_id)
        if not team:
            raise ExplorationTeamError("队伍不存在")

        # 检查队伍状态
        if team['status'] != 'waiting':
            raise ExplorationTeamError("队伍已经开始探索或已结束")

        # 检查邀请者是否是队长
        if team['leader_id'] != inviter_id:
            raise ExplorationTeamError("只有队长可以邀请成员")

        # 检查成员是否已在队伍中
        members = await self.get_team_members(team_id)
        if user_id in [m['user_id'] for m in members]:
            raise ExplorationTeamError("该玩家已在队伍中")

        # 检查队伍人数限制（最多5人）
        if len(members) >= 5:
            raise ExplorationTeamError("队伍已满（最多5人）")

        # 添加邀请记录
        try:
            await self.db.execute("""
                INSERT INTO team_members (
                    team_id, user_id, status
                ) VALUES (?, ?, 'invited')
            """, (team_id, user_id))

            # 设置邀请过期时间（30秒）
            if team_id not in self._pending_invites:
                self._pending_invites[team_id] = {}
            self._pending_invites[team_id][user_id] = datetime.now() + timedelta(seconds=30)

            logger.info(f"邀请玩家 {user_id} 加入队伍 {team_id}")
            return True

        except Exception as e:
            logger.error(f"邀请成员失败: {e}")
            return False

    async def accept_invite(self, team_id: str, user_id: str) -> bool:
        """
        接受队伍邀请

        Args:
            team_id: 队伍ID
            user_id: 玩家ID

        Returns:
            是否成功接受
        """
        # 检查邀请是否过期
        if team_id in self._pending_invites and user_id in self._pending_invites[team_id]:
            if datetime.now() > self._pending_invites[team_id][user_id]:
                # 邀请已过期
                await self.db.execute("""
                    DELETE FROM team_members
                    WHERE team_id = ? AND user_id = ? AND status = 'invited'
                """, (team_id, user_id))
                del self._pending_invites[team_id][user_id]
                raise ExplorationTeamError("邀请已过期")

        # 更新成员状态
        await self.db.execute("""
            UPDATE team_members
            SET status = 'joined', joined_at = ?
            WHERE team_id = ? AND user_id = ? AND status = 'invited'
        """, (datetime.now().isoformat(), team_id, user_id))

        # 清除邀请记录
        if team_id in self._pending_invites and user_id in self._pending_invites[team_id]:
            del self._pending_invites[team_id][user_id]

        logger.info(f"玩家 {user_id} 加入队伍 {team_id}")
        return True

    async def reject_invite(self, team_id: str, user_id: str):
        """
        拒绝队伍邀请

        Args:
            team_id: 队伍ID
            user_id: 玩家ID
        """
        await self.db.execute("""
            DELETE FROM team_members
            WHERE team_id = ? AND user_id = ? AND status = 'invited'
        """, (team_id, user_id))

        # 清除邀请记录
        if team_id in self._pending_invites and user_id in self._pending_invites[team_id]:
            del self._pending_invites[team_id][user_id]

        logger.info(f"玩家 {user_id} 拒绝加入队伍 {team_id}")

    async def get_team(self, team_id: str) -> Optional[Dict]:
        """
        获取队伍信息

        Args:
            team_id: 队伍ID

        Returns:
            队伍信息
        """
        cursor = await self.db.execute("""
            SELECT * FROM exploration_teams
            WHERE id = ?
        """, (team_id,))

        row = await cursor.fetchone()
        if row:
            team = dict(row)
            if team.get('session_data'):
                team['session_data'] = json.loads(team['session_data'])
            return team
        return None

    async def get_team_members(self, team_id: str, status: Optional[str] = None) -> List[Dict]:
        """
        获取队伍成员

        Args:
            team_id: 队伍ID
            status: 成员状态过滤（可选）

        Returns:
            成员列表
        """
        if status:
            cursor = await self.db.execute("""
                SELECT * FROM team_members
                WHERE team_id = ? AND status = ?
                ORDER BY joined_at
            """, (team_id, status))
        else:
            cursor = await self.db.execute("""
                SELECT * FROM team_members
                WHERE team_id = ?
                ORDER BY joined_at
            """, (team_id,))

        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def get_player_invites(self, user_id: str) -> List[Dict]:
        """
        获取玩家收到的邀请

        Args:
            user_id: 玩家ID

        Returns:
            邀请列表
        """
        # 清理过期邀请
        await self._clean_expired_invites()

        cursor = await self.db.execute("""
            SELECT t.*, tm.id as member_id
            FROM exploration_teams t
            JOIN team_members tm ON t.id = tm.team_id
            WHERE tm.user_id = ? AND tm.status = 'invited' AND t.status = 'waiting'
            ORDER BY t.created_at DESC
        """, (user_id,))

        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def start_team_exploration(self, team_id: str) -> bool:
        """
        开始队伍探索

        Args:
            team_id: 队伍ID

        Returns:
            是否成功开始
        """
        # 更新队伍状态
        await self.db.execute("""
            UPDATE exploration_teams
            SET status = 'active', started_at = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), team_id))

        logger.info(f"队伍 {team_id} 开始探索")
        return True

    async def finish_team_exploration(self, team_id: str):
        """
        结束队伍探索

        Args:
            team_id: 队伍ID
        """
        await self.db.execute("""
            UPDATE exploration_teams
            SET status = 'finished', finished_at = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), team_id))

        logger.info(f"队伍 {team_id} 探索结束")

    async def disband_team(self, team_id: str, disbander_id: str):
        """
        解散队伍

        Args:
            team_id: 队伍ID
            disbander_id: 解散者ID
        """
        team = await self.get_team(team_id)
        if not team:
            raise ExplorationTeamError("队伍不存在")

        # 只有队长可以解散队伍（或者所有成员都离开）
        if team['leader_id'] != disbander_id:
            raise ExplorationTeamError("只有队长可以解散队伍")

        # 删除队伍成员
        await self.db.execute("DELETE FROM team_members WHERE team_id = ?", (team_id,))

        # 删除队伍
        await self.db.execute("DELETE FROM exploration_teams WHERE id = ?", (team_id,))

        # 清除邀请记录
        if team_id in self._pending_invites:
            del self._pending_invites[team_id]

        logger.info(f"队伍 {team_id} 已解散")

    async def leave_team(self, team_id: str, user_id: str):
        """
        离开队伍

        Args:
            team_id: 队伍ID
            user_id: 玩家ID
        """
        team = await self.get_team(team_id)
        if not team:
            raise ExplorationTeamError("队伍不存在")

        # 如果是队长离开，自动解散队伍
        if team['leader_id'] == user_id:
            await self.disband_team(team_id, user_id)
            return

        # 删除成员记录
        await self.db.execute("""
            DELETE FROM team_members
            WHERE team_id = ? AND user_id = ?
        """, (team_id, user_id))

        logger.info(f"玩家 {user_id} 离开队伍 {team_id}")

    async def _clean_expired_invites(self):
        """清理过期邀请"""
        now = datetime.now()
        expired_teams = []

        for team_id, invites in self._pending_invites.items():
            expired_users = []
            for user_id, expire_time in invites.items():
                if now > expire_time:
                    expired_users.append(user_id)
                    # 删除过期邀请
                    await self.db.execute("""
                        DELETE FROM team_members
                        WHERE team_id = ? AND user_id = ? AND status = 'invited'
                    """, (team_id, user_id))

            for user_id in expired_users:
                del invites[user_id]

            if not invites:
                expired_teams.append(team_id)

        for team_id in expired_teams:
            del self._pending_invites[team_id]

    async def get_player_active_team(self, user_id: str) -> Optional[Dict]:
        """
        获取玩家当前活跃的队伍

        Args:
            user_id: 玩家ID

        Returns:
            队伍信息（如果有）
        """
        cursor = await self.db.execute("""
            SELECT t.* FROM exploration_teams t
            JOIN team_members tm ON t.id = tm.team_id
            WHERE tm.user_id = ? AND tm.status = 'joined'
              AND t.status IN ('waiting', 'active')
            ORDER BY t.created_at DESC
            LIMIT 1
        """, (user_id,))

        row = await cursor.fetchone()
        if row:
            team = dict(row)
            if team.get('session_data'):
                team['session_data'] = json.loads(team['session_data'])
            return team
        return None
