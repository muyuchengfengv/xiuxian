"""
玩家属性修复脚本

用于修复因突破系统bug导致的玩家属性异常问题。
根据玩家当前境界和等级，重新计算并应用正确的属性加成。

使用方法：
python3 -m astrbot_plugin_xiuxian.utils.fix_player_attributes
"""

import asyncio
import sys
from pathlib import Path

# 添加项目路径到系统路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from astrbot_plugin_xiuxian.core.database import DatabaseManager
from astrbot_plugin_xiuxian.models.player_model import Player
from astrbot_plugin_xiuxian.utils.constants import REALMS, REALM_ORDER
from astrbot_plugin_xiuxian.core.spirit_root import SpiritRootFactory


class PlayerAttributeFixer:
    """玩家属性修复器"""

    def __init__(self, db_path: str):
        """
        初始化修复器

        Args:
            db_path: 数据库文件路径
        """
        self.db = DatabaseManager(db_path)

    def calculate_correct_attributes(self, player: Player) -> dict:
        """
        计算玩家的正确属性值

        Args:
            player: 玩家对象

        Returns:
            正确的属性值字典
        """
        # 1. 从初始属性开始（玩家创建时的属性）
        initial_attrs = {
            'constitution': player.constitution,
            'spiritual_power': player.spiritual_power,
            'comprehension': player.comprehension,
            'luck': player.luck,
            'root_bone': player.root_bone
        }

        # 2. 计算初始战斗属性（炼气期初期的基础属性）
        from astrbot_plugin_xiuxian.utils.constants import INITIAL_COMBAT_STATS

        base_hp = INITIAL_COMBAT_STATS['max_hp']
        base_mp = INITIAL_COMBAT_STATS['max_mp']
        base_attack = INITIAL_COMBAT_STATS['attack']
        base_defense = INITIAL_COMBAT_STATS['defense']

        # 体质影响生命值
        hp_bonus_from_constitution = initial_attrs['constitution'] * 50
        base_hp += hp_bonus_from_constitution

        # 灵力影响法力值和攻击力
        mp_bonus_from_spiritual = initial_attrs['spiritual_power'] * 30
        attack_bonus_from_spiritual = initial_attrs['spiritual_power'] * 2
        base_mp += mp_bonus_from_spiritual
        base_attack += attack_bonus_from_spiritual

        # 根骨影响防御力
        defense_bonus_from_root = initial_attrs['root_bone'] * 1
        base_defense += defense_bonus_from_root

        # 3. 应用灵根战斗加成
        if player.spirit_root_type:
            spirit_root = {
                'type': player.spirit_root_type,
                'quality': player.spirit_root_quality,
                'value': player.spirit_root_value,
                'purity': player.spirit_root_purity
            }
            bonuses = SpiritRootFactory.calculate_bonuses(spirit_root)
            combat_bonus = bonuses.get('combat_bonus', {})

            if 'attack' in combat_bonus:
                base_attack = int(base_attack * (1 + combat_bonus['attack']))
            if 'defense' in combat_bonus:
                base_defense = int(base_defense * (1 + combat_bonus['defense']))
            if 'max_hp' in combat_bonus:
                bonus_hp = int(base_hp * combat_bonus['max_hp'])
                base_hp += bonus_hp
            if 'max_mp' in combat_bonus:
                bonus_mp = int(base_mp * combat_bonus['max_mp'])
                base_mp += bonus_mp

        # 4. 计算所有境界提升带来的属性加成
        current_realm_index = REALMS[player.realm]['index']

        total_hp_bonus = 0
        total_mp_bonus = 0
        total_attack_bonus = 0
        total_defense_bonus = 0

        # 遍历所有已经突破过的境界
        for realm_name in REALM_ORDER:
            realm_config = REALMS[realm_name]
            realm_index = realm_config['index']

            # 如果是当前境界之前的境界，计算完整加成
            if realm_index < current_realm_index:
                # 大境界突破：获得完整的境界属性加成 * 4（因为有4个小境界）
                attribute_bonus = realm_config.get('attribute_bonus', {})
                total_hp_bonus += attribute_bonus.get('max_hp', 0) * 4
                total_mp_bonus += attribute_bonus.get('max_mp', 0) * 4
                total_attack_bonus += attribute_bonus.get('attack', 0) * 4
                total_defense_bonus += attribute_bonus.get('defense', 0) * 4

            # 如果是当前境界，根据小等级计算
            elif realm_index == current_realm_index:
                attribute_bonus = realm_config.get('attribute_bonus', {})
                # 小境界提升：每级25%的境界属性加成
                level_ratio = 0.25
                levels_passed = player.realm_level  # 当前小境界 1-4

                total_hp_bonus += int(attribute_bonus.get('max_hp', 0) * level_ratio * levels_passed)
                total_mp_bonus += int(attribute_bonus.get('max_mp', 0) * level_ratio * levels_passed)
                total_attack_bonus += int(attribute_bonus.get('attack', 0) * level_ratio * levels_passed)
                total_defense_bonus += int(attribute_bonus.get('defense', 0) * level_ratio * levels_passed)

        # 5. 计算最终属性
        final_max_hp = base_hp + total_hp_bonus
        final_max_mp = base_mp + total_mp_bonus
        final_attack = base_attack + total_attack_bonus
        final_defense = base_defense + total_defense_bonus

        return {
            'max_hp': final_max_hp,
            'hp': final_max_hp,  # 满血
            'max_mp': final_max_mp,
            'mp': final_max_mp,  # 满蓝
            'attack': final_attack,
            'defense': final_defense
        }

    async def fix_player(self, player: Player, dry_run: bool = True) -> dict:
        """
        修复单个玩家的属性

        Args:
            player: 玩家对象
            dry_run: 是否为模拟运行（不实际修改数据库）

        Returns:
            修复信息字典
        """
        # 计算正确属性
        correct_attrs = self.calculate_correct_attributes(player)

        # 对比当前属性
        changes = {}
        if player.max_hp != correct_attrs['max_hp']:
            changes['max_hp'] = {
                'old': player.max_hp,
                'new': correct_attrs['max_hp'],
                'diff': correct_attrs['max_hp'] - player.max_hp
            }
        if player.max_mp != correct_attrs['max_mp']:
            changes['max_mp'] = {
                'old': player.max_mp,
                'new': correct_attrs['max_mp'],
                'diff': correct_attrs['max_mp'] - player.max_mp
            }
        if player.attack != correct_attrs['attack']:
            changes['attack'] = {
                'old': player.attack,
                'new': correct_attrs['attack'],
                'diff': correct_attrs['attack'] - player.attack
            }
        if player.defense != correct_attrs['defense']:
            changes['defense'] = {
                'old': player.defense,
                'new': correct_attrs['defense'],
                'diff': correct_attrs['defense'] - player.defense
            }

        # 如果不是模拟运行，执行修复
        if not dry_run and changes:
            await self.db.execute("""
                UPDATE players
                SET max_hp = ?, hp = ?, max_mp = ?, mp = ?, attack = ?, defense = ?
                WHERE user_id = ?
            """, (
                correct_attrs['max_hp'],
                correct_attrs['hp'],
                correct_attrs['max_mp'],
                correct_attrs['mp'],
                correct_attrs['attack'],
                correct_attrs['defense'],
                player.user_id
            ))

        return {
            'user_id': player.user_id,
            'name': player.name,
            'realm': f"{player.realm} {player.realm_level}",
            'changes': changes,
            'fixed': not dry_run and bool(changes)
        }

    async def fix_all_players(self, dry_run: bool = True) -> list:
        """
        修复所有玩家的属性

        Args:
            dry_run: 是否为模拟运行

        Returns:
            修复结果列表
        """
        # 获取所有玩家
        rows = await self.db.fetchall("SELECT * FROM players")

        results = []
        for row in rows:
            player_data = dict(row)
            player = Player.from_dict(player_data)
            result = await self.fix_player(player, dry_run)
            results.append(result)

        return results

    async def run(self, dry_run: bool = True):
        """
        运行修复程序

        Args:
            dry_run: 是否为模拟运行
        """
        print("=" * 60)
        print("玩家属性修复工具")
        print("=" * 60)
        print(f"模式: {'模拟运行（不修改数据）' if dry_run else '实际修复'}")
        print()

        # 初始化数据库
        await self.db.init_db()

        # 修复所有玩家
        results = await self.fix_all_players(dry_run)

        # 统计结果
        total_players = len(results)
        players_with_issues = sum(1 for r in results if r['changes'])
        players_fixed = sum(1 for r in results if r['fixed'])

        print(f"\n检查了 {total_players} 个玩家")
        print(f"发现 {players_with_issues} 个玩家属性异常")

        if players_with_issues > 0:
            print("\n异常详情:")
            print("-" * 60)
            for result in results:
                if result['changes']:
                    print(f"\n玩家: {result['name']} ({result['user_id']})")
                    print(f"境界: {result['realm']}")
                    for attr, change in result['changes'].items():
                        print(f"  {attr}: {change['old']} -> {change['new']} (差值: {change['diff']:+d})")

        if dry_run:
            print("\n" + "=" * 60)
            print("这是模拟运行，未实际修改数据")
            print("如需实际修复，请运行:")
            print("python3 -m astrbot_plugin_xiuxian.utils.fix_player_attributes --fix")
            print("=" * 60)
        else:
            print(f"\n成功修复 {players_fixed} 个玩家的属性")

        # 关闭数据库
        await self.db.close()


async def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='修复玩家属性')
    parser.add_argument('--fix', action='store_true', help='实际修复（默认为模拟运行）')
    parser.add_argument('--db', type=str, default='data/xiuxian.db', help='数据库路径')

    args = parser.parse_args()

    # 确定数据库路径
    db_path = Path(__file__).parent.parent / args.db

    # 创建修复器
    fixer = PlayerAttributeFixer(str(db_path))

    # 运行修复
    await fixer.run(dry_run=not args.fix)


if __name__ == "__main__":
    asyncio.run(main())
