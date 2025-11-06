"""
LLM故事生成器
负责使用大模型生成动态探索故事、剧情和奖励
"""

import json
import random
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from astrbot.api import logger

from .database import DatabaseManager
from .player import PlayerManager
from ..models.player_model import Player
from ..models.location_model import Location
from ..utils import XiuxianException


class StoryGenerationError(XiuxianException):
    """故事生成异常"""
    pass


class LLMStoryGenerator:
    """LLM故事生成器"""

    def __init__(self, db: DatabaseManager, player_mgr: PlayerManager, context=None):
        """
        初始化LLM故事生成器

        Args:
            db: 数据库管理器
            player_mgr: 玩家管理器
            context: AstrBot上下文(用于调用LLM)
        """
        self.db = db
        self.player_mgr = player_mgr
        self.context = context

    async def generate_exploration_story(
        self,
        user_id: str,
        location: Location,
        player: Player,
        enable_ai: bool = True
    ) -> Dict[str, Any]:
        """
        生成探索故事

        Args:
            user_id: 用户ID
            location: 当前地点
            player: 玩家对象
            enable_ai: 是否启用AI生成

        Returns:
            故事字典
        """
        # 获取玩家历史
        player_history = await self._get_player_story_history(user_id, limit=5)

        # 获取当前地点的探索历史
        location_history = await self._get_location_story_history(user_id, location.id, limit=3)

        # 检查是否有进行中的故事弧
        story_arc = await self._get_active_story_arc(user_id, location.id)

        if enable_ai and self.context:
            # 使用LLM生成动态故事
            try:
                story = await self._generate_ai_story(
                    user_id, location, player, player_history, location_history, story_arc
                )
            except Exception as e:
                logger.warning(f"LLM故事生成失败，回退到模板: {e}")
                story = await self._generate_template_story(user_id, location, player)
        else:
            # 使用模板生成故事
            story = await self._generate_template_story(user_id, location, player)

        # 保存故事到数据库
        await self._save_story(story)

        return story

    async def _generate_ai_story(
        self,
        user_id: str,
        location: Location,
        player: Player,
        player_history: List[Dict],
        location_history: List[Dict],
        story_arc: Optional[Dict]
    ) -> Dict[str, Any]:
        """使用LLM生成动态故事"""

        # 构建提示词
        prompt = self._build_story_prompt(
            location, player, player_history, location_history, story_arc
        )

        # 调用LLM
        try:
            # 使用AstrBot的Provider API获取响应
            if self.context and hasattr(self.context, 'get_using_provider'):
                # 获取当前使用的大语言模型提供商
                provider = self.context.get_using_provider()

                # 调用text_chat方法
                llm_response = await provider.text_chat(
                    prompt=prompt,
                    session_id=f"{user_id}_exploration_{uuid.uuid4().hex[:8]}",
                    contexts=[],  # 探索故事不需要历史上下文
                    system_prompt="你是一个修仙世界的故事大师，擅长创作充满想象力和趣味性的修仙探索故事。请严格按照JSON格式返回结果。重要：每次请求都是独立的新事件，不要引用或关联之前的任何事件内容。"
                )

                # 获取响应文本
                if hasattr(llm_response, 'completion_text'):
                    response_text = llm_response.completion_text
                    story_data = self._parse_llm_response(response_text)
                else:
                    raise Exception("LLM响应格式错误")
            else:
                raise Exception("LLM Provider不可用")
        except Exception as e:
            logger.error(f"调用LLM失败: {e}")
            raise StoryGenerationError(f"LLM调用失败: {e}")

        # 生成故事ID
        story_id = str(uuid.uuid4())

        # 构建故事对象
        story = {
            'id': story_id,
            'user_id': user_id,
            'location_id': location.id,
            'story_type': story_data.get('story_type', 'exploration'),
            'story_title': story_data.get('title', '神秘事件'),
            'story_content': story_data.get('content', ''),
            'choices': json.dumps(story_data.get('choices', []), ensure_ascii=False),
            'has_choice': len(story_data.get('choices', [])) > 0,
            'rewards': json.dumps(story_data.get('rewards', {}), ensure_ascii=False),
            'consequences': json.dumps(story_data.get('consequences', {}), ensure_ascii=False),
            'story_arc_id': story_data.get('story_arc_id'),
            'is_completed': 0,
            'created_at': datetime.now().isoformat()
        }

        return story

    def _build_story_prompt(
        self,
        location: Location,
        player: Player,
        player_history: List[Dict],
        location_history: List[Dict],
        story_arc: Optional[Dict]
    ) -> str:
        """构建LLM提示词"""

        # 玩家信息
        player_info = f"""
玩家信息：
- 姓名：{player.name}
- 境界：{player.realm} {self._realm_level_name(player.realm_level)}
- 修为：{player.cultivation}
- 灵根：{player.spirit_root_quality or '未知'}{player.spirit_root_type or ''}灵根
- 攻击：{player.attack} | 防御：{player.defense}
- 生命：{player.hp}/{player.max_hp}
- 幸运：{player.luck}
"""

        # 地点信息
        location_info = f"""
当前地点：
- 名称：{location.name}
- 描述：{location.description}
- 危险等级：{location.danger_level}/10
- 灵气浓度：{location.spirit_energy_density}%
- 地区类型：{location.region_type}
"""

        # 历史信息
        history_text = ""
        if player_history:
            history_text = "\n玩家最近的探索经历：\n"
            for i, h in enumerate(player_history[-3:], 1):
                history_text += f"{i}. {h.get('story_title', '未知事件')}\n"

        # 故事弧信息
        arc_text = ""
        if story_arc:
            arc_text = f"\n当前进行中的故事线：{story_arc.get('story_arc_id')} (第{story_arc.get('current_chapter')}/{story_arc.get('total_chapters')}章)\n"

        prompt = f"""你是一个修仙世界的故事大师，请为玩家生成一个精彩的探索事件。

{player_info}

{location_info}

{history_text}

{arc_text}

请生成一个符合当前环境和玩家状态的探索事件，要求：

1. 故事要有趣、富有想象力，符合修仙世界观
2. 难度应该匹配地点危险等级和玩家境界
3. 提供2-4个有意义的选择，每个选择应该有不同的结果
4. 奖励要合理且多样化（不只是灵石和修为，可以包括特殊物品、技能、声望等）
5. 某些选择可能有长期后果或触发后续剧情
6. 如果有进行中的故事线，应该与之关联

请以JSON格式返回：
{{
  "story_type": "事件类型(encounter/treasure/cultivation/mystery/danger等)",
  "title": "事件标题",
  "content": "事件详细描述（200-400字）",
  "choices": [
    {{
      "id": "choice1",
      "text": "选项文本",
      "description": "选项说明",
      "risk_level": "风险等级(low/medium/high)",
      "possible_outcomes": "可能的结果提示"
    }}
  ],
  "rewards": {{
    "base_rewards": {{"spirit_stone": 数量, "cultivation": 数量}},
    "special_rewards": ["特殊奖励描述"],
    "items": [{{"name": "物品名", "quality": "品质", "description": "描述"}}]
  }},
  "consequences": {{
    "reputation_change": "声望变化",
    "story_arc": "是否触发故事线",
    "long_term_effects": ["长期影响列表"]
  }},
  "story_arc_id": "故事线ID(如果是连续剧情)"
}}
"""

        return prompt

    def _realm_level_name(self, level: int) -> str:
        """境界小等级名称"""
        names = {1: '初期', 2: '中期', 3: '后期', 4: '大圆满'}
        return names.get(level, '')

    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """解析LLM响应"""
        try:
            # 尝试提取JSON
            # 查找JSON代码块
            if '```json' in response:
                start = response.find('```json') + 7
                end = response.find('```', start)
                json_str = response[start:end].strip()
            elif '```' in response:
                start = response.find('```') + 3
                end = response.find('```', start)
                json_str = response[start:end].strip()
            else:
                json_str = response.strip()

            story_data = json.loads(json_str)
            return story_data
        except json.JSONDecodeError as e:
            logger.error(f"解析LLM响应失败: {e}\n响应内容: {response}")
            raise StoryGenerationError(f"解析LLM响应失败: {e}")

    async def _generate_template_story(
        self,
        user_id: str,
        location: Location,
        player: Player
    ) -> Dict[str, Any]:
        """使用模板生成故事（备用方案）"""

        # 根据地点危险等级选择事件类型
        event_types = ['resource_find', 'cultivation_insight', 'mysterious_npc']

        if location.danger_level >= 3:
            event_types.extend(['monster_encounter', 'treasure_chest', 'ancient_ruin'])

        if location.danger_level >= 5:
            event_types.extend(['powerful_cultivator', 'secret_realm'])

        event_type = random.choice(event_types)

        # 生成故事ID
        story_id = str(uuid.uuid4())

        # 根据事件类型生成故事
        templates = {
            'resource_find': {
                'title': '发现灵石矿脉',
                'content': f'在{location.name}探索时，你发现了一处被遗忘的灵石矿脉遗迹。',
                'choices': [],
                'rewards': {
                    'spirit_stone': random.randint(100, 300) * location.danger_level
                }
            },
            'cultivation_insight': {
                'title': '修炼顿悟',
                'content': f'{location.name}的灵气让你有所感悟，对修仙之道的理解更深了一层。',
                'choices': [],
                'rewards': {
                    'cultivation': random.randint(200, 500) * (1 + location.spirit_energy_density / 100)
                }
            },
            'mysterious_npc': {
                'title': '神秘修士',
                'content': '你遇到了一位神秘的修士，他似乎有话要说...',
                'choices': [
                    {'id': 'talk', 'text': '上前交谈', 'description': '可能获得情报或任务'},
                    {'id': 'trade', 'text': '进行交易', 'description': '花费灵石购买物品'},
                    {'id': 'ignore', 'text': '离开', 'description': '无事发生'}
                ],
                'rewards': {}
            }
        }

        template = templates.get(event_type, templates['resource_find'])

        story = {
            'id': story_id,
            'user_id': user_id,
            'location_id': location.id,
            'story_type': event_type,
            'story_title': template['title'],
            'story_content': template['content'],
            'choices': json.dumps(template.get('choices', []), ensure_ascii=False),
            'has_choice': len(template.get('choices', [])) > 0,
            'rewards': json.dumps(template.get('rewards', {}), ensure_ascii=False),
            'consequences': json.dumps({}, ensure_ascii=False),
            'is_completed': 0 if template.get('choices') else 1,
            'created_at': datetime.now().isoformat()
        }

        return story

    async def _save_story(self, story: Dict[str, Any]):
        """保存故事到数据库"""
        await self.db.execute("""
            INSERT INTO exploration_stories (
                id, user_id, location_id, story_type, story_title,
                story_content, choices, rewards, consequences,
                is_completed, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            story['id'],
            story['user_id'],
            story['location_id'],
            story['story_type'],
            story['story_title'],
            story['story_content'],
            story['choices'],
            story['rewards'],
            story['consequences'],
            story['is_completed'],
            story['created_at']
        ))

    async def _get_player_story_history(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[Dict]:
        """获取玩家故事历史"""
        cursor = await self.db.execute("""
            SELECT * FROM exploration_stories
            WHERE user_id = ? AND is_completed = 1
            ORDER BY created_at DESC
            LIMIT ?
        """, (user_id, limit))

        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def _get_location_story_history(
        self,
        user_id: str,
        location_id: int,
        limit: int = 5
    ) -> List[Dict]:
        """获取特定地点的故事历史"""
        cursor = await self.db.execute("""
            SELECT * FROM exploration_stories
            WHERE user_id = ? AND location_id = ? AND is_completed = 1
            ORDER BY created_at DESC
            LIMIT ?
        """, (user_id, location_id, limit))

        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def _get_active_story_arc(
        self,
        user_id: str,
        location_id: int
    ) -> Optional[Dict]:
        """获取进行中的故事弧"""
        cursor = await self.db.execute("""
            SELECT * FROM player_story_states
            WHERE user_id = ? AND current_chapter < total_chapters
            ORDER BY last_updated DESC
            LIMIT 1
        """, (user_id,))

        row = await cursor.fetchone()
        if row:
            return dict(row)
        return None

    async def handle_story_choice(
        self,
        user_id: str,
        story_id: str,
        choice_id: str,
        enable_ai: bool = True
    ) -> Dict[str, Any]:
        """
        处理玩家的故事选择

        Args:
            user_id: 用户ID
            story_id: 故事ID
            choice_id: 选择ID
            enable_ai: 是否启用AI生成结果

        Returns:
            选择结果
        """
        # 获取故事
        cursor = await self.db.execute("""
            SELECT * FROM exploration_stories
            WHERE id = ? AND user_id = ?
        """, (story_id, user_id))

        story_row = await cursor.fetchone()
        if not story_row:
            raise StoryGenerationError("故事不存在")

        story = dict(story_row)
        choices = json.loads(story['choices'])

        # 找到选择
        selected_choice = None
        for choice in choices:
            if choice['id'] == choice_id:
                selected_choice = choice
                break

        if not selected_choice:
            raise StoryGenerationError("选择不存在")

        # 生成结果
        if enable_ai and self.context:
            try:
                result = await self._generate_ai_choice_result(
                    user_id, story, selected_choice
                )
            except Exception as e:
                logger.warning(f"LLM结果生成失败，使用默认: {e}")
                result = await self._generate_template_choice_result(
                    user_id, story, selected_choice
                )
        else:
            result = await self._generate_template_choice_result(
                user_id, story, selected_choice
            )

        # 更新故事状态
        await self.db.execute("""
            UPDATE exploration_stories
            SET selected_choice = ?, outcome = ?, is_completed = 1, completed_at = ?
            WHERE id = ?
        """, (
            choice_id,
            json.dumps(result, ensure_ascii=False),
            datetime.now().isoformat(),
            story_id
        ))

        # 记录后果
        if result.get('consequences'):
            await self._record_consequences(user_id, story_id, result['consequences'])

        return result

    async def _generate_ai_choice_result(
        self,
        user_id: str,
        story: Dict,
        choice: Dict
    ) -> Dict[str, Any]:
        """使用LLM生成选择结果"""

        prompt = f"""玩家在探索事件中做出了选择，请生成结果。

事件：{story['story_title']}
描述：{story['story_content']}

玩家选择：{choice['text']}
选择说明：{choice.get('description', '')}

请生成这个选择的结果，包括：
1. 结果描述（100-200字）
2. 具体奖励
3. 可能的后果

以JSON格式返回：
{{
  "outcome_text": "结果描述",
  "rewards": {{
    "spirit_stone": 数量,
    "cultivation": 数量,
    "items": [{{"name": "物品", "quality": "品质"}}],
    "special": ["特殊奖励"]
  }},
  "consequences": {{
    "reputation": 数值变化,
    "relationship": "关系变化",
    "future_events": ["未来可能触发的事件"]
  }},
  "success": true/false
}}
"""

        if self.context and hasattr(self.context, 'get_using_provider'):
            # 获取当前使用的大语言模型提供商
            provider = self.context.get_using_provider()

            # 调用text_chat方法
            llm_response = await provider.text_chat(
                prompt=prompt,
                session_id=user_id,
                contexts=[],
                system_prompt="你是一个修仙世界的故事大师，擅长为玩家的选择生成合理且有趣的结果。请严格按照JSON格式返回结果。"
            )

            # 获取响应文本
            if hasattr(llm_response, 'completion_text'):
                response_text = llm_response.completion_text
                return self._parse_llm_response(response_text)
            else:
                raise Exception("LLM响应格式错误")
        else:
            raise Exception("LLM Provider不可用")

    async def _generate_template_choice_result(
        self,
        user_id: str,
        story: Dict,
        choice: Dict
    ) -> Dict[str, Any]:
        """使用模板生成选择结果"""

        # 简单的随机结果
        success = random.random() > 0.3

        if success:
            rewards = {
                'spirit_stone': random.randint(100, 500),
                'cultivation': random.randint(50, 200)
            }
            outcome_text = f"你的选择很明智！{choice['text']}带来了不错的结果。"
        else:
            rewards = {
                'spirit_stone': random.randint(-100, 50),
                'damage': random.randint(50, 150)
            }
            outcome_text = f"这个选择似乎不太好...{choice['text']}带来了一些麻烦。"

        return {
            'outcome_text': outcome_text,
            'rewards': rewards,
            'consequences': {},
            'success': success
        }

    async def _record_consequences(
        self,
        user_id: str,
        story_id: str,
        consequences: Dict
    ):
        """记录选择后果"""
        for con_type, con_value in consequences.items():
            if con_value:
                await self.db.execute("""
                    INSERT INTO exploration_consequences (
                        user_id, story_id, consequence_type, consequence_value, created_at
                    ) VALUES (?, ?, ?, ?, ?)
                """, (
                    user_id,
                    story_id,
                    con_type,
                    json.dumps(con_value, ensure_ascii=False),
                    datetime.now().isoformat()
                ))

    async def get_player_consequences(self, user_id: str) -> List[Dict]:
        """获取玩家的所有后果"""
        cursor = await self.db.execute("""
            SELECT * FROM exploration_consequences
            WHERE user_id = ? AND (expires_at IS NULL OR expires_at > datetime('now'))
            ORDER BY created_at DESC
        """, (user_id,))

        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
