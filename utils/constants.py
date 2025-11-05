"""
修仙世界常量配置
定义所有游戏数值、境界、灵根等常量
"""

from typing import Dict, List, Tuple

# ==================== 境界配置 ====================
# 每个境界包含: index(序号)、cultivation_required(4个小境界所需修为)、attribute_bonus(属性加成)

REALMS: Dict[str, Dict] = {
    # ===== 凡人阶段 =====
    "炼气期": {
        "index": 0,
        "stage": "凡人",
        "cultivation_required": [100, 300, 600, 1000],  # 初期、中期、后期、大圆满
        "attribute_bonus": {
            "max_hp": 50,
            "max_mp": 50,
            "attack": 5,
            "defense": 5
        }
    },
    "筑基期": {
        "index": 1,
        "stage": "凡人",
        "cultivation_required": [2000, 4000, 7000, 10000],
        "attribute_bonus": {
            "max_hp": 100,
            "max_mp": 100,
            "attack": 10,
            "defense": 10
        }
    },

    # ===== 修士阶段 =====
    "金丹期": {
        "index": 2,
        "stage": "修士",
        "cultivation_required": [15000, 25000, 40000, 60000],
        "attribute_bonus": {
            "max_hp": 200,
            "max_mp": 200,
            "attack": 20,
            "defense": 20
        }
    },
    "元婴期": {
        "index": 3,
        "stage": "修士",
        "cultivation_required": [80000, 120000, 180000, 250000],
        "attribute_bonus": {
            "max_hp": 400,
            "max_mp": 400,
            "attack": 40,
            "defense": 40
        }
    },
    "化神期": {
        "index": 4,
        "stage": "修士",
        "cultivation_required": [350000, 500000, 700000, 1000000],
        "attribute_bonus": {
            "max_hp": 800,
            "max_mp": 800,
            "attack": 80,
            "defense": 80
        }
    },

    # ===== 真人阶段 =====
    "炼虚期": {
        "index": 5,
        "stage": "真人",
        "cultivation_required": [1500000, 2200000, 3000000, 4000000],
        "attribute_bonus": {
            "max_hp": 1500,
            "max_mp": 1500,
            "attack": 150,
            "defense": 150
        }
    },
    "合体期": {
        "index": 6,
        "stage": "真人",
        "cultivation_required": [5500000, 7500000, 10000000, 13000000],
        "attribute_bonus": {
            "max_hp": 3000,
            "max_mp": 3000,
            "attack": 300,
            "defense": 300
        }
    },
    "大乘期": {
        "index": 7,
        "stage": "真人",
        "cultivation_required": [18000000, 25000000, 35000000, 50000000],
        "attribute_bonus": {
            "max_hp": 6000,
            "max_mp": 6000,
            "attack": 600,
            "defense": 600
        }
    },

    # ===== 仙人阶段 =====
    "渡劫期": {
        "index": 8,
        "stage": "仙人",
        "cultivation_required": [70000000, 100000000, 140000000, 200000000],
        "attribute_bonus": {
            "max_hp": 12000,
            "max_mp": 12000,
            "attack": 1200,
            "defense": 1200
        }
    },
    "地仙": {
        "index": 9,
        "stage": "仙人",
        "level_names": ["下品", "中品", "上品", "极品"],  # 仙人阶段使用品级
        "cultivation_required": [300000000, 450000000, 650000000, 1000000000],
        "attribute_bonus": {
            "max_hp": 25000,
            "max_mp": 25000,
            "attack": 2500,
            "defense": 2500
        }
    },
    "天仙": {
        "index": 10,
        "stage": "仙人",
        "level_names": ["下品", "中品", "上品", "极品"],
        "cultivation_required": [1500000000, 2300000000, 3500000000, 5000000000],
        "attribute_bonus": {
            "max_hp": 50000,
            "max_mp": 50000,
            "attack": 5000,
            "defense": 5000
        }
    },
    "金仙": {
        "index": 11,
        "stage": "仙人",
        "level_names": ["下品", "中品", "上品", "极品"],
        "cultivation_required": [8000000000, 12000000000, 18000000000, 30000000000],
        "attribute_bonus": {
            "max_hp": 100000,
            "max_mp": 100000,
            "attack": 10000,
            "defense": 10000
        }
    },

    # ===== 更高境界（可扩展）=====
    "大罗金仙": {
        "index": 12,
        "stage": "至高",
        "level_names": ["初成", "小成", "大成", "圆满"],
        "cultivation_required": [50000000000, 80000000000, 120000000000, 200000000000],
        "attribute_bonus": {
            "max_hp": 200000,
            "max_mp": 200000,
            "attack": 20000,
            "defense": 20000
        }
    },
    "准圣": {
        "index": 13,
        "stage": "至高",
        "level_names": ["初成", "小成", "大成", "圆满"],
        "cultivation_required": [300000000000, 500000000000, 800000000000, 1500000000000],
        "attribute_bonus": {
            "max_hp": 500000,
            "max_mp": 500000,
            "attack": 50000,
            "defense": 50000
        }
    },
    "混元圣人": {
        "index": 14,
        "stage": "至高",
        "level_names": ["初成", "小成", "大成", "圆满"],
        "cultivation_required": [3000000000000, 6000000000000, 12000000000000, 30000000000000],
        "attribute_bonus": {
            "max_hp": 1000000,
            "max_mp": 1000000,
            "attack": 100000,
            "defense": 100000
        }
    },
}

# 境界顺序列表
REALM_ORDER: List[str] = [
    # 凡人阶段
    "炼气期", "筑基期",
    # 修士阶段
    "金丹期", "元婴期", "化神期",
    # 真人阶段
    "炼虚期", "合体期", "大乘期",
    # 仙人阶段
    "渡劫期", "地仙", "天仙", "金仙",
    # 至高境界
    "大罗金仙", "准圣", "混元圣人"
]

# 境界小等级名称（默认）
REALM_LEVEL_NAMES: List[str] = ["初期", "中期", "后期", "大圆满"]

# 仙人境界小等级名称
IMMORTAL_LEVEL_NAMES: List[str] = ["下品", "中品", "上品", "极品"]

# 至高境界小等级名称
SUPREME_LEVEL_NAMES: List[str] = ["初成", "小成", "大成", "圆满"]


# ==================== 灵根配置 ====================

SPIRIT_ROOTS: Dict[str, Dict] = {
    # 五行灵根
    "金": {
        "type": "五行",
        "cultivation_bonus": 0.15,  # 修为获取加成
        "combat_bonus": {
            "attack": 0.30,  # 攻击力加成
            "defense": 0.10
        },
        "profession_bonus": {
            "炼器师": 0.20  # 职业成功率加成
        },
        "skill_bonus": 0.30,  # 对应属性技能威力加成
        "description": "锐利、坚固、肃杀"
    },
    "木": {
        "type": "五行",
        "cultivation_bonus": 0.10,
        "combat_bonus": {
            "hp_regen": 0.50,  # 回复加成
            "defense": 0.20
        },
        "profession_bonus": {
            "炼丹师": 0.20
        },
        "skill_bonus": 0.30,
        "healing_bonus": 0.50,  # 治疗效果加成
        "description": "生机、治愈、韧性"
    },
    "水": {
        "type": "五行",
        "cultivation_bonus": 0.12,
        "combat_bonus": {
            "defense": 0.30,
            "max_mp": 0.20
        },
        "profession_bonus": {
            "阵法师": 0.15
        },
        "skill_bonus": 0.30,
        "description": "柔韧、流动、包容"
    },
    "火": {
        "type": "五行",
        "cultivation_bonus": 0.18,
        "combat_bonus": {
            "attack": 0.40,
            "crit_rate": 0.10  # 暴击率加成
        },
        "profession_bonus": {
            "炼丹师": 0.25,
            "炼器师": 0.15
        },
        "skill_bonus": 0.40,
        "description": "狂暴、炽热、毁灭"
    },
    "土": {
        "type": "五行",
        "cultivation_bonus": 0.08,
        "combat_bonus": {
            "defense": 0.40,
            "max_hp": 0.30
        },
        "profession_bonus": {
            "阵法师": 0.20
        },
        "skill_bonus": 0.30,
        "description": "厚重、稳固、防御"
    },

    # 变异灵根
    "风": {
        "type": "变异",
        "cultivation_bonus": 0.20,
        "combat_bonus": {
            "speed": 0.40,  # 速度加成
            "dodge": 0.30   # 闪避加成
        },
        "profession_bonus": {
            "符箓师": 0.25
        },
        "skill_bonus": 0.35,
        "description": "迅捷、飘逸、锋利"
    },
    "雷": {
        "type": "变异",
        "cultivation_bonus": 0.25,
        "combat_bonus": {
            "attack": 0.50,
            "crit_damage": 0.30  # 暴击伤害加成
        },
        "profession_bonus": {
            "符箓师": 0.30
        },
        "skill_bonus": 0.50,
        "description": "狂暴、毁灭、迅猛"
    },
    "冰": {
        "type": "变异",
        "cultivation_bonus": 0.22,
        "combat_bonus": {
            "attack": 0.35,
            "control_duration": 0.50  # 控制时间加成
        },
        "profession_bonus": {
            "炼器师": 0.20
        },
        "skill_bonus": 0.45,
        "description": "冰冷、凝固、封印"
    },
    "光": {
        "type": "变异",
        "cultivation_bonus": 0.20,
        "combat_bonus": {
            "healing": 0.60,
            "purify": 0.40  # 净化能力
        },
        "profession_bonus": {
            "炼丹师": 0.30
        },
        "skill_bonus": 0.40,
        "description": "神圣、治愈、净化"
    },
    "暗": {
        "type": "变异",
        "cultivation_bonus": 0.18,
        "combat_bonus": {
            "attack": 0.45,
            "debuff_effect": 0.40  # 负面状态效果
        },
        "profession_bonus": {
            "符箓师": 0.25
        },
        "skill_bonus": 0.45,
        "description": "诡异、侵蚀、诅咒",
        "risk": "易入魔"
    },

    # 特殊灵根
    "混沌": {
        "type": "特殊",
        "cultivation_bonus": 0.50,
        "combat_bonus": {
            "all_stats": 0.20  # 全属性加成
        },
        "profession_bonus": {
            "炼丹师": 0.15,
            "炼器师": 0.15,
            "阵法师": 0.15,
            "符箓师": 0.15
        },
        "skill_bonus": 0.20,  # 对所有技能
        "description": "五行混沌，万中无一"
    },
    "时间": {
        "type": "特殊",
        "cultivation_bonus": 1.00,  # 100%加成
        "combat_bonus": {
            "all_stats": 0.30
        },
        "profession_bonus": {},
        "skill_bonus": 0.50,
        "description": "传说级，可操控时间"
    },
    "空间": {
        "type": "特殊",
        "cultivation_bonus": 1.00,
        "combat_bonus": {
            "dodge": 0.50,
            "all_stats": 0.30
        },
        "profession_bonus": {
            "阵法师": 2.00  # 200%加成
        },
        "skill_bonus": 0.50,
        "description": "传说级，可操控空间"
    }
}


# ==================== 灵根品质配置 ====================

# 灵根品质权重 (品质名, 权重)
SPIRIT_ROOT_WEIGHTS: List[Tuple[str, float]] = [
    ("废灵根", 0.05),
    ("杂灵根", 0.35),
    ("双灵根", 0.40),
    ("单灵根", 0.15),
    ("变异灵根", 0.04),
    ("天灵根", 0.01)
]

# 灵根品质配置
SPIRIT_ROOT_QUALITIES: Dict[str, Dict] = {
    "废灵根": {
        "value_range": (0, 10),
        "cultivation_modifier": -0.50,  # -50%修为获取
        "breakthrough_modifier": -0.30,  # -30%突破成功率
        "description": "几乎无法修炼"
    },
    "杂灵根": {
        "value_range": (11, 30),
        "cultivation_modifier": -0.20,
        "breakthrough_modifier": -0.10,
        "root_count": (3, 5),  # 拥有3-5种属性
        "description": "修为获取分散，难以专精"
    },
    "双灵根": {
        "value_range": (31, 60),
        "cultivation_modifier": 0.00,
        "breakthrough_modifier": 0.00,
        "root_count": 2,
        "description": "平衡型发展"
    },
    "单灵根": {
        "value_range": (61, 80),
        "cultivation_modifier": 0.20,
        "breakthrough_modifier": 0.10,
        "root_count": 1,
        "description": "专精发展，成就极高"
    },
    "变异灵根": {
        "value_range": (61, 90),
        "cultivation_modifier": 0.25,
        "breakthrough_modifier": 0.15,
        "root_count": 1,
        "is_mutation": True,
        "description": "极其稀有，战斗力强"
    },
    "天灵根": {
        "value_range": (91, 100),
        "cultivation_modifier": 0.50,
        "breakthrough_modifier": 0.30,
        "root_count": 1,
        "description": "完美灵根，万年难遇"
    }
}


# ==================== 装备品质 ====================

EQUIPMENT_QUALITY: List[str] = [
    "凡品",    # 白色
    "灵品",    # 绿色
    "宝品",    # 蓝色
    "仙品",    # 紫色
    "神品",    # 橙色
    "道品",    # 红色
    "混沌品"   # 金色
]

# 装备品质属性倍率
EQUIPMENT_QUALITY_MULTIPLIER: Dict[str, float] = {
    "凡品": 1.0,
    "灵品": 1.5,
    "宝品": 2.0,
    "仙品": 3.0,
    "神品": 5.0,
    "道品": 8.0,
    "混沌品": 12.0
}


# ==================== 技能类型 ====================

SKILL_TYPES: List[str] = [
    "attack",    # 攻击
    "defense",   # 防御
    "support",   # 辅助
    "control"    # 控制
]


# ==================== 初始属性 ====================

# 初始属性范围
INITIAL_ATTRIBUTES: Dict[str, Tuple[int, int]] = {
    "constitution": (10, 20),    # 体质
    "spiritual_power": (10, 20), # 灵力
    "comprehension": (5, 15),    # 悟性
    "luck": (5, 15),            # 幸运
    "root_bone": (5, 15)        # 根骨
}

# 初始战斗属性
INITIAL_COMBAT_STATS: Dict[str, int] = {
    "hp": 100,
    "max_hp": 100,
    "mp": 100,
    "max_mp": 100,
    "attack": 10,
    "defense": 10
}


# ==================== 其他游戏常量 ====================

# 默认修炼冷却时间(秒)
DEFAULT_CULTIVATION_COOLDOWN: int = 3600  # 1小时

# 初始灵石
DEFAULT_INITIAL_SPIRIT_STONE: int = 1000

# 基础修炼获得修为
BASE_CULTIVATION_GAIN: int = 50

# 突破基础成功率
BASE_BREAKTHROUGH_RATE: float = 0.50  # 50%

# 战斗回合上限
MAX_COMBAT_ROUNDS: int = 100

# 属性对战斗数值的影响
ATTRIBUTE_COMBAT_MULTIPLIER: Dict[str, Dict[str, float]] = {
    "constitution": {"max_hp": 50.0},  # 每点体质+50最大生命
    "spiritual_power": {"max_mp": 30.0, "attack": 2.0},  # 每点灵力+30法力+2攻击
    "comprehension": {"cultivation_speed": 0.02},  # 每点悟性+2%修炼速度
    "luck": {"crit_rate": 0.005, "breakthrough_rate": 0.01},  # 每点幸运+0.5%暴击+1%突破
    "root_bone": {"stat_growth": 0.01}  # 每点根骨+1%属性成长
}


# ==================== 职业相关 ====================

PROFESSIONS: List[str] = [
    "炼丹师",
    "炼器师",
    "阵法师",
    "符箓师"
]

# 职业品级
PROFESSION_RANKS: List[int] = list(range(1, 8))  # 1-7品


# ==================== 辅助函数 ====================

def get_realm_by_index(index: int) -> str:
    """通过索引获取境界名称"""
    for realm, config in REALMS.items():
        if config["index"] == index:
            return realm
    return "炼气期"


def get_next_realm(current_realm: str, current_level: int) -> Tuple[str, int]:
    """
    获取下一个境界和等级

    Args:
        current_realm: 当前境界
        current_level: 当前小等级(1-4)

    Returns:
        (下一境界, 下一小等级)
    """
    if current_level < 4:
        return current_realm, current_level + 1

    current_index = REALMS[current_realm]["index"]
    next_index = current_index + 1

    if next_index < len(REALM_ORDER):
        return REALM_ORDER[next_index], 1

    # 已经是最高境界
    return current_realm, 4


def get_cultivation_required(realm: str, level: int) -> int:
    """获取指定境界和小等级所需的修为"""
    if realm not in REALMS:
        return 0
    return REALMS[realm]["cultivation_required"][level - 1]


def get_realm_level_name(realm: str, level: int) -> str:
    """
    获取境界小等级名称

    Args:
        realm: 境界名称
        level: 小等级(1-4)

    Returns:
        小等级名称
    """
    if realm not in REALMS:
        return REALM_LEVEL_NAMES[level - 1]

    # 如果境界配置中指定了level_names，使用指定的
    if "level_names" in REALMS[realm]:
        return REALMS[realm]["level_names"][level - 1]

    # 否则使用默认的
    return REALM_LEVEL_NAMES[level - 1]


def get_realm_stage(realm: str) -> str:
    """
    获取境界所属阶段

    Args:
        realm: 境界名称

    Returns:
        阶段名称
    """
    if realm not in REALMS:
        return "凡人"
    return REALMS[realm].get("stage", "凡人")


def validate_constants():
    """验证常量配置的正确性"""
    # 验证灵根品质权重总和为1
    total_weight = sum(weight for _, weight in SPIRIT_ROOT_WEIGHTS)
    assert abs(total_weight - 1.0) < 0.001, f"灵根品质权重总和应为1.0，当前为{total_weight}"

    # 验证境界配置完整性
    for realm, config in REALMS.items():
        assert "index" in config, f"{realm}缺少index配置"
        assert "cultivation_required" in config, f"{realm}缺少cultivation_required配置"
        assert len(config["cultivation_required"]) == 4, f"{realm}的cultivation_required应包含4个值"
        assert "attribute_bonus" in config, f"{realm}缺少attribute_bonus配置"

    print("常量配置验证通过 ✓")


# 在模块导入时验证常量
if __name__ == "__main__":
    validate_constants()
