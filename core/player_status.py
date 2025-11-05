"""
玩家状态管理系统
处理各种临时状态（重伤、中毒、增益等）
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from astrbot.api import logger

from .database import DatabaseManager
from ..utils import XiuxianException


class PlayerStatusError(XiuxianException):
    """玩家状态相关异常"""
    pass


class PlayerStatusManager:
    """玩家状态管理器"""

    # 状态类型常量
    STATUS_INJURED = 'injured'  # 重伤
    STATUS_POISONED = 'poisoned'  # 中毒
    STATUS_BUFF = 'buff'  # 增益
    STATUS_DEBUFF = 'debuff'  # 减益

    def __init__(self, db: DatabaseManager):
        self.db = db

    async def add_status(
        self,
        user_id: str,
        status_type: str,
        duration_seconds: int,
        status_data: Optional[Dict] = None,
        severity: int = 1
    ) -> int:
        """
        添加玩家状态

        Args:
            user_id: 玩家ID
            status_type: 状态类型
            duration_seconds: 持续时间（秒）
            status_data: 状态额外数据
            severity: 严重程度 (1-5)

        Returns:
            状态ID
        """
        expires_at = datetime.now() + timedelta(seconds=duration_seconds)

        # 先清理过期状态
        await self._clean_expired_status(user_id)

        # 插入新状态
        cursor = await self.db.execute("""
            INSERT INTO player_status (
                user_id, status_type, status_data, severity, expires_at
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            user_id,
            status_type,
            json.dumps(status_data or {}, ensure_ascii=False),
            severity,
            expires_at.isoformat()
        ))

        status_id = cursor.lastrowid
        logger.info(f"为玩家 {user_id} 添加状态: {status_type}, 持续 {duration_seconds}秒")
        return status_id

    async def get_active_status(self, user_id: str, status_type: Optional[str] = None) -> List[Dict]:
        """
        获取玩家的活跃状态

        Args:
            user_id: 玩家ID
            status_type: 状态类型过滤（可选）

        Returns:
            状态列表
        """
        # 先清理过期状态
        await self._clean_expired_status(user_id)

        if status_type:
            cursor = await self.db.execute("""
                SELECT * FROM player_status
                WHERE user_id = ? AND status_type = ? AND expires_at > datetime('now')
                ORDER BY created_at DESC
            """, (user_id, status_type))
        else:
            cursor = await self.db.execute("""
                SELECT * FROM player_status
                WHERE user_id = ? AND expires_at > datetime('now')
                ORDER BY created_at DESC
            """, (user_id,))

        rows = await cursor.fetchall()
        statuses = []
        for row in rows:
            status = dict(row)
            if status['status_data']:
                status['status_data'] = json.loads(status['status_data'])
            statuses.append(status)

        return statuses

    async def has_status(self, user_id: str, status_type: str) -> bool:
        """
        检查玩家是否有指定状态

        Args:
            user_id: 玩家ID
            status_type: 状态类型

        Returns:
            是否有该状态
        """
        statuses = await self.get_active_status(user_id, status_type)
        return len(statuses) > 0

    async def remove_status(self, status_id: int):
        """
        移除指定状态

        Args:
            status_id: 状态ID
        """
        await self.db.execute("DELETE FROM player_status WHERE id = ?", (status_id,))
        logger.info(f"移除状态: {status_id}")

    async def clear_status_by_type(self, user_id: str, status_type: str):
        """
        清除玩家指定类型的所有状态

        Args:
            user_id: 玩家ID
            status_type: 状态类型
        """
        await self.db.execute("""
            DELETE FROM player_status
            WHERE user_id = ? AND status_type = ?
        """, (user_id, status_type))
        logger.info(f"清除玩家 {user_id} 的所有 {status_type} 状态")

    async def _clean_expired_status(self, user_id: Optional[str] = None):
        """
        清理过期状态

        Args:
            user_id: 玩家ID（可选，如果不提供则清理所有过期状态）
        """
        if user_id:
            await self.db.execute("""
                DELETE FROM player_status
                WHERE user_id = ? AND expires_at <= datetime('now')
            """, (user_id,))
        else:
            await self.db.execute("""
                DELETE FROM player_status
                WHERE expires_at <= datetime('now')
            """)

    async def apply_injured_status(self, user_id: str, severity: int = 1) -> Dict:
        """
        应用重伤状态

        Args:
            user_id: 玩家ID
            severity: 严重程度 1-5

        Returns:
            状态信息
        """
        # 持续时间：1小时 = 3600秒
        duration = 3600

        # 修炼速度惩罚
        cultivation_penalty = 0.2 * severity  # 每级严重度增加20%惩罚

        status_data = {
            'cultivation_speed_penalty': cultivation_penalty,
            'description': f'重伤状态，修炼速度降低 {int(cultivation_penalty * 100)}%'
        }

        status_id = await self.add_status(
            user_id,
            self.STATUS_INJURED,
            duration,
            status_data,
            severity
        )

        return {
            'status_id': status_id,
            'status_type': self.STATUS_INJURED,
            'duration': duration,
            'data': status_data
        }

    async def get_cultivation_speed_modifier(self, user_id: str) -> float:
        """
        获取玩家当前的修炼速度修正

        Args:
            user_id: 玩家ID

        Returns:
            修炼速度倍率 (1.0 = 正常, 0.8 = 降低20%, 1.2 = 提升20%)
        """
        statuses = await self.get_active_status(user_id)

        modifier = 1.0
        for status in statuses:
            status_data = status.get('status_data', {})

            # 重伤状态降低修炼速度
            if status['status_type'] == self.STATUS_INJURED:
                penalty = status_data.get('cultivation_speed_penalty', 0.2)
                modifier -= penalty

            # 中毒状态也会影响
            elif status['status_type'] == self.STATUS_POISONED:
                penalty = status_data.get('cultivation_speed_penalty', 0.1)
                modifier -= penalty

            # 增益状态提升修炼速度
            elif status['status_type'] == self.STATUS_BUFF:
                bonus = status_data.get('cultivation_speed_bonus', 0)
                modifier += bonus

        # 确保最小为0.1（不会完全无法修炼）
        return max(0.1, modifier)

    async def get_status_description(self, user_id: str) -> str:
        """
        获取玩家所有状态的描述文本

        Args:
            user_id: 玩家ID

        Returns:
            状态描述
        """
        statuses = await self.get_active_status(user_id)

        if not statuses:
            return "状态正常"

        lines = []
        for status in statuses:
            status_data = status.get('status_data', {})
            expires_at = datetime.fromisoformat(status['expires_at'])
            remaining = expires_at - datetime.now()
            remaining_minutes = int(remaining.total_seconds() / 60)

            # 状态图标
            icons = {
                self.STATUS_INJURED: '💔',
                self.STATUS_POISONED: '☠️',
                self.STATUS_BUFF: '✨',
                self.STATUS_DEBUFF: '⚠️'
            }
            icon = icons.get(status['status_type'], '📍')

            # 状态名称
            names = {
                self.STATUS_INJURED: '重伤',
                self.STATUS_POISONED: '中毒',
                self.STATUS_BUFF: '增益',
                self.STATUS_DEBUFF: '减益'
            }
            name = names.get(status['status_type'], status['status_type'])

            description = status_data.get('description', '')
            lines.append(f"{icon} {name}: {description} (剩余 {remaining_minutes} 分钟)")

        return "\n".join(lines)

    async def can_explore(self, user_id: str) -> tuple[bool, str]:
        """
        检查玩家是否可以探索

        Args:
            user_id: 玩家ID

        Returns:
            (是否可以探索, 原因说明)
        """
        # 重伤状态不影响探索，只影响修炼
        # 但可以在这里添加其他限制
        return True, ""
