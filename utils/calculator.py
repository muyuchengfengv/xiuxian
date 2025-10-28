"""
战斗和修炼计算工具
提供战力、伤害、修为等各类数值计算
"""

from typing import Optional, Dict
from ..models.player_model import Player
from ..models.skill_model import Skill
from .constants import (
    REALMS,
    BASE_CULTIVATION_GAIN,
    BASE_BREAKTHROUGH_RATE,
    SPIRIT_ROOTS,
    SPIRIT_ROOT_QUALITIES
)
from ..core.spirit_root import SpiritRootFactory


class CombatCalculator:
    """战斗计算器类"""

    @staticmethod
    def calculate_power(player: Player, equipment_score: int = 0) -> int:
        """
        计算玩家战力

        战力公式（指数增长）：
        - 境界战力 = 基础战力 × 2^(境界序号-1) × (1 + 小境界加成)
        - 属性战力 = 属性总和 × 境界倍率 × 5
        - 总战力 = 境界战力 + 属性战力 + 装备评分

        这样每提升一个大境界，战力翻倍！
        例如：炼气期1000 → 筑基期2000 → 金丹期4000 → 元婴期8000

        Args:
            player: 玩家对象
            equipment_score: 装备评分(默认0)

        Returns:
            战力值
        """
        # 1. 获取境界配置
        realm_config = REALMS.get(player.realm, REALMS["炼气期"])
        realm_index = realm_config["index"]
        realm_level = player.realm_level  # 1-4

        # 2. 境界倍率（指数增长）
        # 炼气期(1) = 2^0 = 1倍
        # 筑基期(2) = 2^1 = 2倍
        # 金丹期(3) = 2^2 = 4倍
        # 元婴期(4) = 2^3 = 8倍
        # 以此类推...
        realm_multiplier = 2 ** (realm_index - 1)

        # 3. 小境界加成（0%-30%，每个小境界+10%）
        level_bonus = (realm_level - 1) * 0.1

        # 4. 境界战力
        base_realm_power = 1000  # 基础战力
        realm_power = base_realm_power * realm_multiplier * (1 + level_bonus)

        # 5. 属性总和
        total_attributes = (
            player.constitution +
            player.spiritual_power +
            player.comprehension +
            player.luck +
            player.root_bone
        )

        # 6. 属性战力（属性也随境界指数增长）
        attribute_power = total_attributes * realm_multiplier * 5

        # 7. 计算总战力
        total_power = realm_power + attribute_power + equipment_score

        return int(total_power)

    @staticmethod
    def calculate_damage(
        attacker: Player,
        defender: Player,
        skill: Optional[Skill] = None,
        skill_multiplier: float = 1.0
    ) -> int:
        """
        计算伤害

        伤害计算考虑：攻击力、防御力、技能加成、灵根加成、随机波动

        Args:
            attacker: 攻击者
            defender: 防御者
            skill: 使用的技能(可选)
            skill_multiplier: 技能倍率(默认1.0)

        Returns:
            实际伤害值
        """
        import random

        # 1. 基础伤害 = 攻击力 - 防御力 * 0.5
        base_damage = attacker.attack - defender.defense * 0.5

        # 2. 技能加成
        if skill:
            skill_damage = skill.get_actual_damage(attacker.attack)
            base_damage += skill_damage

            # 检查灵根与技能元素匹配
            if skill.element and skill.element == attacker.spirit_root_type:
                # 同属性技能获得灵根加成
                root_config = SPIRIT_ROOTS.get(attacker.spirit_root_type, {})
                skill_bonus = root_config.get('skill_bonus', 0)
                base_damage *= (1 + skill_bonus)

        # 3. 应用技能倍率
        base_damage *= skill_multiplier

        # 4. 境界压制
        attacker_realm_index = REALMS.get(attacker.realm, REALMS["炼气期"])["index"]
        defender_realm_index = REALMS.get(defender.realm, REALMS["炼气期"])["index"]

        realm_diff = attacker_realm_index - defender_realm_index
        if realm_diff > 0:
            # 攻击者境界高，伤害增加
            base_damage *= (1 + realm_diff * 0.1)  # 每高一个境界+10%伤害
        elif realm_diff < 0:
            # 攻击者境界低，伤害减少
            base_damage *= (1 + realm_diff * 0.05)  # 每低一个境界-5%伤害

        # 5. 随机波动 (90%-110%)
        damage = base_damage * random.uniform(0.9, 1.1)

        # 6. 最小伤害为1
        return max(1, int(damage))

    @staticmethod
    def calculate_cultivation_gain(player: Player) -> int:
        """
        计算修炼获得的修为

        考虑因素：
        - 基础修为
        - 灵根加成
        - 悟性加成
        - 境界影响

        Args:
            player: 玩家对象

        Returns:
            获得的修为值
        """
        # 1. 基础修为
        base_gain = BASE_CULTIVATION_GAIN

        # 2. 灵根加成
        spirit_root_bonus = 0.0
        if player.spirit_root_type and player.spirit_root_quality:
            # 灵根类型加成
            root_config = SPIRIT_ROOTS.get(player.spirit_root_type, {})
            spirit_root_bonus += root_config.get('cultivation_bonus', 0)

            # 灵根品质加成
            quality_config = SPIRIT_ROOT_QUALITIES.get(player.spirit_root_quality, {})
            spirit_root_bonus += quality_config.get('cultivation_modifier', 0)

            # 灵根纯度加成
            purity_multiplier = 1.0
            if player.spirit_root_purity >= 90:
                purity_multiplier = 2.0
            elif player.spirit_root_purity >= 80:
                purity_multiplier = 1.5

            spirit_root_bonus *= purity_multiplier

        # 3. 悟性加成 (每点悟性+2%修炼速度)
        comprehension_bonus = player.comprehension * 0.02

        # 4. 境界影响 (境界越高，基础修为获取越多)
        realm_config = REALMS.get(player.realm, REALMS["炼气期"])
        realm_multiplier = 1.0 + realm_config["index"] * 0.5

        # 5. 计算总修为
        total_gain = base_gain * (1 + spirit_root_bonus + comprehension_bonus) * realm_multiplier

        return int(total_gain)

    @staticmethod
    def get_breakthrough_success_rate(player: Player) -> float:
        """
        计算突破成功率

        考虑因素：
        - 基础成功率
        - 幸运加成
        - 灵根品质加成
        - 境界难度

        Args:
            player: 玩家对象

        Returns:
            突破成功率 (0.0-1.0)
        """
        # 1. 基础成功率
        base_rate = BASE_BREAKTHROUGH_RATE

        # 2. 幸运加成 (每点幸运+1%成功率)
        luck_bonus = player.luck * 0.01

        # 3. 灵根品质加成
        spirit_bonus = 0.0
        if player.spirit_root_quality:
            quality_config = SPIRIT_ROOT_QUALITIES.get(player.spirit_root_quality, {})
            spirit_bonus = quality_config.get('breakthrough_modifier', 0)

        # 4. 境界难度 (境界越高,突破越难)
        realm_config = REALMS.get(player.realm, REALMS["炼气期"])
        realm_penalty = realm_config["index"] * 0.05  # 每个境界-5%成功率

        # 5. 小境界影响
        level_penalty = (player.realm_level - 1) * 0.02  # 每个小境界-2%成功率

        # 6. 计算总成功率
        total_rate = base_rate + luck_bonus + spirit_bonus - realm_penalty - level_penalty

        # 限制在10%-95%之间
        return max(0.1, min(0.95, total_rate))

    @staticmethod
    def calculate_breakthrough_rate(player: Player) -> tuple[float, Dict]:
        """
        计算突破成功率（详细信息版本）

        Args:
            player: 玩家对象

        Returns:
            (成功率, 影响因素字典)
        """
        # 基础成功率
        base_rate = BASE_BREAKTHROUGH_RATE

        # 获取当前境界配置
        realm_config = REALMS.get(player.realm, REALMS["炼气期"])
        realm_index = realm_config["index"]

        # 1. 境界等级影响 - 等级越高成功率越低
        level_penalty = (player.realm_level - 1) * 0.05  # 每级降低5%

        # 2. 灵根品质加成
        breakthrough_bonus = 0.0
        if player.spirit_root_quality:
            quality_config = SPIRIT_ROOT_QUALITIES.get(player.spirit_root_quality, {})
            breakthrough_bonus = quality_config.get('breakthrough_modifier', 0)

        # 3. 境界加成 - 高境界基础成功率更低
        realm_penalty = realm_index * 0.1  # 每个大境界降低10%

        # 4. 灵根纯度影响
        purity_bonus = 0
        if player.spirit_root_purity >= 90:
            purity_bonus = 0.15  # 纯度90%以上+15%
        elif player.spirit_root_purity >= 80:
            purity_bonus = 0.10  # 纯度80%以上+10%
        elif player.spirit_root_purity >= 70:
            purity_bonus = 0.05  # 纯度70%以上+5%

        # 5. 境界等级修正（防止过低等级突破）
        if player.realm_level < 3 and realm_index >= 3:  # 筑基期以下3级内
            level_penalty *= 1.5  # 额外降低成功率

        # 计算最终成功率
        final_rate = base_rate - level_penalty - realm_penalty + breakthrough_bonus + purity_bonus

        # 确保成功率在合理范围内 (5% - 95%)
        final_rate = max(0.05, min(0.95, final_rate))

        # 影响因素详情
        factors = {
            'base_rate': f"{base_rate:.0%}",
            'level_penalty': f"-{level_penalty:.0%}",
            'realm_penalty': f"-{realm_penalty:.0%}",
            'spirit_bonus': f"+{breakthrough_bonus:.0%}",
            'purity_bonus': f"+{purity_bonus:.0%}" if purity_bonus > 0 else "0%",
            'final_rate': f"{final_rate:.1%}"
        }

        return final_rate, factors

    @staticmethod
    def calculate_equipment_score(equipment_list: list) -> int:
        """
        计算装备评分

        Args:
            equipment_list: 装备列表

        Returns:
            装备评分
        """
        if not equipment_list:
            return 0

        total_score = 0
        for equip in equipment_list:
            if not equip.is_equipped:
                continue

            # 基础评分 = 攻击力 + 防御力 + 生命加成/10 + 法力加成/10
            base_score = (
                equip.get_total_attack() +
                equip.get_total_defense() +
                equip.hp_bonus // 10 +
                equip.mp_bonus // 10
            )

            # 品质加成
            from .constants import EQUIPMENT_QUALITY_MULTIPLIER
            quality_multiplier = EQUIPMENT_QUALITY_MULTIPLIER.get(equip.quality, 1.0)

            equip_score = base_score * quality_multiplier
            total_score += int(equip_score)

        return total_score

    @staticmethod
    def calculate_critical_hit(base_damage: int, luck: int) -> tuple[int, bool]:
        """
        计算暴击

        Args:
            base_damage: 基础伤害
            luck: 幸运值

        Returns:
            (最终伤害, 是否暴击)
        """
        import random

        # 暴击率 = 5% + 幸运 * 0.5%
        crit_rate = 0.05 + luck * 0.005

        # 判断是否暴击
        is_crit = random.random() < crit_rate

        if is_crit:
            # 暴击伤害为2倍
            return int(base_damage * 2.0), True
        else:
            return base_damage, False

    @staticmethod
    def calculate_dodge_chance(attacker_speed: int, defender_speed: int) -> bool:
        """
        计算闪避

        Args:
            attacker_speed: 攻击者速度
            defender_speed: 防御者速度

        Returns:
            是否闪避成功
        """
        import random

        # 基础闪避率5%
        base_dodge = 0.05

        # 速度差影响 (防御者速度 - 攻击者速度) * 0.5%
        speed_diff = (defender_speed - attacker_speed) * 0.005

        dodge_rate = base_dodge + speed_diff

        # 限制在0%-30%之间
        dodge_rate = max(0.0, min(0.3, dodge_rate))

        return random.random() < dodge_rate
