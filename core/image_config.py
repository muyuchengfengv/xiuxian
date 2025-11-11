"""
图片配置管理模块
管理图片生成相关的配置选项
"""

import json
from pathlib import Path
from typing import Optional, Dict, Any


class ImageConfig:
    """图片配置管理"""

    # 默认配置
    DEFAULT_CONFIG = {
        # 背景相关
        "enable_background": True,  # 是否启用背景图片
        "background_type": "gradient",  # gradient(渐变) / texture(纹理) / solid(纯色)
        "default_theme": "xiuxian",  # 默认主题
        "gradient_direction": "radial",  # 渐变方向: vertical/horizontal/radial/diagonal
        "gradient_smooth": True,  # 是否使用平滑渐变

        # 效果相关
        "enable_effects": True,  # 是否启用特效（纹理、粒子、光晕等）
        "enable_texture": True,  # 是否启用纹理叠加
        "texture_opacity": 0.15,  # 纹理透明度 (0.0-1.0)
        "enable_particles": True,  # 是否启用粒子效果
        "particle_count": 40,  # 粒子数量
        "enable_glow": True,  # 是否启用光晕效果
        "glow_intensity": 0.2,  # 光晕强度 (0.0-1.0)

        # 质量相关
        "image_quality": "high",  # 图片质量: low/medium/high
        "enable_anti_alias": True,  # 是否启用抗锯齿

        # AI背景相关（可选功能）
        "enable_ai_background": False,  # 是否启用AI背景
        "ai_provider": "local",  # AI服务提供商: local/qwen/stable-diffusion/dalle3
        "ai_api_key": "",  # AI服务API密钥
        "ai_cache_enabled": True,  # 是否启用AI背景缓存
        "ai_trigger_events": [  # 触发AI生成的事件类型
            "breakthrough",  # 突破
            "tribulation",  # 渡劫
            "sect_create",  # 创建宗门
            "epic_equipment"  # 获得史诗装备
        ],
        "ai_generation_timeout": 30,  # AI生成超时时间（秒）
        "ai_fallback_to_gradient": True,  # AI失败时是否降级到渐变背景

        # 性能相关
        "enable_cache": True,  # 是否启用图片缓存
        "cache_max_size": 100,  # 最大缓存数量（张）
        "cache_expire_time": 3600,  # 缓存过期时间（秒）

        # 主题映射（不同类型卡片使用的主题）
        "theme_mapping": {
            "player": "xiuxian",  # 玩家卡片
            "cultivation": "cultivation",  # 修炼卡片
            "breakthrough": "xiuxian",  # 突破卡片
            "combat": "combat",  # 战斗卡片
            "equipment": "treasure",  # 装备卡片
            "alchemy": "alchemy",  # 炼丹卡片
            "sect": "sect",  # 宗门卡片
            "exploration": "nature",  # 探索卡片
        }
    }

    def __init__(self, config_path: Optional[Path] = None):
        """
        初始化配置管理器

        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path
        self.config = self.DEFAULT_CONFIG.copy()

        # 如果提供了配置文件路径，尝试加载
        if config_path and config_path.exists():
            self.load_config(config_path)

    def load_config(self, config_path: Path) -> None:
        """
        从文件加载配置

        Args:
            config_path: 配置文件路径
        """
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                user_config = json.load(f)

            # 合并用户配置和默认配置
            self._merge_config(user_config)

            self.config_path = config_path
        except Exception as e:
            print(f"加载配置文件失败: {e}，使用默认配置")

    def save_config(self, config_path: Optional[Path] = None) -> None:
        """
        保存配置到文件

        Args:
            config_path: 配置文件路径（如果为None则使用初始化时的路径）
        """
        if config_path is None:
            config_path = self.config_path

        if config_path is None:
            raise ValueError("未指定配置文件路径")

        try:
            # 确保目录存在
            config_path.parent.mkdir(parents=True, exist_ok=True)

            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存配置文件失败: {e}")

    def _merge_config(self, user_config: Dict[str, Any]) -> None:
        """
        合并用户配置和默认配置

        Args:
            user_config: 用户配置字典
        """
        for key, value in user_config.items():
            if key in self.config:
                # 如果是字典类型，递归合并
                if isinstance(value, dict) and isinstance(self.config[key], dict):
                    self.config[key].update(value)
                else:
                    self.config[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置项

        Args:
            key: 配置项名称
            default: 默认值

        Returns:
            配置值
        """
        return self.config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """
        设置配置项

        Args:
            key: 配置项名称
            value: 配置值
        """
        self.config[key] = value

    def get_theme_for_card(self, card_type: str) -> str:
        """
        获取指定卡片类型的主题

        Args:
            card_type: 卡片类型

        Returns:
            主题名称
        """
        theme_mapping = self.config.get('theme_mapping', {})
        return theme_mapping.get(card_type, self.config.get('default_theme', 'xiuxian'))

    def should_use_ai_background(self, event_type: str) -> bool:
        """
        判断是否应该使用AI背景

        Args:
            event_type: 事件类型

        Returns:
            是否使用AI背景
        """
        if not self.config.get('enable_ai_background', False):
            return False

        ai_trigger_events = self.config.get('ai_trigger_events', [])
        return event_type in ai_trigger_events

    def get_background_config(self) -> Dict[str, Any]:
        """
        获取背景相关的配置

        Returns:
            背景配置字典
        """
        return {
            'enable_background': self.config.get('enable_background', True),
            'background_type': self.config.get('background_type', 'gradient'),
            'default_theme': self.config.get('default_theme', 'xiuxian'),
            'gradient_direction': self.config.get('gradient_direction', 'radial'),
            'gradient_smooth': self.config.get('gradient_smooth', True),
        }

    def get_effects_config(self) -> Dict[str, Any]:
        """
        获取效果相关的配置

        Returns:
            效果配置字典
        """
        return {
            'enable_effects': self.config.get('enable_effects', True),
            'enable_texture': self.config.get('enable_texture', True),
            'texture_opacity': self.config.get('texture_opacity', 0.15),
            'enable_particles': self.config.get('enable_particles', True),
            'particle_count': self.config.get('particle_count', 40),
            'enable_glow': self.config.get('enable_glow', True),
            'glow_intensity': self.config.get('glow_intensity', 0.2),
        }

    def get_ai_config(self) -> Dict[str, Any]:
        """
        获取AI相关的配置

        Returns:
            AI配置字典
        """
        return {
            'enable_ai_background': self.config.get('enable_ai_background', False),
            'ai_provider': self.config.get('ai_provider', 'local'),
            'ai_api_key': self.config.get('ai_api_key', ''),
            'ai_cache_enabled': self.config.get('ai_cache_enabled', True),
            'ai_trigger_events': self.config.get('ai_trigger_events', []),
            'ai_generation_timeout': self.config.get('ai_generation_timeout', 30),
            'ai_fallback_to_gradient': self.config.get('ai_fallback_to_gradient', True),
        }

    def enable_feature(self, feature: str) -> None:
        """
        启用某个功能

        Args:
            feature: 功能名称（如 'ai_background', 'effects', 'particles' 等）
        """
        key = f"enable_{feature}"
        if key in self.config:
            self.config[key] = True

    def disable_feature(self, feature: str) -> None:
        """
        禁用某个功能

        Args:
            feature: 功能名称（如 'ai_background', 'effects', 'particles' 等）
        """
        key = f"enable_{feature}"
        if key in self.config:
            self.config[key] = False

    def reset_to_default(self) -> None:
        """重置为默认配置"""
        self.config = self.DEFAULT_CONFIG.copy()

    def export_config(self) -> Dict[str, Any]:
        """
        导出当前配置

        Returns:
            配置字典
        """
        return self.config.copy()

    def __repr__(self) -> str:
        """字符串表示"""
        return f"ImageConfig(config_path={self.config_path})"

    def __str__(self) -> str:
        """可读的字符串表示"""
        return json.dumps(self.config, indent=2, ensure_ascii=False)


# 全局配置单例
_global_config: Optional[ImageConfig] = None


def get_global_config() -> ImageConfig:
    """
    获取全局配置单例

    Returns:
        ImageConfig实例
    """
    global _global_config
    if _global_config is None:
        # 尝试从默认位置加载配置
        config_path = Path(__file__).parent.parent / "config" / "image_config.json"
        _global_config = ImageConfig(config_path if config_path.exists() else None)
    return _global_config


def set_global_config(config: ImageConfig) -> None:
    """
    设置全局配置单例

    Args:
        config: ImageConfig实例
    """
    global _global_config
    _global_config = config
