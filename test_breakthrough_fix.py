"""
突破系统修复测试脚本

测试修复后的突破系统是否能正确应用属性加成
"""

import asyncio
import sys
from pathlib import Path

# 添加项目路径到系统路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.database import DatabaseManager
from core.player import PlayerManager
from core.breakthrough import BreakthroughSystem
from models.player_model import Player
from utils.constants import REALMS


async def test_breakthrough():
    """测试突破系统修复"""
    print("=" * 60)
    print("突破系统修复测试")
    print("=" * 60)

    # 初始化数据库
    db_path = "data/test_xiuxian.db"
    db = DatabaseManager(db_path)
    await db.init_db()

    # 创建玩家管理器
    player_mgr = PlayerManager(db)

    # 创建突破系统
    breakthrough_sys = BreakthroughSystem(db, player_mgr)

    # 创建测试玩家
    test_user_id = "test_user_001"
    test_name = "测试道友"

    print(f"\n1. 创建测试玩家: {test_name}")
    player = await player_mgr.create_player(test_user_id, test_name)

    print(f"初始属性:")
    print(f"  境界: {player.realm} {player.realm_level}")
    print(f"  HP: {player.max_hp}, MP: {player.max_mp}")
    print(f"  攻击: {player.attack}, 防御: {player.defense}")

    # 设置足够的修为进行多次突破
    player.cultivation = 1000000  # 足够突破多次
    await player_mgr.update_player(player)

    print(f"\n2. 开始突破测试...")

    # 测试小境界突破（炼气期初期 -> 中期）
    print("\n--- 测试小境界突破（炼气期初期 -> 中期）---")
    result = await breakthrough_sys.attempt_breakthrough(test_user_id)

    if result['success']:
        print(f"✅ 突破成功!")
        print(f"  消息: {result['message']}")

        # 获取更新后的玩家
        player = await player_mgr.get_player(test_user_id)
        print(f"  突破后属性:")
        print(f"  境界: {player.realm} {player.realm_level}")
        print(f"  HP: {player.max_hp}, MP: {player.max_mp}")
        print(f"  攻击: {player.attack}, 防御: {player.defense}")

        # 计算期望的属性加成
        realm_config = REALMS["炼气期"]
        attribute_bonus = realm_config.get("attribute_bonus", {})
        level_ratio = 0.25
        expected_hp = 100 + int(attribute_bonus.get("max_hp", 0) * level_ratio)
        expected_mp = 100 + int(attribute_bonus.get("max_mp", 0) * level_ratio)
        expected_attack = 10 + int(attribute_bonus.get("attack", 0) * level_ratio)
        expected_defense = 10 + int(attribute_bonus.get("defense", 0) * level_ratio)

        print(f"  期望属性:")
        print(f"  HP: {expected_hp}, MP: {expected_mp}")
        print(f"  攻击: {expected_attack}, 防御: {expected_defense}")

        # 验证属性是否正确增加
        if (player.max_hp == expected_hp and
            player.max_mp == expected_mp and
            player.attack == expected_attack and
            player.defense == expected_defense):
            print("✅ 小境界突破属性加成正确!")
        else:
            print("❌ 小境界突破属性加成异常!")
    else:
        print(f"❌ 突破失败: {result['message']}")

    # 继续测试大境界突破（先升到炼气期大圆满）
    print("\n--- 测试大境界突破（炼气期 -> 筑基期）---")

    # 先升级到炼气期大圆满
    for i in range(2, 4):  # 升级到3级和4级
        player.cultivation = 1000000
        await player_mgr.update_player(player)
        result = await breakthrough_sys.attempt_breakthrough(test_user_id)
        if result['success']:
            print(f"  突破到 {result['new_realm']} 成功")
        else:
            print(f"  突破到下一境界失败: {result['message']}")
            break

    # 现在测试突破到筑基期
    player = await player_mgr.get_player(test_user_id)
    player.cultivation = 1000000
    await player_mgr.update_player(player)

    # 记录突破前的属性
    before_breakthrough = {
        'realm': f"{player.realm} {player.realm_level}",
        'hp': player.max_hp,
        'mp': player.max_mp,
        'attack': player.attack,
        'defense': player.defense
    }

    result = await breakthrough_sys.attempt_breakthrough(test_user_id)

    if result['success']:
        print(f"✅ 大境界突破成功!")
        print(f"  从 {before_breakthrough['realm']} -> {result['new_realm']}")

        # 获取突破后的玩家
        player = await player_mgr.get_player(test_user_id)

        # 计算期望的属性加成
        qi_config = REALMS["炼气期"]
        zhuji_config = REALMS["筑基期"]

        qi_bonus = qi_config.get("attribute_bonus", {})
        zhuji_bonus = zhuji_config.get("attribute_bonus", {})

        # 炼气期完整加成（4个小境界）
        total_qi_hp = qi_bonus.get("max_hp", 0) * 4
        total_qi_mp = qi_bonus.get("max_mp", 0) * 4
        total_qi_attack = qi_bonus.get("attack", 0) * 4
        total_qi_defense = qi_bonus.get("defense", 0) * 4

        # 筑基期初期加成
        expected_hp = 100 + total_qi_hp + zhuji_bonus.get("max_hp", 0)
        expected_mp = 100 + total_qi_mp + zhuji_bonus.get("max_mp", 0)
        expected_attack = 10 + total_qi_attack + zhuji_bonus.get("attack", 0)
        expected_defense = 10 + total_qi_defense + zhuji_bonus.get("defense", 0)

        print(f"\n突破后属性:")
        print(f"  境界: {player.realm} {player.realm_level}")
        print(f"  HP: {player.max_hp}, MP: {player.max_mp}")
        print(f"  攻击: {player.attack}, 防御: {player.defense}")

        print(f"\n期望属性:")
        print(f"  HP: {expected_hp}, MP: {expected_mp}")
        print(f"  攻击: {expected_attack}, 防御: {expected_defense}")

        # 验证属性是否正确增加
        if (player.max_hp == expected_hp and
            player.max_mp == expected_mp and
            player.attack == expected_attack and
            player.defense == expected_defense):
            print("✅ 大境界突破属性加成正确!")
        else:
            print("❌ 大境界突破属性加成异常!")
            print(f"HP差异: {player.max_hp - expected_hp}")
            print(f"MP差异: {player.max_mp - expected_mp}")
            print(f"攻击差异: {player.attack - expected_attack}")
            print(f"防御差异: {player.defense - expected_defense}")
    else:
        print(f"❌ 大境界突破失败: {result['message']}")

    print("\n" + "=" * 60)
    print("测试完成!")

    # 清理测试数据
    await db.execute("DELETE FROM players WHERE user_id = ?", (test_user_id,))
    await db.close()


if __name__ == "__main__":
    asyncio.run(test_breakthrough())