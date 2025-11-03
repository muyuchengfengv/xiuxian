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


# NPC模板配置
NPC_TEMPLATES = {
    '炼气期': [
        {
            'name': '野兽',
            'level_range': (1, 3),
            'hp_mult': 0.8,
            'atk_mult': 0.7,
            'rewards': {'spirit_stone': (10, 30), 'exp': (50, 100)}
        },
        {
            'name': '妖兽',
            'level_range': (4, 9),
            'hp_mult': 1.0,
            'atk_mult': 0.9,
            'rewards': {'spirit_stone': (30, 100), 'exp': (100, 300)}
        }
    ],
    '筑基期': [
        {
            'name': '灵兽',
            'level_range': (1, 3),
            'hp_mult': 1.2,
            'atk_mult': 1.0,
            'rewards': {'spirit_stone': (100, 300), 'exp': (300, 600)}
        },
        {
            'name': '妖兽',
            'level_range': (4, 9),
            'hp_mult': 1.3,
            'atk_mult': 1.1,
            'rewards': {'spirit_stone': (200, 500), 'exp': (500, 1000)}
        }
    ],
    '金丹期': [
        {
            'name': '妖王',
            'level_range': (1, 5),
            'hp_mult': 1.5,
            'atk_mult': 1.2,
            'rewards': {'spirit_stone': (500, 1000), 'exp': (1000, 2000)}
        }
    ]
}


class NPC:
    """NPC妖兽类"""

    def __init__(self, name: str, realm: str, level: int, hp: int, attack: int, defense: int, rewards: Dict):
        """
        初始化NPC

        Args:
            name: NPC名称
            realm: 境界
            level: 等级
            hp: 生命值
            attack: 攻击力
            defense: 防御力
            rewards: 奖励
        """
        self.user_id = f"npc_{name}_{level}"  # NPC的唯一标识
        self.name = name
        self.realm = realm
        self.level = level
        self.realm_level = level
        self.hp = hp
        self.max_hp = hp
        self.attack = attack
        self.defense = defense
        self.mp = 100
        self.max_mp = 100
        self.rewards = rewards


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
                'message': f"💨 回合{round_num}：{defender.name} 闪避了 {attacker.name} 的攻击！",
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
            if is_crit:
                damage_text = f"💥 回合{round_num}：{attacker.name} 暴击 {defender.name}，造成 【{actual_damage}】 点伤害！"
            else:
                damage_text = f"⚔️ 回合{round_num}：{attacker.name} 攻击 {defender.name}，造成 【{actual_damage}】 点伤害"

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

    def _get_hp_bar(self, current_hp: int, max_hp: int, length: int = 10) -> str:
        """
        生成HP百分比条

        Args:
            current_hp: 当前HP
            max_hp: 最大HP
            length: 条的长度

        Returns:
            HP条字符串
        """
        if max_hp <= 0:
            return "█" * length

        percentage = current_hp / max_hp
        filled = int(percentage * length)
        empty = length - filled

        bar = "█" * filled + "░" * empty
        return f"[{bar}] {percentage*100:.0f}%"

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

        # 1. 战斗标题和基础信息
        lines.append("⚔️ 切磋对战")
        lines.append("─" * 40)

        # 计算战力
        attacker_power = CombatCalculator.calculate_power(attacker)
        defender_power = CombatCalculator.calculate_power(defender)

        # 2. 参与者信息（包含战力）
        lines.append(f"👥 对战双方：")
        lines.append(f"   🔴 {attacker.name} ({attacker.realm}) - 战力: {attacker_power}")
        lines.append(f"   🔵 {defender.name} ({defender.realm}) - 战力: {defender_power}")
        lines.append("")

        # 3. 统计战斗数据
        total_rounds = len([log for log in combat_log if log['type'] in ['attack', 'dodge']])
        attacker_stats = {
            'total_damage': 0,
            'crit_count': 0,
            'dodge_count': 0,
            'attack_count': 0
        }
        defender_stats = {
            'total_damage': 0,
            'crit_count': 0,
            'dodge_count': 0,
            'attack_count': 0
        }

        # 统计每个玩家的数据
        for i, log_entry in enumerate(combat_log):
            if log_entry['type'] not in ['attack', 'dodge']:
                continue

            # 判断当前回合的攻击者（奇数回合是attacker，偶数回合是defender）
            round_num = log_entry.get('round', 0)
            is_attacker_turn = (round_num % 2 == 1)
            current_stats = attacker_stats if is_attacker_turn else defender_stats

            if log_entry['type'] == 'attack':
                current_stats['attack_count'] += 1
                current_stats['total_damage'] += log_entry.get('damage', 0)
                if log_entry.get('is_crit'):
                    current_stats['crit_count'] += 1
            elif log_entry['type'] == 'dodge':
                # 对方闪避了攻击
                current_stats['attack_count'] += 1
                opponent_stats = defender_stats if is_attacker_turn else attacker_stats
                opponent_stats['dodge_count'] += 1

        # 4. 显示前10回合的战斗过程
        lines.append("📜 战斗过程（前10回合）：")
        lines.append("")

        display_count = 0
        for log_entry in combat_log:
            if log_entry['type'] == 'start':
                lines.append(f"📢 {log_entry['message']}")
                lines.append(f"   💚 {attacker.name}: {log_entry['attacker_hp']}/{attacker.max_hp} HP")
                lines.append(f"   💙 {defender.name}: {log_entry['defender_hp']}/{defender.max_hp} HP")
                lines.append("")
            elif log_entry['type'] in ['attack', 'dodge'] and display_count < 10:
                lines.append(f"   {log_entry['message']}")
                # 显示当前HP状态和HP条
                attacker_hp_bar = self._get_hp_bar(log_entry['attacker_hp'], attacker.max_hp, 8)
                defender_hp_bar = self._get_hp_bar(log_entry['defender_hp'], defender.max_hp, 8)
                lines.append(f"      💚 {attacker.name}: {log_entry['attacker_hp']}/{attacker.max_hp} {attacker_hp_bar}")
                lines.append(f"      💙 {defender.name}: {log_entry['defender_hp']}/{defender.max_hp} {defender_hp_bar}")
                display_count += 1
                if display_count < 10 and display_count < total_rounds:
                    lines.append("")
            elif log_entry['type'] == 'timeout':
                lines.append("")
                lines.append(f"⏰ {log_entry['message']}")
            elif log_entry['type'] == 'end':
                lines.append("")
                lines.append(f"🏁 {log_entry['message']}")

        # 如果战斗超过10回合，显示省略提示
        if total_rounds > 10:
            lines.append("")
            lines.append(f"   ... 省略 {total_rounds - 10} 回合 ...")

        lines.append("")

        # 5. 战斗统计
        lines.append("📊 战斗统计")
        lines.append("─" * 40)
        lines.append(f"🔴 {attacker.name}：")
        lines.append(f"   总伤害: {attacker_stats['total_damage']}")
        lines.append(f"   攻击次数: {attacker_stats['attack_count']}")
        lines.append(f"   暴击次数: {attacker_stats['crit_count']}")
        if attacker_stats['attack_count'] > 0:
            crit_rate = (attacker_stats['crit_count'] / attacker_stats['attack_count']) * 100
            avg_damage = attacker_stats['total_damage'] / attacker_stats['attack_count']
            lines.append(f"   暴击率: {crit_rate:.1f}%")
            lines.append(f"   平均伤害: {avg_damage:.1f}")
        lines.append(f"   闪避次数: {attacker_stats['dodge_count']}")

        lines.append("")
        lines.append(f"🔵 {defender.name}：")
        lines.append(f"   总伤害: {defender_stats['total_damage']}")
        lines.append(f"   攻击次数: {defender_stats['attack_count']}")
        lines.append(f"   暴击次数: {defender_stats['crit_count']}")
        if defender_stats['attack_count'] > 0:
            crit_rate = (defender_stats['crit_count'] / defender_stats['attack_count']) * 100
            avg_damage = defender_stats['total_damage'] / defender_stats['attack_count']
            lines.append(f"   暴击率: {crit_rate:.1f}%")
            lines.append(f"   平均伤害: {avg_damage:.1f}")
        lines.append(f"   闪避次数: {defender_stats['dodge_count']}")

        lines.append("")
        lines.append(f"⏱️ 总回合数: {total_rounds}")

        # 6. 战斗结果
        lines.append("")
        if combat_log and combat_log[-1].get('winner'):
            winner_id = combat_log[-1]['winner']
            winner_name = attacker.name if winner_id == attacker.user_id else defender.name
            loser_name = defender.name if winner_id == attacker.user_id else attacker.name

            # 获取最终HP
            final_attacker_hp = combat_log[-1].get('attacker_hp', 0)
            final_defender_hp = combat_log[-1].get('defender_hp', 0)

            lines.append("🏆 战斗结果")
            lines.append("─" * 40)
            lines.append(f"🥇 胜者：{winner_name}")
            lines.append(f"🥈 败者：{loser_name}")
            lines.append("")
            lines.append(f"💚 最终状态：")
            attacker_final_bar = self._get_hp_bar(final_attacker_hp, attacker.max_hp, 10)
            defender_final_bar = self._get_hp_bar(final_defender_hp, defender.max_hp, 10)
            lines.append(f"   {attacker.name}: {final_attacker_hp}/{attacker.max_hp} HP")
            lines.append(f"   {attacker_final_bar}")
            lines.append(f"   {defender.name}: {final_defender_hp}/{defender.max_hp} HP")
            lines.append(f"   {defender_final_bar}")
        else:
            lines.append("🤝 战斗结果：平局")
            final_attacker_hp = combat_log[-1].get('attacker_hp', 0)
            final_defender_hp = combat_log[-1].get('defender_hp', 0)
            lines.append("")
            lines.append(f"💚 最终状态：")
            attacker_final_bar = self._get_hp_bar(final_attacker_hp, attacker.max_hp, 10)
            defender_final_bar = self._get_hp_bar(final_defender_hp, defender.max_hp, 10)
            lines.append(f"   {attacker.name}: {final_attacker_hp}/{attacker.max_hp} HP")
            lines.append(f"   {attacker_final_bar}")
            lines.append(f"   {defender.name}: {final_defender_hp}/{defender.max_hp} HP")
            lines.append(f"   {defender_final_bar}")

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


    async def generate_npc(self, realm: str, level: int) -> NPC:
        """
        生成NPC妖兽

        Args:
            realm: 境界
            level: 等级

        Returns:
            生成的NPC对象
        """
        templates = NPC_TEMPLATES.get(realm, NPC_TEMPLATES['炼气期'])

        # 选择合适的模板
        suitable_templates = [
            t for t in templates
            if t['level_range'][0] <= level <= t['level_range'][1]
        ]

        if not suitable_templates:
            suitable_templates = templates

        template = random.choice(suitable_templates)

        # 计算NPC属性
        base_hp = 100 + level * 50
        base_attack = 10 + level * 5
        base_defense = 5 + level * 3

        npc = NPC(
            name=f"{template['name']}({level}级)",
            realm=realm,
            level=level,
            hp=int(base_hp * template['hp_mult']),
            attack=int(base_attack * template['atk_mult']),
            defense=base_defense,
            rewards=template['rewards']
        )

        logger.info(f"生成NPC: {npc.name}, HP:{npc.hp}, 攻击:{npc.attack}, 防御:{npc.defense}")

        return npc

    async def battle_npc(self, user_id: str, npc_level: int = None) -> Dict:
        """
        PVE战斗

        Args:
            user_id: 玩家ID
            npc_level: NPC等级（可选，默认根据玩家境界等级）

        Returns:
            战斗结果字典，包含：
            {
                'battle_id': str,
                'player': Player,
                'npc': NPC,
                'combat_log': List[Dict],
                'winner': str,
                'rewards': Dict
            }
        """
        # 获取玩家
        player = await self.player_mgr.get_player_or_error(user_id)

        # 确定NPC等级
        if npc_level is None:
            npc_level = player.realm_level

        # 生成NPC
        npc = await self.generate_npc(player.realm, npc_level)

        # 执行战斗（复用PVP战斗逻辑）
        battle_id = self._generate_battle_id(user_id, 'NPC')
        combat_log = await self._execute_combat(player, npc, battle_id)

        # 判断胜负
        winner = combat_log[-1]['winner'] if combat_log else None

        result = {
            'battle_id': battle_id,
            'player': player,
            'npc': npc,
            'combat_log': combat_log,
            'winner': winner,
            'rewards': {}
        }

        # 如果玩家胜利，发放奖励
        if winner == user_id:
            spirit_stone = random.randint(*npc.rewards['spirit_stone'])
            exp = random.randint(*npc.rewards['exp'])

            player.spirit_stone += spirit_stone
            await self.player_mgr.update_player(player)

            result['rewards'] = {
                'spirit_stone': spirit_stone,
                'exp': exp
            }

            logger.info(f"玩家 {player.name} 战胜 {npc.name}，获得灵石 {spirit_stone}，经验 {exp}")
        else:
            logger.info(f"玩家 {player.name} 被 {npc.name} 击败")

        return result