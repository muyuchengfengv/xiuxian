"""
天劫系统常量定义
"""

# 天劫类型配置
TRIBULATION_TYPES = {
    "thunder": {
        "name": "雷劫",
        "emoji": "⚡",
        "description": "天降雷霆，考验肉身强度",
        "damage_multiplier": 1.0,
        "special_effect": "对防御力低的修仙者伤害更高"
    },
    "fire": {
        "name": "火劫",
        "emoji": "🔥",
        "description": "业火焚身，考验真气纯度",
        "damage_multiplier": 1.1,
        "special_effect": "持续灼烧伤害"
    },
    "heart_demon": {
        "name": "心魔劫",
        "emoji": "👹",
        "description": "心魔侵扰，考验道心坚定",
        "damage_multiplier": 0.8,
        "special_effect": "对意志力弱的修仙者伤害更高"
    },
    "wind": {
        "name": "风劫",
        "emoji": "💨",
        "description": "罡风刮骨，考验元神稳固",
        "damage_multiplier": 0.9,
        "special_effect": "速度快，��以闪避"
    },
    "ice": {
        "name": "冰劫",
        "emoji": "❄️",
        "description": "寒冰冻魂，考验真气温度",
        "damage_multiplier": 0.95,
        "special_effect": "降低恢复速度"
    },
    "mixed": {
        "name": "混合天劫",
        "emoji": "🌀",
        "description": "多种天劫混合，难度极高",
        "damage_multiplier": 1.3,
        "special_effect": "包含所有劫难特性"
    }
}

# 境界对应的天劫配置
REALM_TRIBULATIONS = {
    # ===== 凡人阶段 =====
    "炼气期": {
        "has_tribulation": False,  # 炼气期无天劫
        "tribulation_level": 0
    },
    "筑基期": {
        "has_tribulation": True,
        "tribulation_level": 1,
        "types": ["thunder"],
        "base_damage": 100,
        "waves": 3,
        "difficulty": "easy"
    },

    # ===== 修士阶段 =====
    "金丹期": {
        "has_tribulation": True,
        "tribulation_level": 2,
        "types": ["thunder", "fire"],
        "base_damage": 200,
        "waves": 4,
        "difficulty": "normal"
    },
    "元婴期": {
        "has_tribulation": True,
        "tribulation_level": 3,
        "types": ["thunder", "fire", "wind"],
        "base_damage": 400,
        "waves": 5,
        "difficulty": "normal"
    },
    "化神期": {
        "has_tribulation": True,
        "tribulation_level": 4,
        "types": ["thunder", "fire", "wind", "heart_demon"],
        "base_damage": 800,
        "waves": 6,
        "difficulty": "hard"
    },

    # ===== 真人阶段 =====
    "炼虚期": {
        "has_tribulation": True,
        "tribulation_level": 5,
        "types": ["thunder", "fire", "wind", "ice", "heart_demon"],
        "base_damage": 1600,
        "waves": 7,
        "difficulty": "hard"
    },
    "合体期": {
        "has_tribulation": True,
        "tribulation_level": 6,
        "types": ["mixed"],
        "base_damage": 3200,
        "waves": 8,
        "difficulty": "hard"
    },
    "大乘期": {
        "has_tribulation": True,
        "tribulation_level": 7,
        "types": ["mixed"],
        "base_damage": 6400,
        "waves": 9,
        "difficulty": "hell"
    },

    # ===== 仙人阶段 =====
    "渡劫期": {
        "has_tribulation": True,
        "tribulation_level": 8,
        "types": ["mixed"],
        "base_damage": 12800,
        "waves": 9,
        "difficulty": "hell"
    },
    "地仙": {
        "has_tribulation": False,  # 地仙不需要渡劫，已成功渡过
        "tribulation_level": 0
    },
    "天仙": {
        "has_tribulation": False,  # 天仙不需要渡劫，已成功渡过
        "tribulation_level": 0
    },
    "金仙": {
        "has_tribulation": False,  # 金仙不需要渡劫，已成功渡过
        "tribulation_level": 0
    },

    # ===== 至高境界 =====
    "大罗金仙": {
        "has_tribulation": False,  # 大罗金仙不需要渡劫
        "tribulation_level": 0
    },
    "准圣": {
        "has_tribulation": False,  # 准圣不需要渡劫
        "tribulation_level": 0
    },
    "混元圣人": {
        "has_tribulation": False,  # 混元圣人不需要渡劫
        "tribulation_level": 0
    },
}

# 难度系数
DIFFICULTY_MULTIPLIERS = {
    "easy": 0.7,
    "normal": 1.0,
    "hard": 1.5,
    "hell": 2.0
}

# 渡劫成功奖励
TRIBULATION_REWARDS = {
    "cultivation_boost": 0.1,  # 修为提升10%
    "attribute_boost": 5,      # 属性提升5点
    "special_item_chance": 0.2  # 20%获得特殊物品
}

# 渡劫失败惩罚
TRIBULATION_PENALTIES = {
    "cultivation_loss": 0.3,   # 损失30%修为
    "realm_drop": False,       # 不掉境界
    "injury_duration": 3600    # 受伤时间（秒）
}

# 伤害减免计算因素
DAMAGE_REDUCTION_FACTORS = {
    "defense": 0.001,          # 防御力转化率
    "spirit_root": 0.05,       # 灵根加成
    "method_bonus": 0.1,       # 功法加成
    "equipment_bonus": 0.15,   # 装备加成
    "sect_bonus": 0.05         # 宗门加成
}

# 每波伤害递增率
WAVE_DAMAGE_INCREASE = 1.2  # 每波伤害增加20%

# 自动渡劫设置
AUTO_TRIBULATION = {
    "enabled": True,           # 是否启用自动渡劫
    "min_hp_percentage": 0.8,  # 最低生命百分比要求
    "preparation_time": 60     # 准备时间（秒）
}