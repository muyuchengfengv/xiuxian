"""
功法系统常量定义
"""

# 功法类型
METHOD_TYPES = {
    "attack": {
        "name": "攻击功法",
        "description": "提升攻击力和战斗能力的功法",
        "slots": ["active_1", "active_2"]
    },
    "defense": {
        "name": "防御功法",
        "description": "提升防御力和生存能力的功法",
        "slots": ["passive_1", "passive_2"]
    },
    "speed": {
        "name": "速度功法",
        "description": "提升速度和闪避能力的功法",
        "slots": ["passive_1", "passive_2"]
    },
    "auxiliary": {
        "name": "辅助功法",
        "description": "提供各种辅助效果的功法",
        "slots": ["passive_1", "passive_2"]
    }
}

# 元素属性
ELEMENT_TYPES = {
    "fire": {"name": "火系", "emoji": "🔥", "strong_against": ["metal", "wood"], "weak_against": ["water"]},
    "water": {"name": "水系", "emoji": "💧", "strong_against": ["fire", "earth"], "weak_against": ["wood"]},
    "earth": {"name": "土系", "emoji": "🪨", "strong_against": ["water", "thunder"], "weak_against": ["wood"]},
    "metal": {"name": "金系", "emoji": "⚔️", "strong_against": ["wood", "ice"], "weak_against": ["fire"]},
    "wood": {"name": "木系", "emoji": "🌿", "strong_against": ["earth", "water"], "weak_against": ["metal"]},
    "thunder": {"name": "雷系", "emoji": "⚡", "strong_against": ["ice", "fire"], "weak_against": ["earth"]},
    "ice": {"name": "冰系", "emoji": "❄️", "strong_against": ["metal", "wood"], "weak_against": ["thunder"]},
    "none": {"name": "无属性", "emoji": "⚪", "strong_against": [], "weak_against": []}
}

# 修炼类型
CULTIVATION_TYPES = {
    "sword_refining": {"name": "剑修", "description": "专修剑法的修仙者"},
    "body_refining": {"name": "体修", "description": "专修肉身的修仙者"},
    "qi_refining": {"name": "气修", "description": "专修真气的修仙者"},
    "element_refining": {"name": "元素修", "description": "专修元素的修仙者"},
    "demon_refining": {"name": "魔修", "description": "修炼魔功的修仙者"},
    "buddha_refining": {"name": "佛修", "description": "修炼佛法的修仙者"}
}

# 功法品质和等级
METHOD_QUALITIES = [
    ("凡品", "⚪", 1),
    ("灵品", "🔵", 2),
    ("宝品", "🟣", 3),
    ("仙品", "🟡", 4),
    ("神品", "🔴", 5),
    ("道品", "🌟", 6),
    ("天地品", "⚫", 7)
]

# 熟练度等级
MASTERY_LEVELS = [
    (0, "入门", 0),
    (1, "初学", 200),
    (2, "掌握", 400),
    (3, "精通", 600),
    (4, "大成", 800),
    (5, "圆满", 1000)
]

# 功法来源
METHOD_SOURCES = {
    "sect_reward": {
        "name": "门派赐予",
        "description": "宗门发放给门人的功法",
        "probability": 0.3
    },
    "secret_realm": {
        "name": "秘境探索",
        "description": "在秘境中发现的古老功法",
        "probability": 0.2
    },
    "dungeon": {
        "name": "副本掉落",
        "description": "通过挑战副本获得的功法",
        "probability": 0.2
    },
    "purchase": {
        "name": "购买获得",
        "description": "从商店或其他玩家处购买",
        "probability": 0.15
    },
    "gift": {
        "name": "赠送获得",
        "description": "其他玩家赠送的功法",
        "probability": 0.1
    },
    "inheritance": {
        "name": "传���获得",
        "description": "师门传承或特殊机缘获得",
        "probability": 0.05
    }
}

# 装备槽位
EQUIPMENT_SLOTS = {
    "active_1": {"name": "主动功法1", "type": "active", "description": "主动释放的功法"},
    "active_2": {"name": "主动功法2", "type": "active", "description": "主动释放的功法"},
    "passive_1": {"name": "被动功法1", "type": "passive", "description": "自动生效的功法"},
    "passive_2": {"name": "被动功法2", "type": "passive", "description": "自动生效的功法"}
}

# 功法模板库
METHOD_TEMPLATES = {
    "attack": [
        {
            "name": "基础剑诀",
            "description": "最基础的剑法功法，适合初学者修炼",
            "element_type": "none",
            "quality": "凡品",
            "grade": 1,
            "min_realm": "炼气期",
            "min_realm_level": 1,
            "attack_bonus": 5,
            "cultivation_speed_bonus": 0.05,
            "special_effects": ["基础剑气"]
        },
        {
            "name": "烈火诀",
            "description": "修炼火系真气的功法，攻击力强但消耗也大",
            "element_type": "fire",
            "quality": "灵品",
            "grade": 2,
            "min_realm": "筑基期",
            "min_realm_level": 1,
            "attack_bonus": 15,
            "mp_bonus": 10,
            "cultivation_speed_bonus": 0.08,
            "special_effects": ["火焰伤害", "燃烧效果"]
        },
        {
            "name": "九转玄功",
            "description": "上古功法，修炼后可大幅提升综合实力",
            "element_type": "none",
            "quality": "仙品",
            "grade": 4,
            "min_realm": "元婴期",
            "min_realm_level": 1,
            "attack_bonus": 40,
            "defense_bonus": 20,
            "hp_bonus": 50,
            "cultivation_speed_bonus": 0.15,
            "breakthrough_rate_bonus": 0.05,
            "special_effects": ["肉身强悍", "真气雄浑", "恢复能力"]
        }
    ],
    "defense": [
        {
            "name": "护体真气",
            "description": "凝聚真气护体，提升防御力",
            "element_type": "none",
            "quality": "凡品",
            "grade": 1,
            "min_realm": "炼气期",
            "min_realm_level": 1,
            "defense_bonus": 5,
            "cultivation_speed_bonus": 0.03
        },
        {
            "name": "玄冰护盾",
            "description": "运用冰系真气形成护盾，防御力强",
            "element_type": "ice",
            "quality": "灵品",
            "grade": 2,
            "min_realm": "筑基期",
            "min_realm_level": 1,
            "defense_bonus": 15,
            "hp_bonus": 20,
            "cultivation_speed_bonus": 0.06,
            "special_effects": ["冰霜护盾", "减速敌人"]
        }
    ],
    "speed": [
        {
            "name": "轻身术",
            "description": "减轻身体重量，提升移动速度",
            "element_type": "none",
            "quality": "凡品",
            "grade": 1,
            "min_realm": "炼气期",
            "min_realm_level": 1,
            "speed_bonus": 5,
            "cultivation_speed_bonus": 0.04
        },
        {
            "name": "追风逐电",
            "description": "修炼后速度快如闪电，身法飘逸",
            "element_type": "thunder",
            "quality": "宝品",
            "grade": 3,
            "min_realm": "金丹期",
            "min_realm_level": 1,
            "speed_bonus": 25,
            "cultivation_speed_bonus": 0.12,
            "special_effects": ["雷电加速", "闪避提升"]
        }
    ],
    "auxiliary": [
        {
            "name": "聚气诀",
            "description": "加速真气聚集，提升修炼效率",
            "element_type": "none",
            "quality": "凡品",
            "grade": 1,
            "min_realm": "炼气期",
            "min_realm_level": 1,
            "cultivation_speed_bonus": 0.08,
            "mp_bonus": 5
        },
        {
            "name": "长春功",
            "description": "延年益寿的功法，增强生命力和恢复力",
            "element_type": "wood",
            "quality": "灵品",
            "grade": 2,
            "min_realm": "筑基期",
            "min_realm_level": 1,
            "hp_bonus": 30,
            "cultivation_speed_bonus": 0.1,
            "special_effects": ["生命恢复", "延年益寿"]
        }
    ]
}

# 熟练度增加规则
PROFICIENCY_GAIN = {
    "cultivation": {  # 修炼时获得
        "base_gain": 10,
        "quality_bonus": {
            "凡品": 1.0,
            "灵品": 1.2,
            "宝品": 1.5,
            "仙品": 2.0,
            "神品": 3.0,
            "道品": 5.0,
            "天地品": 10.0
        }
    },
    "combat": {  # 战斗时获得
        "base_gain": 5,
        "victory_bonus": 2.0,
        "defeat_bonus": 0.5
    },
    "breakthrough": {  # 突破时获得
        "base_gain": 50,
        "success_bonus": 2.0,
        "failure_bonus": 1.0
    }
}

# 功法限制
METHOD_LIMITS = {
    "max_equipped": 4,  # 最多装备4门功法
    "max_owned": 20,    # 最多拥有20门功法
    "active_slots": 2,  # 主动功法槽位数量
    "passive_slots": 2  # 被动功法槽位数量
}