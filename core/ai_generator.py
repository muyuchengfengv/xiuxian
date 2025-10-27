"""
AI基础生成系统
负责使用AI生成修仙世界的内容，如场景、任务、故事等
"""

import json
import random
from typing import Dict, List, Optional, Any
from datetime import datetime
from astrbot.api import logger

from .database import DatabaseManager
from .player import PlayerManager
from ..utils import XiuxianException


class AIGenerationError(XiuxianException):
    """AI生成相关异常"""
    pass


class ContentNotAvailableError(AIGenerationError):
    """内容不可用异常"""
    pass


class AIGenerator:
    """AI内容生成器类"""

    def __init__(self, db: DatabaseManager, player_mgr: PlayerManager):
        """
        初始化AI生成器

        Args:
            db: 数据库管理器
            player_mgr: 玩家管理器
        """
        self.db = db
        self.player_mgr = player_mgr

        # AI生成内容类型
        self.content_types = {
            'scene': '修仙场景',
            'quest': '修仙任务',
            'story': '修仙故事',
            'location': '修仙地点',
            'character': '修仙人物',
            'item': '修仙物品',
            'pill_recipe': '丹药配方',
            'equipment_blueprint': '装备图纸',
            'formation_pattern': '阵法图谱',
            'talisman_pattern': '符箓图案'
        }

        # 预定义的模板库
        self.templates = self._init_templates()

    def _init_templates(self) -> Dict[str, List[Dict]]:
        """初始化预定义模板"""
        return {
            'scene': [
                {
                    'id': 'scene_001',
                    'title': '竹林深处',
                    'description': '一片幽深的竹林，月光透过竹叶洒下斑驳光影',
                    'atmosphere': '宁静、神��',
                    'elements': ['竹子', '月光', '微风'],
                    'level_requirement': 1
                },
                {
                    'id': 'scene_002',
                    'title': '瀑布水帘',
                    'description': '巨大的瀑布如白练般垂下，水声轰鸣如雷',
                    'atmosphere': '壮观、威严',
                    'elements': ['瀑布', '水雾', '岩石'],
                    'level_requirement': 5
                },
                {
                    'id': 'scene_003',
                    'title': '古战场遗迹',
                    'description': '古老的战场上散落着断剑残旗，怨气缭绕不散',
                    'atmosphere': '肃杀、悲凉',
                    'elements': ['断剑', '残旗', '怨气'],
                    'level_requirement': 10
                }
            ],
            'quest': [
                {
                    'id': 'quest_001',
                    'title': '寻找灵草',
                    'description': '听说后山出现了一种罕见的灵草，能够提升修为',
                    'difficulty': '简单',
                    'reward': '修为+100',
                    'requirements': ['等级≥1', '修为≥50'],
                    'level_requirement': 1
                },
                {
                    'id': 'quest_002',
                    'title': '除妖护村',
                    'description': '村庄附近出现了妖兽，需要修仙者出手相助',
                    'difficulty': '中等',
                    'reward': '灵石+50，声望+100',
                    'requirements': ['等级≥3', '战力≥500'],
                    'level_requirement': 3
                },
                {
                    'id': 'quest_003',
                    'title': '���寻秘境',
                    'description': '发现了一处古老秘境的入口，据说内有重宝',
                    'difficulty': '困难',
                    'reward': '随机装备，灵石+200',
                    'requirements': ['等级≥5', '境界≥筑基期'],
                    'level_requirement': 5
                }
            ],
            'story': [
                {
                    'id': 'story_001',
                    'title': '剑仙的传说',
                    'content': '很久以前，有一位剑仙凭一柄凡铁剑斩尽天下妖魔...',
                    'theme': '励志、成长',
                    'moral': '坚持和勇气是修仙路上最重要的品质',
                    'level_requirement': 1
                },
                {
                    'id': 'story_002',
                    'title': '灵根觉醒',
                    'content': '少年在生死关头觉醒了混沌灵根，从此踏上不平凡的修仙之路...',
                    'theme': '觉醒、命运',
                    'moral': '每个人都有自己的道，无需盲从他人',
                    'level_requirement': 1
                }
            ],
            'location': [
                {
                    'id': 'location_001',
                    'name': '青云宗',
                    'type': '宗门',
                    'description': '正道第一大宗，门人遍布天下',
                    'specialties': ['剑法', '阵法', '炼丹'],
                    'reputation': 1000,
                    'level_requirement': 1
                },
                {
                    'id': 'location_002',
                    'name': '黑风寨',
                    'type': '魔道据点',
                    'description': '魔道修仙者的聚集地，经常作乱四方',
                    'specialties': ['魔功', '毒术', '炼尸'],
                    'reputation': -500,
                    'level_requirement': 3
                }
            ],
            'character': [
                {
                    'id': 'character_001',
                    'name': '青云剑仙',
                    'title': '剑仙',
                    'description': '一位白发剑仙，剑法通玄，平易近人',
                    'realm': '元婴期',
                    'personality': '温和、智慧',
                    'special_skills': ['青云剑法', '剑气化形'],
                    'level_requirement': 1
                },
                {
                    'id': 'character_002',
                    'name': '红莲魔女',
                    'title': '魔女',
                    'description': '红衣魔女，容貌绝美但心机深沉',
                    'realm': '金丹期',
                    'personality': '狡黠、野心',
                    'special_skills': ['红莲魔焰', '幻术'],
                    'level_requirement': 1
                }
            ]
        }

    async def generate_content(self, user_id: str, content_type: str, params: Optional[Dict] = None) -> Dict:
        """
        生成AI内容

        Args:
            user_id: 用户ID
            content_type: 内容类型(scene/quest/story/location/character/item)
            params: 生成参数

        Returns:
            生成的内容字典

        Raises:
            ValueError: 内容类型不支持
            ContentNotAvailableError: 内容不可用
        """
        # 检查内容类型
        if content_type not in self.content_types:
            raise ValueError(f"不支持的内容类型: {content_type}")

        # 获取玩家信息
        try:
            player = await self.player_mgr.get_player(user_id)
        except Exception:
            # 如果玩家不存在，使用默认等级
            player = None

        # 根据玩家等级筛选合适的内容
        available_content = self._filter_content_by_level(content_type, player)

        if not available_content:
            raise ContentNotAvailableError(f"当前等级暂无{self.content_types[content_type]}内容")

        # 选择内容（如果有参数则加权选择）
        selected_content = self._select_content(available_content, params)

        # 记录生成历史
        await self._record_generation_history(user_id, content_type, selected_content['id'])

        logger.info(f"为用户 {user_id} 生成AI内容: {content_type} - {selected_content['id']}")

        return selected_content

    def _filter_content_by_level(self, content_type: str, player) -> List[Dict]:
        """根据玩家等级筛选内容"""
        if not player:
            # 新玩家只能看到1级内容
            player_level = 1
        else:
            player_level = self._calculate_player_level(player)

        # 筛选符合等级要求的内容
        available = [
            content for content in self.templates.get(content_type, [])
            if content.get('level_requirement', 1) <= player_level
        ]

        return available

    def _calculate_player_level(self, player) -> int:
        """计算玩家综合等级"""
        # 根据境界和等级计算综合等级
        realm_levels = {
            '炼气期': 1,
            '筑基期': 10,
            '金丹期': 20,
            '元婴期': 30,
            '化神期': 40,
            '炼虚期': 50,
            '合体期': 60,
            '大乘期': 70,
            '渡劫期': 80
        }

        base_level = realm_levels.get(player.realm, 1)
        return base_level + player.realm_level - 1

    def _select_content(self, content_list: List[Dict], params: Optional[Dict]) -> Dict:
        """选择内容"""
        if not content_list:
            return {}

        # 如果有参数，进行加权选择
        if params:
            weights = []
            for content in content_list:
                weight = 1.0

                # 根据参数调整权重
                if params.get('difficulty') == 'easy' and content.get('difficulty') == '简单':
                    weight *= 2.0
                elif params.get('difficulty') == 'hard' and content.get('difficulty') == '困难':
                    weight *= 2.0

                if params.get('theme') and params.get('theme') in content.get('description', ''):
                    weight *= 1.5

                weights.append(weight)

            return random.choices(content_list, weights=weights)[0]

        # 随机选择
        return random.choice(content_list)

    async def _record_generation_history(self, user_id: str, content_type: str, content_id: str):
        """记录生成历史"""
        await self._ensure_history_table()

        await self.db.execute(
            "INSERT INTO ai_generation_history (user_id, content_type, content_id, generated_at) VALUES (?, ?, ?)",
            (user_id, content_type, content_id, datetime.now().isoformat())
        )

    async def _ensure_history_table(self):
        """确保历史记录表存在"""
        sql = """
        CREATE TABLE IF NOT EXISTS ai_generation_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            content_type TEXT NOT NULL,
            content_id TEXT NOT NULL,
            generated_at TEXT NOT NULL
        )
        """
        await self.db.execute(sql)

    async def get_generation_history(self, user_id: str, limit: int = 10) -> List[Dict]:
        """获取用户的生成历史"""
        await self._ensure_history_table()

        results = await self.db.fetchall(
            "SELECT * FROM ai_generation_history WHERE user_id = ? ORDER BY generated_at DESC LIMIT ?",
            (user_id, limit)
        )

        history = []
        for result in results:
            history.append(dict(result))

        return history

    def format_content_for_display(self, content: Dict, content_type: str) -> str:
        """格式化内容用于显示"""
        if content_type == 'scene':
            return self._format_scene_content(content)
        elif content_type == 'quest':
            return self._format_quest_content(content)
        elif content_type == 'story':
            return self._format_story_content(content)
        elif content_type == 'location':
            return self._format_location_content(content)
        elif content_type == 'character':
            return self._format_character_content(content)
        else:
            return str(content)

    def _format_scene_content(self, scene: Dict) -> str:
        """格式化场景内容"""
        lines = [
            f"🌄 {scene['title']}",
            "",
            f"📝 {scene['description']}",
            "",
            f"🎭 氛围：{scene.get('atmosphere', '未知')}",
            f"🔮 包含元素：{', '.join(scene.get('elements', []))}",
            f"📊 等级要求：{scene.get('level_requirement', 1)}"
        ]
        return "\n".join(lines)

    def _format_quest_content(self, quest: Dict) -> str:
        """格式化任务内容"""
        lines = [
            f"📜 任务：{quest['title']}",
            "",
            f"📝 描述：{quest['description']}",
            "",
            f"⚡ 难度：{quest.get('difficulty', '未知')}",
            f"🎁 奖励：{quest.get('reward', '未知')}",
            f"📋 要求：{', '.join(quest.get('requirements', ['无']))}",
            f"📊 等级要求：{quest.get('level_requirement', 1)}"
        ]
        return "\n".join(lines)

    def _format_story_content(self, story: Dict) -> str:
        """格式化故事内容"""
        lines = [
            f"📖 {story['title']}",
            "",
            f"📝 {story['content']}",
            "",
            f"🎭 主题：{story.get('theme', '未知')}",
            f"✨ 寓意：{story.get('moral', '无')}",
            f"📊 等级要求：{story.get('level_requirement', 1)}"
        ]
        return "\n".join(lines)

    def _format_location_content(self, location: Dict) -> str:
        """格式化地点内容"""
        lines = [
            f"🗺️ 地点：{location['name']}",
            "",
            f"📝 描述：{location.get('description', '未知')}",
            f"🏷️ 类型：{location.get('type', '未知')}",
            f"⭐ 特色：{', '.join(location.get('specialties', []))}",
            f"📊 声望：{location.get('reputation', 0)}",
            f"📊 等级要求：{location.get('level_requirement', 1)}"
        ]
        return "\n".join(lines)

    def _format_character_content(self, character: Dict) -> str:
        """格式化人物内容"""
        lines = [
            f"👤 人物：{character['name']}",
            "",
            f"🏷️ 称号：{character.get('title', '未知')}",
            f"📝 描述：{character.get('description', '未知')}",
            f"🎭 性格：{character.get('personality', '未知')}",
            f"⚔️ 境界：{character.get('realm', '未知')}",
            f"✨ 特殊技能：{', '.join(character.get('special_skills', []))}",
            f"📊 等级要求：{character.get('level_requirement', 1)}"
        ]
        return "\n".join(lines)

    async def get_available_content_types(self, user_id: str) -> Dict[str, Any]:
        """获取用户可用的内容类型"""
        try:
            player = await self.player_mgr.get_player(user_id)
            player_level = self._calculate_player_level(player)
        except:
            player_level = 1

        available_types = {}
        for content_type, type_name in self.content_types.items():
            available_content = self._filter_content_by_level(content_type, player)
            available_types[content_type] = {
                'name': type_name,
                'available_count': len(available_content),
                'total_count': len(self.templates.get(content_type, []))
            }

        return available_types

    def get_content_suggestions(self, user_level: int) -> List[str]:
        """获取内容建议"""
        suggestions = []

        if user_level < 5:
            suggestions.extend([
                "推荐查看新手修仙故事",
                "适合完成简单的寻物任务",
                "可以探索低级修炼场景"
            ])
        elif user_level < 15:
            suggestions.extend([
                "推荐尝试中等难度任务",
                "可以探索更危险的场景",
                "适合学习高级修仙技巧"
            ])
        else:
            suggestions.extend([
                "推荐挑战高难度任务",
                "可以探索传说中的秘境",
                "适合面对强大的妖魔"
            ])

        return suggestions