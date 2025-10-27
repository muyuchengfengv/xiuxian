"""
灵根生成工厂
负责随机生成灵根及其属性
"""

import random
from typing import Dict, List
from ..utils.constants import (
    SPIRIT_ROOT_WEIGHTS,
    SPIRIT_ROOT_QUALITIES,
    SPIRIT_ROOTS
)


class SpiritRootFactory:
    """灵根生成工厂类"""

    @staticmethod
    def generate_random() -> Dict:
        """
        随机生成灵根

        Returns:
            包含灵根信息的字典 {
                'quality': 灵根品质,
                'type': 灵根类型,
                'value': 灵根值,
                'purity': 灵根纯度
            }
        """
        # 1. 根据权重随机选择灵根品质
        qualities = [item[0] for item in SPIRIT_ROOT_WEIGHTS]
        weights = [item[1] for item in SPIRIT_ROOT_WEIGHTS]

        quality = random.choices(qualities, weights=weights, k=1)[0]

        # 2. 根据品质配置生成灵根值
        quality_config = SPIRIT_ROOT_QUALITIES[quality]
        value_range = quality_config['value_range']
        spirit_value = random.randint(value_range[0], value_range[1])

        # 3. 根据品质选择灵根类型
        spirit_type = SpiritRootFactory._select_root_type(quality, quality_config)

        # 4. 生成灵根纯度 (50-100%)
        # 品质越高，纯度基础值越高
        purity_base = {
            "废灵根": 50,
            "杂灵根": 55,
            "双灵根": 60,
            "单灵根": 70,
            "变异灵根": 75,
            "天灵根": 85
        }
        base = purity_base.get(quality, 50)
        purity = random.randint(base, min(100, base + 15))

        return {
            'quality': quality,
            'type': spirit_type,
            'value': spirit_value,
            'purity': purity
        }

    @staticmethod
    def _select_root_type(quality: str, quality_config: Dict) -> str:
        """
        根据品质选择灵根类型

        Args:
            quality: 灵根品质
            quality_config: 品质配置

        Returns:
            灵根类型字符串
        """
        # 获取五行灵根和变异灵根列表
        basic_roots = ['金', '木', '水', '火', '土']
        mutation_roots = ['风', '雷', '冰', '光', '暗']
        special_roots = ['混沌', '时间', '空间']

        if quality == "废灵根":
            # 废灵根：随机一个五行
            return random.choice(basic_roots)

        elif quality == "杂灵根":
            # 杂灵根：3-5种五行属性混杂
            count = random.randint(3, 5)
            selected = random.sample(basic_roots, count)
            return '+'.join(selected)

        elif quality == "双灵根":
            # 双灵根：随机两个五行
            selected = random.sample(basic_roots, 2)
            return '+'.join(selected)

        elif quality == "单灵根":
            # 单灵根：单一五行
            return random.choice(basic_roots)

        elif quality == "变异灵根":
            # 变异灵根：稀有属性
            # 95%概率为常见变异(风雷冰光暗)，5%概率为特殊灵根
            if random.random() < 0.95:
                return random.choice(mutation_roots)
            else:
                return random.choice(special_roots)

        elif quality == "天灵根":
            # 天灵根：99%单一五行纯净，1%特殊灵根
            if random.random() < 0.99:
                return random.choice(basic_roots)
            else:
                # 极小概率出现特殊灵根
                return random.choice(special_roots)

        return "金"  # 默认

    @staticmethod
    def calculate_bonuses(spirit_root: Dict) -> Dict:
        """
        计算灵根带来的各项加成

        Args:
            spirit_root: 灵根信息字典

        Returns:
            加成字典 {
                'cultivation_bonus': 修为加成,
                'combat_bonus': 战斗属性加成,
                'profession_bonus': 职业加成
            }
        """
        quality = spirit_root['quality']
        root_type = spirit_root['type']
        purity = spirit_root['purity']

        bonuses = {
            'cultivation_bonus': 0.0,
            'combat_bonus': {},
            'profession_bonus': {},
            'skill_bonus': 0.0
        }

        # 1. 品质基础加成
        quality_config = SPIRIT_ROOT_QUALITIES.get(quality, {})
        bonuses['cultivation_bonus'] += quality_config.get('cultivation_modifier', 0)
        bonuses['breakthrough_bonus'] = quality_config.get('breakthrough_modifier', 0)

        # 2. 灵根类型加成
        # 对于多灵根(杂灵根、双灵根)，取第一个主要属性
        main_root = root_type.split('+')[0] if '+' in root_type else root_type

        root_config = SPIRIT_ROOTS.get(main_root, {})
        if root_config:
            # 修为加成
            bonuses['cultivation_bonus'] += root_config.get('cultivation_bonus', 0)

            # 战斗加成
            bonuses['combat_bonus'] = root_config.get('combat_bonus', {}).copy()

            # 职业加成
            bonuses['profession_bonus'] = root_config.get('profession_bonus', {}).copy()

            # 技能加成
            bonuses['skill_bonus'] = root_config.get('skill_bonus', 0)

        # 3. 纯度影响 (纯度80%以上有额外倍率)
        purity_multiplier = 1.0
        if purity >= 90:
            purity_multiplier = 2.0
        elif purity >= 80:
            purity_multiplier = 1.5

        # 应用纯度倍率到修为加成
        bonuses['cultivation_bonus'] *= purity_multiplier

        return bonuses

    @staticmethod
    def get_spirit_root_description(spirit_root: Dict) -> str:
        """
        获取灵根描述文本

        Args:
            spirit_root: 灵根信息字典

        Returns:
            灵根描述字符串
        """
        quality = spirit_root['quality']
        root_type = spirit_root['type']

        # 获取主要灵根的描述
        main_root = root_type.split('+')[0] if '+' in root_type else root_type
        root_config = SPIRIT_ROOTS.get(main_root, {})
        description = root_config.get('description', '未知特性')

        # 品质描述
        quality_desc = {
            "废灵根": "几乎无法修炼，需寻找机缘改善",
            "杂灵根": "属性分散，难以专精，但技能学习范围广",
            "双灵根": "平衡型发展，上限较高",
            "单灵根": "专精发展，成就极高",
            "变异灵根": "极其稀有，战斗力强",
            "天灵根": "完美灵根，万年难遇"
        }

        return f"{description}。{quality_desc.get(quality, '')}"
