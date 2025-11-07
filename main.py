"""
AstrBot 修仙世界插件
完整的修仙主题游戏插件,支持修炼、战斗、宗门、AI生成世界
"""

from typing import Dict, Optional, List
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from pathlib import Path

# 导入核心模块
from .core.database import DatabaseManager
from .core.player import PlayerManager
from .core.cultivation import CultivationSystem, RetreatError, AlreadyInRetreatError, NotInRetreatError, RetreatNotFinishedError
from .core.breakthrough import BreakthroughSystem
from .core.combat import CombatSystem, InvalidTargetException, SelfCombatException, CombatException
from .core.equipment import EquipmentSystem
from .core.ai_generator import AIGenerator, AIGenerationError, ContentNotAvailableError
from .core.cultivation_method import CultivationMethodSystem, MethodNotFoundError, MethodNotOwnError, MethodAlreadyEquippedError, SlotOccupiedError
from .core.skill import SkillSystem, SkillError, SkillNotFoundError, InsufficientMPError
from .core.sect import SectSystem, SectError, SectNotFoundError, SectNameExistsError, NotSectMemberError, AlreadyInSectError, InsufficientPermissionError, InsufficientResourceError, SectFullError
from .core.tribulation import TribulationSystem, TribulationError, TribulationNotFoundError, TribulationInProgressError, NoTribulationRequiredError, InsufficientHPError
from .core.world import WorldManager, WorldException, LocationNotFoundError, InvalidMoveError, MoveCooldownError

# 导入职业系统模块
from .core.profession import ProfessionManager, ProfessionError, AlreadyLearnedError, InsufficientLevelError, ProfessionNotFoundError
from .core.alchemy import AlchemySystem, AlchemyError, RecipeNotFoundError
from .core.refining import RefiningSystem, RefiningError, BlueprintNotFoundError
from .core.formation import FormationSystem, FormationError, FormationPatternNotFoundError, FormationAlreadyExistsError
from .core.talisman import TalismanSystem, TalismanError, TalismanPatternNotFoundError
from .core.items import ItemManager, ItemError, ItemNotFoundError, InsufficientItemError, ItemCannotUseError

# 导入坊市系统模块
from .core.market import MarketSystem, MarketError, ItemNotOwnedError, ItemNotTradableError, ListingNotFoundError, InsufficientSpiritStoneError

# 导入灵宠系统模块
from .core.pet import PetSystem, PetError, PetNotFoundError, AlreadyHasPetError

# 导入工具类
from .utils import (
    MessageFormatter,
    PlayerNotFoundError,
    CooldownNotReadyError,
    BreakthroughFailedError,
    XiuxianException,
    CombatCalculator,
    EquipmentNotFoundError,
    InsufficientLevelError
)


@register(
    "修仙世界",
    "AstrBot开发者",
    "完整的修仙主题游戏插件",
    "1.0.0",
    "https://github.com/yourname/astrbot-plugin-xiuxian"
)
class XiuxianPlugin(Star):
    """修仙世界插件主类"""

    def __init__(self, context: Context):
        """初始化插件"""
        super().__init__(context)

        logger.info("=" * 60)
        logger.info("修仙世界插件开始加载...")
        logger.info("=" * 60)

        # 数据库路径
        data_dir = Path(__file__).parent / "data"
        db_path = data_dir / "xiuxian.db"

        # 初始化数据库管理器
        self.db = DatabaseManager(str(db_path))

        # 初始化标志
        self._initialized = False
        self._initializing = False

        # 初始化业务管理器
        self.player_mgr = None  # 在首次使用时初始化
        self.cultivation_sys = None
        self.breakthrough_sys = None
        self.combat_sys = None
        self.equipment_sys = None
        self.method_sys = None
        self.skill_sys = None
        self.sect_sys = None
        self.ai_generator = None
        self.tribulation_sys = None
        self.world_mgr = None

        # 职业系统管理器
        self.profession_mgr = None
        self.alchemy_sys = None
        self.refining_sys = None
        self.formation_sys = None
        self.talisman_sys = None

        # 物品系统管理器
        self.item_mgr = None

        # 坊市系统管理器
        self.market_sys = None

        # 灵宠系统管理器
        self.pet_sys = None

        # 图片生成器
        self.card_generator = None

        # 探索事件临时存储 {user_id: event_data}
        self._exploration_events = {}

        # 探索会话管理 {user_id: session_data}
        self._exploration_sessions = {}

        # 队伍探索事件临时存储 {team_id: event_data}
        self._team_exploration_events = {}

        # 队伍探索会话管理 {team_id: session_data}
        self._team_exploration_sessions = {}

        logger.info("修仙世界插件已加载 (使用懒加载模式)")

    @filter.on_astrbot_loaded()
    async def on_loaded(self):
        """AstrBot加载完成钩子（备用初始化）"""
        logger.info("触发 on_astrbot_loaded 钩子")
        await self._ensure_initialized()

    async def _ensure_initialized(self):
        """确保插件已初始化（懒加载模式）"""
        if self._initialized:
            return True

        if self._initializing:
            # 正在初始化中，等待
            import asyncio
            for _ in range(50):  # 最多等待5秒
                if self._initialized:
                    return True
                await asyncio.sleep(0.1)
            return False

        self._initializing = True

        try:
            logger.info("🔄 开始初始化修仙世界插件...")

            # 初始化数据库
            logger.info("📦 正在初始化数据库...")
            await self.db.init_db()
            logger.info("✓ 数据库初始化完成")

            # 初始化业务管理器
            logger.info("⚙️ 正在初始化核心系统...")
            self.player_mgr = PlayerManager(self.db)
            self.cultivation_sys = CultivationSystem(self.db, self.player_mgr)
            self.breakthrough_sys = BreakthroughSystem(self.db, self.player_mgr)
            self.combat_sys = CombatSystem(self.db, self.player_mgr)
            self.equipment_sys = EquipmentSystem(self.db, self.player_mgr)
            self.method_sys = CultivationMethodSystem(self.db, self.player_mgr)
            self.skill_sys = SkillSystem(self.db, self.player_mgr)
            self.sect_sys = SectSystem(self.db, self.player_mgr)
            self.ai_generator = AIGenerator(self.db, self.player_mgr)
            self.tribulation_sys = TribulationSystem(self.db, self.player_mgr)

            # 获取配置 - 安全访问配置
            enable_ai = True  # 默认启用AI生成
            try:
                # 尝试多种配置访问方式
                if hasattr(self.context, 'config_helper'):
                    enable_ai = self.context.config_helper.get('enable_ai_generation', True)
                elif hasattr(self.context, 'get_config'):
                    enable_ai = self.context.get_config('enable_ai_generation', True)
                elif hasattr(self, 'config'):
                    enable_ai = self.config.get('enable_ai_generation', True)
            except Exception as e:
                logger.warning(f"无法获取配置，使用默认值 enable_ai=True: {e}")

            # 初始化世界管理器（支持LLM故事生成）
            self.world_mgr = WorldManager(self.db, self.player_mgr, self.context, enable_ai)

            # 初始化玩家状态管理器
            from .core.player_status import PlayerStatusManager
            self.status_mgr = PlayerStatusManager(self.db)

            # 初始化探索队伍管理器
            from .core.exploration_team import ExplorationTeamManager
            self.team_mgr = ExplorationTeamManager(self.db)

            logger.info("✓ 核心系统初始化完成")
            logger.info("✓ 技能系统初始化完成")

            # 初始化物品系统（职业系统需要用到）
            logger.info("📦 正在初始化物品系统...")
            self.item_mgr = ItemManager(self.db, self.player_mgr)
            logger.info("✓ 物品系统初始化完成")

            # 初始化职业系统
            logger.info("🔨 正在初始化职业系统...")
            self.profession_mgr = ProfessionManager(self.db, self.player_mgr)
            self.alchemy_sys = AlchemySystem(self.db, self.player_mgr, self.profession_mgr, self.item_mgr)
            self.refining_sys = RefiningSystem(self.db, self.player_mgr, self.profession_mgr)
            self.formation_sys = FormationSystem(self.db, self.player_mgr, self.profession_mgr)
            self.talisman_sys = TalismanSystem(self.db, self.player_mgr, self.profession_mgr, self.item_mgr)
            logger.info("✓ 职业系统初始化完成")

            # 初始化坊市系统
            logger.info("🏪 正在初始化坊市系统...")
            self.market_sys = MarketSystem(self.db, self.player_mgr, self.item_mgr)
            await self.market_sys.initialize()
            logger.info("✓ 坊市系统初始化完成")

            # 初始化灵宠系统
            logger.info("🐾 正在初始化灵宠系统...")
            self.pet_sys = PetSystem(self.db, self.player_mgr)
            await self.pet_sys.init_pet_templates()
            logger.info("✓ 灵宠系统初始化完成")

            # 注入天劫系统到突破系统
            self.breakthrough_sys.set_tribulation_system(self.tribulation_sys)

            # 初始化基础职业配方
            logger.info("📚 正在加载基础配方...")
            await self.alchemy_sys.init_base_recipes()
            await self.refining_sys.init_base_blueprints()
            await self.formation_sys.init_base_formations()
            await self.talisman_sys.init_base_talismans()
            logger.info("✓ 基础配方加载完成")

            # 初始化宗门系统
            logger.info("🏛️ 正在初始化宗门系统...")
            await self.sect_sys.init_base_tasks()
            logger.info("✓ 宗门任务初始化完成")

            # 注入宗门系统到其他系统（用于加成计算）
            logger.info("🔗 正在连接系统...")
            self.cultivation_sys.set_sect_system(self.sect_sys)
            self.alchemy_sys.set_sect_system(self.sect_sys)
            self.refining_sys.set_sect_system(self.sect_sys)

            # 注入灵宠系统到其他系统（用于加成计算）
            self.cultivation_sys.set_pet_system(self.pet_sys)
            self.breakthrough_sys.set_pet_system(self.pet_sys)

            # 注入世界系统到修炼系统（用于地点灵气加成）
            self.cultivation_sys.set_world_manager(self.world_mgr)

            # 注入宗门系统到灵宠系统（用于宗门检查）
            self.pet_sys.set_sect_system(self.sect_sys)

            logger.info("✓ 系统连接完成")

            # 初始化图片生成器
            try:
                logger.info("🎨 正在初始化图片生成器...")
                from .core.card_generator import CardGenerator
                self.card_generator = CardGenerator()
                logger.info("✓ 图片生成器初始化完成")
            except Exception as e:
                logger.warning(f"⚠ 图片生成器初始化失败（将使用文本模式）: {e}")
                self.card_generator = None

            self._initialized = True
            logger.info("=" * 60)
            logger.info("✅ 修仙世界插件初始化完成！")
            logger.info("=" * 60)
            return True

        except Exception as e:
            logger.error("=" * 60)
            logger.error(f"❌ 修仙世界插件初始化失败: {e}", exc_info=True)
            logger.error("=" * 60)
            self._initialized = False
            return False
        finally:
            self._initializing = False

    async def terminate(self):
        """插件卸载时调用"""
        # 关闭数据库连接
        if self.db and self.db.db:
            await self.db.close()

        logger.info("修仙世界插件已卸载")

    # ========== 辅助方法 ==========

    def _check_initialized(self) -> bool:
        """检查插件是否已初始化"""
        return self.player_mgr is not None

    def _get_message_text(self, event: AstrMessageEvent) -> str:
        """
        兼容性方法：获取消息文本
        尝试多种方式获取消息文本以兼容不同版本的AstrBot
        """
        # 方法1: get_plain_text() - 新版API
        if hasattr(event, 'get_plain_text'):
            return event.get_plain_text().strip()

        # 方法2: message_str - 字符串属性
        if hasattr(event, 'message_str'):
            return event.message_str.strip()

        # 方法3: unified_msg_origin - 统一消息来源
        if hasattr(event, 'unified_msg_origin'):
            return event.unified_msg_origin.strip()

        # 方法4: raw_message - 原始消息（aiocqhttp）
        if hasattr(event, 'raw_message'):
            return event.raw_message.strip()

        # 方法5: message - 消息对象
        if hasattr(event, 'message'):
            msg = event.message
            # 如果是字符串，直接返回
            if isinstance(msg, str):
                return msg.strip()
            # 如果是列表或其他对象，尝试转换
            return str(msg).strip()

        # 如果都不行，抛出错误
        raise AttributeError(f"无法从事件对象获取消息文本。事件类型: {type(event).__name__}")

    # ========== 命令处理器 ==========

    @filter.command("修仙初始化", alias={"xiuxian_init", "初始化"})
    async def manual_init_cmd(self, event: AstrMessageEvent):
        """手动初始化插件（调试用）"""
        if self._initialized:
            yield event.plain_result("✅ 修仙世界插件已经初始化完成")
            return

        yield event.plain_result("🔄 开始初始化修仙世界插件...")

        if await self._ensure_initialized():
            yield event.plain_result("✅ 初始化成功！现在可以使用 /修仙 创建角色了")
        else:
            yield event.plain_result("❌ 初始化失败，请查看日志获取详细错误信息")

    @filter.command("修仙", alias={"开始修仙", "创建角色"})
    async def create_character(self, event: AstrMessageEvent):
        """创建修仙角色"""
        user_id = event.get_sender_id()

        try:
            # 确保插件已初始化
            if not await self._ensure_initialized():
                yield event.plain_result("❌ 修仙世界初始化失败，请使用 /修仙初始化 命令查看详情")
                return

            # 1. 检查是否已创建角色
            if await self.player_mgr.player_exists(user_id):
                yield event.plain_result("道友已经踏上修仙之路，无需重复创建角色。\n使用 /属性 查看角色信息")
                return

            # 2. 获取道号（从命令参数）
            message_text = self._get_message_text(event)
            parts = message_text.split(maxsplit=1)

            if len(parts) < 2:
                yield event.plain_result(
                    "欢迎来到修仙世界！\n\n"
                    "请输入您的道号（角色名称）\n\n"
                    "💡 使用方法：/修仙 [道号]\n"
                    "💡 例如：/修仙 逍遥子"
                )
                return

            name = parts[1].strip()

            # 验证道号
            if not name or len(name) > 20:
                yield event.plain_result("道号不合法！请使用1-20个字符的道号\n\n💡 例如：/修仙 逍遥子")
                return

            # 3. 创建角色
            yield event.plain_result(f"正在为道友 {name} 检测灵根...")

            player = await self.player_mgr.create_player(user_id, name)

            # 5. 格式化展示信息
            player_info = MessageFormatter.format_player_info(player)
            spirit_info = MessageFormatter.format_spirit_root_info(player)

            result_text = (
                f"🎉{name}踏上修仙之路！\n"
                f"{player_info}\n"
                f"{spirit_info}\n"
                f"💡/修炼 开始修炼 | /修仙帮助 查看命令"
            )

            yield event.plain_result(result_text)

            logger.info(f"用户 {user_id} 创建角色: {name}")

        except Exception as e:
            logger.error(f"创建角色失败: {e}", exc_info=True)
            yield event.plain_result(f"创建角色失败：{str(e)}")

    @filter.command("属性", alias={"角色信息", "信息"})
    async def show_status(self, event: AstrMessageEvent):
        """查看角色属性"""
        user_id = event.get_sender_id()

        try:
            # 确保插件已初始化
            if not await self._ensure_initialized():
                yield event.plain_result("❌ 修仙世界初始化失败，请使用 /修仙初始化 命令查看详情")
                return

            # 获取玩家信息
            player = await self.player_mgr.get_player_or_error(user_id)

            # 尝试使用图形化展示
            if self.card_generator:
                try:
                    # 准备卡片数据
                    player_data = {
                        'name': player.name,
                        'realm': player.realm,
                        'realm_level': player.realm_level,
                        'cultivation': player.cultivation,
                        'max_cultivation': player.cultivation_required,
                        'hp': player.hp,
                        'max_hp': player.max_hp,
                        'mp': player.mp,
                        'max_mp': player.max_mp,
                        'attack': player.attack,
                        'defense': player.defense,
                        'spirit_root': player.spirit_root,
                        'spirit_root_quality': player.spirit_root_quality,
                    }

                    # 生成卡片
                    import time
                    card_image = self.card_generator.generate_player_card(player_data)

                    # 保存图片
                    filename = f"player_card_{user_id}_{int(time.time())}.png"
                    filepath = self.card_generator.save_image(card_image, filename)

                    # 尝试发送图片
                    try:
                        # 尝试使用 image_result (如果 AstrBot 支持)
                        if hasattr(event, 'image_result'):
                            yield event.image_result(str(filepath))
                        else:
                            # 如果不支持，发送文本提示
                            yield event.plain_result(
                                f"✅ 角色卡片已生成！\n"
                                f"📸 图片路径：{filepath}\n\n"
                                f"💡 您的平台可能不支持自动发送图片\n"
                                f"💡 请手动查看上述路径的图片文件"
                            )
                        return  # 成功发送图片，直接返回
                    except Exception as img_send_error:
                        logger.warning(f"发送图片失败，使用文本模式: {img_send_error}")
                        # 继续执行文本模式

                except Exception as card_error:
                    logger.warning(f"生成卡片失败，使用文本模式: {card_error}")
                    # 继续执行文本模式

            # 文本模式（降级方案）
            # 格式化玩家信息
            player_info = MessageFormatter.format_player_info(player)

            # 检查是否在闭关中
            retreat_info = await self.cultivation_sys.get_retreat_info(user_id)

            # 构建额外信息
            extra_info = []

            if retreat_info:
                # 在闭关中，显示闭关信息
                elapsed_h = int(retreat_info['elapsed_hours'])
                remaining_h = int(retreat_info['remaining_hours'])
                extra_info.append(f"🧘闭关中 已{elapsed_h}h 还需{remaining_h}h")
                extra_info.append(f"💡/闭关信息 查看详情")
            else:
                # 不在闭关中，显示修炼信息
                cult_info = await self.cultivation_sys.get_cultivation_info(user_id)

                # 冷却信息
                if cult_info['can_cultivate']:
                    extra_info.append(f"✅可修炼 预计+{cult_info['next_cultivation_gain']}")
                else:
                    hours = cult_info['cooldown_remaining'] // 3600
                    minutes = (cult_info['cooldown_remaining'] % 3600) // 60
                    seconds = cult_info['cooldown_remaining'] % 60
                    time_str = ""
                    if hours > 0:
                        time_str += f"{hours}h"
                    if minutes > 0:
                        time_str += f"{minutes}m"
                    if seconds > 0 or not time_str:
                        time_str += f"{seconds}s"
                    extra_info.append(f"⏰冷却{time_str}")

                # 突破信息
                if cult_info['can_breakthrough']:
                    next_realm = cult_info['next_realm']['name']
                    extra_info.append(f"⚡可突破至{next_realm} /突破")

            result_text = player_info
            if extra_info:
                result_text += "\n" + "\n".join(extra_info)

            result_text += "\n💡/灵根 查看灵根详情"

            yield event.plain_result(result_text)

        except PlayerNotFoundError as e:
            yield event.plain_result(str(e))
        except Exception as e:
            logger.error(f"查看属性失败: {e}", exc_info=True)
            yield event.plain_result(f"查看属性失败：{str(e)}")

    @filter.command("灵根", alias={"灵根信息"})
    async def show_spirit_root(self, event: AstrMessageEvent):
        """查看灵根详情"""
        user_id = event.get_sender_id()

        try:
            # 检查插件是否已初始化
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return

            # 获取玩家信息
            player = await self.player_mgr.get_player_or_error(user_id)

            # 格式化灵根信息
            spirit_info = MessageFormatter.format_spirit_root_info(player)

            yield event.plain_result(spirit_info)

        except PlayerNotFoundError as e:
            yield event.plain_result(str(e))
        except Exception as e:
            logger.error(f"查看灵根失败: {e}", exc_info=True)
            yield event.plain_result(f"查看灵根失败：{str(e)}")

    @filter.command("修炼", alias={"打坐"})
    async def cultivate_cmd(self, event: AstrMessageEvent):
        """进行修炼（传统单次修炼）"""
        user_id = event.get_sender_id()

        try:
            # 检查插件是否已初始化
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return

            # 执行修炼
            result = await self.cultivation_sys.cultivate(user_id)

            # 应用玩家状态修正（重伤等）
            status_modifier = await self.status_mgr.get_cultivation_speed_modifier(user_id)
            if status_modifier < 1.0:
                # 有减益效果，重新计算修为获得
                original_gain = result['cultivation_gained']
                result['cultivation_gained'] = int(original_gain * status_modifier)
                result['status_penalty'] = original_gain - result['cultivation_gained']

            # 更新宗门任务进度
            try:
                task_updates = await self.sect_sys.update_task_progress(user_id, 'cultivation', 1)
                if task_updates:
                    for task_update in task_updates:
                        if task_update['completed']:
                            logger.info(f"玩家 {user_id} 完成宗门任务: {task_update['task_name']}")
            except Exception as e:
                # 任务更新失败不影响修炼
                logger.warning(f"更新宗门任务进度失败: {e}")

            # 构建结果消息
            message_lines = [
                f"✨修炼完成 +{result['cultivation_gained']}修为",
                f"📊当前 {result['total_cultivation']}"
            ]

            # 显示状态惩罚
            if result.get('status_penalty', 0) > 0:
                message_lines.append(f"⚠️ 状态惩罚 -{result['status_penalty']}修为")
                # 显示状态说明
                status_desc = await self.status_mgr.get_status_description(user_id)
                if status_desc != "状态正常":
                    message_lines.append(f"📍 {status_desc}")

            # 显示宗门加成
            if result.get('sect_bonus_rate', 0) > 0:
                message_lines.append(f"🏛️宗门加成 +{result['sect_bonus_rate']*100:.0f}%")

            # 显示灵宠加成
            if result.get('pet_bonus_rate', 0) > 0:
                message_lines.append(f"🐾灵宠加成 +{result['pet_bonus_rate']*100:.0f}%")

            # 显示地点加成
            if result.get('location_bonus_rate', 0) != 0:
                location_name = result.get('location_name', '未知')
                bonus = result['location_bonus_rate'] * 100
                message_lines.append(f"🗺️地点加成 [{location_name}] {bonus:+.0f}%")

            # 检查是否可以突破
            if result['can_breakthrough']:
                message_lines.append(f"⚡可突破至{result['next_realm']} 需{result['required_cultivation']}")
                message_lines.append(f"💡/突破 进行突破")

            result_text = "\n".join(message_lines)
            yield event.plain_result(result_text)

            logger.info(f"用户 {user_id} 修炼: +{result['cultivation_gained']} 修为")

        except PlayerNotFoundError as e:
            yield event.plain_result(str(e))
        except CooldownNotReadyError as e:
            yield event.plain_result(f"⏰{str(e)}\n💡/属性 查看冷却")
        except Exception as e:
            logger.error(f"修炼失败: {e}", exc_info=True)
            yield event.plain_result(f"修炼失败：{str(e)}")

    @filter.command("闭关", alias={"retreat", "闭关修炼"})
    async def retreat_cmd(self, event: AstrMessageEvent):
        """开始闭关修炼"""
        user_id = event.get_sender_id()

        try:
            # 检查插件是否已初始化
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return

            # 检查是否在闭关中
            retreat_info = await self.cultivation_sys.get_retreat_info(user_id)
            if retreat_info:
                # 已经在闭关中，显示闭关信息
                elapsed_h = int(retreat_info['elapsed_hours'])
                remaining_h = int(retreat_info['remaining_hours'])

                info_lines = [
                    "🧘 道友正在闭关中",
                    f"⏱️已闭关 {elapsed_h}h | 还需 {remaining_h}h",
                    f"📊预计修为 +{retreat_info['estimated_reward']}",
                    f"⏰结束时间 {retreat_info['end_time'].strftime('%m-%d %H:%M')}"
                ]

                if retreat_info['is_finished']:
                    info_lines.append("✅闭关已完成 /出关 可以出关了")
                else:
                    info_lines.append("💡/出关 强制 提前出关(奖励减半)")

                yield event.plain_result("\n".join(info_lines))
                return

            # 获取闭关时长参数
            message_text = self._get_message_text(event)
            parts = message_text.split()

            if len(parts) < 2:
                yield event.plain_result(
                    "🧘 闭关修炼\n\n"
                    "请指定闭关时长（小时）\n\n"
                    "💡 使用方法：/闭关 [时长]\n"
                    "💡 例如：/闭关 24（闭关24小时）\n\n"
                    "📋 时长限制：1-168小时（1-7天）\n"
                    "⚡ 效率说明：\n"
                    "  1-24h: 100%效率\n"
                    "  24-72h: 90%效率\n"
                    "  72-168h: 80%效率"
                )
                return

            try:
                duration_hours = int(parts[1])
            except ValueError:
                yield event.plain_result("❌ 时长必须是数字！")
                return

            # 开始闭关
            result = await self.cultivation_sys.start_retreat(user_id, duration_hours)

            # 构建结果消息
            result_lines = [
                "🧘 道友开始闭关修炼",
                f"⏱️闭关时长 {result['duration_hours']}h",
                f"📊预计修为 +{result['estimated_reward']}",
                f"⏰开始时间 {result['start_time'].strftime('%m-%d %H:%M')}",
                f"⏰结束时间 {result['end_time'].strftime('%m-%d %H:%M')}",
                "",
                "💡/闭关信息 查看进度",
                "💡/出关 完成闭关（到时间后）"
            ]

            yield event.plain_result("\n".join(result_lines))

            logger.info(f"用户 {user_id} 开始闭关: {duration_hours}小时")

        except PlayerNotFoundError as e:
            yield event.plain_result(str(e))
        except AlreadyInRetreatError as e:
            yield event.plain_result(f"⚠️ {str(e)}")
        except ValueError as e:
            yield event.plain_result(f"❌ {str(e)}")
        except Exception as e:
            logger.error(f"闭关失败: {e}", exc_info=True)
            yield event.plain_result(f"闭关失败：{str(e)}")

    @filter.command("出关", alias={"end_retreat", "结束闭关"})
    async def end_retreat_cmd(self, event: AstrMessageEvent):
        """结束闭关修炼（出关）"""
        user_id = event.get_sender_id()

        try:
            # 检查插件是否已初始化
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return

            # 检查是否有强制出关参数
            message_text = self._get_message_text(event)
            parts = message_text.split()
            force = len(parts) > 1 and parts[1] in ['强制', 'force', '是', 'y', 'yes']

            # 结束闭关
            result = await self.cultivation_sys.end_retreat(user_id, force)

            # 构建结果消息
            result_lines = [
                "🎉 道友出关了！",
                f"✨获得修为 +{result['cultivation_gained']}",
                f"📊当前修为 {result['total_cultivation']}",
                f"⏱️实际闭关 {result['actual_duration']:.1f}h"
            ]

            if result['is_early']:
                result_lines.append("⚠️ 提前出关")
            if result['penalty_applied']:
                result_lines.append("💔 修为奖励减半")

            # 检查是否可以突破
            if result['can_breakthrough']:
                result_lines.append(f"⚡可突破至{result['next_realm']} 需{result['required_cultivation']}")
                result_lines.append("💡/突破 进行突破")

            yield event.plain_result("\n".join(result_lines))

            logger.info(
                f"用户 {user_id} 出关: "
                f"获得修为 {result['cultivation_gained']}, "
                f"实际时长 {result['actual_duration']:.1f}h"
            )

        except PlayerNotFoundError as e:
            yield event.plain_result(str(e))
        except NotInRetreatError as e:
            yield event.plain_result(f"⚠️ {str(e)}")
        except RetreatNotFinishedError as e:
            yield event.plain_result(f"⏰ {str(e)}")
        except Exception as e:
            logger.error(f"出关失败: {e}", exc_info=True)
            yield event.plain_result(f"出关失败：{str(e)}")

    @filter.command("闭关信息", alias={"retreat_info", "闭关状态"})
    async def retreat_info_cmd(self, event: AstrMessageEvent):
        """查看闭关信息"""
        user_id = event.get_sender_id()

        try:
            # 检查插件是否已初始化
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return

            # 获取闭关信息
            retreat_info = await self.cultivation_sys.get_retreat_info(user_id)

            if not retreat_info:
                yield event.plain_result(
                    "📜 道友当前不在闭关中\n\n"
                    "💡 使用 /闭关 [时长] 开始闭关修炼"
                )
                return

            # 格式化时间
            elapsed_h = int(retreat_info['elapsed_hours'])
            remaining_h = int(retreat_info['remaining_hours'])
            progress = min(100, int(retreat_info['elapsed_hours'] / retreat_info['duration_hours'] * 100))

            # 构建信息消息
            info_lines = [
                "🧘 闭关修炼信息",
                "─" * 40,
                "",
                f"⏰ 开始时间：{retreat_info['start_time'].strftime('%m-%d %H:%M')}",
                f"⏰ 结束时间：{retreat_info['end_time'].strftime('%m-%d %H:%M')}",
                f"⏱️ 计划时长：{retreat_info['duration_hours']}小时",
                f"⏱️ 已闭关：{elapsed_h}小时",
                f"⏱️ 剩余：{remaining_h}小时",
                f"📊 进度：{progress}%",
                "",
                f"💎 预计修为：+{retreat_info['estimated_reward']}",
                ""
            ]

            if retreat_info['is_finished']:
                info_lines.append("✅ 闭关已完成！")
                info_lines.append("💡 使用 /出关 结束闭关")
            else:
                info_lines.append("⏳ 闭关进行中...")
                info_lines.append("💡 使用 /出关 强制 提前出关（奖励减半）")

            yield event.plain_result("\n".join(info_lines))

        except PlayerNotFoundError as e:
            yield event.plain_result(str(e))
        except Exception as e:
            logger.error(f"查看闭关信息失败: {e}", exc_info=True)
            yield event.plain_result(f"查看闭关信息失败：{str(e)}")

    @filter.command("突破", alias={"境界突破", "突破境界"})
    async def breakthrough_cmd(self, event: AstrMessageEvent):
        """境界突破"""
        user_id = event.get_sender_id()

        try:
            # 检查插件是否已初始化
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return

            # 获取突破信息
            breakthrough_info = await self.breakthrough_sys.get_breakthrough_info(user_id)

            if not breakthrough_info['can_breakthrough']:
                # 不能突破的原因
                reason = breakthrough_info['reason']
                if reason == '修为不足':
                    current = breakthrough_info['current_cultivation']
                    required = breakthrough_info['required_cultivation']
                    next_realm = breakthrough_info['next_realm']
                    yield event.plain_result(
                        f"⚠️ 修为不足，无法突破！\n\n"
                        f"🎯 目标境界：{next_realm}\n"
                        f"📊 当前修为：{current}\n"
                        f"📈 需要修为：{required}\n"
                        f"📉 还差修为：{required - current}\n\n"
                        f"💡 继续修炼积累修为吧！"
                    )
                else:
                    yield event.plain_result(f"⚠️ {reason}！")
                return

            # 显示突破信息
            rate = breakthrough_info['success_rate']
            factors = breakthrough_info['rate_factors']
            current_realm = breakthrough_info['current_realm']
            next_realm = breakthrough_info['next_realm']

            info_lines = [
                f"⚡ 境界突破信息",
                "",
                f"📍 当前境界：{current_realm}",
                f"🎯 目标境界：{next_realm}",
                f"📊 突破成功率：{rate:.1%}",
                "",
                "📋 成功率详情："
            ]

            for factor_name, factor_value in factors.items():
                factor_desc = {
                    'base_rate': '基础成功率',
                    'level_penalty': '小等级惩罚',
                    'realm_penalty': '大境界难度',
                    'spirit_bonus': '灵根加成',
                    'purity_bonus': '纯度加成',
                    'final_rate': '最终成功率'
                }
                if factor_name in factor_desc:
                    info_lines.append(f"   {factor_desc[factor_name]}：{factor_value}")

            # 检查是否有确认参数
            message_text = self._get_message_text(event)
            parts = message_text.split()

            if len(parts) < 2 or parts[1] not in ['确认', '是', 'y', 'yes']:
                info_lines.extend([
                    "",
                    "⚠️ 突破失败将损失20%当前修为",
                    "",
                    "💡 使用 /突破 确认 执行突破"
                ])
                yield event.plain_result("\n".join(info_lines))
                return

            # 执行突破
            yield event.plain_result("🔮 正在尝试突破...")

            result = await self.breakthrough_sys.attempt_breakthrough(user_id)

            # 检查是否需要渡劫
            if result.get('requires_tribulation', False):
                # 需要渡劫，显示天劫信息
                tribulation = result['tribulation']
                tribulation_info = tribulation.get_display_info()

                yield event.plain_result(
                    f"{result['message']}\n\n"
                    f"{tribulation_info}"
                )
                return

            # 格式化突破结果
            result_lines = [
                result['message'],
                "",
                f"📊 突破成功率：{result['breakthrough_rate']:.1%}"
            ]

            if result['success']:
                result_lines.extend([
                    "🎉 恭喜道友成功突破！",
                    f"🎁 获得10%突破修为奖励",
                    "",
                    "💡 使用 /属性 查看新的境界信息"
                ])
            else:
                result_lines.extend([
                    "💔 突破失败，损失了20%修为",
                    "",
                    "💡 不要灰心，继续修炼再来一次！"
                ])

            yield event.plain_result("\n".join(result_lines))

        except PlayerNotFoundError as e:
            yield event.plain_result(str(e))
        except BreakthroughFailedError as e:
            yield event.plain_result(f"⚠️ {str(e)}")
        except Exception as e:
            logger.error(f"突破失败: {e}", exc_info=True)
            yield event.plain_result(f"突破失败：{str(e)}")

    @filter.command("切磋", alias={"战斗", "pk", "pvp"})
    async def combat_cmd(self, event: AstrMessageEvent):
        """发起切磋"""
        attacker_id = event.get_sender_id()

        try:
            # 检查插件是否已初始化
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return

            # 1. 检查攻击者是否已创建角色
            attacker = await self.player_mgr.get_player_or_error(attacker_id)

            # 2. 提取被@的用户
            message_text = self._get_message_text(event)

            # 尝试从消息中提取@用户
            import re
            # 支持两种格式：
            # 1. @用户名(ID) - 如 @小皮(2984301456)
            # 2. @用户名 - 如 @小皮
            at_pattern = r'@([^()\s]+)(?:\((\d+)\))?'
            matches = re.findall(at_pattern, message_text)

            if not matches:
                yield event.plain_result(
                    "⚠️ 请@要切磋的玩家！\n\n"
                    "💡 使用方法：/切磋 @玩家名"
                )
                return

            # matches[0] = (用户名, ID) 或 (用户名, '')
            defender_name, potential_user_id = matches[0]

            # 3. 尝试找到目标玩家
            defender = None
            defender_id = None

            # 方法1: 优先使用ID查找（如果有ID）
            if potential_user_id:
                try:
                    defender = await self.player_mgr.get_player_or_error(potential_user_id)
                    defender_id = potential_user_id
                    logger.info(f"通过ID找到玩家: {defender.name} (ID: {defender_id})")
                except PlayerNotFoundError:
                    logger.warning(f"未找到ID为 {potential_user_id} 的玩家")
                    pass

            # 方法2: 通过用户名直接查找
            if defender is None:
                all_players = await self.player_mgr.get_all_players()
                for player in all_players:
                    if player.name == defender_name:
                        defender = player
                        defender_id = player.user_id
                        logger.info(f"通过用户名找到玩家: {defender.name} (ID: {defender_id})")
                        break

            # 方法3: 模糊匹配用户名
            if defender is None:
                all_players = await self.player_mgr.get_all_players()
                matched_players = [
                    player for player in all_players
                    if defender_name.lower() in player.name.lower() or
                       player.name.lower() in defender_name.lower()
                ]

                if len(matched_players) == 1:
                    defender = matched_players[0]
                    defender_id = defender.user_id
                    logger.info(f"通过模糊匹配找到玩家: {defender.name} (ID: {defender_id})")
                elif len(matched_players) > 1:
                    yield event.plain_result(
                        f"⚠️ 找到多个匹配的玩家：\n\n"
                        f"{'、'.join([p.name for p in matched_players[:5]])}\n\n"
                        f"💡 请使用更精确的玩家名"
                    )
                    return

            # 检查是否找到目标玩家
            if defender is None:
                debug_info = f"用户名: {defender_name}"
                if potential_user_id:
                    debug_info += f", ID: {potential_user_id}"

                yield event.plain_result(
                    f"⚠️ 未找到玩家 @{defender_name}\n\n"
                    f"💡 请确认玩家名是否正确，或该玩家是否已创建角色\n\n"
                    f"🔍 调试信息: {debug_info}"
                )
                return

            # 4. 检查不能自己切磋自己
            if attacker_id == defender_id:
                yield event.plain_result("⚠️ 道友不能与自己切磋")
                return

            # 5. 执行切磋
            yield event.plain_result(f"⚔️ {attacker.name} 向 {defender.name} 发起切磋...")

            result = await self.combat_sys.initiate_combat(attacker_id, defender_id)

            # 6. 格式化战斗结果
            combat_text = await self.combat_sys.format_combat_log(
                result['combat_log'], result['attacker'], result['defender']
            )

            yield event.plain_result(combat_text)

        except PlayerNotFoundError as e:
            yield event.plain_result(str(e))
        except SelfCombatException as e:
            yield event.plain_result(str(e))
        except CombatException as e:
            yield event.plain_result(f"⚠️ 切磋失败：{str(e)}")
        except Exception as e:
            logger.error(f"切磋命令失败: {e}", exc_info=True)
            yield event.plain_result(f"切磋失败：{str(e)}")

    @filter.command("战力", alias={"power", "战斗力"})
    async def power_cmd(self, event: AstrMessageEvent):
        """查看战力"""
        user_id = event.get_sender_id()

        try:
            # 检查插件是否已初始化
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return

            # 获取玩家信息
            player = await self.player_mgr.get_player_or_error(user_id)

            # 计算战力
            power = CombatCalculator.calculate_power(player)

            # 获取战斗统计
            combat_stats = await self.combat_sys.get_combat_stats(user_id)

            # 格式化战力信息
            realm_level = combat_stats.get('realm_level_name', '')
            power_lines = [
                f"⚔️{player.name} | 战力{power}",
                f"🎯{player.realm}{realm_level}",
                f"❤️{player.hp}/{player.max_hp} 💙{player.mp}/{player.max_mp}",
                f"⚔️攻{player.attack} 🛡️防{player.defense} 🍀运{player.luck}",
                "💡/切磋 @玩家"
            ]

            yield event.plain_result("\n".join(power_lines))

        except PlayerNotFoundError as e:
            yield event.plain_result(str(e))
        except Exception as e:
            logger.error(f"查看战力失败: {e}", exc_info=True)
            yield event.plain_result(f"查看战力失败：{str(e)}")

    @filter.command("储物袋", alias={"背包", "bag", "inventory"})
    async def inventory_cmd(self, event: AstrMessageEvent):
        """查看储物袋（装备+物品）"""
        user_id = event.get_sender_id()

        try:
            # 检查插件是否已初始化
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return

            lines = ["📦 储物袋", "─" * 40, ""]

            # 1. 显示装备
            equipment_list = await self.equipment_sys.get_player_equipment(user_id)
            if equipment_list:
                lines.append("⚔️ 装备:")
                for i, equipment in enumerate(equipment_list, 1):
                    status = "✅" if equipment.is_equipped else "⭕"
                    lines.append(f"  {i}. {status} {equipment.get_display_name()}")
                lines.append("")

            # 2. 显示丹药
            pills = await self.item_mgr.get_player_items(user_id, "pill")
            if pills:
                lines.append("💊 丹药:")
                for pill in pills:
                    lines.append(f"  • {pill['item_name']} x{pill['quantity']}")
                    if pill.get('description'):
                        lines.append(f"    {pill['description']}")
                lines.append("")

            # 3. 显示符箓
            talismans = await self.item_mgr.get_player_items(user_id, "talisman")
            if talismans:
                lines.append("📜 符箓:")
                for talisman in talismans:
                    lines.append(f"  • {talisman['item_name']} x{talisman['quantity']}")
                lines.append("")

            # 4. 显示材料
            materials = await self.item_mgr.get_player_items(user_id, "material")
            if materials:
                lines.append("🌿 材料:")
                for material in materials:
                    lines.append(f"  • {material['item_name']} x{material['quantity']}")
                lines.append("")

            # 5. 显示其他物品
            other_items = await self.item_mgr.get_player_items(user_id, "consumable")
            if other_items:
                lines.append("🎁 其他:")
                for item in other_items:
                    lines.append(f"  • {item['item_name']} x{item['quantity']}")
                lines.append("")

            if not equipment_list and not pills and not talismans and not materials and not other_items:
                lines.append("储物袋空空如也")
                lines.append("")

            lines.extend([
                "💡 使用 /装备 [编号] 穿戴装备",
                "💡 使用 /使用 [物品名] 使用物品"
            ])

            yield event.plain_result("\n".join(lines))

        except PlayerNotFoundError as e:
            yield event.plain_result(str(e))
        except Exception as e:
            logger.error(f"查看储物袋失败: {e}", exc_info=True)
            yield event.plain_result(f"查看储物袋失败：{str(e)}")

    @filter.command("装备", alias={"equip", "穿戴"})
    async def equip_cmd(self, event: AstrMessageEvent):
        """穿戴装备"""
        user_id = event.get_sender_id()
        message_text = self._get_message_text(event)

        try:
            # 检查插件是否已初始化
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return

            # 提取装备编号
            parts = message_text.split()
            if len(parts) < 2:
                yield event.plain_result(
                    "⚠️ 请指定要装备的物品编号！\n\n"
                    "💡 使用方法：/装备 [编号]\n"
                    "💡 使用 /储物袋 查看物品编号"
                )
                return

            try:
                equipment_index = int(parts[1])
            except ValueError:
                yield event.plain_result("❌ 装备编号必须是数字！")
                return

            # 获取装备列表
            equipment_list = await self.equipment_sys.get_player_equipment(user_id)

            if equipment_index < 1 or equipment_index > len(equipment_list):
                yield event.plain_result(
                    f"❌ 装备编号 {equipment_index} 不存在！\n\n"
                    f"💡 装备编号范围：1-{len(equipment_list)}"
                )
                return

            # 获取要装备的物品
            equipment = equipment_list[equipment_index - 1]

            # 检查是否已装备
            if equipment.is_equipped:
                yield event.plain_result(f"⚠️ {equipment.get_display_name()} 已经装备了！")
                return

            # 装备物品
            await self.equipment_sys.equip_item(user_id, equipment.id)

            yield event.plain_result(
                f"✅ 成功装备了 {equipment.get_display_name()}！\n\n"
                f"💡 使用 /属性 查看属性变化"
            )

        except PlayerNotFoundError as e:
            yield event.plain_result(str(e))
        except InsufficientLevelError as e:
            yield event.plain_result(f"⚠️ 等级不足，无法装备此物品！\n需要等级：{e}")
        except Exception as e:
            logger.error(f"装备失败: {e}", exc_info=True)
            yield event.plain_result(f"装备失败：{str(e)}")

    @filter.command("卸下", alias={"unequip", "脱下"})
    async def unequip_cmd(self, event: AstrMessageEvent):
        """卸下装备"""
        user_id = event.get_sender_id()
        message_text = self._get_message_text(event)

        try:
            # 检查插件是否已初始化
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return

            # 提取槽位名称
            parts = message_text.split()
            if len(parts) < 2:
                yield event.plain_result(
                    "⚠️ 请指定要卸下的槽位！\n\n"
                    "💡 使用方法：/卸下 [槽位]\n"
                    "💡 可用槽位：武器、护甲、饰品"
                )
                return

            slot_name = parts[1]

            # 槽位名称映射
            slot_mapping = {
                '武器': 'weapon',
                '护甲': 'armor',
                '饰品': 'accessory',
                'weapon': 'weapon',
                'armor': 'armor',
                'accessory': 'accessory'
            }

            if slot_name not in slot_mapping:
                yield event.plain_result(
                    "❌ 无效的槽位名称！\n\n"
                    "💡 可用槽位：武器、护甲、饰品"
                )
                return

            slot = slot_mapping[slot_name]

            # 卸下装备
            unequipped_item = await self.equipment_sys.unequip_item(user_id, slot)

            yield event.plain_result(
                f"✅ 成功卸下了 {unequipped_item.get_display_name()}！\n\n"
                f"💡 使用 /储物袋 查看装备状态"
            )

        except PlayerNotFoundError as e:
            yield event.plain_result(str(e))
        except EquipmentNotFoundError:
            yield event.plain_result(f"⚠️ {slot_name} 槽位没有装备任何物品！")
        except Exception as e:
            logger.error(f"卸下装备失败: {e}", exc_info=True)
            yield event.plain_result(f"卸下装备失败：{str(e)}")

    @filter.command("获得装备", alias={"getequip", "奖励装备"})
    async def get_equipment_cmd(self, event: AstrMessageEvent):
        """获得随机装备（测试用）"""
        user_id = event.get_sender_id()

        try:
            # 检查插件是否已初始化
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return

            # 提取装备类型
            message_text = self._get_message_text(event)
            parts = message_text.split()

            equipment_type = 'weapon'  # 默认武器
            if len(parts) > 1:
                type_mapping = {
                    '武器': 'weapon',
                    '护甲': 'armor',
                    '饰品': 'accessory',
                    'weapon': 'weapon',
                    'armor': 'armor',
                    'accessory': 'accessory'
                }
                equipment_type = type_mapping.get(parts[1], 'weapon')

            # 创建装备
            equipment = await self.equipment_sys.create_equipment(user_id, equipment_type)

            # 格式化获得信息
            lines = [
                f"🎉 获得了新装备！",
                "",
                equipment.get_detailed_info(),
                "",
                f"💡 使用 /装备 {len(await self.equipment_sys.get_player_equipment(user_id))} 穿戴此装备"
            ]

            yield event.plain_result("\n".join(lines))

        except PlayerNotFoundError as e:
            yield event.plain_result(str(e))
        except Exception as e:
            logger.error(f"获得装备失败: {e}", exc_info=True)
            yield event.plain_result(f"获得装备失败：{str(e)}")

    @filter.command("强化", alias={"enhance", "强化装备"})
    async def enhance_equipment_cmd(self, event: AstrMessageEvent):
        """强化装备"""
        user_id = event.get_sender_id()
        message_text = self._get_message_text(event)

        try:
            # 检查插件是否已初始化
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return

            # 提取装备编号
            parts = message_text.split()
            if len(parts) < 2:
                yield event.plain_result(
                    "⚠️ 请指定要强化的装备编号！\n\n"
                    "💡 使用方法：/强化 [编号]\n"
                    "💡 使用 /储物袋 查看装备编号"
                )
                return

            try:
                equipment_index = int(parts[1])
            except ValueError:
                yield event.plain_result("❌ 装备编号必须是数字！")
                return

            # 获取装备列表
            equipment_list = await self.equipment_sys.get_player_equipment(user_id)

            if equipment_index < 1 or equipment_index > len(equipment_list):
                yield event.plain_result(
                    f"❌ 装备编号 {equipment_index} 不存在！\n\n"
                    f"💡 装备编号范围：1-{len(equipment_list)}"
                )
                return

            # 获取要强化的装备
            equipment = equipment_list[equipment_index - 1]

            # 显示强化信息和确认
            if len(parts) < 3 or parts[2] not in ['确认', '是', 'y', 'yes']:
                # 计算强化消耗和成功率
                base_cost = 100
                spirit_stone_cost = int(base_cost * (1.5 ** equipment.enhance_level))
                base_rate = 1.0
                level_penalty = equipment.enhance_level * 0.05
                success_rate = max(0.1, base_rate - level_penalty)

                player = await self.player_mgr.get_player_or_error(user_id)

                info_lines = [
                    f"⚡ 装备强化信息",
                    "",
                    f"装备：{equipment.get_display_name()}",
                    f"当前强化等级：+{equipment.enhance_level}",
                    f"目标强化等级：+{equipment.enhance_level + 1}",
                    "",
                    f"📊 强化成功率：{success_rate:.1%}",
                    f"💎 消耗灵石：{spirit_stone_cost}",
                    f"💰 当前灵石：{player.spirit_stone}",
                    "",
                    "💡 强化成功：装备属性提升5%",
                    "💡 强化失败：仅消耗灵石，装备等级不变",
                    "",
                    "💡 使用 /强化 [编号] 确认 执行强化"
                ]

                yield event.plain_result("\n".join(info_lines))
                return

            # 执行强化
            yield event.plain_result("⚡ 正在强化装备...")

            result = await self.equipment_sys.enhance_equipment(user_id, equipment.id)

            # 格式化强化结果
            result_lines = [
                f"⚡ 装备强化结果",
                "",
                f"装备：{result['equipment'].get_display_name()}"
            ]

            if result['success']:
                result_lines.extend([
                    "",
                    f"🎉 强化成功！",
                    f"✨ 强化等级：+{result['old_level']} → +{result['new_level']}",
                    ""
                ])

                # 显示属性提升
                if result['attribute_bonus']:
                    result_lines.append("📈 属性提升：")
                    for attr, value in result['attribute_bonus'].items():
                        attr_names = {
                            'attack': '攻击力',
                            'defense': '防御力',
                            'hp_bonus': '生命值',
                            'mp_bonus': '法力值'
                        }
                        attr_name = attr_names.get(attr, attr)
                        result_lines.append(f"   {attr_name} +{value}")
                    result_lines.append("")
            else:
                result_lines.extend([
                    "",
                    f"💔 强化失败！",
                    f"📊 强化等级：+{result['old_level']} (未变化)",
                    ""
                ])

            result_lines.extend([
                f"💎 消耗灵石：{result['spirit_stone_cost']}",
                f"💰 剩余灵石：{result['remaining_spirit_stone']}",
                f"📊 成功率：{result['success_rate']:.1%}",
                "",
                "💡 使用 /储物袋 查看装备详情"
            ])

            yield event.plain_result("\n".join(result_lines))

            logger.info(
                f"用户 {user_id} 强化装备: {equipment.name} "
                f"{'成功' if result['success'] else '失败'} "
                f"(+{result['old_level']} → +{result['new_level']})"
            )

        except PlayerNotFoundError as e:
            yield event.plain_result(str(e))
        except InvalidOperationError as e:
            yield event.plain_result(f"⚠️ {str(e)}")
        except Exception as e:
            logger.error(f"强化装备失败: {e}", exc_info=True)
            yield event.plain_result(f"强化装备失败：{str(e)}")

    @filter.command("使用", alias={"use", "使用物品"})
    async def use_item_cmd(self, event: AstrMessageEvent):
        """使用物品（丹药、符箓等）"""
        user_id = event.get_sender_id()
        message_text = self._get_message_text(event)

        try:
            # 检查插件是否已初始化
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return

            # 提取物品名称
            parts = message_text.split(maxsplit=1)
            if len(parts) < 2:
                yield event.plain_result(
                    "⚠️ 请指定要使用的物品名称！\n\n"
                    "💡 使用方法：/使用 [物品名称]\n"
                    "💡 例如：/使用 回血丹\n"
                    "💡 使用 /储物袋 查看拥有的物品"
                )
                return

            item_name = parts[1].strip()

            # 使用物品
            result = await self.item_mgr.use_item(user_id, item_name)

            if result['success']:
                yield event.plain_result(f"✅ {result['message']}")
            else:
                yield event.plain_result(f"❌ {result['message']}")

        except PlayerNotFoundError:
            yield event.plain_result("❌ 道友还未踏上修仙之路，请先使用 /修仙 创建角色")
        except ItemNotFoundError as e:
            yield event.plain_result(f"❌ {str(e)}")
        except ItemCannotUseError as e:
            yield event.plain_result(f"⚠️ {str(e)}")
        except Exception as e:
            logger.error(f"使用物品失败: {e}", exc_info=True)
            yield event.plain_result(f"使用物品失败：{str(e)}")

    @filter.command("AI生成", alias={"ai", "生成", "create"})
    async def ai_generate_cmd(self, event: AstrMessageEvent):
        """AI内容生成"""
        user_id = event.get_sender_id()
        message_text = self._get_message_text(event)

        try:
            # 检查插件是否已初始化
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return

            # 提取内容类型
            parts = message_text.split()
            if len(parts) < 2:
                # 显示可用内容类型
                available_types = await self.ai_generator.get_available_content_types(user_id)

                lines = ["🤖 AI内容生成", "─" * 40, ""]

                for content_type, info in available_types.items():
                    lines.append(f"📝 {info['name']}")
                    lines.append(f"   可用内容：{info['available_count']}/{info['total_count']}")

                lines.extend([
                    "",
                    "💡 使用方法：/AI生成 [类型]",
                    "📋 可用类型：场景、任务、故事、地点、人物",
                    "💨 示例：/AI生成 场景"
                ])

                yield event.plain_result("\n".join(lines))
                return

            content_type = parts[1]
            type_mapping = {
                '场景': 'scene',
                '任务': 'quest',
                '故事': 'story',
                '地点': 'location',
                '人物': 'character',
                'scene': 'scene',
                'quest': 'quest',
                'story': 'story',
                'location': 'location',
                'character': 'character'
            }

            mapped_type = type_mapping.get(content_type)
            if not mapped_type:
                yield event.plain_result(
                    f"❌ 不支持的内容类型：{content_type}\n\n"
                    "💡 支持的类型：场景、任务、故事、地点、人物"
                )
                return

            # 生成内容
            generated_content = await self.ai_generator.generate_content(user_id, mapped_type)

            # 格式化输出
            formatted_content = self.ai_generator.format_content_for_display(generated_content, mapped_type)

            # 获取历史记录数量
            history_count = len(await self.ai_generator.get_generation_history(user_id, 5))

            result_lines = [
                f"🤖 AI内容生成完成！",
                "",
                formatted_content,
                "",
                f"📊 已生成内容：{history_count} 条",
                "",
                "💡 再次使用相同类型可获得更多相关内容",
                "💡 使用 /AI历史 查看生成历史"
            ]

            yield event.plain_result("\n".join(result_lines))

        except PlayerNotFoundError as e:
            yield event.plain_result(str(e))
        except (AIGenerationError, ContentNotAvailableError) as e:
            yield event.plain_result(f"🚫 {str(e)}")
        except Exception as e:
            logger.error(f"AI生成失败: {e}", exc_info=True)
            yield event.plain_result(f"AI生成失败：{str(e)}")

    @filter.command("AI历史", alias={"ai_history", "历史"})
    async def ai_history_cmd(self, event: AstrMessageEvent):
        """查看AI生成历史"""
        user_id = event.get_sender_id()

        try:
            # 检查插件是否已初始化
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return

            # 获取历史记录
            history = await self.ai_generator.get_generation_history(user_id, 10)

            if not history:
                yield event.plain_result("📜 还没有任何AI生成历史")
                return

            lines = ["📜 AI生成历史", "─" * 40]

            for i, record in enumerate(history, 1):
                content_type = record['content_type']
                type_names = {
                    'scene': '修仙场景',
                    'quest': '修仙任务',
                    'story': '修仙故事',
                    'location': '修仙地点',
                    'character': '修仙人物'
                }

                type_name = type_names.get(content_type, content_type)
                generated_time = record['generated_at'][:19] if record['generated_at'] else '未知'

                lines.extend([
                    f"{i}. 🤖 {type_name}",
                    f"   📝 内容ID：{record['content_id']}",
                    f"   ⏰ 生成时间：{generated_time}"
                ])

            lines.extend([
                "",
                f"💡 最近10条生成记录",
                "💡 使用 /AI生成 [类型] 继续创作"
            ])

            yield event.plain_result("\n".join(lines))

        except PlayerNotFoundError as e:
            yield event.plain_result(str(e))
        except Exception as e:
            logger.error(f"查看AI历史失败: {e}", exc_info=True)
            yield event.plain_result(f"查看AI历史失败：{str(e)}")

    @filter.command("AI帮助", alias={"ai_help", "ai使用说明"})
    async def ai_help_cmd(self, event: AstrMessageEvent):
        """AI生成帮助"""
        help_text = """
【AI内容生成系统】

🤖 AI生成类型：
   场景 - 修仙场景描述
   任务 - 修仙任务内容
   故事 - 修仙故事文本
   地点 - 修仙地点信息
   人物 - 修仙人物设定

📝 使用方法：
   /AI生成 [类型] - 生成指定类型内容
   /AI历史 - 查看生成历史

⭐ 特色功能：
   🔮 智能等级匹配 - 根据玩家境界生成合适内容
   🎭 丰富模板库 - 预定义多种修仙元素
   📊 历史记录 - 追踪用户生成历史
   🎨 个性化推荐 - 基于用户偏好提供内容

💡 示例：
   /AI生成 场景  - 生成修仙场景
   /AI生成 任务  - 生成修仙任务

📝 提示：内容会根据您的修仙境界自动调整难度！
        """.strip()

        yield event.plain_result(help_text)

    @filter.command("功法", alias={"methods", "功法簿"})
    async def methods_cmd(self, event: AstrMessageEvent):
        """查看功法簿"""
        user_id = event.get_sender_id()

        try:
            # 检查插件是否已初始化
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return

            methods_text = await self.method_sys.format_method_list(user_id)
            yield event.plain_result(methods_text)

        except Exception as e:
            logger.error(f"查看功法簿失败: {e}", exc_info=True)
            yield event.plain_result(f"查看功法簿失败：{str(e)}")

    @filter.command("已装备功法", alias={"equipped_methods", "装备功法"})
    async def equipped_methods_cmd(self, event: AstrMessageEvent):
        """查看已装备功法"""
        user_id = event.get_sender_id()

        try:
            # 检查插件是否已初始化
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return

            equipped_text = await self.method_sys.format_equipped_methods(user_id)
            yield event.plain_result(equipped_text)

        except Exception as e:
            logger.error(f"查看已装备功法失败: {e}", exc_info=True)
            yield event.plain_result(f"查看已装备功法失败：{str(e)}")

    @filter.command("功法装备", alias={"method_equip", "装备功法"})
    async def method_equip_cmd(self, event: AstrMessageEvent):
        """装备功法"""
        user_id = event.get_sender_id()
        message_text = self._get_message_text(event)

        try:
            # 检查插件是否已初始化
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return

            # 解析命令参数
            parts = message_text.split()
            if len(parts) < 3:
                yield event.plain_result(
                    "⚠️ 请指定功法编号和槽位！\n\n"
                    "💡 使用方法：/功法装备 [编号] [槽位]\n"
                    "💡 可用槽位：active_1, active_2, passive_1, passive_2\n"
                    "💡 槽位说明：active为主动功法，passive为被动功法\n"
                    "💡 使用 /功法 查看功法编号"
                )
                return

            try:
                method_index = int(parts[1])
            except ValueError:
                yield event.plain_result("❌ 功法编号必须是数字！")
                return

            slot = parts[2]

            # 获取功法列表
            methods = await self.method_sys.get_player_methods(user_id)

            if method_index < 1 or method_index > len(methods):
                yield event.plain_result(
                    f"❌ 功法编号 {method_index} 不存在！\n\n"
                    f"💡 功法编号范围：1-{len(methods)}"
                )
                return

            # 获取要装备的功法
            method = methods[method_index - 1]
            method_id = method.id

            # 装备功法
            equipped_method = await self.method_sys.equip_method(user_id, method_id, slot)

            yield event.plain_result(
                f"✅ 成功装备了 {equipped_method.get_display_name()} 到 {slot} 槽位！\n\n"
                f"💡 使用 /已装备功法 查看装备状态"
            )

        except (MethodNotFoundError, InsufficientLevelError) as e:
            yield event.plain_result(f"⚠️ {e}")
        except Exception as e:
            logger.error(f"装备功法失败: {e}", exc_info=True)
            yield event.plain_result(f"装备功法失败：{str(e)}")

    @filter.command("功法卸下", alias={"method_unequip", "卸下功法"})
    async def method_unequip_cmd(self, event: AstrMessageEvent):
        """卸下功法"""
        user_id = event.get_sender_id()
        message_text = self._get_message_text(event)

        try:
            # 检查插件是否已初始化
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return

            # 解析命令参数
            parts = message_text.split()
            if len(parts) < 2:
                yield event.plain_result(
                    "⚠️ 请指定要卸下的槽位！\n\n"
                    "💡 使用方法：/功法卸下 [槽位]\n"
                    "💡 可用槽位：active_1, active_2, passive_1, passive_2\n"
                    "💡 使用 /已装备功法 查看当前装备状态"
                )
                return

            slot = parts[1]

            # 卸下功法
            unequipped_method = await self.method_sys.unequip_method(user_id, slot)

            yield event.plain_result(
                f"✅ 成功卸下了槽位 {slot} 的功法：{unequipped_method.get_display_name()}\n\n"
                f"💡 使用 /功法 查看功法簿"
            )

        except MethodNotFoundError as e:
            yield event.plain_result(f"❌ {e}")
        except Exception as e:
            logger.error(f"卸下功法失败: {e}", exc_info=True)
            yield event.plain_result(f"卸下功法失败：{str(e)}")

    @filter.command("功法详情", alias={"method_info", "功法信息"})
    async def method_info_cmd(self, event: AstrMessageEvent):
        """查看功法详情"""
        user_id = event.get_sender_id()
        message_text = self._get_message_text(event)

        try:
            # 检查插件是否已初始化
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return

            # 解析命令参数
            parts = message_text.split()
            if len(parts) < 2:
                yield event.plain_result(
                    "⚠️ 请指定功法编号！\n\n"
                    "💡 使用方法：/功法详情 [编号]\n"
                    "💡 使用 /功法 查看功法编号"
                )
                return

            try:
                method_index = int(parts[1])
            except ValueError:
                yield event.plain_result("❌ 功法编号必须是数字！")
                return

            # 获取功法列表
            methods = await self.method_sys.get_player_methods(user_id)

            if method_index < 1 or method_index > len(methods):
                yield event.plain_result(
                    f"❌ 功法编号 {method_index} 不存在！\n\n"
                    f"💡 功法编号范围：1-{len(methods)}"
                )
                return

            # 获取功法详情
            method = methods[method_index - 1]
            method_info = method.get_detailed_info()

            yield event.plain_result(method_info)

        except Exception as e:
            logger.error(f"查看功法详情失败: {e}", exc_info=True)
            yield event.plain_result(f"查看功法详情失败：{str(e)}")

    @filter.command("获得功法", alias={"get_method", "奖励功法"})
    async def get_method_cmd(self, event: AstrMessageEvent):
        """获得随机功法（测试用）"""
        user_id = event.get_sender_id()
        message_text = self._get_message_text(event)

        try:
            # 检查插件是否已初始化
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return

            # 解析命令参数
            parts = message_text.split()

            method_type = None  # 默认随机类型
            quality = None      # 默认随机品质

            if len(parts) > 1:
                # 指定功法类型
                type_mapping = {
                    '攻击': 'attack', 'attack': 'attack',
                    '防御': 'defense', 'defense': 'defense',
                    '速度': 'speed', 'speed': 'speed',
                    '辅助': 'auxiliary', 'auxiliary': 'auxiliary'
                }
                method_type = type_mapping.get(parts[1])

            if len(parts) > 2:
                # 指定品质
                quality_mapping = {
                    '凡品': '凡品', '灵品': '灵品', '宝品': '宝品',
                    '仙品': '仙品', '神品': '神品', '道品': '道品'
                }
                quality = quality_mapping.get(parts[2])

            # 生成功法
            method = await self.method_sys.generate_method(user_id, method_type, quality)

            # 格式化获得信息
            lines = [
                f"🎉 获得了新功法！",
                "",
                method.get_detailed_info(),
                "",
                f"💡 使用 /功法装备 {len(await self.method_sys.get_player_methods(user_id))} active_1 装备此功法"
            ]

            yield event.plain_result("\n".join(lines))

        except Exception as e:
            logger.error(f"获得功法失败: {e}", exc_info=True)
            yield event.plain_result(f"获得功法失败：{str(e)}")

    @filter.command("功法帮助", alias={"method_help", "功法使用说明"})
    async def method_help_cmd(self, event: AstrMessageEvent):
        """功法系统帮助"""
        help_text = """
【功法系统 - 使用说明】

🎯 功法类型：
   攻击功法 - 提升攻击力和战斗能力
   防御功法 - 提升防御力和生存能力
   速度功法 - 提升速度和闪避能力
   辅助功法 - 提供各种辅助效果

📋 装备槽位：
   active_1/active_2 - 主动功法槽位
   passive_1/passive_2 - 被动功法槽位

📝 基础命令：
/功法 - 查看功法簿
/已装备功法 - 查看已装备功法
/功法装备 [编号] [槽位] - 装备功法
/功法卸下 [槽位] - 卸下功法
/功法详情 [编号] - 查看功法详情
/获得功法 [类型] [品质] - 获得随机功法(测试)

⭐ 熟练度系统：
   功法通过使用获得熟练度
   熟练度等级：入门→初学→掌握→精通→大成→圆满
   高熟练度提供额外属性加成

💡 使用技巧：
• 攻击功法装备在主动槽位
• 防御、速度、辅助功法装备在被动槽位
• 品质越高的功法，属性加成越强
• 根据自己修仙路线选择合适的功法组合
        """.strip()

        yield event.plain_result(help_text)

    @filter.command("修炼功法", alias={"practice_method", "功法修炼"})
    async def practice_method_cmd(self, event: AstrMessageEvent):
        """修炼功法"""
        user_id = event.get_sender_id()

        try:
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return

            # 解析命令参数
            message_text = self._get_message_text(event)
            parts = message_text.split()

            if len(parts) < 2:
                # 显示功法列表和使用说明
                methods = await self.method_sys.get_player_methods(user_id)
                if not methods:
                    yield event.plain_result("⚠️ 您还没有任何功法\n\n💡 使用 /获得功法 获取随机功法")
                    return

                lines = ["🧘 功法修炼", "─" * 40, ""]
                for i, method in enumerate(methods, 1):
                    lines.append(f"{i}. {method.get_display_name()}")
                    lines.append(f"   熟练度: {method.get_mastery_display()}")

                lines.extend(["", "💡 使用方法：/修炼功法 [编号]", "💡 例如：/修炼功法 1"])
                yield event.plain_result("\n".join(lines))
                return

            # 解析功法编号
            try:
                method_index = int(parts[1])
            except ValueError:
                yield event.plain_result("��� 功法编号必须是数字！")
                return

            # 获取功法列表
            methods = await self.method_sys.get_player_methods(user_id)
            if method_index < 1 or method_index > len(methods):
                yield event.plain_result(f"❌ 功法编号 {method_index} 不存在！")
                return

            method = methods[method_index - 1]

            # 执行修炼
            result = await self.method_sys.practice_method(user_id, method.id)

            # 检查技能解锁
            if result['leveled_up']:
                unlocked = await self.skill_sys.check_and_unlock_skills(
                    user_id, method.id, method.proficiency
                )
                result['unlocked_skills'] = unlocked

            # 构建结果消息
            lines = [
                f"✨ 修炼 {method.get_display_name()} 完成",
                "",
                f"📊 熟练度 +{result['proficiency_gain']}",
                f"🎯 当前熟练度：{result['mastery_level']}",
                f"💫 灵根适配度：{result['compatibility']}%"
            ]

            if result['leveled_up']:
                lines.append("")
                lines.append(f"🎉 功法境界提升至 {result['mastery_level']}！")

            if result['unlocked_skills']:
                lines.append("")
                lines.append("🔓 解锁新技能：")
                for skill in result['unlocked_skills']:
                    lines.append(f"   • {skill}")

            yield event.plain_result("\n".join(lines))

            logger.info(f"玩家 {user_id} 修炼功法: {method.name}，熟练度 +{result['proficiency_gain']}")

        except MethodNotOwnError as e:
            yield event.plain_result(f"❌ {str(e)}")
        except Exception as e:
            logger.error(f"修炼功法失败: {e}", exc_info=True)
            yield event.plain_result(f"修炼功法失败：{str(e)}")

    @filter.command("技能", alias={"skills", "我的技能"})
    async def skills_cmd(self, event: AstrMessageEvent):
        """查看技能列表"""
        user_id = event.get_sender_id()

        try:
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return

            skills = await self.skill_sys.get_player_skills(user_id)

            if not skills:
                yield event.plain_result("⚠️ 您还没有任何技能\n\n💡 通过修炼功法可以解锁技能")
                return

            lines = ["⚔️ 技能列表", "─" * 40, ""]

            by_type = {}
            for skill in skills:
                if skill.skill_type not in by_type:
                    by_type[skill.skill_type] = []
                by_type[skill.skill_type].append(skill)

            type_names = {
                'attack': '⚔️ 攻击技能',
                'defense': '🛡️ 防御技能',
                'support': '✨ 辅助技能',
                'control': '🎯 控制技能'
            }

            for skill_type, skill_list in by_type.items():
                type_name = type_names.get(skill_type, skill_type)
                lines.append(f"\n{type_name}:")
                for i, skill in enumerate(skill_list, 1):
                    lines.append(f"  {i}. {skill}")

            lines.extend(["", "💡 使用 /使用技能 [技能名] 使用技能"])
            yield event.plain_result("\n".join(lines))

        except Exception as e:
            logger.error(f"查看技能失败: {e}", exc_info=True)
            yield event.plain_result(f"查看技能失败：{str(e)}")

    @filter.command("使用技能", alias={"use_skill", "施放技能"})
    async def use_skill_cmd(self, event: AstrMessageEvent):
        """使用技能"""
        user_id = event.get_sender_id()
        message_text = self._get_message_text(event)

        try:
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return

            # 解析命令参数
            parts = message_text.split(maxsplit=1)

            if len(parts) < 2:
                # 显示技能列表
                skills = await self.skill_sys.get_player_skills(user_id)
                if not skills:
                    yield event.plain_result("⚠️ 您还没有任何技能\n\n💡 通过修炼功法可以解锁技能")
                    return

                lines = ["⚔️ 使用技能", "─" * 40, "", "请输入要使用的技能名称：", ""]
                for skill in skills:
                    lines.append(f"  • {skill}")

                lines.extend(["", "💡 使用方法：/使用技能 [技能名]", "💡 例如：/使用技能 火球术"])
                yield event.plain_result("\n".join(lines))
                return

            skill_name = parts[1].strip()

            # 使用技能
            result = await self.skill_sys.use_skill(user_id, skill_name)

            # 构建结果消息
            lines = [
                f"✨ 施放技能：{result['skill_name']}",
                "",
                f"💥 造成伤害：{result['damage']}",
                f"💙 消耗法力：{result['mp_cost']} MP",
                f"💫 剩余法力：{result['remaining_mp']} MP"
            ]

            if result['leveled_up']:
                lines.append("")
                lines.append("🎉 技能升级！伤害提升30%！")

            yield event.plain_result("\n".join(lines))

            logger.info(f"玩家 {user_id} 使用技能: {skill_name}")

        except SkillNotFoundError as e:
            yield event.plain_result(f"❌ {str(e)}")
        except InsufficientMPError as e:
            yield event.plain_result(f"❌ {str(e)}")
        except Exception as e:
            logger.error(f"使用技能失败: {e}", exc_info=True)
            yield event.plain_result(f"使用技能失败：{str(e)}")

    @filter.command("挑战", alias={"challenge", "pve"})
    async def challenge_npc_cmd(self, event: AstrMessageEvent):
        """挑战NPC妖兽"""
        user_id = event.get_sender_id()

        try:
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return

            # 解析命令参数
            message_text = self._get_message_text(event)
            parts = message_text.split()

            # 获取NPC等级
            npc_level = None
            if len(parts) >= 2:
                try:
                    npc_level = int(parts[1])
                    if npc_level < 1 or npc_level > 10:
                        yield event.plain_result("❌ 等级范围：1-10")
                        return
                except ValueError:
                    yield event.plain_result("❌ 等级必须是数字")
                    return

            # 获取玩家信息
            player = await self.player_mgr.get_player_or_error(user_id)

            if npc_level is None:
                npc_level = player.realm_level

            # 执行战斗
            yield event.plain_result(f"⚔️ 正在挑战 {npc_level} 级妖兽...")

            result = await self.combat_sys.battle_npc(user_id, npc_level)

            # 构建战斗结果
            lines = [
                "⚔️ 战斗结果",
                "─" * 40,
                "",
                f"挑战者：{player.name} ({player.realm} {player.realm_level}级)",
                f"对手：{result['npc'].name}",
                ""
            ]

            # 显示战斗过程（简化版）
            combat_log = result['combat_log']
            if len(combat_log) > 0:
                lines.append("📜 战斗记录：")
                for i, log_entry in enumerate(combat_log[-5:], 1):
                    lines.append(f"  回合{log_entry.get('round', i)}: {log_entry.get('message', '')}")
                lines.append("")

            # 判断胜负
            if result['winner'] == user_id:
                lines.extend([
                    "🎉 战斗胜利！",
                    "",
                    "🎁 获得奖励：",
                    f"  💎 灵石 +{result['rewards']['spirit_stone']}",
                    f"  ⭐ 经验 +{result['rewards']['exp']}",
                    "",
                    f"💰 当前灵石：{player.spirit_stone}"
                ])
            else:
                lines.extend([
                    "💔 战斗失败！",
                    "",
                    "💡 提升实力后再来挑战吧"
                ])

            yield event.plain_result("\n".join(lines))

            logger.info(f"玩家 {user_id} 挑战{npc_level}级妖兽: {'胜利' if result['winner'] == user_id else '失败'}")

        except Exception as e:
            logger.error(f"挑战妖兽失败: {e}", exc_info=True)
            yield event.plain_result(f"挑战失败：{str(e)}")

    @filter.command("创建宗门", alias={"create_sect", "建立宗门"})
    async def create_sect_cmd(self, event: AstrMessageEvent):
        """创建宗门"""
        user_id = event.get_sender_id()

        try:
            # 检查插件是否已初始化
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return

            # 获取宗门名称和描述（从命令参数）
            message_text = self._get_message_text(event)
            parts = message_text.split(maxsplit=2)

            if len(parts) < 3:
                yield event.plain_result(
                    "🏛️ 创建宗门\n\n"
                    "请提供宗门名称和描述\n\n"
                    "💡 使用方法：/创建宗门 [宗门名称] [宗门描述]\n"
                    "💡 例如：/创建宗门 逍遥宗 天下第一的修仙宗门\n\n"
                    "📋 要求：\n"
                    "  • 宗门名称：1-20个字符\n"
                    "  • 宗门描述：1-100个字符"
                )
                return

            sect_name = parts[1].strip()
            sect_desc = parts[2].strip()

            # 验证宗门名称
            if not sect_name or len(sect_name) > 20:
                yield event.plain_result("❌ 宗门名称不合法！请使用1-20个字符")
                return

            # 验证宗门描述
            if not sect_desc or len(sect_desc) > 100:
                yield event.plain_result("❌ 宗门描述不合法！请使用1-100个字符")
                return

            # 创建宗门
            sect = await self.sect_sys.create_sect(user_id, sect_name, sect_desc)

            result_text = (
                f"🎉 恭喜！宗门 {sect.name} 创建成功！\n\n"
                f"{sect.get_display_info()}\n\n"
                f"💡 使用 /宗门信息 查看宗门详情\n"
                f"💡 使用 /宗门帮助 查看宗门命令"
            )

            yield event.plain_result(result_text)

        except AlreadyInSectError as e:
            yield event.plain_result(f"⚠️ {e}")
        except SectNameExistsError as e:
            yield event.plain_result(f"❌ {e}")
        except Exception as e:
            logger.error(f"创建宗门失败: {e}", exc_info=True)
            yield event.plain_result(f"创建宗门失败：{str(e)}")

    @filter.command("宗门信息", alias={"sect_info", "宗门"})
    async def sect_info_cmd(self, event: AstrMessageEvent):
        """查看宗门信息"""
        user_id = event.get_sender_id()

        try:
            # 检查插件是否已初始化
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return

            # 获取玩家所在宗门
            sect = await self.sect_sys.get_player_sect(user_id)
            if not sect:
                yield event.plain_result(
                    "⚠️ 道友尚未加入任何宗门\n\n"
                    "💡 使用 /创建宗门 创建宗门\n"
                    "💡 使用 /宗门列表 查看所有宗门"
                )
                return

            # 获取成员信息
            member = await self.sect_sys.get_sect_member(user_id)
            members = await self.sect_sys.get_sect_members(sect.id)

            info_lines = [
                sect.get_display_info(),
                "",
                f"📋 您的职位：{member.get_position_display()}",
                f"🎖️ 您的贡献：{member.contribution}",
                "",
                f"👥 成员列表 (共{len(members)}人)："
            ]

            for i, m in enumerate(members[:10], 1):  # 只显示前10名
                player = await self.player_mgr.get_player(m.user_id)
                name = player.name if player else "未知"
                info_lines.append(f"  {i}. {m.get_position_display()} - {name} (贡献: {m.total_contribution})")

            if len(members) > 10:
                info_lines.append(f"  ... 还有 {len(members) - 10} 名成员")

            yield event.plain_result("\n".join(info_lines))

        except Exception as e:
            logger.error(f"查看宗门信息失败: {e}", exc_info=True)
            yield event.plain_result(f"查看宗门信息失败：{str(e)}")

    @filter.command("加入宗门", alias={"join_sect"})
    async def join_sect_cmd(self, event: AstrMessageEvent):
        """加入宗门"""
        user_id = event.get_sender_id()
        message_text = self._get_message_text(event)

        try:
            # 检查插件是否已初始化
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return

            # 解析宗门名称
            parts = message_text.split()
            if len(parts) < 2:
                yield event.plain_result(
                    "⚠️ 请指定要加入的宗门名称！\n\n"
                    "💡 使用方法：/加入宗门 [宗门名称]\n"
                    "💡 使用 /宗门列表 查看所有宗门"
                )
                return

            sect_name = " ".join(parts[1:])

            # 根据名称查找宗门
            sect = await self.sect_sys.get_sect_by_name(sect_name)
            if not sect:
                yield event.plain_result(f"❌ 找不到宗门：{sect_name}")
                return

            # 加入宗门
            member = await self.sect_sys.join_sect(user_id, sect.id)

            yield event.plain_result(
                f"🎉 成功加入宗门 {sect.name}！\n\n"
                f"📋 您的职位：{member.get_position_display()}\n\n"
                f"💡 使用 /宗门信息 查看宗门详情"
            )

        except AlreadyInSectError as e:
            yield event.plain_result(f"⚠️ {e}")
        except SectFullError as e:
            yield event.plain_result(f"⚠️ {e}")
        except SectError as e:
            yield event.plain_result(f"⚠️ {e}")
        except Exception as e:
            logger.error(f"加入宗门失败: {e}", exc_info=True)
            yield event.plain_result(f"加入宗门失败：{str(e)}")

    @filter.command("离开宗门", alias={"leave_sect", "退出宗门"})
    async def leave_sect_cmd(self, event: AstrMessageEvent):
        """离开宗门"""
        user_id = event.get_sender_id()

        try:
            # 检查插件是否已初始化
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return

            # 检查是否有确认参数
            message_text = self._get_message_text(event)
            parts = message_text.split()

            if len(parts) < 2 or parts[1] not in ['确认', '是', 'y', 'yes']:
                yield event.plain_result(
                    "⚠️ 确认要离开宗门吗？\n\n"
                    "离开后您将失去所有宗门贡献度和职位\n\n"
                    "💡 使用 /离开宗门 确认 执行操作"
                )
                return

            # 离开宗门
            sect = await self.sect_sys.leave_sect(user_id)

            yield event.plain_result(
                f"✅ 已离开宗门 {sect.name}\n\n"
                f"💡 使用 /宗门列表 查看其他宗门"
            )

        except NotSectMemberError as e:
            yield event.plain_result(f"⚠️ {e}")
        except SectError as e:
            yield event.plain_result(f"⚠️ {e}")
        except Exception as e:
            logger.error(f"离开宗门失败: {e}", exc_info=True)
            yield event.plain_result(f"离开宗门失败：{str(e)}")

    @filter.command("宗门列表", alias={"sect_list", "所有宗门"})
    async def sect_list_cmd(self, event: AstrMessageEvent):
        """查看所有宗门"""
        try:
            # 检查插件是否已初始化
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return

            sects = await self.sect_sys.get_all_sects(limit=20)

            if not sects:
                yield event.plain_result("📜 目前还没有任何宗门")
                return

            lines = ["🏛️ 宗门列表", "─" * 40, ""]

            for i, sect in enumerate(sects, 1):
                recruiting = "✅ 招募中" if sect.is_recruiting else "❌ 不招募"
                lines.append(
                    f"{i}. {sect.get_type_emoji()} {sect.name} (Lv.{sect.level})\n"
                    f"   成员: {sect.member_count}/{sect.max_members} | {recruiting}\n"
                    f"   {sect.description[:30]}..."
                )

            lines.extend([
                "",
                "💡 使用 /加入宗门 [宗门名称] 加入宗门",
                "💡 使用 /创建宗门 创建新宗门"
            ])

            yield event.plain_result("\n".join(lines))

        except Exception as e:
            logger.error(f"查看宗门列表失败: {e}", exc_info=True)
            yield event.plain_result(f"查看宗门列表失败：{str(e)}")

    @filter.command("宗门捐献", alias={"sect_donate", "捐献"})
    async def sect_donate_cmd(self, event: AstrMessageEvent):
        """捐献灵石"""
        user_id = event.get_sender_id()
        message_text = self._get_message_text(event)

        try:
            # 检查插件是否已初始化
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return

            # 解析捐献数量
            parts = message_text.split()
            if len(parts) < 2:
                yield event.plain_result(
                    "⚠️ 请指定捐献数量！\n\n"
                    "💡 使用方法：/宗门捐献 [数量]\n"
                    "💡 示例：/宗门捐献 100"
                )
                return

            try:
                amount = int(parts[1])
                if amount <= 0:
                    yield event.plain_result("❌ 捐献数量必须大于0")
                    return
            except ValueError:
                yield event.plain_result("❌ 捐献数量必须是数字")
                return

            # 捐献灵石
            sect, contribution = await self.sect_sys.donate_spirit_stone(user_id, amount)

            yield event.plain_result(
                f"🎉 捐献成功！\n\n"
                f"💎 捐献灵石：{amount}\n"
                f"🎖️ 获得贡献：{contribution}\n\n"
                f"宗门当前灵石：{sect.spirit_stone}\n"
                f"宗门等级：Lv.{sect.level} ({sect.experience}/{sect.max_experience})"
            )

        except NotSectMemberError as e:
            yield event.plain_result(f"⚠️ {e}")
        except Exception as e:
            logger.error(f"宗门捐献失败: {e}", exc_info=True)
            yield event.plain_result(f"宗门捐献失败：{str(e)}")

    @filter.command("宗门功法", alias={"sect_methods", "功法库"})
    async def sect_methods_cmd(self, event: AstrMessageEvent):
        """查看宗门功法库"""
        user_id = event.get_sender_id()

        try:
            # 检查插件是否已初始化
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return

            # 获取玩家所在宗门
            member = await self.sect_sys.get_sect_member(user_id)
            if not member:
                yield event.plain_result("⚠️ 道友尚未加入任何宗门")
                return

            # 获取宗门信息
            sect = await self.sect_sys.get_sect_by_id(member.sect_id)

            # 获取宗门功法列表
            methods = await self.sect_sys.get_sect_methods(sect.id, user_id)

            if not methods:
                yield event.plain_result(
                    f"📚 {sect.name} - 功法库\n\n"
                    f"⚠️ 宗门功法库空空如也\n\n"
                    f"💡 使用 /捐献功法 [编号] 捐献功法给宗门"
                )
                return

            # 格式化显示
            lines = [f"📚 {sect.name} - 功法库", ""]

            for i, method in enumerate(methods, 1):
                learned_mark = "✅" if method['learned'] else "⭕"
                lines.append(
                    f"{i}. {learned_mark} {method['method_name']} ({method['method_quality']})"
                )
                lines.append(f"   类型：{method['method_type']}")
                lines.append(
                    f"   要求：{method['required_position']} | "
                    f"贡献度 {method['required_contribution']}"
                )
                lines.append(f"   学习次数：{method['learn_count']}次")
                lines.append("")

            lines.append(f"🎓 您的贡献度：{member.contribution}")
            lines.append(f"📋 您的职位：{member.position}")
            lines.append("")
            lines.append("💡 使用 /学习功法 [编号] 学习功法")

            yield event.plain_result("\n".join(lines))

        except Exception as e:
            logger.exception("查看宗门功法库失败")
            yield event.plain_result(f"查看宗门功法库失败：{str(e)}")

    @filter.command("学习功法", alias={"learn_method", "学功法"})
    async def learn_sect_method_cmd(self, event: AstrMessageEvent):
        """学习宗门功法"""
        user_id = event.get_sender_id()
        message_text = self._get_message_text(event)

        try:
            # 检查插件是否已初始化
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return

            # 解析参数
            parts = message_text.strip().split()
            if len(parts) < 2:
                yield event.plain_result(
                    "❌ 参数不足\n\n"
                    "📖 使用方法：/学习功法 [编号]\n"
                    "💡 使用 /宗门功法 查看功法库"
                )
                return

            try:
                method_index = int(parts[1]) - 1
            except ValueError:
                yield event.plain_result("❌ 编号必须是数字")
                return

            # 获取玩家所在宗门
            member = await self.sect_sys.get_sect_member(user_id)
            if not member:
                yield event.plain_result("⚠️ 道友尚未加入任何宗门")
                return

            # 获取宗门功法列表
            methods = await self.sect_sys.get_sect_methods(member.sect_id, user_id)

            if method_index < 0 or method_index >= len(methods):
                yield event.plain_result(f"❌ 编号无效，请输入1-{len(methods)}之间的数字")
                return

            selected_method = methods[method_index]

            # 检查是否已学习
            if selected_method['learned']:
                yield event.plain_result(f"⚠️ 您已经学习过 {selected_method['method_name']}")
                return

            # 学习功法
            result = await self.sect_sys.learn_sect_method(
                user_id,
                selected_method['id'],
                self.method_sys
            )

            yield event.plain_result(
                f"🎓 学习成功！\n\n"
                f"📖 功法：{result['method_name']}\n"
                f"⭐ 品质：{result['method_quality']}\n"
                f"🔷 类型：{result['method_type']}\n\n"
                f"💰 消耗贡献度：{result['contribution_cost']}\n"
                f"🎁 剩余贡献度：{result['remaining_contribution']}\n\n"
                f"💡 使用 /功法列表 查看已学功法"
            )

        except Exception as e:
            logger.exception("学习宗门功法失败")
            yield event.plain_result(f"学习宗门功法失败：{str(e)}")

    @filter.command("捐献功法", alias={"donate_method", "功法捐献"})
    async def donate_method_cmd(self, event: AstrMessageEvent):
        """捐献功法到宗门"""
        user_id = event.get_sender_id()
        message_text = self._get_message_text(event)

        try:
            # 检查插件是否已初始化
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return

            # 解析参数
            parts = message_text.strip().split()
            if len(parts) < 2:
                yield event.plain_result(
                    "❌ 参数不足\n\n"
                    "📖 使用方法：/捐献功法 [编号]\n"
                    "💡 使用 /功法列表 查看您的功法"
                )
                return

            try:
                method_index = int(parts[1]) - 1
            except ValueError:
                yield event.plain_result("❌ 编号必须是数字")
                return

            # 获取玩家功法列表
            methods = await self.method_sys.get_player_methods(user_id)

            if method_index < 0 or method_index >= len(methods):
                yield event.plain_result(f"❌ 编号无效，请输入1-{len(methods)}之间的数字")
                return

            selected_method = methods[method_index]

            # 捐献功法
            result = await self.sect_sys.donate_method_to_sect(
                user_id,
                selected_method.id,
                self.method_sys
            )

            yield event.plain_result(
                f"🎁 捐献成功！\n\n"
                f"📖 功法：{result['method_name']}\n"
                f"⭐ 品质：{result['method_quality']}\n\n"
                f"🎖️ 获得贡献度：+{result['contribution_reward']}\n"
                f"💎 总贡献度：{result['total_contribution']}\n\n"
                f"💡 功法已添加到宗门功法库"
            )

        except Exception as e:
            logger.exception("捐献功法失败")
            yield event.plain_result(f"捐献功法失败：{str(e)}")

    @filter.command("宗门任务", alias={"sect_tasks", "宗门quest"})
    async def sect_tasks_cmd(self, event: AstrMessageEvent):
        """查看宗门任务"""
        user_id = event.get_sender_id()

        try:
            # 检查插件是否已初始化
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return

            # 获取可接取任务
            tasks = await self.sect_sys.get_available_tasks(user_id)

            if not tasks:
                yield event.plain_result("⚠️ 当前没有可用任务")
                return

            # 按类型分组
            daily_tasks = [t for t in tasks if t['task_type'] == 'daily']
            weekly_tasks = [t for t in tasks if t['task_type'] == 'weekly']

            lines = ["📋 宗门任务", ""]

            # 每日任务
            if daily_tasks:
                lines.append("📅 每日任务：")
                for i, task in enumerate(daily_tasks, 1):
                    status = ""
                    if task['is_accepted']:
                        if task['status'] == 'completed':
                            status = "✅ 已完成"
                        else:
                            status = f"⏳ 进行中 ({task['progress']}/{task['target']})"
                    else:
                        status = "⭕ 可接取"

                    lines.append(f"\n{i}. {task['task_name']} - {status}")
                    lines.append(f"   📝 {task['task_description']}")
                    lines.append(
                        f"   🎁 奖励：贡献度+{task['contribution_reward']} | "
                        f"灵石+{task['spirit_stone_reward']} | "
                        f"经验+{task['exp_reward']}"
                    )

            # 每周任务
            if weekly_tasks:
                lines.append("\n\n📆 每周任务：")
                for i, task in enumerate(weekly_tasks, len(daily_tasks) + 1):
                    status = ""
                    if task['is_accepted']:
                        if task['status'] == 'completed':
                            status = "✅ 已完成"
                        else:
                            status = f"⏳ 进行中 ({task['progress']}/{task['target']})"
                    else:
                        status = "⭕ 可接取"

                    lines.append(f"\n{i}. {task['task_name']} - {status}")
                    lines.append(f"   📝 {task['task_description']}")
                    lines.append(
                        f"   🎁 奖励：贡献度+{task['contribution_reward']} | "
                        f"灵石+{task['spirit_stone_reward']} | "
                        f"经验+{task['exp_reward']}"
                    )

            lines.append("\n\n💡 使用 /接取任务 [任务ID] 接取任务")
            lines.append("💡 使用 /我的任务 查看已接取任务")

            yield event.plain_result("\n".join(lines))

        except Exception as e:
            logger.exception("查看宗门任务失败")
            yield event.plain_result(f"查看宗门任务失败：{str(e)}")

    @filter.command("接取任务", alias={"accept_task", "接任务"})
    async def accept_task_cmd(self, event: AstrMessageEvent):
        """接取宗门任务"""
        user_id = event.get_sender_id()
        message_text = self._get_message_text(event)

        try:
            # 检查插件是否已初始化
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return

            # 解析参数
            parts = message_text.strip().split()
            if len(parts) < 2:
                yield event.plain_result(
                    "❌ 参数不足\n\n"
                    "📖 使用方法：/接取任务 [任务ID]\n"
                    "💡 使用 /宗门任务 查看可接取任务"
                )
                return

            task_id = parts[1]

            # 接取任务
            result = await self.sect_sys.accept_task(user_id, task_id)

            yield event.plain_result(
                f"✅ 接取成功！\n\n"
                f"📋 任务：{result['task_name']}\n"
                f"📝 描述：{result['task_description']}\n"
                f"🎯 目标：0/{result['target']}\n\n"
                f"💡 任务进度会自动更新\n"
                f"💡 完成后使用 /我的任务 查看并领取奖励"
            )

        except Exception as e:
            logger.exception("接取任务失败")
            yield event.plain_result(f"接取任务失败：{str(e)}")

    @filter.command("我的任务", alias={"my_tasks", "任务列表"})
    async def my_tasks_cmd(self, event: AstrMessageEvent):
        """查看我的任务"""
        user_id = event.get_sender_id()

        try:
            # 检查插件是否已初始化
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return

            # 获取任务列表
            tasks = await self.sect_sys.get_member_tasks(user_id)

            if not tasks:
                yield event.plain_result(
                    "📋 我的任务\n\n"
                    "⚠️ 您还没有接取任何任务\n\n"
                    "💡 使用 /宗门任务 查看可接取任务"
                )
                return

            lines = ["📋 我的任务", ""]

            # 活跃任务
            active_tasks = [t for t in tasks if t['status'] == 'active']
            if active_tasks:
                lines.append("⏳ 进行中：")
                for i, task in enumerate(active_tasks, 1):
                    progress_pct = (task['progress'] / task['target']) * 100
                    lines.append(
                        f"\n{i}. {task['task_name']} ({task['task_type']})"
                    )
                    lines.append(
                        f"   📊 进度：{task['progress']}/{task['target']} ({progress_pct:.0f}%)"
                    )
                    lines.append(
                        f"   🎁 奖励：贡献度+{task['contribution_reward']} | "
                        f"灵石+{task['spirit_stone_reward']}"
                    )

            # 已完成任务
            completed_tasks = [t for t in tasks if t['status'] == 'completed' and t['can_claim']]
            if completed_tasks:
                lines.append("\n\n✅ 可领取：")
                for task in completed_tasks:
                    lines.append(f"\n• {task['task_name']}")
                    lines.append(f"  📦 任务ID：{task['id']}")
                    lines.append(
                        f"  🎁 奖励：贡献度+{task['contribution_reward']} | "
                        f"灵石+{task['spirit_stone_reward']}"
                    )
                lines.append("\n💡 使用 /完成任务 [任务ID] 领取奖励")

            # 已领取任务
            claimed_tasks = [t for t in tasks if t['claimed_at']]
            if claimed_tasks:
                lines.append(f"\n\n🎉 已领取：{len(claimed_tasks)}个任务")

            yield event.plain_result("\n".join(lines))

        except Exception as e:
            logger.exception("查看我的任务失败")
            yield event.plain_result(f"查看我的任务失败：{str(e)}")

    @filter.command("完成任务", alias={"complete_task", "领取奖励"})
    async def complete_task_cmd(self, event: AstrMessageEvent):
        """完成任务并领取奖励"""
        user_id = event.get_sender_id()
        message_text = self._get_message_text(event)

        try:
            # 检查插件是否已初始化
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return

            # 解析参数
            parts = message_text.strip().split()
            if len(parts) < 2:
                yield event.plain_result(
                    "❌ 参数不足\n\n"
                    "📖 使用方法：/完成任务 [任务ID]\n"
                    "💡 使用 /我的任务 查看可领取任务"
                )
                return

            member_task_id = parts[1]

            # 完成任务
            result = await self.sect_sys.complete_task(user_id, member_task_id)

            rewards = result['rewards']
            lines = [
                "🎉 任务完成！",
                "",
                f"📋 任务：{result['task_name']}",
                "",
                "🎁 获得奖励："
            ]

            if rewards['contribution'] > 0:
                lines.append(f"   🎖️ 贡献度 +{rewards['contribution']}")
            if rewards['spirit_stone'] > 0:
                lines.append(f"   💎 灵石 +{rewards['spirit_stone']}")
            if rewards['exp'] > 0:
                lines.append(f"   ⭐ 经验 +{rewards['exp']}")

            yield event.plain_result("\n".join(lines))

        except Exception as e:
            logger.exception("完成任务失败")
            yield event.plain_result(f"完成任务失败：{str(e)}")

    @filter.command("宗门帮助", alias={"sect_help"})
    async def sect_help_cmd(self, event: AstrMessageEvent):
        """宗门系统帮助"""
        help_text = """
【宗门系统 - 使用说明】

🏛️ 基础命令：
/创建宗门 - 创建新宗门
/宗门信息 - 查看宗门详情
/加入宗门 [名称] - 加入指定宗门
/离开宗门 - 离开当前宗门
/宗门列表 - 查看所有宗门
/宗门捐献 [数量] - 捐献灵石给宗门

📚 功法库系统：
/宗门功法 - 查看宗门功法库
/学习功法 [编号] - 学习宗门功法
/捐献功法 [编号] - 捐献功法到宗门

📋 任务系统：
/宗门任务 - 查看可接取任务
/接取任务 [任务ID] - 接取宗门任务
/我的任务 - 查看已接取任务
/完成任务 [任务ID] - 领取任务奖励

👥 职位系统：
宗主 👑 - 最高权限，可管理一切
长老 🎖️ - 可升级建筑、管理成员
执事 🏅 - 可管理普通成员
精英弟子 ⭐ - 核心成员
弟子 📚 - 普通成员

🏗️ 宗门建筑：
大殿 - 宗门核心建筑
藏经阁 - 提升功法品质 +5%/级
练功房 - 提升修炼效率 +10%/级
炼丹房 - 提升炼丹成功率 +8%/级
炼器房 - 提升炼器成功率 +8%/级

📈 宗门升级：
• 捐献灵石可获得贡献度和宗门经验
• 宗门升级可增加成员上限
• 建筑升级需要消耗宗门灵石
• 贡献度可用于学习宗门功法

🐾 宗门灵宠福利：
/领取灵宠 - 加入宗门后可领取初始灵宠（仅一次）
/我的灵宠 - 查看已拥有的灵宠
/激活灵宠 [编号] - 激活灵宠获得加成效果
/灵宠秘境 - 探索秘境捕获野生灵宠
/灵宠详情 [编号] - 查看灵宠详细属性

🐾 灵宠养成：
/喂养灵宠 [编号] - 消耗灵石喂养灵宠提升亲密度
/训练灵宠 [编号] - 消耗灵石训练灵宠获得经验
/升级灵宠 [编号] - 经验足够时升级灵宠
/进化灵宠 [编号] - 满足条件时进化成更强形态

💡 提示：
• 加入宗门可获得建筑加成
• 加入宗门后可领取一只初始灵宠
• 激活灵宠可获得修炼/突破等加成
• 灵宠等级和亲密度会增强加成效果
• 部分灵宠可进化成更强大的形态
• 积极捐献可提升个人地位
• 完成宗门任务获得丰厚奖励
• 宗门越强，成员收益越高
        """.strip()

        yield event.plain_result(help_text)

    @filter.command("渡劫", alias={"tribulation", "cross_tribulation"})
    async def tribulation_cmd(self, event: AstrMessageEvent):
        """渡劫命令"""
        user_id = event.get_sender_id()

        try:
            # 检查插件是否已初始化
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return

            # 获取玩家信息
            player = await self.player_mgr.get_player_or_error(user_id)

            # 获取当前天劫
            tribulation = await self.tribulation_sys.get_active_tribulation(user_id)

            if not tribulation:
                yield event.plain_result(
                    "⚠️ 道友当前没有天劫需要渡过\\n\\n"
                    "💡 天劫会在突破某些境界时自动触发\\n"
                    "💡 使用 /突破 尝试突破境界"
                )
                return

            # 如果天劫是待开始状态，开始渡劫
            if tribulation.status == "pending":
                # 检查生命值
                hp_percentage = (player.hp / player.max_hp) * 100
                if hp_percentage < 80:
                    yield event.plain_result(
                        f"⚠️ 生命值不足！\\n\\n"
                        f"❤️ 当前生命值：{player.hp}/{player.max_hp} ({hp_percentage:.1f}%)\\n"
                        f"📋 渡劫要求：至少80%生命值\\n\\n"
                        f"💡 请先恢复生命值再来渡劫"
                    )
                    return

                # 开始渡劫
                tribulation = await self.tribulation_sys.start_tribulation(user_id)

                yield event.plain_result(
                    f"⚡ 开始渡劫！\\n\\n"
                    f"{tribulation.get_display_info()}\\n\\n"
                    f"💡 使用 /渡劫 继续下一波天劫"
                )

            elif tribulation.status == "in_progress":
                # 执行下一波天劫
                tribulation, wave_result = await self.tribulation_sys.execute_wave(user_id)

                result_lines = [
                    f"⚡ {wave_result['message']}",
                    "",
                    f"📊 第 {wave_result['wave']}/{tribulation.total_waves} 波",
                    f"💥 伤害：{wave_result['damage']}",
                    f"❤️ 生命值：{wave_result['hp_before']} → {wave_result['hp_after']} ({wave_result['hp_percentage']:.1f}%)",
                    ""
                ]

                if wave_result.get('completed') or wave_result.get('failed'):
                    # 天劫完成或失败
                    if wave_result['final_result'] == 'success':
                        # 渡劫成功，自动触发突破
                        result_lines.extend([
                            "🎉 恭喜！成功渡过天劫！",
                            "",
                            "🎁 渡劫奖励：",
                            f"   📈 修为提升：+{tribulation.rewards.get('cultivation_boost', 0)}",
                            f"   ⚡ 属性提升：{tribulation.rewards.get('attribute_boost', {})}",
                            f"   ❤️ 生命恢复：已恢复至满值",
                            "",
                            "⚡ 正在完成境界突破..."
                        ])

                        yield event.plain_result("\n".join(result_lines))

                        # 触发突破（跳过天劫检查）
                        breakthrough_result = await self.breakthrough_sys.attempt_breakthrough(user_id, skip_tribulation=True)

                        if breakthrough_result['success']:
                            yield event.plain_result(
                                f"🎉 突破成功！\\n\\n"
                                f"✨ {breakthrough_result['old_realm']} → {breakthrough_result['new_realm']}\\n\\n"
                                f"💡 使用 /属性 查看新的境界信息"
                            )
                        else:
                            yield event.plain_result(
                                f"💔 突破失败！\\n\\n"
                                f"虽然渡劫成功，但境界突破失败了\\n"
                                f"损失了部分修为，请继续修炼后再次尝试"
                            )

                    else:
                        # 渡劫失败
                        result_lines.extend([
                            "💔 渡劫失败！",
                            "",
                            "💀 惩罚：",
                            f"   📉 修为损失：-{tribulation.penalties.get('cultivation_loss', 0)}",
                            f"   ❤️ 生命降低：已降至10%",
                            "",
                            "💡 不要灰心，继续修炼提升实力后再来！"
                        ])

                        yield event.plain_result("\n".join(result_lines))

                else:
                    # 还有更多波数
                    result_lines.extend([
                        f"💡 还有 {tribulation.total_waves - wave_result['wave']} 波天劫",
                        f"💡 使用 /渡劫 继续下一波"
                    ])

                    yield event.plain_result("\n".join(result_lines))

            else:
                # 天劫已完成
                yield event.plain_result(
                    f"📜 天劫已完成\\n\\n"
                    f"状态：{tribulation.get_status_display()}\\n\\n"
                    f"💡 使用 /天劫历史 查看历史记录"
                )

        except PlayerNotFoundError as e:
            yield event.plain_result(str(e))
        except (TribulationNotFoundError, InsufficientHPError, TribulationError) as e:
            yield event.plain_result(f"⚠️ {str(e)}")
        except Exception as e:
            logger.error(f"渡劫失败: {e}", exc_info=True)
            yield event.plain_result(f"渡劫失败：{str(e)}")

    @filter.command("天劫信息", alias={"tribulation_info", "天劫"})
    async def tribulation_info_cmd(self, event: AstrMessageEvent):
        """查看天劫信息"""
        user_id = event.get_sender_id()

        try:
            # 检查插件是否已初始化
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return

            tribulation = await self.tribulation_sys.get_active_tribulation(user_id)

            if not tribulation:
                yield event.plain_result(
                    "📜 当前没有天劫\\n\\n"
                    "💡 天劫会在突破某些境界时自动触发\\n"
                    "💡 使用 /天劫历史 查看历史天劫"
                )
                return

            # 显示天劫详细信息
            info_lines = [
                "⚡ 天劫信息",
                "─" * 40,
                "",
                tribulation.get_display_info()
            ]

            # 如果有波次记录，显示最近的几波
            if tribulation.wave_logs:
                info_lines.extend([
                    "",
                    "📋 渡劫记录（最近5波）：",
                    ""
                ])

                recent_logs = tribulation.wave_logs[-5:]
                for log in recent_logs:
                    info_lines.append(
                        f"第{log['wave']}波：{log['message']} "
                        f"(HP: {log['hp_before']} → {log['hp_after']})"
                    )

            info_lines.extend([
                "",
                "💡 使用 /渡劫 继续渡劫" if tribulation.status in ["pending", "in_progress"] else "💡 天劫已完成"
            ])

            yield event.plain_result("\n".join(info_lines))

        except PlayerNotFoundError as e:
            yield event.plain_result(str(e))
        except Exception as e:
            logger.error(f"查看天劫信息失败: {e}", exc_info=True)
            yield event.plain_result(f"查看天劫信息失败：{str(e)}")

    @filter.command("天劫历史", alias={"tribulation_history", "历史天劫"})
    async def tribulation_history_cmd(self, event: AstrMessageEvent):
        """查看天劫历史"""
        user_id = event.get_sender_id()

        try:
            # 检查插件是否已初始化
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return

            history = await self.tribulation_sys.get_tribulation_history(user_id, 10)

            if not history:
                yield event.plain_result("📜 还没有任何天劫历史")
                return

            lines = ["📜 天劫历史", "─" * 40, ""]

            for i, tribulation in enumerate(history, 1):
                status_emoji = "✅" if tribulation.success else "❌"
                lines.extend([
                    f"{i}. {status_emoji} {tribulation.get_type_name()} - {tribulation.realm}",
                    f"   难度：{tribulation.get_difficulty_display()} | 波数：{tribulation.current_wave}/{tribulation.total_waves}",
                    f"   状态：{tribulation.get_status_display()}",
                    f"   时间：{tribulation.created_at.strftime('%Y-%m-%d %H:%M') if tribulation.created_at else '未知'}",
                    ""
                ])

            lines.extend([
                "💡 最近10条天劫记录",
                "💡 使用 /天劫统计 查看详细统计"
            ])

            yield event.plain_result("\n".join(lines))

        except PlayerNotFoundError as e:
            yield event.plain_result(str(e))
        except Exception as e:
            logger.error(f"查看天劫历史失败: {e}", exc_info=True)
            yield event.plain_result(f"查看天劫历史失败：{str(e)}")

    @filter.command("天劫统计", alias={"tribulation_stats", "统计天劫"})
    async def tribulation_stats_cmd(self, event: AstrMessageEvent):
        """查看天劫统计"""
        user_id = event.get_sender_id()

        try:
            # 检查插件是否已初始化
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return

            stats = await self.tribulation_sys.get_tribulation_stats(user_id)

            if stats['total_tribulations'] == 0:
                yield event.plain_result("📊 还没有任何天劫记录")
                return

            lines = [
                "📊 天劫统计",
                "─" * 40,
                "",
                f"📈 总天劫次数：{stats['total_tribulations']}",
                f"✅ 成功次数：{stats['success_count']}",
                f"❌ 失败次数：{stats['failed_count']}",
                f"📊 成功率：{stats['success_rate']:.1f}%",
                ""
            ]

            # 各类型天劫统计
            if stats['type_stats']:
                lines.append("📋 各类型天劫统计：")
                lines.append("")

                type_names = {
                    'thunder': '⚡ 雷劫',
                    'fire': '🔥 火劫',
                    'heart_demon': '👹 心魔劫',
                    'wind': '💨 风劫',
                    'ice': '❄️ 冰劫',
                    'mixed': '🌀 混合天劫'
                }

                for trib_type, type_stat in stats['type_stats'].items():
                    type_name = type_names.get(trib_type, trib_type)
                    total = type_stat['total']
                    success = type_stat['success']
                    rate = (success / total * 100) if total > 0 else 0

                    lines.append(
                        f"{type_name}：{success}/{total} 次 ({rate:.1f}%)"
                    )

            lines.extend([
                "",
                "💡 继续修炼，提升渡劫成功率！"
            ])

            yield event.plain_result("\n".join(lines))

        except PlayerNotFoundError as e:
            yield event.plain_result(str(e))
        except Exception as e:
            logger.error(f"查看天劫统计失败: {e}", exc_info=True)
            yield event.plain_result(f"查看天劫统计失败：{str(e)}")

    # ========== 探索会话管理辅助方法 ==========

    def _create_exploration_session(self, user_id: str, location) -> Dict:
        """创建探索会话"""
        import time
        session = {
            'user_id': user_id,
            'start_time': time.time(),
            'last_activity_time': time.time(),
            'location': location,
            'round': 1,
            'max_rounds': 5,  # 最多5轮
            'status': 'active',
            'story_history': []
        }
        self._exploration_sessions[user_id] = session
        return session

    def _get_exploration_session(self, user_id: str) -> Optional[Dict]:
        """获取探索会话"""
        import time
        session = self._exploration_sessions.get(user_id)
        if session:
            # 检查是否超时（120秒）
            if time.time() - session['last_activity_time'] > 120:
                self._end_exploration_session(user_id)
                return None
        return session

    def _update_session_activity(self, user_id: str):
        """更新会话活动时间"""
        import time
        if user_id in self._exploration_sessions:
            self._exploration_sessions[user_id]['last_activity_time'] = time.time()

    def _end_exploration_session(self, user_id: str):
        """结束探索会话"""
        if user_id in self._exploration_sessions:
            del self._exploration_sessions[user_id]
        if user_id in self._exploration_events:
            del self._exploration_events[user_id]

    # ========== 队伍探索会话管理辅助方法 ==========

    def _create_team_exploration_session(self, team_id: str, location, members: List) -> Dict:
        """创建队伍探索会话"""
        import time
        session = {
            'team_id': team_id,
            'start_time': time.time(),
            'last_activity_time': time.time(),
            'location': location,
            'members': [m['user_id'] for m in members],
            'round': 1,
            'max_rounds': 5,  # 最多5轮
            'status': 'active',
            'story_history': []
        }
        self._team_exploration_sessions[team_id] = session
        return session

    def _get_team_exploration_session(self, team_id: str) -> Optional[Dict]:
        """获取队伍探索会话"""
        import time
        session = self._team_exploration_sessions.get(team_id)
        if session:
            # 检查是否超时（120秒）
            if time.time() - session['last_activity_time'] > 120:
                self._end_team_exploration_session(team_id)
                return None
        return session

    def _update_team_session_activity(self, team_id: str):
        """更新队伍会话活动时间"""
        import time
        if team_id in self._team_exploration_sessions:
            self._team_exploration_sessions[team_id]['last_activity_time'] = time.time()

    def _end_team_exploration_session(self, team_id: str):
        """结束队伍探索会话"""
        if team_id in self._team_exploration_sessions:
            del self._team_exploration_sessions[team_id]
        if team_id in self._team_exploration_events:
            del self._team_exploration_events[team_id]

    async def _handle_team_choice(self, event: AstrMessageEvent, user_id: str, team: Dict, message_text: str):
        """处理队伍探索的选择"""
        team_id = team['id']

        # 检查队伍会话
        session = self._get_team_exploration_session(team_id)
        if not session:
            yield event.plain_result("⚠️ 队伍探索会话已超时\n\n💡 队长可以使用 /开始探索 重新开始")
            return

        # 检查是否有待选择的事件
        if team_id not in self._team_exploration_events:
            yield event.plain_result("⚠️ 当前没有需要选择的事件")
            return

        # 解析选择编号
        parts = message_text.split()
        if len(parts) < 2:
            yield event.plain_result("⚠️ 请输入选择的编号\n\n💡 使用方法：/选择 [编号]\n   例如：/选择 1")
            return

        try:
            choice_num = int(parts[1])
        except ValueError:
            yield event.plain_result("⚠️ 请输入有效的编号！")
            return

        # 获取事件数据
        event_data = self._team_exploration_events[team_id]
        event_info = event_data['event']
        location = event_data['location']
        choices = event_info.get('choices', [])
        choices_made = event_data['choices_made']

        # 检查是否选择了"结束探索"
        num_story_choices = len(choices)
        if choice_num == num_story_choices + 1:
            # 队员选择结束探索
            choices_made[user_id] = 'end'

            # 获取队伍成员
            members = await self.team_mgr.get_team_members(team_id, status='joined')
            remaining = [m['user_id'] for m in members if m['user_id'] not in choices_made]

            if remaining:
                yield event.plain_result(
                    f"✅ 你选择了结束探索\n\n"
                    f"⏳ 等待其他成员选择... ({len(choices_made)}/{len(members)})"
                )
            else:
                # 所有成员都选择了，统计结果
                end_count = sum(1 for c in choices_made.values() if c == 'end')
                if end_count > len(members) / 2:
                    # 多数人选择结束
                    self._end_team_exploration_session(team_id)
                    await self.team_mgr.finish_team_exploration(team_id)
                    yield event.plain_result(
                        "🚪 队伍决定结束探索，离开了此地\n\n"
                        f"📍 本次探索轮次：{session['round']}/{session['max_rounds']}\n"
                        "💡 使用 /开始探索 开始新的探索"
                    )
                else:
                    # 继续探索，忽略结束投票
                    yield event.plain_result("⏳ 等待其他成员选择...")
            return

        # 检查选择是否有效
        choice_index = choice_num - 1
        if choice_index < 0 or choice_index >= len(choices):
            yield event.plain_result(f"⚠️ 无效的选择编号！请选择 1-{num_story_choices + 1}")
            return

        # 记录选择
        choices_made[user_id] = choice_index

        # 获取队伍成员
        members = await self.team_mgr.get_team_members(team_id, status='joined')
        remaining = [m['user_id'] for m in members if m['user_id'] not in choices_made]

        if remaining:
            # 还有成员未选择
            yield event.plain_result(
                f"✅ 你选择了：{choices[choice_index]['text']}\n\n"
                f"⏳ 等待其他成员选择... ({len(choices_made)}/{len(members)})"
            )
            return

        # 所有成员都做了选择，统计结果
        # 排除"结束探索"的选择
        valid_choices = [c for c in choices_made.values() if c != 'end']

        # 使用投票方式，选择最多人选的选项，如果平票则使用队长的选择
        from collections import Counter
        choice_counts = Counter(valid_choices)
        most_common = choice_counts.most_common()

        if most_common:
            final_choice_index = most_common[0][0]

            # 如果有多个选项票数相同，使用队长的选择
            if len(most_common) > 1 and most_common[0][1] == most_common[1][1]:
                leader_choice = choices_made.get(team['leader_id'])
                if leader_choice is not None and leader_choice != 'end':
                    final_choice_index = leader_choice

            selected_choice = choices[final_choice_index]

            # 更新队伍会话活动时间
            self._update_team_session_activity(team_id)

            # 处理选择结果（使用队长作为代表）
            result = await self.world_mgr.handle_event_choice(
                team['leader_id'],
                event_info,
                selected_choice,
                location
            )

            # 清除当前事件
            del self._team_exploration_events[team_id]

            # 显示结果
            lines = [
                f"✓ 队伍选择了：{selected_choice['text']}",
                "─" * 40,
                ""
            ]

            # 显示投票情况
            lines.append("📊 投票结果：")
            for i, choice in enumerate(choices):
                vote_count = sum(1 for c in valid_choices if c == i)
                if vote_count > 0:
                    lines.append(f"   {choice['text']}: {vote_count}票")
            lines.append("")

            # 显示结果描述
            result_text = result.get('outcome_text') or result.get('message')
            if result_text:
                lines.append(result_text)
                lines.append("")

            # 发放奖励给所有队员
            rewards = result.get('rewards', {})
            if rewards:
                lines.append("")
                lines.append("📦 队伍获得奖励：")

                for member in members:
                    member_id = member['user_id']
                    if 'spirit_stone' in rewards and rewards['spirit_stone'] != 0:
                        spirit_stone_change = rewards['spirit_stone']
                        await self.db.execute(
                            "UPDATE players SET spirit_stone = MAX(0, spirit_stone + ?) WHERE user_id = ?",
                            (spirit_stone_change, member_id)
                        )

                    if 'cultivation' in rewards and rewards['cultivation'] != 0:
                        cultivation_change = rewards['cultivation']
                        await self.db.execute(
                            "UPDATE players SET cultivation = MAX(0, cultivation + ?) WHERE user_id = ?",
                            (cultivation_change, member_id)
                        )

                if rewards.get('spirit_stone', 0) > 0:
                    lines.append(f"   💎 灵石 +{rewards['spirit_stone']} (每人)")
                if rewards.get('cultivation', 0) > 0:
                    lines.append(f"   ✨ 修为 +{rewards['cultivation']} (每人)")

            # 处理伤害（所有队员都受伤）
            if result.get('damage', 0) > 0:
                damage = result['damage']
                lines.append("")
                lines.append(f"💔 队伍受到伤害 -{damage} 生命值 (每人)")

                for member in members:
                    member_id = member['user_id']
                    await self.db.execute(
                        "UPDATE players SET hp = MAX(1, hp - ?) WHERE user_id = ?",
                        (damage, member_id)
                    )

            # 检查是否继续探索
            session['round'] += 1
            session['story_history'].append({
                'choice': selected_choice['text'],
                'result': result_text
            })

            if session['round'] <= session['max_rounds']:
                # 继续探索
                lines.append("")
                lines.append("─" * 40)
                lines.append(f"📍 探索继续... (第 {session['round']}/{session['max_rounds']} 轮)")
                lines.append("")

                # 生成新的事件
                next_result = await self.world_mgr.explore_location(location)

                if next_result.get('event'):
                    next_event_info = next_result['event']
                    lines.append(f"📖 {next_event_info['title']}")
                    lines.append("")
                    lines.append(next_event_info['description'])
                    lines.append("")

                    if next_result.get('has_choice') and next_event_info.get('choices'):
                        lines.append("🎯 队伍需要做出选择：")
                        for i, choice in enumerate(next_event_info['choices'], 1):
                            lines.append(f"{i}. {choice['text']} - {choice['description']}")

                        lines.append(f"{len(next_event_info['choices']) + 1}. 🚪 结束探索 - 离开此地")
                        lines.append("")
                        lines.append(f"💡 使用 /选择 [编号] 做出选择")
                        lines.append(f"⏱️ 120秒内无操作将自动结束探索")

                        # 暂存新的事件数据
                        self._team_exploration_events[team_id] = {
                            'event': next_event_info,
                            'location': location,
                            'session': session,
                            'choices_made': {}
                        }
                    else:
                        # 自动结算，探索结束
                        self._end_team_exploration_session(team_id)
                        await self.team_mgr.finish_team_exploration(team_id)
                        lines.append("")
                        lines.append("✅ 队伍探索结束")
                else:
                    # 没有新事件，探索结束
                    self._end_team_exploration_session(team_id)
                    await self.team_mgr.finish_team_exploration(team_id)
                    lines.append("")
                    lines.append("✅ 队伍探索结束")
            else:
                # 达到最大轮次，探索结束
                self._end_team_exploration_session(team_id)
                await self.team_mgr.finish_team_exploration(team_id)
                lines.append("")
                lines.append(f"✅ 队伍探索结束 - 已完成全部 {session['max_rounds']} 轮探索")

            yield event.plain_result("\n".join(lines))

    # ========== 世界探索系统命令 ==========

    @filter.command("地点", alias={"locations", "where", "位置"})
    async def locations_cmd(self, event: AstrMessageEvent):
        """查看当前可到达的地点"""
        user_id = event.get_sender_id()

        try:
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return

            formatted = await self.world_mgr.format_location_list(user_id)
            yield event.plain_result(formatted)

        except PlayerNotFoundError:
            yield event.plain_result("您还没有创建角色，请先使用 /修仙 创建角色")
        except Exception as e:
            logger.error(f"查看地点失败: {e}", exc_info=True)
            yield event.plain_result(f"查看地点失败：{str(e)}")

    @filter.command("地图", alias={"map", "世界地图"})
    async def world_map_cmd(self, event: AstrMessageEvent):
        """查看世界地图"""
        user_id = event.get_sender_id()

        try:
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return

            formatted = await self.world_mgr.format_world_map(user_id)
            yield event.plain_result(formatted)

        except PlayerNotFoundError:
            yield event.plain_result("您还没有创建角色，请先使用 /修仙 创建角色")
        except Exception as e:
            logger.error(f"查看地图失败: {e}", exc_info=True)
            yield event.plain_result(f"查看地图失败：{str(e)}")

    @filter.command("前往", alias={"move", "go", "移动"})
    async def move_cmd(self, event: AstrMessageEvent):
        """前往指定地点"""
        user_id = event.get_sender_id()
        message_text = self._get_message_text(event)

        try:
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return

            # 解析目标地点
            parts = message_text.split()
            if len(parts) < 2:
                yield event.plain_result(
                    "🗺️ 移动到其他地点\n\n"
                    "请指定要前往的地点编号\n\n"
                    "💡 使用方法: /前往 [编号]\n"
                    "💡 例如: /前往 2\n\n"
                    "💡 使用 /地点 查看可到达的地点"
                )
                return

            try:
                destination_index = int(parts[1])
            except ValueError:
                yield event.plain_result("❌ 地点编号必须是数字！")
                return

            # 获取可到达的地点列表
            current_loc, _ = await self.world_mgr.get_player_location(user_id)
            connected_locs = await self.world_mgr.get_connected_locations(current_loc)

            if destination_index < 1 or destination_index > len(connected_locs):
                yield event.plain_result(
                    f"❌ 地点编号 {destination_index} 不存在！\n\n"
                    f"💡 可选编号范围：1-{len(connected_locs)}"
                )
                return

            destination = connected_locs[destination_index - 1]

            # 执行移动
            result = await self.world_mgr.move_to(user_id, destination.id)

            lines = [
                f"🚶 从 {result['from_location']} 前往 {result['to_location']}",
                "",
                result['destination'].get_display_info(),
                "",
                f"🚶 移动次数: {result['move_count']}"
            ]

            if result.get('encounter'):
                encounter = result['encounter']
                lines.extend([
                    "",
                    f"⚠️ {encounter['description']}"
                ])

            yield event.plain_result("\n".join(lines))

        except PlayerNotFoundError:
            yield event.plain_result("您还没有创建角色，请先使用 /修仙 创建角色")
        except MoveCooldownError as e:
            yield event.plain_result(f"⏰ {str(e)}")
        except InvalidMoveError as e:
            yield event.plain_result(f"❌ {str(e)}")
        except WorldException as e:
            yield event.plain_result(f"⚠️ {str(e)}")
        except Exception as e:
            logger.error(f"移动失败: {e}", exc_info=True)
            yield event.plain_result(f"移动失败：{str(e)}")

    @filter.command("探索", alias={"explore", "搜索"})
    async def explore_cmd(self, event: AstrMessageEvent):
        """探索当前地点"""
        user_id = event.get_sender_id()

        try:
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return

            # 检查是否有进行中的探索会话
            existing_session = self._get_exploration_session(user_id)
            if existing_session and existing_session['status'] == 'active':
                yield event.plain_result(
                    f"⚠️ 你正在 {existing_session['location'].name} 探索中！\n\n"
                    f"📍 当前轮次：{existing_session['round']}/{existing_session['max_rounds']}\n"
                    f"💡 请先完成当前的选择，或使用 /结束探索 结束当前探索"
                )
                return

            result = await self.world_mgr.explore_current_location(user_id)
            location = result['location']

            # 创建新的探索会话
            session = self._create_exploration_session(user_id, location)

            lines = [
                f"🔍 开始探索 {location.name}",
                "─" * 40,
                ""
            ]

            # 如果有事件
            if result.get('event'):
                event_info = result['event']
                lines.append(f"📖 {event_info['title']}")
                lines.append("")
                lines.append(event_info['description'])
                lines.append("")

                # 如果需要玩家做出选择
                if result.get('has_choice') and event_info.get('choices'):
                    lines.append("🎯 请选择你的行动：")
                    for i, choice in enumerate(event_info['choices'], 1):
                        lines.append(f"{i}. {choice['text']} - {choice['description']}")

                    # 添加"结束探索"选项
                    lines.append(f"{len(event_info['choices']) + 1}. 🚪 结束探索 - 离开此地")
                    lines.append("")
                    lines.append(f"💡 使用 /选择 [编号] 做出选择 (例如：/选择 1)")
                    lines.append(f"⏱️ 120秒内无操作将自动结束探索")

                    # 暂存事件数据供后续选择使用
                    self._exploration_events[user_id] = {
                        'event': event_info,
                        'location': location,
                        'session': session
                    }
                else:
                    # 自动结算的事件
                    auto_result = event_info.get('auto_result', {})
                    if auto_result.get('message'):
                        lines.append(auto_result['message'])

                    # 发放奖励
                    rewards = auto_result.get('rewards', {})
                    if rewards.get('spirit_stone', 0) > 0:
                        player = await self.player_mgr.get_player(user_id)
                        await self.db.execute(
                            "UPDATE players SET spirit_stone = spirit_stone + ? WHERE user_id = ?",
                            (rewards['spirit_stone'], user_id)
                        )
                        lines.append(f"💎 灵石 +{rewards['spirit_stone']}")

                    if rewards.get('cultivation', 0) > 0:
                        await self.db.execute(
                            "UPDATE players SET cultivation = cultivation + ? WHERE user_id = ?",
                            (rewards['cultivation'], user_id)
                        )
                        lines.append(f"✨ 修为 +{rewards['cultivation']}")

                    # 处理伤害
                    if auto_result.get('damage', 0) > 0:
                        damage = auto_result['damage']
                        await self.db.execute(
                            "UPDATE players SET hp = MAX(1, hp - ?) WHERE user_id = ?",
                            (damage, user_id)
                        )
                        lines.append(f"💔 生命值 -{damage}")
            else:
                # 没有触发事件
                lines.append("🌫️ 什么也没有发现...")
                lines.append("")
                lines.append("💡 提示：探索有概率触发各种事件")
                lines.append("   • 地点危险等级越高，事件越丰富")
                lines.append("   • 灵气浓度越高，好事件概率越大")

            yield event.plain_result("\n".join(lines))

        except PlayerNotFoundError:
            yield event.plain_result("您还没有创建角色，请先使用 /修仙 创建角色")
        except WorldException as e:
            yield event.plain_result(f"⚠️ {str(e)}")
        except Exception as e:
            logger.error(f"探索失败: {e}", exc_info=True)
            yield event.plain_result(f"探索失败：{str(e)}")

    @filter.command("选择", alias={"choice", "choose"})
    async def event_choice_cmd(self, event: AstrMessageEvent):
        """处理探索事件的选择"""
        user_id = event.get_sender_id()
        message_text = self._get_message_text(event)

        try:
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return

            # 优先检查用户是否在队伍探索中
            team = await self.team_mgr.get_player_active_team(user_id)
            if team and team['status'] == 'active':
                # 处理队伍探索的选择
                async for result in self._handle_team_choice(event, user_id, team, message_text):
                    yield result
                return

            # 检查会话是否超时
            session = self._get_exploration_session(user_id)
            if not session:
                yield event.plain_result("⚠️ 探索会话已超时\n\n💡 使用 /探索 重新开始探索")
                return

            # 检查是否有待选择的事件
            if user_id not in self._exploration_events:
                yield event.plain_result("⚠️ 当前没有需要选择的事件\n\n💡 使用 /探索 开始探索")
                return

            # 解析选择编号
            parts = message_text.split()
            if len(parts) < 2:
                yield event.plain_result("⚠️ 请输入选择的编号\n\n💡 使用方法：/选择 [编号]\n   例如：/选择 1")
                return

            try:
                choice_num = int(parts[1])
            except ValueError:
                yield event.plain_result("⚠️ 请输入有效的编号！")
                return

            # 获取事件数据
            event_data = self._exploration_events[user_id]
            event_info = event_data['event']
            location = event_data['location']
            choices = event_info.get('choices', [])

            # 检查是否选择了"结束探索"
            num_story_choices = len(choices)
            if choice_num == num_story_choices + 1:
                # 玩家选择结束探索
                self._end_exploration_session(user_id)
                yield event.plain_result(
                    "🚪 你结束了这次探索，离开了此地\n\n"
                    f"📍 本次探索轮次：{session['round']}/{session['max_rounds']}\n"
                    "💡 使用 /探索 开始新的探索"
                )
                return

            # 检查选择是否有效
            choice_index = choice_num - 1
            if choice_index < 0 or choice_index >= len(choices):
                yield event.plain_result(f"⚠️ 无效的选择编号！请选择 1-{num_story_choices + 1}")
                return

            selected_choice = choices[choice_index]

            # 更新会话活动时间
            self._update_session_activity(user_id)

            # 处理选择结果
            result = await self.world_mgr.handle_event_choice(
                user_id,
                event_info,
                selected_choice,
                location
            )

            # 清除当前事件
            del self._exploration_events[user_id]

            # 显示结果
            lines = [
                f"✓ 你选择了：{selected_choice['text']}",
                "─" * 40,
                ""
            ]

            # 显示结果描述（优先使用 outcome_text，回退到 message）
            result_text = result.get('outcome_text') or result.get('message')
            if result_text:
                lines.append(result_text)
                lines.append("")

            # 发放奖励
            rewards = result.get('rewards', {})
            if rewards:
                lines.append("")
                reward_lines = []

                if 'spirit_stone' in rewards and rewards['spirit_stone'] != 0:
                    spirit_stone_change = rewards['spirit_stone']
                    await self.db.execute(
                        "UPDATE players SET spirit_stone = MAX(0, spirit_stone + ?) WHERE user_id = ?",
                        (spirit_stone_change, user_id)
                    )
                    if spirit_stone_change > 0:
                        reward_lines.append(f"   💎 灵石 +{spirit_stone_change}")
                    else:
                        reward_lines.append(f"   💎 灵石 {spirit_stone_change}")

                if 'cultivation' in rewards and rewards['cultivation'] != 0:
                    cultivation_change = rewards['cultivation']
                    await self.db.execute(
                        "UPDATE players SET cultivation = MAX(0, cultivation + ?) WHERE user_id = ?",
                        (cultivation_change, user_id)
                    )
                    if cultivation_change > 0:
                        reward_lines.append(f"   ✨ 修为 +{cultivation_change}")
                    else:
                        reward_lines.append(f"   ✨ 修为 {cultivation_change}")

                if reward_lines:
                    lines.append("📦 获得奖励：" if any(rewards.get(k, 0) > 0 for k in rewards) else "💰 消耗资源：")
                    lines.extend(reward_lines)

            # 处理伤害
            if result.get('damage', 0) > 0:
                damage = result['damage']
                await self.db.execute(
                    "UPDATE players SET hp = MAX(1, hp - ?) WHERE user_id = ?",
                    (damage, user_id)
                )
                lines.append(f"\n💔 生命值 -{damage}")

                # 检查血量是否归零
                player = await self.player_mgr.get_player(user_id)
                if player and player.hp <= 1:
                    # 应用重伤状态
                    injury_info = await self.status_mgr.apply_injured_status(user_id, severity=1)
                    lines.append("\n" + "=" * 40)
                    lines.append("💔 你受了重伤，无法继续探索！")
                    lines.append(f"⚠️ {injury_info['data']['description']}")
                    lines.append("🏥 请回去休息恢复...")

                    # 强制结束探索
                    self._end_exploration_session(user_id)

                    yield event.plain_result("\n".join(lines))
                    return

            # 检查是否继续探索
            session['round'] += 1
            session['story_history'].append({
                'choice': selected_choice['text'],
                'result': result_text
            })

            if session['round'] <= session['max_rounds']:
                # 继续生成下一轮故事
                lines.append("")
                lines.append("─" * 40)
                lines.append(f"📍 探索继续... (第 {session['round']}/{session['max_rounds']} 轮)")
                lines.append("")

                # 生成新的故事
                next_result = await self.world_mgr.explore_current_location(user_id)

                if next_result.get('event'):
                    next_event_info = next_result['event']
                    lines.append(f"📖 {next_event_info['title']}")
                    lines.append("")
                    lines.append(next_event_info['description'])
                    lines.append("")

                    if next_result.get('has_choice') and next_event_info.get('choices'):
                        lines.append("🎯 请选择你的行动：")
                        for i, choice in enumerate(next_event_info['choices'], 1):
                            lines.append(f"{i}. {choice['text']} - {choice['description']}")

                        # 添加"结束探索"选项
                        lines.append(f"{len(next_event_info['choices']) + 1}. 🚪 结束探索 - 离开此地")
                        lines.append("")
                        lines.append(f"💡 使用 /选择 [编号] 做出选择")
                        lines.append(f"⏱️ 120秒内无操作将自动结束探索")

                        # 暂存新的事件数据
                        self._exploration_events[user_id] = {
                            'event': next_event_info,
                            'location': location,
                            'session': session
                        }
                    else:
                        # 自动结算，探索结束
                        self._end_exploration_session(user_id)
                        lines.append("")
                        lines.append("✅ 探索结束")
                else:
                    # 没有新事件，探索结束
                    self._end_exploration_session(user_id)
                    lines.append("")
                    lines.append("✅ 探索结束")
            else:
                # 达到最大轮次，探索结束
                self._end_exploration_session(user_id)
                lines.append("")
                lines.append(f"✅ 探索结束 - 已完成全部 {session['max_rounds']} 轮探索")

            yield event.plain_result("\n".join(lines))

        except PlayerNotFoundError:
            yield event.plain_result("您还没有创建角色，请先使用 /修仙 创建角色")
        except Exception as e:
            logger.error(f"处理选择失败: {e}", exc_info=True)
            yield event.plain_result(f"处理选择失败：{str(e)}")

    @filter.command("结束探索", alias={"end_explore", "离开"})
    async def end_exploration_cmd(self, event: AstrMessageEvent):
        """主动结束当前探索"""
        user_id = event.get_sender_id()

        try:
            session = self._get_exploration_session(user_id)
            if not session:
                yield event.plain_result("⚠️ 你当前没有进行中的探索")
                return

            # 结束探索
            self._end_exploration_session(user_id)
            yield event.plain_result(
                "🚪 你结束了这次探索，离开了此地\n\n"
                f"📍 本次探索轮次：{session['round']}/{session['max_rounds']}\n"
                "💡 使用 /探索 开始新的探索"
            )

        except Exception as e:
            logger.error(f"结束探索失败: {e}", exc_info=True)
            yield event.plain_result(f"结束探索失败：{str(e)}")

    # ========== 组队探索系统命令 ==========

    @filter.command("组队探索", alias={"team_explore", "邀请探索"})
    async def team_explore_cmd(self, event: AstrMessageEvent):
        """创建队伍并邀请其他玩家一起探索"""
        user_id = event.get_sender_id()
        message_text = self._get_message_text(event)

        try:
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return

            # 解析@的用户列表
            # 支持格式：/组队探索 @user1 @user2 或 /组队探索 user1 user2
            parts = message_text.split()
            if len(parts) < 2:
                yield event.plain_result(
                    "⚠️ 请@要邀请的玩家\n\n"
                    "💡 使用方法：/组队探索 @user1 @user2\n"
                    "   或：/组队探索 user1 user2"
                )
                return

            # 提取被邀请的玩家ID（这里需要根据实际情况解析@）
            # 简化版：假设后面跟的是用户ID
            invited_users = []
            for part in parts[1:]:
                invited_id = part.strip('@').strip()
                if invited_id and invited_id != user_id:
                    invited_users.append(invited_id)

            if not invited_users:
                yield event.plain_result("⚠️ 请至少邀请一位其他玩家")
                return

            # 检查是否已有活跃队伍
            existing_team = await self.team_mgr.get_player_active_team(user_id)
            if existing_team:
                yield event.plain_result("⚠️ 你已经在一个队伍中了！\n\n💡 使用 /离开队伍 先离开当前队伍")
                return

            # 获取玩家当前位置
            location, _ = await self.world_mgr.get_player_location(user_id)

            # 创建队伍
            team_id = await self.team_mgr.create_team(user_id, location.id)

            # 发送邀请
            success_invites = []
            failed_invites = []
            for invited_id in invited_users:
                try:
                    await self.team_mgr.invite_member(team_id, invited_id, user_id)
                    success_invites.append(invited_id)
                except Exception as e:
                    failed_invites.append(f"{invited_id}: {str(e)}")

            lines = [
                f"🎉 探索队伍已创建！",
                f"📍 地点：{location.name}",
                f"👥 队长：你",
                ""
            ]

            if success_invites:
                lines.append("✅ 成功邀请：")
                for inv_id in success_invites:
                    lines.append(f"   • {inv_id}")
                lines.append("")
                lines.append("⏳ 等待队员接受邀请（30秒超时）")

            if failed_invites:
                lines.append("")
                lines.append("❌ 邀请失败：")
                for fail in failed_invites:
                    lines.append(f"   • {fail}")

            yield event.plain_result("\n".join(lines))

        except Exception as e:
            logger.error(f"组队探索失败: {e}", exc_info=True)
            yield event.plain_result(f"组队探索失败：{str(e)}")

    @filter.command("查看邀请", alias={"my_invites", "探索邀请"})
    async def view_invites_cmd(self, event: AstrMessageEvent):
        """查看收到的探索邀请"""
        user_id = event.get_sender_id()

        try:
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return

            invites = await self.team_mgr.get_player_invites(user_id)

            if not invites:
                yield event.plain_result("📭 你当前没有待处理的探索邀请")
                return

            lines = ["📬 探索邀请列表", "─" * 40, ""]

            for i, invite in enumerate(invites, 1):
                # 获取地点信息
                location = await self.world_mgr.get_location(invite['location_id'])
                lines.append(f"{i}. 队长：{invite['leader_id']}")
                lines.append(f"   地点：{location.name if location else '未知'}")
                lines.append("")

            lines.append("💡 使用以下命令响应邀请：")
            lines.append("   /接受邀请 [队伍编号]")
            lines.append("   /拒绝邀请 [队伍编号]")

            yield event.plain_result("\n".join(lines))

        except Exception as e:
            logger.error(f"查看邀请失败: {e}", exc_info=True)
            yield event.plain_result(f"查看邀请失败：{str(e)}")

    @filter.command("接受邀请", alias={"accept_invite", "同意探索"})
    async def accept_invite_cmd(self, event: AstrMessageEvent):
        """接受探索邀请"""
        user_id = event.get_sender_id()
        message_text = self._get_message_text(event)

        try:
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return

            parts = message_text.split()
            if len(parts) < 2:
                yield event.plain_result("⚠️ 请指定要接受的邀请编号\n\n💡 使用方法：/接受邀请 [编号]")
                return

            try:
                invite_num = int(parts[1])
            except ValueError:
                yield event.plain_result("⚠️ 请输入有效的编号！")
                return

            # 获取邀请列表
            invites = await self.team_mgr.get_player_invites(user_id)
            if invite_num < 1 or invite_num > len(invites):
                yield event.plain_result(f"⚠️ 无效的编号！请选择 1-{len(invites)}")
                return

            invite = invites[invite_num - 1]
            team_id = invite['id']

            # 接受邀请
            await self.team_mgr.accept_invite(team_id, user_id)

            # 获取队伍信息
            team = await self.team_mgr.get_team(team_id)
            location = await self.world_mgr.get_location(team['location_id'])

            yield event.plain_result(
                f"✅ 已加入探索队伍！\n\n"
                f"📍 地点：{location.name if location else '未知'}\n"
                f"👥 队长：{team['leader_id']}\n\n"
                f"⏳ 等待队长开始探索..."
            )

        except Exception as e:
            logger.error(f"接受邀请失败: {e}", exc_info=True)
            yield event.plain_result(f"接受邀请失败：{str(e)}")

    @filter.command("拒绝邀请", alias={"reject_invite", "拒绝探索"})
    async def reject_invite_cmd(self, event: AstrMessageEvent):
        """拒绝探索邀请"""
        user_id = event.get_sender_id()
        message_text = self._get_message_text(event)

        try:
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return

            parts = message_text.split()
            if len(parts) < 2:
                yield event.plain_result("⚠️ 请指定要拒绝的邀请编号\n\n💡 使用方法：/拒绝邀请 [编号]")
                return

            try:
                invite_num = int(parts[1])
            except ValueError:
                yield event.plain_result("⚠️ 请输入有效的编号！")
                return

            # 获取邀请列表
            invites = await self.team_mgr.get_player_invites(user_id)
            if invite_num < 1 or invite_num > len(invites):
                yield event.plain_result(f"⚠️ 无效的编号！请选择 1-{len(invites)}")
                return

            invite = invites[invite_num - 1]
            team_id = invite['id']

            # 拒绝邀请
            await self.team_mgr.reject_invite(team_id, user_id)

            yield event.plain_result("✅ 已拒绝探索邀请")

        except Exception as e:
            logger.error(f"拒绝邀请失败: {e}", exc_info=True)
            yield event.plain_result(f"拒绝邀请失败：{str(e)}")

    @filter.command("离开队伍", alias={"leave_team", "退出队伍"})
    async def leave_team_cmd(self, event: AstrMessageEvent):
        """离开当前探索队伍"""
        user_id = event.get_sender_id()

        try:
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return

            # 获取玩家当前队伍
            team = await self.team_mgr.get_player_active_team(user_id)
            if not team:
                yield event.plain_result("⚠️ 你当前不在任何队伍中")
                return

            # 离开队伍
            await self.team_mgr.leave_team(team['id'], user_id)

            if team['leader_id'] == user_id:
                yield event.plain_result("✅ 队伍已解散")
            else:
                yield event.plain_result("✅ 已离开队伍")

        except Exception as e:
            logger.error(f"离开队伍失败: {e}", exc_info=True)
            yield event.plain_result(f"离开队伍失败：{str(e)}")

    @filter.command("查看队伍", alias={"team_status", "队伍状态", "我的队伍"})
    async def team_status_cmd(self, event: AstrMessageEvent):
        """查看当前队伍状态"""
        user_id = event.get_sender_id()

        try:
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return

            # 获取玩家当前队伍
            team = await self.team_mgr.get_player_active_team(user_id)
            if not team:
                yield event.plain_result("⚠️ 你当前不在任何队伍中\n\n💡 使用 /组队探索 @user 创建队伍")
                return

            # 获取队伍成员
            members = await self.team_mgr.get_team_members(team['id'], status='joined')

            # 获取地点信息
            location = await self.world_mgr.get_location(team['location_id'])

            # 构建显示信息
            lines = [
                "👥 队伍状态",
                "─" * 40,
                ""
            ]

            # 队伍基本信息
            status_emoji = {
                'waiting': '⏳',
                'active': '🔍',
                'finished': '✅'
            }
            status_text = {
                'waiting': '等待中',
                'active': '探索中',
                'finished': '已完成'
            }

            lines.append(f"📍 地点：{location.name if location else '未知'}")
            lines.append(f"{status_emoji.get(team['status'], '❓')} 状态：{status_text.get(team['status'], '未知')}")
            lines.append("")

            # 队伍成员列表
            lines.append("👥 成员列表：")
            for i, member in enumerate(members, 1):
                member_id = member['user_id']
                is_leader = member_id == team['leader_id']
                leader_mark = " 👑 (队长)" if is_leader else ""

                # 获取玩家信息
                try:
                    player = await self.player_mgr.get_player(member_id)
                    name = player.name if player else member_id
                    realm = player.realm if player else "未知"
                    lines.append(f"   {i}. {name} [{realm}]{leader_mark}")
                except:
                    lines.append(f"   {i}. {member_id}{leader_mark}")

            lines.append("")

            # 根据状态显示提示
            if team['status'] == 'waiting':
                if team['leader_id'] == user_id:
                    lines.append("💡 你是队长，可以使用 /开始探索 开始队伍探索")
                else:
                    lines.append("⏳ 等待队长开始探索...")
            elif team['status'] == 'active':
                lines.append("🔍 探索进行中...")
                lines.append("💡 队伍成员可以一起做出选择")

            yield event.plain_result("\n".join(lines))

        except Exception as e:
            logger.error(f"查看队伍状态失败: {e}", exc_info=True)
            yield event.plain_result(f"查看队伍状态失败：{str(e)}")

    @filter.command("开始探索", alias={"start_team_explore", "队伍探索"})
    async def start_team_explore_cmd(self, event: AstrMessageEvent):
        """队长开始队伍探索"""
        user_id = event.get_sender_id()

        try:
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return

            # 获取玩家当前队伍
            team = await self.team_mgr.get_player_active_team(user_id)
            if not team:
                yield event.plain_result("⚠️ 你当前不在任何队伍中\n\n💡 使用 /组队探索 @user 创建队伍")
                return

            # 检查是否是队长
            if team['leader_id'] != user_id:
                yield event.plain_result("⚠️ 只有队长可以开始探索！")
                return

            # 检查队伍状态
            if team['status'] != 'waiting':
                yield event.plain_result("⚠️ 队伍已经开始探索或已结束！")
                return

            # 获取队伍成员
            members = await self.team_mgr.get_team_members(team['id'], status='joined')
            if len(members) < 2:
                yield event.plain_result("⚠️ 队伍至少需要2名成员才能开始探索！\n\n💡 使用 /查看队伍 查看当前成员")
                return

            # 获取地点信息
            location = await self.world_mgr.get_location(team['location_id'])
            if not location:
                yield event.plain_result("❌ 探索地点无效")
                return

            # 开始队伍探索
            await self.team_mgr.start_team_exploration(team['id'])

            # 创建队伍探索会话
            team_session = self._create_team_exploration_session(team['id'], location, members)

            # 触发第一个探索事件
            # 这里使用队长作为代表触发事件
            result = await self.world_mgr.explore_location(location)

            lines = [
                f"🔍 队伍开始探索 {location.name}",
                "─" * 40,
                ""
            ]

            # 显示队伍成员
            lines.append("👥 探索队伍：")
            for member in members:
                try:
                    player = await self.player_mgr.get_player(member['user_id'])
                    name = player.name if player else member['user_id']
                    realm = player.realm if player else "未知"
                    is_leader = member['user_id'] == team['leader_id']
                    leader_mark = " 👑" if is_leader else ""
                    lines.append(f"   • {name} [{realm}]{leader_mark}")
                except:
                    lines.append(f"   • {member['user_id']}")
            lines.append("")

            # 如果有事件
            if result.get('event'):
                event_info = result['event']
                lines.append(f"📖 {event_info['title']}")
                lines.append("")
                lines.append(event_info['description'])
                lines.append("")

                # 如果需要玩家做出选择
                if result.get('has_choice') and event_info.get('choices'):
                    lines.append("🎯 队伍需要做出选择：")
                    for i, choice in enumerate(event_info['choices'], 1):
                        lines.append(f"{i}. {choice['text']} - {choice['description']}")

                    # 添加"结束探索"选项
                    lines.append(f"{len(event_info['choices']) + 1}. 🚪 结束探索 - 离开此地")
                    lines.append("")
                    lines.append(f"💡 使用 /选择 [编号] 做出选择 (例如：/选择 1)")
                    lines.append(f"⏱️ 120秒内无操作将自动结束探索")

                    # 暂存事件数据供后续选择使用
                    self._team_exploration_events[team['id']] = {
                        'event': event_info,
                        'location': location,
                        'session': team_session,
                        'choices_made': {}  # 记录每个成员的选择
                    }
                else:
                    # 自动结算的事件
                    auto_result = event_info.get('auto_result', {})
                    if auto_result.get('message'):
                        lines.append(auto_result['message'])

                    # 发放奖励给所有队员
                    rewards = auto_result.get('rewards', {})
                    if rewards:
                        lines.append("")
                        lines.append("📦 队伍获得奖励：")
                        for member in members:
                            member_id = member['user_id']
                            if rewards.get('spirit_stone', 0) > 0:
                                await self.db.execute(
                                    "UPDATE players SET spirit_stone = spirit_stone + ? WHERE user_id = ?",
                                    (rewards['spirit_stone'], member_id)
                                )
                            if rewards.get('cultivation', 0) > 0:
                                await self.db.execute(
                                    "UPDATE players SET cultivation = cultivation + ? WHERE user_id = ?",
                                    (rewards['cultivation'], member_id)
                                )

                        if rewards.get('spirit_stone', 0) > 0:
                            lines.append(f"   💎 灵石 +{rewards['spirit_stone']} (每人)")
                        if rewards.get('cultivation', 0) > 0:
                            lines.append(f"   ✨ 修为 +{rewards['cultivation']} (每人)")
            else:
                # 没有触发事件
                lines.append("🌫️ 什么也没有发现...")
                lines.append("")
                lines.append("💡 提示：探索有概率触发各种事件")

            yield event.plain_result("\n".join(lines))

        except Exception as e:
            logger.error(f"开始队伍探索失败: {e}", exc_info=True)
            yield event.plain_result(f"开始队伍探索失败：{str(e)}")

    @filter.command("地点详情", alias={"location_info", "地点信息"})
    async def location_info_cmd(self, event: AstrMessageEvent):
        """查看地点详细信息"""
        user_id = event.get_sender_id()
        message_text = self._get_message_text(event)

        try:
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return

            parts = message_text.split()
            if len(parts) < 2:
                # 显示当前地点详情
                current_loc, _ = await self.world_mgr.get_player_location(user_id)
                yield event.plain_result(current_loc.get_display_info(show_coordinates=True))
                return

            # 解析地点编号或名称
            location = None
            try:
                # 尝试作为编号解析
                location_index = int(parts[1])
                current_loc, _ = await self.world_mgr.get_player_location(user_id)
                connected_locs = await self.world_mgr.get_connected_locations(current_loc)

                if 1 <= location_index <= len(connected_locs):
                    location = connected_locs[location_index - 1]
            except ValueError:
                # 作为名称解析
                location_name = " ".join(parts[1:])
                location = await self.world_mgr.get_location_by_name(location_name)

            if not location:
                yield event.plain_result("❌ 地点不存在或无法查看")
                return

            yield event.plain_result(location.get_display_info(show_coordinates=True))

        except PlayerNotFoundError:
            yield event.plain_result("您还没有创建角色，请先使用 /修仙 创建角色")
        except Exception as e:
            logger.error(f"查看地点详情失败: {e}", exc_info=True)
            yield event.plain_result(f"查看地点详情失败：{str(e)}")

    @filter.command("修仙帮助", alias={"xiuxian", "help"})
    async def help_cmd(self, event: AstrMessageEvent):
        """显示帮助信息"""
        help_text = """📖修仙世界命令
基础: /修仙[道号] /属性 /灵根 /突破
修炼: /修炼 单次修炼 | /修炼功法[#] /闭关[时长] /出关 /闭关信息
战斗: /切磋@用户 /战力 /挑战[等级] /使用技能[技能名]
装备: /储物袋 /装备[#] /卸下[槽位] /强化[#] /获得装备[类型]
技能: /技能 /使用技能[技能名]
世界: /地点 /地图 /前往[#] /探索 /地点详情 /结束探索
组队: /组队探索[@用户] /查看邀请 /接受邀请[#] /拒绝邀请[#] /查看队伍 /开始探索 /离开队伍
职业: /学习职业[类型] /我的职业
炼丹: /丹方列表 /炼丹[#]
炼器: /图纸列表 /炼器[#]
阵法: /阵法列表 /布阵[#]
符箓: /符箓列表 /制符[#][量] /我的符箓
物品: /使用[物品名]
坊市: /坊市 /上架[类型][#][价][量] /购买[#] /下架[#] /我的上架
宗门: /宗门列表 /加入宗门[名] /宗门信息 /宗门帮助 (详细命令)
灵宠: /领取灵宠[#] /我的灵宠 /激活灵宠[#] /灵宠秘境 /灵宠详情[#]
养成: /喂养灵宠[#] /训练灵宠[#] /升级灵宠[#] /进化灵宠[#]
天劫: /渡劫 /天劫信息 /天劫历史 /天劫统计
功法: /功法 /功法装备[#][槽] /已装备功法 /功法详情[#] /获得功法[类型]
AI: /AI生成[类型] /AI历史 /AI帮助
详细:/功法帮助 /宗门帮助 /AI帮助""".strip()
        yield event.plain_result(help_text)

    # ========== 职业系统命令 ==========

    @filter.command("学习职业", alias={"学职业", "拜师"})
    async def learn_profession_cmd(self, event: AstrMessageEvent):
        """学习新职业"""
        user_id = event.get_sender_id()

        try:
            # 确保插件已初始化
            if not await self._ensure_initialized():
                yield event.plain_result("❌ 修仙世界初始化失败，请使用 /修仙初始化 命令查看详情")
                return

            # 获取职业类型参数
            text = self._get_message_text(event)
            args = text.split()

            # 职业类型映射
            profession_map = {
                "炼丹师": "alchemist",
                "炼器师": "blacksmith",
                "阵法师": "formation_master",
                "符箓师": "talisman_master"
            }

            if len(args) < 2:
                yield event.plain_result(
                    "📜 学习职业\n"
                    "─" * 40 + "\n\n"
                    "请选择要学习的职业：\n\n"
                    "🔥 炼丹师 - 精通炼制各类丹药\n"
                    "⚒️ 炼器师 - 精通炼制各类法宝装备\n"
                    "⭐ 阵法师 - 精通布置和破解各类阵法\n"
                    "📜 符箓师 - 精通制作和使用各类符箓\n\n"
                    "💡 使用方法: /学习职业 [职业类型]\n"
                    "💡 例如: /学习职业 炼丹师"
                )
                return

            profession_name = args[1]
            profession_type = profession_map.get(profession_name)

            if not profession_type:
                yield event.plain_result(
                    f"❌ 无效的职业类型: {profession_name}\n\n"
                    "可选职业: 炼丹师、炼器师、阵法师、符箓师"
                )
                return

            # 学习职业
            profession = await self.profession_mgr.learn_profession(user_id, profession_type)

            yield event.plain_result(
                f"🎉 恭喜道友学习了{profession.get_profession_name()}职业！\n\n"
                f"{profession.get_display_info()}\n\n"
                f"💡 使用 /我的职业 查看职业信息\n"
                f"💡 使用 /{profession.get_profession_name()[0:2]}列�� 查看可用配方"
            )

        except PlayerNotFoundError:
            yield event.plain_result("您还没有创建角色，请先使用 /修仙 创建角色")
        except AlreadyLearnedError as e:
            yield event.plain_result(f"❌ {str(e)}")
        except ValueError as e:
            yield event.plain_result(f"❌ {str(e)}")
        except Exception as e:
            logger.error(f"学习职业失败: {e}", exc_info=True)
            yield event.plain_result(f"学习职业失败：{str(e)}")

    @filter.command("我的职业", alias={"职业", "profession", "职业列表"})
    async def my_professions_cmd(self, event: AstrMessageEvent):
        """查看已学习的职业"""
        user_id = event.get_sender_id()

        try:
            # 检查插件是否已初始化
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return

            # 获取职业列表
            formatted = await self.profession_mgr.format_profession_list(user_id)
            yield event.plain_result(formatted)

        except PlayerNotFoundError:
            yield event.plain_result("您还没有创建角色，请先使用 /修仙 创建角色")
        except Exception as e:
            logger.error(f"查看职业失败: {e}", exc_info=True)
            yield event.plain_result(f"查看职业失败：{str(e)}")

    # ========== 炼丹系统命令 ==========

    @filter.command("丹方列表", alias={"丹方", "alchemy_recipes"})
    async def alchemy_recipes_cmd(self, event: AstrMessageEvent):
        """查看可用丹方列表"""
        user_id = event.get_sender_id()
        try:
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return
            formatted = await self.alchemy_sys.format_recipe_list(user_id)
            yield event.plain_result(formatted)
        except PlayerNotFoundError:
            yield event.plain_result("您还没有创建角色，请先使用 /修仙 创建角色")
        except Exception as e:
            logger.error(f"查看丹方列表失败: {e}", exc_info=True)
            yield event.plain_result(f"查看丹方列表失败：{str(e)}")

    @filter.command("炼丹", alias={"refine_pill", "炼制丹药"})
    async def refine_pill_cmd(self, event: AstrMessageEvent):
        """炼制丹药"""
        user_id = event.get_sender_id()
        try:
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return
            text = self._get_message_text(event)
            args = text.split()
            if len(args) < 2:
                yield event.plain_result(
                    "📜 炼制丹药\n" + "─" * 40 + "\n\n"
                    "请指定要炼制的丹方编号\n\n"
                    "💡 使用方法: /炼丹 [丹方编号]\n"
                    "💡 例如: /炼丹 1\n\n"
                    "💡 使用 /丹方列表 查看可用丹方"
                )
                return
            try:
                recipe_id = int(args[1])
            except ValueError:
                yield event.plain_result("❌ 丹方编号必须是数字")
                return
            result = await self.alchemy_sys.refine_pill(user_id, recipe_id)
            if result['success']:
                yield event.plain_result(
                    f"🎉 {result['message']}\n\n"
                    f"丹药名称: {result['quality']}{result['pill_name']}\n"
                    f"消耗灵石: {result['spirit_stone_cost']}\n"
                    f"获得经验: {result['experience_gained']}\n"
                    f"获得声望: {result['reputation_gained']}"
                )
            else:
                yield event.plain_result(f"😞 {result['message']}\n\n消耗灵石: {result['spirit_stone_cost']}\n获得经验: {result['experience_gained']}")
        except PlayerNotFoundError:
            yield event.plain_result("您还没有创建角色，请先使用 /修仙 创建角色")
        except ProfessionNotFoundError as e:
            yield event.plain_result(f"❌ {str(e)}\n\n💡 使用 /学习职业 炼丹师 学习炼丹")
        except RecipeNotFoundError as e:
            yield event.plain_result(f"❌ {str(e)}")
        except AlchemyError as e:
            yield event.plain_result(f"❌ {str(e)}")
        except Exception as e:
            logger.error(f"炼丹失败: {e}", exc_info=True)
            yield event.plain_result(f"炼丹失败：{str(e)}")

    # ========== 炼器系统命令 ==========

    @filter.command("图纸列表", alias={"图纸", "refining_blueprints"})
    async def refining_blueprints_cmd(self, event: AstrMessageEvent):
        """查看可用图纸列表"""
        user_id = event.get_sender_id()
        try:
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return
            formatted = await self.refining_sys.format_blueprint_list(user_id)
            yield event.plain_result(formatted)
        except PlayerNotFoundError:
            yield event.plain_result("您还没有创建角色，请先使用 /修仙 创建角色")
        except Exception as e:
            logger.error(f"查看图纸列表失败: {e}", exc_info=True)
            yield event.plain_result(f"查看图纸列表失败：{str(e)}")

    @filter.command("炼器", alias={"refine_equipment", "炼制装备"})
    async def refine_equipment_cmd(self, event: AstrMessageEvent):
        """炼制装备"""
        user_id = event.get_sender_id()
        try:
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return
            text = self._get_message_text(event)
            args = text.split()
            if len(args) < 2:
                yield event.plain_result(
                    "📜 炼制装备\n" + "─" * 40 + "\n\n"
                    "请指定要炼制的图纸编号\n\n"
                    "💡 使用方法: /炼器 [图纸编号]\n"
                    "💡 例如: /炼器 1\n\n"
                    "💡 使用 /图纸列表 查看可用图纸"
                )
                return
            try:
                blueprint_id = int(args[1])
            except ValueError:
                yield event.plain_result("❌ 图纸编号必须是数字")
                return
            result = await self.refining_sys.refine_equipment(user_id, blueprint_id)
            if result['success']:
                attrs_str = "\n".join([f"  {k}: {v}" for k, v in result['attributes'].items()])
                yield event.plain_result(
                    f"🎉 {result['message']}\n\n"
                    f"装备名称: {result['quality']}{result['equipment_name']}\n"
                    f"装备ID: {result['equipment_id']}\n"
                    f"属性:\n{attrs_str}\n\n"
                    f"消耗灵石: {result['spirit_stone_cost']}\n"
                    f"获得经验: {result['experience_gained']}\n"
                    f"获得声望: {result['reputation_gained']}"
                )
            else:
                yield event.plain_result(f"😞 {result['message']}\n\n消耗灵石: {result['spirit_stone_cost']}\n获得经验: {result['experience_gained']}")
        except PlayerNotFoundError:
            yield event.plain_result("您还没有创建角色，请先使用 /修仙 创建角色")
        except ProfessionNotFoundError as e:
            yield event.plain_result(f"❌ {str(e)}\n\n💡 使用 /学习职业 炼器师 学习炼器")
        except BlueprintNotFoundError as e:
            yield event.plain_result(f"❌ {str(e)}")
        except RefiningError as e:
            yield event.plain_result(f"❌ {str(e)}")
        except Exception as e:
            logger.error(f"炼器失败: {e}", exc_info=True)
            yield event.plain_result(f"炼器失败：{str(e)}")

    # ========== 阵法系统命令 ==========

    @filter.command("阵法列表", alias={"阵法", "formation_list"})
    async def formation_list_cmd(self, event: AstrMessageEvent):
        """查看可用阵法列表"""
        user_id = event.get_sender_id()
        try:
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return
            formatted = await self.formation_sys.format_formation_list(user_id)
            yield event.plain_result(formatted)
        except PlayerNotFoundError:
            yield event.plain_result("您还没有创建角色，请先使用 /修仙 创建角色")
        except Exception as e:
            logger.error(f"查看阵法列表失败: {e}", exc_info=True)
            yield event.plain_result(f"查看阵法列表失败：{str(e)}")

    @filter.command("布阵", alias={"deploy_formation", "布置阵法"})
    async def deploy_formation_cmd(self, event: AstrMessageEvent):
        """布置阵法"""
        user_id = event.get_sender_id()
        try:
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return
            text = self._get_message_text(event)
            args = text.split()
            if len(args) < 2:
                yield event.plain_result(
                    "📜 布置阵法\n" + "─" * 40 + "\n\n"
                    "请指定要布置的阵法编号\n\n"
                    "💡 使用方法: /布阵 [阵法编号]\n"
                    "💡 例如: /布阵 1\n\n"
                    "💡 使用 /阵法列表 查看可用阵法"
                )
                return
            try:
                formation_id = int(args[1])
            except ValueError:
                yield event.plain_result("❌ 阵法编号必须是数字")
                return
            result = await self.formation_sys.deploy_formation(user_id, formation_id)
            if result['success']:
                yield event.plain_result(
                    f"🎉 {result['message']}\n\n"
                    f"阵法名称: {result['formation_name']}\n"
                    f"阵法类型: {result['formation_type']}\n"
                    f"布阵位置: {result['location']}\n"
                    f"阵法强度: {result['strength']}\n"
                    f"作用范围: {result['range']}米\n"
                    f"持续时间: {result['duration_hours']}小时\n"
                    f"过期时间: {result['expires_at']}\n\n"
                    f"消耗灵石: {result['spirit_stone_cost']}\n"
                    f"获得经验: {result['experience_gained']}\n"
                    f"获得声望: {result['reputation_gained']}"
                )
            else:
                yield event.plain_result(f"😞 {result['message']}\n\n消耗灵石: {result['spirit_stone_cost']}\n获得经验: {result['experience_gained']}")
        except PlayerNotFoundError:
            yield event.plain_result("您还没有创建角色，请先使用 /修仙 创建角色")
        except ProfessionNotFoundError as e:
            yield event.plain_result(f"❌ {str(e)}\n\n💡 使用 /学习职业 阵法师 学习阵法")
        except FormationPatternNotFoundError as e:
            yield event.plain_result(f"❌ {str(e)}")
        except FormationAlreadyExistsError as e:
            yield event.plain_result(f"❌ {str(e)}")
        except FormationError as e:
            yield event.plain_result(f"❌ {str(e)}")
        except Exception as e:
            logger.error(f"布阵失败: {e}", exc_info=True)
            yield event.plain_result(f"布阵失败：{str(e)}")

    # ========== 符箓系统命令 ==========

    @filter.command("符箓列表", alias={"符箓", "talisman_list"})
    async def talisman_list_cmd(self, event: AstrMessageEvent):
        """查看可用符箓配方列表"""
        user_id = event.get_sender_id()
        try:
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return
            formatted = await self.talisman_sys.format_talisman_list(user_id)
            yield event.plain_result(formatted)
        except PlayerNotFoundError:
            yield event.plain_result("您还没有创建角色，请先使用 /修仙 创建角色")
        except Exception as e:
            logger.error(f"查看符箓列表失败: {e}", exc_info=True)
            yield event.plain_result(f"查看符箓列表失败：{str(e)}")

    @filter.command("制符", alias={"craft_talisman", "制作符箓"})
    async def craft_talisman_cmd(self, event: AstrMessageEvent):
        """制作符箓"""
        user_id = event.get_sender_id()
        try:
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return
            text = self._get_message_text(event)
            args = text.split()
            if len(args) < 2:
                yield event.plain_result(
                    "📜 制作符箓\n" + "─" * 40 + "\n\n"
                    "请指定要制作的符箓编号和数量\n\n"
                    "💡 使用方法: /制符 [符箓编号] [数量]\n"
                    "💡 例如: /制符 1 3\n\n"
                    "💡 使用 /符箓列表 查看可用符箓"
                )
                return
            try:
                talisman_id = int(args[1])
                quantity = int(args[2]) if len(args) > 2 else 1
            except ValueError:
                yield event.plain_result("❌ 符箓编号和数量必须是数字")
                return
            result = await self.talisman_sys.craft_talisman(user_id, talisman_id, quantity)
            if result['success']:
                yield event.plain_result(
                    f"🎉 {result['message']}\n\n"
                    f"符箓名称: {result['talisman_name']}\n"
                    f"符箓类型: {result['talisman_type']}\n"
                    f"制作数量: {result['total_quantity']}\n"
                    f"成功数量: {result['success_count']}\n"
                    f"失败数量: {result['failed_count']}\n\n"
                    f"消耗灵石: {result['spirit_stone_cost']}\n"
                    f"获得经验: {result['experience_gained']}\n"
                    f"获得声望: {result['reputation_gained']}"
                )
            else:
                yield event.plain_result(f"😞 {result['message']}\n\n消耗灵石: {result['spirit_stone_cost']}\n获得经验: {result['experience_gained']}")
        except PlayerNotFoundError:
            yield event.plain_result("您还没有创建角色，请先使用 /修仙 创建角色")
        except ProfessionNotFoundError as e:
            yield event.plain_result(f"❌ {str(e)}\n\n💡 使用 /学习职业 符箓师 学习符箓")
        except TalismanPatternNotFoundError as e:
            yield event.plain_result(f"❌ {str(e)}")
        except TalismanError as e:
            yield event.plain_result(f"❌ {str(e)}")
        except Exception as e:
            logger.error(f"制符失败: {e}", exc_info=True)
            yield event.plain_result(f"制符失败：{str(e)}")

    @filter.command("我的符箓", alias={"查看符箓", "player_talismans"})
    async def player_talismans_cmd(self, event: AstrMessageEvent):
        """查看拥有的符箓"""
        user_id = event.get_sender_id()
        try:
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return
            formatted = await self.talisman_sys.format_player_talismans(user_id)
            yield event.plain_result(formatted)
        except PlayerNotFoundError:
            yield event.plain_result("您还没有创建角色，请先使用 /修仙 创建角色")
        except Exception as e:
            logger.error(f"查看符箓失败: {e}", exc_info=True)
            yield event.plain_result(f"查看符箓失败：{str(e)}")

    # ========== 坊市系统命令 ==========

    @filter.command("坊市", alias={"market", "市场"})
    async def market_cmd(self, event: AstrMessageEvent):
        """查看坊市物品列表"""
        user_id = event.get_sender_id()
        try:
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return

            # 解析参数
            text = self._get_message_text(event)
            args = text.split()

            # 类型筛选映射
            type_mapping = {
                "装备": "equipment",
                "丹药": "pill",
                "功法": "method",
                "材料": "material"
            }

            item_type = None
            if len(args) > 1:
                item_type = type_mapping.get(args[1], args[1])

            # 获取市场物品
            items = await self.market_sys.get_market_items(item_type=item_type, page=1, page_size=20)

            if not items:
                yield event.plain_result(
                    "🏪 坊市空空如也\n\n"
                    "💡 使用 /上架 出售物品"
                )
                return

            # 格式化显示
            lines = ["🏪 修仙坊市", "─" * 40, ""]

            for i, item in enumerate(items, 1):
                quality_emoji = {
                    '凡品': '⚪', '灵品': '🔵', '宝品': '🟣',
                    '仙品': '🟡', '神品': '🔴', '道品': '⭐'
                }.get(item['quality'], '⚪')

                lines.append(
                    f"{i}. {quality_emoji} {item['item_name']} x{item['quantity']}\n"
                    f"   💎 价格: {item['price']} 灵石"
                )

            lines.extend([
                "",
                "💡 使用 /购买 [编号] 购买物品",
                "💡 使用 /坊市 [类型] 筛选类型（装备/丹药/功法/材料）"
            ])

            yield event.plain_result("\n".join(lines))

        except Exception as e:
            logger.error(f"查看坊市失败: {e}", exc_info=True)
            yield event.plain_result(f"查看坊市失败：{str(e)}")

    @filter.command("上架", alias={"list_item", "出售"})
    async def list_item_cmd(self, event: AstrMessageEvent):
        """上架物品到坊市"""
        user_id = event.get_sender_id()
        try:
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return

            # 解析参数
            text = self._get_message_text(event)
            args = text.split()

            if len(args) < 4:
                yield event.plain_result(
                    "🏪 上架物品到坊市\n" + "─" * 40 + "\n\n"
                    "请指定物品类型、编号、价格和数量\n\n"
                    "💡 使用方法: /上架 [类型] [编号] [价格] [数量]\n"
                    "💡 例如: /上架 装备 1 1000\n"
                    "💡 例如: /上架 丹药 2 500 10\n\n"
                    "📋 支持类型:\n"
                    "  装备 - 装备和法宝\n"
                    "  丹药 - 各类丹药\n"
                    "  功法 - 功法秘籍\n"
                    "  材料 - 炼丹炼器材料"
                )
                return

            # 类型映射
            type_mapping = {
                "装备": "equipment",
                "丹药": "pill",
                "功法": "method",
                "材料": "material"
            }

            item_type_input = args[1]
            item_type = type_mapping.get(item_type_input, item_type_input)

            if item_type not in ["equipment", "pill", "method", "material"]:
                yield event.plain_result("❌ 不支持的物品类型！\n\n💡 支持类型：装备、丹药、功法、材料")
                return

            # 解析编号和价格
            try:
                item_index = int(args[2])
                price = int(args[3])
                quantity = int(args[4]) if len(args) > 4 else 1
            except ValueError:
                yield event.plain_result("❌ 编号、价格和数量必须是数字！")
                return

            if price <= 0:
                yield event.plain_result("❌ 价格必须大于0！")
                return

            # 获取物品ID（需要根据编号查询实际ID）
            # 这里简化处理，实际应该从背包/装备列表获取
            if item_type == "equipment":
                equipment_list = await self.equipment_sys.get_player_equipment(user_id)
                if item_index < 1 or item_index > len(equipment_list):
                    yield event.plain_result(f"❌ 装备编号 {item_index} 不存在！")
                    return
                equipment = equipment_list[item_index - 1]
                item_id = equipment.id
            elif item_type == "method":
                methods = await self.method_sys.get_player_methods(user_id)
                if item_index < 1 or item_index > len(methods):
                    yield event.plain_result(f"❌ 功法编号 {item_index} 不存在！")
                    return
                method = methods[item_index - 1]
                item_id = method.id
            else:
                # 丹药和材料使用item_index作为item_id（简化处理）
                item_id = str(item_index)

            # 上架物品
            result = await self.market_sys.list_item(user_id, item_type, item_id, price, quantity)

            yield event.plain_result(
                f"✅ 上架成功！\n\n"
                f"物品：{result['item_name']} x{result['quantity']}\n"
                f"价格：{result['price']} 灵石\n\n"
                f"💡 使用 /我的上架 查看上架物品"
            )

        except PlayerNotFoundError:
            yield event.plain_result("您还没有创建角色，请先使用 /修仙 创建角色")
        except ItemNotOwnedError as e:
            yield event.plain_result(f"❌ {str(e)}")
        except ItemNotTradableError as e:
            yield event.plain_result(f"⚠️ {str(e)}")
        except Exception as e:
            logger.error(f"上架物品失败: {e}", exc_info=True)
            yield event.plain_result(f"上架失败：{str(e)}")

    @filter.command("购买", alias={"buy", "购买物品"})
    async def purchase_item_cmd(self, event: AstrMessageEvent):
        """购买坊市物品"""
        user_id = event.get_sender_id()
        try:
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return

            # 解析参数
            text = self._get_message_text(event)
            args = text.split()

            if len(args) < 2:
                yield event.plain_result(
                    "🏪 购买坊市物品\n" + "─" * 40 + "\n\n"
                    "请指定要购买的物品编号\n\n"
                    "💡 使用方法: /购买 [编号]\n"
                    "💡 例如: /购买 1\n\n"
                    "💡 使用 /坊市 查看可购买物品"
                )
                return

            try:
                item_index = int(args[1])
            except ValueError:
                yield event.plain_result("❌ 物品编号必须是数字！")
                return

            # 获取市场物品列表
            items = await self.market_sys.get_market_items(page=1, page_size=20)

            if item_index < 1 or item_index > len(items):
                yield event.plain_result(f"❌ 物品编号 {item_index} 不存在！")
                return

            # 获取要购买的物品
            item = items[item_index - 1]
            listing_id = item['id']

            # 执行购买
            result = await self.market_sys.purchase_item(user_id, listing_id)

            yield event.plain_result(
                f"🎉 购买成功！\n\n"
                f"物品：{result['item_name']} x{result['quantity']}\n"
                f"价格：{result['price']} 灵石\n"
                f"税费：{result['tax']} 灵石（5%）\n"
                f"剩余灵石：{result['buyer_remaining']}\n\n"
                f"💡 物品已放入背包"
            )

        except PlayerNotFoundError:
            yield event.plain_result("您还没有创建角色，请先使用 /修仙 创建角色")
        except ListingNotFoundError as e:
            yield event.plain_result(f"❌ {str(e)}")
        except InsufficientSpiritStoneError as e:
            yield event.plain_result(f"💎 {str(e)}")
        except ValueError as e:
            yield event.plain_result(f"⚠️ {str(e)}")
        except Exception as e:
            logger.error(f"购买物品失败: {e}", exc_info=True)
            yield event.plain_result(f"购买失败：{str(e)}")

    @filter.command("下架", alias={"cancel_listing", "取消上架"})
    async def cancel_listing_cmd(self, event: AstrMessageEvent):
        """取消上架"""
        user_id = event.get_sender_id()
        try:
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return

            # 解析参数
            text = self._get_message_text(event)
            args = text.split()

            if len(args) < 2:
                yield event.plain_result(
                    "🏪 取消上架\n" + "─" * 40 + "\n\n"
                    "请指定要下架的物品编号\n\n"
                    "💡 使用方法: /下架 [编号]\n"
                    "💡 例如: /下架 1\n\n"
                    "💡 使用 /我的上架 查看上架物品"
                )
                return

            try:
                item_index = int(args[1])
            except ValueError:
                yield event.plain_result("❌ 物品编号必须是数字！")
                return

            # 获取我的上架列表
            my_listings = await self.market_sys.get_my_listings(user_id)

            if item_index < 1 or item_index > len(my_listings):
                yield event.plain_result(f"❌ 物品编号 {item_index} 不存在！")
                return

            # 获取要下架的物品
            listing = my_listings[item_index - 1]
            listing_id = listing['id']

            # 执行下架
            result = await self.market_sys.cancel_listing(user_id, listing_id)

            yield event.plain_result(
                f"✅ 下架成功！\n\n"
                f"物品：{result['item_name']} x{result['quantity']}\n\n"
                f"💡 物品已退回背包"
            )

        except PlayerNotFoundError:
            yield event.plain_result("您还没有创建角色，请先使用 /修仙 创建角色")
        except ListingNotFoundError as e:
            yield event.plain_result(f"❌ {str(e)}")
        except ValueError as e:
            yield event.plain_result(f"⚠️ {str(e)}")
        except Exception as e:
            logger.error(f"下架物品失败: {e}", exc_info=True)
            yield event.plain_result(f"下架失败：{str(e)}")

    @filter.command("我的上架", alias={"my_listings", "我的物品"})
    async def my_listings_cmd(self, event: AstrMessageEvent):
        """查看我的上架物品"""
        user_id = event.get_sender_id()
        try:
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return

            # 获取我的上架列表
            my_listings = await self.market_sys.get_my_listings(user_id)

            if not my_listings:
                yield event.plain_result(
                    "📦 您还没有上架任何物品\n\n"
                    "💡 使用 /上架 出售物品"
                )
                return

            # 格式化显示
            lines = ["📦 我的上架物品", "─" * 40, ""]

            for i, item in enumerate(my_listings, 1):
                quality_emoji = {
                    '凡品': '⚪', '灵品': '🔵', '宝品': '🟣',
                    '仙品': '🟡', '神品': '🔴', '道品': '⭐'
                }.get(item['quality'], '⚪')

                lines.append(
                    f"{i}. {quality_emoji} {item['item_name']} x{item['quantity']}\n"
                    f"   💎 价格: {item['price']} 灵石\n"
                    f"   📅 上架: {item['listed_at'][:10]}"
                )

            lines.extend([
                "",
                f"📊 共 {len(my_listings)} 件物品",
                "",
                "💡 使用 /下架 [编号] 取消上架"
            ])

            yield event.plain_result("\n".join(lines))

        except PlayerNotFoundError:
            yield event.plain_result("您还没有创建角色，请先使用 /修仙 创建角色")
        except Exception as e:
            logger.error(f"查看我的上架失败: {e}", exc_info=True)
            yield event.plain_result(f"查看失败：{str(e)}")

    # ========== 灵宠系统命令 ==========

    @filter.command("领取灵宠", alias={"claim_pet", "领宠"})
    async def claim_starter_pet_cmd(self, event: AstrMessageEvent):
        """从宗门领取初始灵宠"""
        user_id = event.get_sender_id()
        try:
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return

            message_text = self._get_message_text(event)
            parts = message_text.split()

            if len(parts) < 2:
                # 显示可选灵宠
                starters = await self.pet_sys.get_starter_pets()
                lines = [
                    "🐾 宗门初始灵宠",
                    "─" * 40,
                    "",
                    "请选择一只灵宠领取（终身只能领取一次）：",
                    ""
                ]

                for i, pet in enumerate(starters, 1):
                    # 解析灵宠效果
                    import json
                    base_attrs = json.loads(pet.base_attributes)
                    effects = []
                    if 'cultivation_speed_bonus' in base_attrs:
                        effects.append(f"修炼速度+{base_attrs['cultivation_speed_bonus']*100:.0f}%")
                    if 'breakthrough_bonus' in base_attrs:
                        effects.append(f"突破率+{base_attrs['breakthrough_bonus']*100:.0f}%")
                    if 'luck_bonus' in base_attrs:
                        effects.append(f"幸运+{base_attrs['luck_bonus']}")
                    if 'attack_bonus' in base_attrs:
                        effects.append(f"攻击+{base_attrs['attack_bonus']*100:.0f}%")
                    if 'defense_bonus' in base_attrs:
                        effects.append(f"防御+{base_attrs['defense_bonus']*100:.0f}%")

                    pet_info = (
                        f"{i}. {pet.get_rarity_color()}{pet.name}\n"
                        f"   类型：{pet.pet_type}\n"
                        f"   稀有度：{pet.rarity}\n"
                    )
                    if effects:
                        pet_info += f"   效果：{', '.join(effects)}\n"
                    pet_info += f"   {pet.description}\n"

                    lines.append(pet_info)

                lines.extend([
                    "─" * 40,
                    "💡 使用方法：/领取灵宠 [编号]",
                    "   例如：/领取灵宠 1"
                ])

                yield event.plain_result("\n".join(lines))
                return

            # 领取灵宠
            try:
                pet_index = int(parts[1])
                player_pet = await self.pet_sys.claim_starter_pet(user_id, pet_index)

                # 解析灵宠效果
                import json
                effect_lines = []
                if player_pet.pet_template and player_pet.pet_template.base_attributes:
                    base_attrs = json.loads(player_pet.pet_template.base_attributes)
                    if 'cultivation_speed_bonus' in base_attrs:
                        effect_lines.append(f"   • 修炼速度 +{base_attrs['cultivation_speed_bonus']*100:.0f}%")
                    if 'breakthrough_bonus' in base_attrs:
                        effect_lines.append(f"   • 突破成功率 +{base_attrs['breakthrough_bonus']*100:.0f}%")
                    if 'luck_bonus' in base_attrs:
                        effect_lines.append(f"   • 幸运 +{base_attrs['luck_bonus']}")
                    if 'attack_bonus' in base_attrs:
                        effect_lines.append(f"   • 攻击力 +{base_attrs['attack_bonus']*100:.0f}%")
                    if 'defense_bonus' in base_attrs:
                        effect_lines.append(f"   • 防御力 +{base_attrs['defense_bonus']*100:.0f}%")

                effect_text = "\n".join(effect_lines) if effect_lines else ""

                # 构建成功消息
                yield event.plain_result(
                    f"🎉 恭喜您领取了初始灵宠！\n\n"
                    f"🐾 {player_pet.get_display_name()}\n"
                    f"📝 获取途径：宗门福利\n\n"
                    f"✨ 基础效果：\n{effect_text}\n\n"
                    f"💡 使用 /激活灵宠 1 让灵宠出战获得加成\n"
                    f"   使用 /我的灵宠 查看所有灵宠"
                )
            except ValueError:
                yield event.plain_result("⚠️ 请输入有效的编号！")

        except PlayerNotFoundError:
            yield event.plain_result("您还没有创建角色，请先使用 /修仙 创建角色")
        except (PetError, AlreadyHasPetError, PetNotFoundError) as e:
            yield event.plain_result(f"⚠️ {str(e)}")
        except Exception as e:
            logger.error(f"领取灵宠失败: {e}", exc_info=True)
            yield event.plain_result(f"领取失败：{str(e)}")

    @filter.command("我的灵宠", alias={"my_pets", "灵宠列表"})
    async def my_pets_cmd(self, event: AstrMessageEvent):
        """查看我的所有灵宠"""
        user_id = event.get_sender_id()
        try:
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return

            pets = await self.pet_sys.get_player_pets(user_id)

            if not pets:
                yield event.plain_result(
                    "🐾 您还没有灵宠\n\n"
                    "💡 可以通过以下方式获得灵宠：\n"
                    "   • 使用 /领取灵宠 在宗门领取初始灵宠\n"
                    "   • 使用 /灵宠秘境 探索并捕获野生灵宠"
                )
                return

            # 格式化显示
            lines = ["🐾 我的灵宠", "─" * 40, ""]

            for i, pet in enumerate(pets, 1):
                status = "⭐ 出战中" if pet.is_active else ""
                intimacy_level = pet.get_intimacy_level()
                next_exp = pet.get_next_level_exp()

                # 解析灵宠加成效果
                import json
                effect_text = ""
                if pet.pet_template and pet.pet_template.base_attributes:
                    base_attrs = json.loads(pet.pet_template.base_attributes)
                    effects = []
                    if 'cultivation_speed_bonus' in base_attrs:
                        effects.append(f"修炼速度+{base_attrs['cultivation_speed_bonus']*100:.0f}%")
                    if 'breakthrough_bonus' in base_attrs:
                        effects.append(f"突破率+{base_attrs['breakthrough_bonus']*100:.0f}%")
                    if 'luck_bonus' in base_attrs:
                        effects.append(f"幸运+{base_attrs['luck_bonus']}")
                    if 'attack_bonus' in base_attrs:
                        effects.append(f"攻击+{base_attrs['attack_bonus']*100:.0f}%")
                    if 'defense_bonus' in base_attrs:
                        effects.append(f"防御+{base_attrs['defense_bonus']*100:.0f}%")
                    if effects:
                        effect_text = f"   效果：{', '.join(effects)}\n"

                pet_info = f"{i}. {pet.get_display_name()} {status}\n"
                if effect_text:
                    pet_info += f"{effect_text}"
                pet_info += (
                    f"   经验：{pet.experience}/{next_exp}\n"
                    f"   亲密度：{pet.intimacy}/100 ({intimacy_level})\n"
                    f"   参战次数：{pet.battle_count}\n"
                    f"   获取途径：{pet.acquired_from}\n"
                )
                lines.append(pet_info)

            lines.extend([
                "",
                f"📊 共 {len(pets)} 只灵宠",
                "",
                "💡 使用 /激活灵宠 [编号] 让灵宠出战",
                "   使用 /灵宠详情 [编号] 查看详细信息",
                "",
                "📈 提示：灵宠等级和亲密度会增强加成效果"
            ])

            yield event.plain_result("\n".join(lines))

        except PlayerNotFoundError:
            yield event.plain_result("您还没有创建角色，请先使用 /修仙 创建角色")
        except Exception as e:
            logger.error(f"查看灵宠失败: {e}", exc_info=True)
            yield event.plain_result(f"查看失败：{str(e)}")

    @filter.command("激活灵宠", alias={"activate_pet", "出战灵宠"})
    async def activate_pet_cmd(self, event: AstrMessageEvent):
        """激活灵宠让其出战"""
        user_id = event.get_sender_id()
        try:
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return

            message_text = self._get_message_text(event)
            parts = message_text.split()

            if len(parts) < 2:
                yield event.plain_result(
                    "⚠️ 请指定要激活的灵宠编号\n\n"
                    "💡 使用方法：/激活灵宠 [编号]\n"
                    "   先使用 /我的灵宠 查看灵宠列表"
                )
                return

            try:
                pet_index = int(parts[1]) - 1

                # 获取玩家的灵宠列表
                pets = await self.pet_sys.get_player_pets(user_id)

                if pet_index < 0 or pet_index >= len(pets):
                    yield event.plain_result("⚠️ 无效的灵宠编号！")
                    return

                # 使用玩家灵宠的数据库ID激活
                selected_pet = pets[pet_index]
                activated_pet = await self.pet_sys.activate_pet(user_id, selected_pet.id)

                yield event.plain_result(
                    f"✅ 已激活灵宠：{activated_pet.get_display_name()}\n\n"
                    f"💡 灵宠加成将在修炼、突破等操作中生效"
                )
            except ValueError:
                yield event.plain_result("⚠️ 请输入有效的编号！")

        except PlayerNotFoundError:
            yield event.plain_result("您还没有创建角色，请先使用 /修仙 创建角色")
        except XiuxianException as e:
            yield event.plain_result(f"⚠️ {str(e)}")
        except Exception as e:
            logger.error(f"激活灵宠失败: {e}", exc_info=True)
            yield event.plain_result(f"激活失败：{str(e)}")

    @filter.command("灵宠秘境", alias={"pet_realm", "捕捉灵宠"})
    async def pet_secret_realm_cmd(self, event: AstrMessageEvent):
        """探索灵宠秘境"""
        user_id = event.get_sender_id()
        try:
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return

            result = await self.pet_sys.explore_secret_realm(user_id)
            yield event.plain_result(result['message'])

        except PlayerNotFoundError:
            yield event.plain_result("您还没有创建角色，请先使用 /修仙 创建角色")
        except XiuxianException as e:
            yield event.plain_result(f"⚠️ {str(e)}")
        except Exception as e:
            logger.error(f"探索灵宠秘境失败: {e}", exc_info=True)
            yield event.plain_result(f"探索失败：{str(e)}")

    @filter.command("灵宠详情", alias={"pet_info", "查看灵宠"})
    async def pet_detail_cmd(self, event: AstrMessageEvent):
        """查看灵宠详细信息"""
        user_id = event.get_sender_id()
        try:
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return

            message_text = self._get_message_text(event)
            parts = message_text.split()

            if len(parts) < 2:
                yield event.plain_result(
                    "⚠️ 请指定要查看的灵宠编号\n\n"
                    "💡 使用方法：/灵宠详情 [编号]\n"
                    "   先使用 /我的灵宠 查看灵宠列表"
                )
                return

            try:
                pet_index = int(parts[1]) - 1
                pets = await self.pet_sys.get_player_pets(user_id)

                if pet_index < 0 or pet_index >= len(pets):
                    yield event.plain_result("⚠️ 无效的灵宠编号！")
                    return

                pet = pets[pet_index]
                if not pet.pet_template:
                    yield event.plain_result("⚠️ 无法加载灵宠模板信息")
                    return

                template = pet.pet_template
                intimacy_level = pet.get_intimacy_level()
                next_exp = pet.get_next_level_exp()

                # 解析属性和效果
                import json
                base_attrs = json.loads(template.base_attributes)

                # 计算当前等级和亲密度下的实际加成
                level_multiplier = 1.0 + (pet.level - 1) * 0.02
                intimacy_multiplier = 1.0 + (pet.intimacy / 100) * 0.3
                total_multiplier = level_multiplier * intimacy_multiplier

                lines = [
                    f"🐾 {pet.get_display_name()}",
                    "─" * 40,
                    "",
                    f"📋 基础信息：",
                    f"   种族：{template.name}",
                    f"   类型：{template.pet_type}",
                    f"   稀有度：{template.get_rarity_color()}{template.rarity}",
                    f"   元素：{template.element or '无'}",
                    "",
                    f"📊 成长信息：",
                    f"   等级：{pet.level}/{template.max_level}",
                    f"   经验：{pet.experience}/{next_exp}",
                    f"   成长率：{template.growth_rate}",
                    "",
                    f"💖 亲密度：{pet.intimacy}/100 ({intimacy_level})",
                    f"⚔️ 参战次数：{pet.battle_count}",
                    f"📅 获取时间：{pet.acquired_at[:10]}",
                    f"📍 获取途径：{pet.acquired_from}",
                    "",
                    f"✨ 基础加成效果：",
                ]

                # 显示人类可读的加成效果
                base_effects = []
                actual_effects = []
                if 'cultivation_speed_bonus' in base_attrs:
                    base_val = base_attrs['cultivation_speed_bonus']
                    actual_val = base_val * total_multiplier
                    base_effects.append(f"   • 修炼速度：+{base_val*100:.0f}%")
                    actual_effects.append(f"   • 修炼速度：+{actual_val*100:.1f}%")
                if 'breakthrough_bonus' in base_attrs:
                    base_val = base_attrs['breakthrough_bonus']
                    actual_val = base_val * total_multiplier
                    base_effects.append(f"   • 突破成功率：+{base_val*100:.0f}%")
                    actual_effects.append(f"   • 突破成功率：+{actual_val*100:.1f}%")
                if 'luck_bonus' in base_attrs:
                    base_val = base_attrs['luck_bonus']
                    actual_val = base_val * total_multiplier
                    base_effects.append(f"   • 幸运：+{base_val}")
                    actual_effects.append(f"   • 幸运：+{actual_val:.1f}")
                if 'attack_bonus' in base_attrs:
                    base_val = base_attrs['attack_bonus']
                    actual_val = base_val * total_multiplier
                    base_effects.append(f"   • 攻击力：+{base_val*100:.0f}%")
                    actual_effects.append(f"   • 攻击力：+{actual_val*100:.1f}%")
                if 'defense_bonus' in base_attrs:
                    base_val = base_attrs['defense_bonus']
                    actual_val = base_val * total_multiplier
                    base_effects.append(f"   • 防御力：+{base_val*100:.0f}%")
                    actual_effects.append(f"   • 防御力：+{actual_val*100:.1f}%")

                lines.extend(base_effects)

                if actual_effects:
                    lines.extend([
                        "",
                        f"🔥 当前实际加成（等级{pet.level}，亲密度{pet.intimacy}）：",
                    ])
                    lines.extend(actual_effects)
                    lines.append(f"   💡 加成倍率：{total_multiplier:.2f}x")

                lines.extend([
                    "",
                    f"📝 描述：",
                    f"   {template.description}"
                ])

                if template.evolution_to:
                    lines.extend([
                        "",
                        f"🔄 可进化至更强形态"
                    ])

                yield event.plain_result("\n".join(lines))

            except ValueError:
                yield event.plain_result("⚠️ 请输入有效的编号！")

        except PlayerNotFoundError:
            yield event.plain_result("您还没有创建角色，请先使用 /修仙 创建角色")
        except Exception as e:
            logger.error(f"查看灵宠详情失败: {e}", exc_info=True)
            yield event.plain_result(f"查看失败：{str(e)}")

    @filter.command("喂养灵宠", alias={"feed_pet", "喂宠"})
    async def feed_pet_cmd(self, event: AstrMessageEvent):
        """喂养灵宠提升亲密度"""
        user_id = event.get_sender_id()
        try:
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return

            message_text = self._get_message_text(event)
            parts = message_text.split()

            if len(parts) < 2:
                yield event.plain_result(
                    "⚠️ 请指定要喂养的灵宠编号\n\n"
                    "💡 使用方法：/喂养灵宠 [编号]\n"
                    "   例如：/喂养灵宠 1\n\n"
                    "📝 喂养说明：\n"
                    "   • 消耗灵石喂养灵宠\n"
                    "   • 提升亲密度 3-8点\n"
                    "   • 消耗随灵宠等级增加\n"
                    "   • 亲密度提升加成效果"
                )
                return

            try:
                pet_index = int(parts[1]) - 1
                pets = await self.pet_sys.get_player_pets(user_id)

                if pet_index < 0 or pet_index >= len(pets):
                    yield event.plain_result("⚠️ 无效的灵宠编号！")
                    return

                pet = pets[pet_index]
                result = await self.pet_sys.feed_pet(user_id, pet.id)

                if result['success']:
                    yield event.plain_result(result['message'])
                else:
                    yield event.plain_result(f"⚠️ {result['message']}")

            except ValueError as e:
                if "灵石不足" in str(e):
                    yield event.plain_result(f"⚠️ {str(e)}")
                else:
                    yield event.plain_result("⚠️ 请输入有效的编号！")

        except PlayerNotFoundError:
            yield event.plain_result("您还没有创建角色，请先使用 /修仙 创建角色")
        except PetNotFoundError as e:
            yield event.plain_result(f"⚠️ {str(e)}")
        except Exception as e:
            logger.error(f"喂养灵宠失败: {e}", exc_info=True)
            yield event.plain_result(f"喂养失败：{str(e)}")

    @filter.command("训练灵宠", alias={"train_pet", "练宠"})
    async def train_pet_cmd(self, event: AstrMessageEvent):
        """训练灵宠提升经验"""
        user_id = event.get_sender_id()
        try:
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return

            message_text = self._get_message_text(event)
            parts = message_text.split()

            if len(parts) < 2:
                yield event.plain_result(
                    "⚠️ 请指定要训练的灵宠编号\n\n"
                    "💡 使用方法：/训练灵宠 [编号]\n"
                    "   例如：/训练灵宠 1\n\n"
                    "📝 训练说明：\n"
                    "   • 消耗灵石训练灵宠\n"
                    "   • 获得经验值\n"
                    "   • 经验增加受成长率影响\n"
                    "   • 消耗随灵宠等级增加"
                )
                return

            try:
                pet_index = int(parts[1]) - 1
                pets = await self.pet_sys.get_player_pets(user_id)

                if pet_index < 0 or pet_index >= len(pets):
                    yield event.plain_result("⚠️ 无效的灵宠编号！")
                    return

                pet = pets[pet_index]
                result = await self.pet_sys.train_pet(user_id, pet.id)

                if result['success']:
                    yield event.plain_result(result['message'])
                else:
                    yield event.plain_result(f"⚠️ {result['message']}")

            except ValueError as e:
                if "灵石不足" in str(e):
                    yield event.plain_result(f"⚠️ {str(e)}")
                else:
                    yield event.plain_result("⚠️ 请输入有效的编号！")

        except PlayerNotFoundError:
            yield event.plain_result("您还没有创建角色，请先使用 /修仙 创建角色")
        except PetNotFoundError as e:
            yield event.plain_result(f"⚠️ {str(e)}")
        except Exception as e:
            logger.error(f"训练灵宠失败: {e}", exc_info=True)
            yield event.plain_result(f"训练失败：{str(e)}")

    @filter.command("升级灵宠", alias={"level_up_pet", "宠物升级"})
    async def level_up_pet_cmd(self, event: AstrMessageEvent):
        """灵宠升级"""
        user_id = event.get_sender_id()
        try:
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return

            message_text = self._get_message_text(event)
            parts = message_text.split()

            if len(parts) < 2:
                yield event.plain_result(
                    "⚠️ 请指定要升级的灵宠编号\n\n"
                    "💡 使用方法：/升级灵宠 [编号]\n"
                    "   例如：/升级灵宠 1\n\n"
                    "📝 升级说明：\n"
                    "   • 经验达到要求时可以升级\n"
                    "   • 升级后提升加成效果\n"
                    "   • 先使用 /我的灵宠 查看灵宠列表"
                )
                return

            try:
                pet_index = int(parts[1]) - 1
                pets = await self.pet_sys.get_player_pets(user_id)

                if pet_index < 0 or pet_index >= len(pets):
                    yield event.plain_result("⚠️ 无效的灵宠编号！")
                    return

                pet = pets[pet_index]
                result = await self.pet_sys.level_up_pet(user_id, pet.id)

                if result['success']:
                    yield event.plain_result(result['message'])
                else:
                    yield event.plain_result(f"⚠️ {result['message']}")

            except ValueError:
                yield event.plain_result("⚠️ 请输入有效的编号！")

        except PlayerNotFoundError:
            yield event.plain_result("您还没有创建角色，请先使用 /修仙 创建角色")
        except PetNotFoundError as e:
            yield event.plain_result(f"⚠️ {str(e)}")
        except Exception as e:
            logger.error(f"升级灵宠失败: {e}", exc_info=True)
            yield event.plain_result(f"升级失败：{str(e)}")

    @filter.command("进化灵宠", alias={"evolve_pet", "宠物进化"})
    async def evolve_pet_cmd(self, event: AstrMessageEvent):
        """灵宠进化"""
        user_id = event.get_sender_id()
        try:
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return

            message_text = self._get_message_text(event)
            parts = message_text.split()

            if len(parts) < 2:
                yield event.plain_result(
                    "⚠️ 请指定要进化的灵宠编号\n\n"
                    "💡 使用方法：/进化灵宠 [编号]\n"
                    "   例如：/进化灵宠 1\n\n"
                    "📝 进化说明：\n"
                    "   • 并非所有灵宠都能进化\n"
                    "   • 需要达到等级要求（最大等级的80%）\n"
                    "   • 需要达到亲密度要求（80点）\n"
                    "   • 消耗大量灵石\n"
                    "   • 进化后变成更强大的形态\n"
                    "   • 进化后亲密度保留一半"
                )
                return

            try:
                pet_index = int(parts[1]) - 1
                pets = await self.pet_sys.get_player_pets(user_id)

                if pet_index < 0 or pet_index >= len(pets):
                    yield event.plain_result("⚠️ 无效的灵宠编号！")
                    return

                pet = pets[pet_index]
                result = await self.pet_sys.evolve_pet(user_id, pet.id)

                if result['success']:
                    yield event.plain_result(result['message'])
                else:
                    yield event.plain_result(f"⚠️ {result['message']}")

            except ValueError as e:
                if "灵石不足" in str(e):
                    yield event.plain_result(f"⚠️ {str(e)}")
                else:
                    yield event.plain_result("⚠️ 请输入有效的编号！")

        except PlayerNotFoundError:
            yield event.plain_result("您还没有创建角色，请先使用 /修仙 创建角色")
        except PetNotFoundError as e:
            yield event.plain_result(f"⚠️ {str(e)}")
        except Exception as e:
            logger.error(f"进化灵宠失败: {e}", exc_info=True)
            yield event.plain_result(f"进化失败：{str(e)}")
