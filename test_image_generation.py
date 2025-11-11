"""
图片生成功能测试脚本
测试新的背景生成和卡片生成功能
"""

from pathlib import Path
from core.card_generator import CardGenerator
from core.background_generator import BackgroundGenerator
from core.image_config import ImageConfig


def test_background_generator():
    """测试背景生成器"""
    print("=" * 60)
    print("测试背景生成器...")
    print("=" * 60)

    bg_gen = BackgroundGenerator()

    # 测试所有可用主题
    themes = bg_gen.get_available_themes()
    print(f"\n可用主题: {', '.join(themes)}")

    for theme in themes:
        print(f"\n生成 {theme} 主题背景...")
        try:
            # 生成背景
            background = bg_gen.generate_themed_background(
                width=600,
                height=400,
                theme=theme,
                direction='radial',
                add_effects=True
            )

            # 保存图片
            output_path = Path(__file__).parent / "assets" / "output" / f"bg_test_{theme}.png"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            background.save(output_path)
            print(f"  ✓ 成功生成并保存到: {output_path}")

        except Exception as e:
            print(f"  ✗ 生成失败: {e}")

    print("\n" + "=" * 60)
    print("背景生成器测试完成")
    print("=" * 60)


def test_card_generator():
    """测试卡片生成器"""
    print("\n" + "=" * 60)
    print("测试卡片生成器...")
    print("=" * 60)

    # 创建配置
    config = ImageConfig()
    config.set('enable_background', True)
    config.set('enable_effects', True)

    # 创建卡片生成器
    card_gen = CardGenerator(config=config)

    # 测试数据
    test_cases = [
        {
            'name': 'player_card',
            'method': 'generate_player_card',
            'data': {
                'name': '李逍遥',
                'realm': '元婴期',
                'realm_level': 3,
                'cultivation': 850000,
                'max_cultivation': 1000000,
                'hp': 8500,
                'max_hp': 10000,
                'mp': 12000,
                'max_mp': 15000,
                'attack': 3500,
                'defense': 2800,
                'spirit_root': '五行灵根',
                'spirit_root_quality': '仙品',
            }
        },
        {
            'name': 'cultivation_card',
            'method': 'generate_cultivation_card',
            'data': {
                'player_name': '李逍遥',
                'cultivation_gained': 15000,
                'total_cultivation': 850000,
                'can_breakthrough': True,
                'next_realm': '元婴期大圆满',
                'required_cultivation': 1000000,
                'sect_bonus_rate': 0.2,
            }
        },
        {
            'name': 'equipment_card',
            'method': 'generate_equipment_card',
            'data': {
                'name': '紫霄仙剑',
                'type': 'weapon',
                'quality': '仙品',
                'level': 80,
                'enhance_level': 15,
                'attributes': {
                    'attack': 2500,
                    'crit_rate': 35,
                    'hp_bonus': 1000,
                }
            }
        },
        {
            'name': 'combat_card',
            'method': 'generate_combat_result_card',
            'data': {
                'winner_name': '李逍遥',
                'loser_name': '邪修',
                'winner_hp': 7500,
                'winner_max_hp': 10000,
                'rounds': 8,
                'rewards': {
                    'spirit_stone': 5000,
                    'exp': 10000,
                }
            }
        }
    ]

    # 测试每种卡片
    for test_case in test_cases:
        print(f"\n生成 {test_case['name']}...")
        try:
            # 调用对应的生成方法
            method = getattr(card_gen, test_case['method'])
            card_image = method(test_case['data'])

            # 保存图片
            output_path = Path(__file__).parent / "assets" / "output" / f"test_{test_case['name']}.png"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            card_image.save(output_path)
            print(f"  ✓ 成功生成并保存到: {output_path}")

        except Exception as e:
            print(f"  ✗ 生成失败: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 60)
    print("卡片生成器测试完成")
    print("=" * 60)


def test_different_effects():
    """测试不同效果组合"""
    print("\n" + "=" * 60)
    print("测试不同效果组合...")
    print("=" * 60)

    # 测试不同配置
    test_configs = [
        {'name': 'full_effects', 'enable_effects': True, 'enable_particles': True, 'enable_glow': True},
        {'name': 'no_effects', 'enable_effects': False},
        {'name': 'particles_only', 'enable_effects': True, 'enable_particles': True, 'enable_glow': False},
        {'name': 'glow_only', 'enable_effects': True, 'enable_particles': False, 'enable_glow': True},
    ]

    for test_config in test_configs:
        print(f"\n测试配置: {test_config['name']}...")
        try:
            config = ImageConfig()
            for key, value in test_config.items():
                if key != 'name':
                    config.set(key, value)

            card_gen = CardGenerator(config=config)

            # 生成测试卡片
            player_data = {
                'name': '测试修仙者',
                'realm': '金丹期',
                'realm_level': 2,
                'cultivation': 500000,
                'max_cultivation': 1000000,
                'hp': 5000,
                'max_hp': 8000,
                'mp': 6000,
                'max_mp': 10000,
                'attack': 2000,
                'defense': 1500,
                'spirit_root': '雷灵根',
                'spirit_root_quality': '宝品',
            }

            card_image = card_gen.generate_player_card(player_data)

            # 保存图片
            output_path = Path(__file__).parent / "assets" / "output" / f"effect_test_{test_config['name']}.png"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            card_image.save(output_path)
            print(f"  ✓ 成功生成并保存到: {output_path}")

        except Exception as e:
            print(f"  ✗ 生成失败: {e}")

    print("\n" + "=" * 60)
    print("效果组合测试完成")
    print("=" * 60)


def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("开始测试图片生成功能")
    print("=" * 60)

    try:
        # 测试背景生成器
        test_background_generator()

        # 测试卡片生成器
        test_card_generator()

        # 测试不同效果组合
        test_different_effects()

        print("\n" + "=" * 60)
        print("✓ 所有测试完成！")
        print("=" * 60)
        print("\n生成的图片已保存到 assets/output/ 目录")
        print("请查看生成的图片以验证效果")

    except Exception as e:
        print(f"\n✗ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
