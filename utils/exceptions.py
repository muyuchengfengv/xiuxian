"""
修仙世界自定义异常类
提供统一的错误处理机制
"""


class XiuxianException(Exception):
    """修仙世界基础异常类"""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return self.message


class PlayerNotFoundError(XiuxianException):
    """玩家不存在异常"""

    def __init__(self, user_id: str):
        super().__init__(f"玩家 {user_id} 不存在，请先使用 /修仙 创建角色")


class InsufficientResourceError(XiuxianException):
    """资源不足异常"""

    def __init__(self, resource_type: str, required: int, current: int):
        super().__init__(
            f"{resource_type}不足！需要 {required}，当前只有 {current}"
        )


class CooldownNotReadyError(XiuxianException):
    """冷却未完成异常"""

    def __init__(self, action: str, remaining_time: int):
        hours = remaining_time // 3600
        minutes = (remaining_time % 3600) // 60
        seconds = remaining_time % 60

        time_str = ""
        if hours > 0:
            time_str += f"{hours}小时"
        if minutes > 0:
            time_str += f"{minutes}分钟"
        if seconds > 0 or not time_str:
            time_str += f"{seconds}秒"

        super().__init__(f"{action}冷却中，还需等待 {time_str}")


class BreakthroughFailedError(XiuxianException):
    """突破失败异常"""

    def __init__(self, reason: str = ""):
        message = "突破失败！"
        if reason:
            message += f" {reason}"
        super().__init__(message)


class InvalidRealmError(XiuxianException):
    """境界无效异常"""

    def __init__(self, realm: str):
        super().__init__(f"无效的境界：{realm}")


class EquipmentNotFoundError(XiuxianException):
    """装备不存在异常"""

    def __init__(self, equipment_name: str):
        super().__init__(f"装备 {equipment_name} 不存在")


class SkillNotFoundError(XiuxianException):
    """技能不存在异常"""

    def __init__(self, skill_name: str):
        super().__init__(f"技能 {skill_name} 未学习或不存在")


class InsufficientLevelError(XiuxianException):
    """等级不足异常"""

    def __init__(self, required_realm: str, current_realm: str):
        super().__init__(
            f"境界不足！需要 {required_realm}，当前为 {current_realm}"
        )


class InvalidOperationError(XiuxianException):
    """无效操作异常"""

    def __init__(self, message: str):
        super().__init__(f"无效操作：{message}")
