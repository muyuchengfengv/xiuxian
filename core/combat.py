"""
战斗系统
负责玩家间PVP战斗的处理
"""

import random
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from astrbot.api import logger

from .database import DatabaseManager
from .player import PlayerManager
from ..models.player_model import Player
from ..utils import (
    CombatCalculator,
    MessageFormatter,
    XiuxianException,
    MAX_COMBAT_ROUNDS
)


class CombatException(XiuxianException):
    """战斗相关异常"""
    pass


class InvalidTargetException(CombatException):
    """无效目标异常"""
    pass


class SelfCombatException(CombatException):
    """自我战斗异常"""
    pass


class CombatSystem:
    """战斗系统类"""

    def __init__(self, db: DatabaseManager, player_mgr: PlayerManager):
        """
        初始化战斗系统

        Args:
            db: 数据库管理器
            player_mgr: 玩家管理器
        """
        self.db = db
        self.player_mgr = player_mgr
        self.active_combats = {}  # 活跃战斗 {battle_id: combat_data}

    async def initiate_combat(self, attacker_id: str, defender_id: str) -> Dict:
        """
        发起战斗

        Args:
            attacker_id: 攻击者用户ID
            defender_id: 防御者用户ID

        Returns:
            战斗结果字典

        Raises:
            PlayerNotFoundError: 玩家不存在
            InvalidTargetException: 无效目标
            SelfCombatException: 自我战斗
        """
        # 1. 检查战斗参与者
        attacker = await self.player_mgr.get_player_or_error(attacker_id)
        defender = await self.player_mgr.get_player_or_error(defender_id)

        # 2. 检查是否是自我战斗
        if attacker_id == defender_id:
            raise SelfCombatException("道友不能与自己切磋")

        # 3. 检查是否已在战斗中
        if self._is_in_combat(attacker_id) or self._is_in_combat(defender_id):
            raise CombatException("已有玩家正在战斗中")

        # 4. 生成战斗ID
        battle_id = self._generate_battle_id(attacker_id, defender_id)

        # 5. 执行战斗
        combat_log = await self._execute_combat(attacker, defender, battle_id)

        return {
            'battle_id': battle_id,
            'attacker': attacker,
            'defender': defender,
            'combat_log': combat_log,
            'winner': combat_log[-1]['winner'] if combat_log else None
        }

    def _is_in_combat(self, user_id: str) -> bool:
        """
        检查玩家是否在战斗中

        Args:
            user_id: 用户ID

        Returns:
            是否在战斗中
        """
        return any(user_id in combat['participants'] for combat in self.active_combats.values())

    def _generate_battle_id(self, attacker_id: str, defender_id: str) -> str:
        """
        生成战斗ID

        Args:
            attacker_id: 攻击者ID
            defender_id: 防御者ID

        Returns:
            战斗ID
        """
        timestamp = int(datetime.now().timestamp())
        return f"battle_{attacker_id[:8]}_{defender_id[:8]}_{timestamp}"

    async def _execute_combat(self, attacker: Player, defender: Player, battle_id: str) -> List[Dict]:
        """
        执行战斗逻辑

        Args:
            attacker: 攻击者
            defender: 防御者
            battle_id: 战斗ID

        Returns:
            战斗日志列表
        """
        # 1. 创建战斗记录
        combat_data = {
            'battle_id': battle_id,
            'participants': [attacker.user_id, defender.user_id],
            'start_time': datetime.now(),
            'status': 'active'
        }
        self.active_combats[battle_id] = combat_data

        combat_log = []
        current_attacker, current_defender = attacker, defender
        round_count = 0

        try:
            # 2. 战斗开始信息
            combat_log.append({
                'round': 0,
                'type': 'start',
                'message': f"⚔️ {attacker.name} 向 {defender.name} 发起切磋！",
                'attacker_hp': attacker.hp,
                'defender_hp': defender.hp,
                'winner': None
            })

            # 3. 战斗主循环
            while round_count < MAX_COMBAT_ROUNDS:
                round_count += 1

                # 执行一回合攻击
                round_result = await self._execute_attack_round(
                    current_attacker, current_defender, round_count
                )
                combat_log.append(round_result)

                # 检查战斗是否结束
                if round_result.get('battle_ended'):
                    break

                # 交换攻击方
                current_attacker, current_defender = current_defender, current_attacker

            # 4. 如果达到最大回合数，判定平局
            if round_count >= MAX_COMBAT_ROUNDS and not combat_log[-1].get('battle_ended'):
                winner = self._determine_winner_by_hp(attacker, defender)
                combat_log.append({
                    'round': round_count,
                    'type': 'timeout',
                    'message': f"⏰ 切磋达到最大回合数{MAX_COMBAT_ROUNDS}！",
                    'winner': winner,
                    'attacker_hp': attacker.hp,
                    'defender_hp': defender.hp
                })

        finally:
            # 5. 清理战斗记录
            if battle_id in self.active_combats:
                del self.active_combats[battle_id]

        return combat_log

    async def _execute_attack_round(self, attacker: Player, defender: Player, round_num: int) -> Dict:
        """
        执行一回合攻击

        Args:
            attacker: 攻击者
            defender: 防御者
            round_num: 回合数

        Returns:
            回合结果字典
        """
        # 1. 计算基础伤害
        base_damage = CombatCalculator.calculate_damage(attacker, defender)

        # 2. 计算暴击
        crit_damage, is_crit = CombatCalculator.calculate_critical_hit(base_damage, attacker.luck)

        # 3. 计算闪避
        is_dodge = CombatCalculator.calculate_dodge_attack(attacker, defender)

        if is_dodge:
            result = {
                'round': round_num,
                'type': 'dodge',
                'message': f"💨 第{round_num}回合：{defender.name} 闪避了 {attacker.name} 的攻击！",
                'damage': 0,
                'is_crit': False,
                'is_dodge': True,
                'attacker_hp': attacker.hp,
                'defender_hp': defender.hp,
                'battle_ended': False,
                'winner': None
            }
        else:
            # 应用伤害
            actual_damage = min(crit_damage, defender.hp)  # 不能超过当前HP
            defender.hp -= actual_damage

            # 构建消息
            crit_text = "💥 暴击！" if is_crit else ""
            damage_text = f"第{round_num}回合：{attacker.name} 对 {defender.name} 造成 {actual_damage} 点伤害{crit_text}"

            result = {
                'round': round_num,
                'type': 'attack',
                'message': damage_text,
                'damage': actual_damage,
                'is_crit': is_crit,
                'is_dodge': False,
                'attacker_hp': attacker.hp,
                'defender_hp': max(0, defender.hp),
                'battle_ended': defender.hp <= 0,
                'winner': attacker.user_id if defender.hp <= 0 else None
            }

        return result

    def _determine_winner_by_hp(self, attacker: Player, defender: Player) -> Optional[str]:
        """
        根据HP判定胜者

        Args:
            attacker: 攻击者
            defender: 防御者

        Returns:
            胜者用户ID，平局返回None
        """
        if attacker.hp > defender.hp:
            return attacker.user_id
        elif defender.hp > attacker.hp:
            return defender.user_id
        else:
            return None

    async def format_combat_log(self, combat_log: List[Dict], attacker: Player, defender: Player) -> str:
        """
        格式化战斗日志为可读文本

        Args:
            combat_log: 战斗日志
            attacker: 攻击者
            defender: 防御者

        Returns:
            格式化的战斗文本
        """
        if not combat_log:
            return "❌ 战斗日志为空"

        lines = []

        # 1. 战斗标题
        lines.append("⚔️ 切磋对战")
        lines.append("─" * 40)

        # 2. 参与者信息
        lines.append(f"👥 对战双方：")
        lines.append(f"   🔴 {attacker.name} ({attacker.realm})")
        lines.append(f"   🔵 {defender.name} ({defender.realm})")
        lines.append("")

        # 3. 战斗过程
        for log_entry in combat_log:
            if log_entry['type'] == 'start':
                lines.append(f"📢 {log_entry['message']}")
                lines.append("")
            elif log_entry['type'] in ['attack', 'dodge']:
                lines.append(f"   {log_entry['message']}")

                # 显示状态
                lines.append(f"   📊 {attacker.name} HP: {log_entry['attacker_hp']}/{attacker.max_hp} | "
                           f"{defender.name} HP: {log_entry['defender_hp']}/{defender.max_hp}")
                lines.append("")
            elif log_entry['type'] == 'timeout':
                lines.append(f"⏰ {log_entry['message']}")
                lines.append("")
            elif log_entry['type'] == 'end':
                lines.append(f"🏁 {log_entry['message']}")
                lines.append("")

        # 4. 战斗结果
        if combat_log and combat_log[-1].get('winner'):
            winner_id = combat_log[-1]['winner']
            winner_name = attacker.name if winner_id == attacker.user_id else defender.name
            loser_name = defender.name if winner_id == attacker.user_id else attacker.name

            lines.append("🏆 战斗结果")
            lines.append("─" * 40)
            lines.append(f"🥇 胜者：{winner_name}")
            lines.append(f"🥈 败者：{loser_name}")

            # 计算战力对比
            attacker_power = CombatCalculator.calculate_power(attacker)
            defender_power = CombatCalculator.calculate_power(defender)

            lines.append("")
            lines.append("📊 战力对比")
            lines.append(f"   {attacker.name}: {attacker_power}")
            lines.append(f"   {defender.name}: {defender_power}")
        else:
            lines.append("🤝 战斗结果：平局")

        return "\n".join(lines)

    async def get_combat_stats(self, user_id: str) -> Dict:
        """
        获取玩家战斗统计

        Args:
            user_id: 用户ID

        Returns:
            战斗统计信息
        """
        player = await self.player_mgr.get_player_or_error(user_id)

        power = CombatCalculator.calculate_power(player)

        return {
            'user_id': user_id,
            'name': player.name,
            'realm': player.realm,
            'power': power,
            'hp': player.hp,
            'max_hp': player.max_hp,
            'attack': player.attack,
            'defense': player.defense,
            'luck': player.luck,
            'is_in_combat': self._is_in_combat(user_id)
        }

    @staticmethod
    def calculate_dodge_attack(attacker: Player, defender: Player) -> bool:
        """
        计算闪避攻击

        Args:
            attacker: 攻击者
            defender: 防御者

        Returns:
            是否闪避成功
        """
        # 使用 CombatCalculator 的闪避计算
        # 假设攻击者和防御者都有速度属性（如果有）
        attacker_speed = getattr(attacker, 'speed', 10)  # 默认速度
        defender_speed = getattr(defender, 'speed', 10)

        return CombatCalculator.calculate_dodge_chance(attacker_speed, defender_speed)