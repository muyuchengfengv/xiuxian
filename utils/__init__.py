"""工具函数模块"""

from .exceptions import (
    XiuxianException,
    PlayerNotFoundError,
    InsufficientResourceError,
    CooldownNotReadyError,
    BreakthroughFailedError,
    InvalidRealmError,
    EquipmentNotFoundError,
    SkillNotFoundError,
    InsufficientLevelError,
    InvalidOperationError
)

from .formatter import MessageFormatter

from .calculator import CombatCalculator

from .constants import (
    REALMS,
    REALM_ORDER,
    REALM_LEVEL_NAMES,
    SPIRIT_ROOTS,
    SPIRIT_ROOT_QUALITIES,
    SPIRIT_ROOT_WEIGHTS,
    EQUIPMENT_QUALITY,
    EQUIPMENT_QUALITY_MULTIPLIER,
    SKILL_TYPES,
    INITIAL_ATTRIBUTES,
    INITIAL_COMBAT_STATS,
    DEFAULT_CULTIVATION_COOLDOWN,
    DEFAULT_INITIAL_SPIRIT_STONE,
    BASE_CULTIVATION_GAIN,
    BASE_BREAKTHROUGH_RATE,
    MAX_COMBAT_ROUNDS,
    ATTRIBUTE_COMBAT_MULTIPLIER,
    PROFESSIONS,
    PROFESSION_RANKS,
    get_realm_by_index,
    get_next_realm,
    get_cultivation_required
)

__all__ = [
    # 异常类
    'XiuxianException',
    'PlayerNotFoundError',
    'InsufficientResourceError',
    'CooldownNotReadyError',
    'BreakthroughFailedError',
    'InvalidRealmError',
    'EquipmentNotFoundError',
    'SkillNotFoundError',
    'InsufficientLevelError',
    'InvalidOperationError',

    # 格式化工具
    'MessageFormatter',

    # 计算器
    'CombatCalculator',

    # 常量
    'REALMS',
    'REALM_ORDER',
    'REALM_LEVEL_NAMES',
    'IMMORTAL_LEVEL_NAMES',
    'SUPREME_LEVEL_NAMES',
    'SPIRIT_ROOTS',
    'SPIRIT_ROOT_QUALITIES',
    'SPIRIT_ROOT_WEIGHTS',
    'EQUIPMENT_QUALITY',
    'EQUIPMENT_QUALITY_MULTIPLIER',
    'SKILL_TYPES',
    'INITIAL_ATTRIBUTES',
    'INITIAL_COMBAT_STATS',
    'DEFAULT_CULTIVATION_COOLDOWN',
    'DEFAULT_INITIAL_SPIRIT_STONE',
    'BASE_CULTIVATION_GAIN',
    'BASE_BREAKTHROUGH_RATE',
    'MAX_COMBAT_ROUNDS',
    'ATTRIBUTE_COMBAT_MULTIPLIER',
    'PROFESSIONS',
    'PROFESSION_RANKS',

    # 辅助函数
    'get_realm_by_index',
    'get_next_realm',
    'get_cultivation_required',
    'get_realm_level_name',
    'get_realm_stage',
]
