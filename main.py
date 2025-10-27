"""
AstrBot 修仙世界插件
完整的修仙主题游戏插件,支持修炼、战斗、宗门、AI生成世界
"""

from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from pathlib import Path

# 导入核心模块
from .core.database import DatabaseManager
from .core.player import PlayerManager
from .core.cultivation import CultivationSystem
from .core.breakthrough import BreakthroughSystem
from .core.combat import CombatSystem, InvalidTargetException, SelfCombatException
from .core.equipment import EquipmentSystem
from .core.ai_generator import AIGenerator, AIGenerationError, ContentNotAvailableError
from .core.cultivation_method import CultivationMethodSystem, MethodNotFoundError, MethodNotOwnError, MethodAlreadyEquippedError, SlotOccupiedError
from .core.sect import SectSystem, SectError, SectNotFoundError, SectNameExistsError, NotSectMemberError, AlreadyInSectError, InsufficientPermissionError, InsufficientResourceError, SectFullError
from .core.tribulation import TribulationSystem, TribulationError, TribulationNotFoundError, TribulationInProgressError, NoTribulationRequiredError, InsufficientHPError

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

        # 数据库路径
        data_dir = Path(__file__).parent / "data"
        db_path = data_dir / "xiuxian.db"

        # 初始化数据库管理器
        self.db = DatabaseManager(str(db_path))

        # 初始化业务管理器
        self.player_mgr = None  # 在on_loaded中初始化
        self.cultivation_sys = None  # 在on_loaded中初始化
        self.breakthrough_sys = None  # 在on_loaded中初始化
        self.combat_sys = None  # 在on_loaded中初始化
        self.equipment_sys = None  # 在on_loaded中初始化
        self.method_sys = None  # 在on_loaded中初始化
        self.sect_sys = None  # 在on_loaded中初始化
        self.ai_generator = None  # 在on_loaded中初始化
        self.tribulation_sys = None  # 在on_loaded中初始化

        logger.info("修仙世界插件已加载")

    @filter.on_astrbot_loaded()
    async def on_loaded(self):
        """AstrBot加载完成钩子"""
        # 初始化数据库
        await self.db.init_db()

        # 初始化业务管理器
        self.player_mgr = PlayerManager(self.db)
        self.cultivation_sys = CultivationSystem(self.db, self.player_mgr)
        self.breakthrough_sys = BreakthroughSystem(self.db, self.player_mgr)
        self.combat_sys = CombatSystem(self.db, self.player_mgr)
        self.equipment_sys = EquipmentSystem(self.db, self.player_mgr)
        self.method_sys = CultivationMethodSystem(self.db, self.player_mgr)
        self.sect_sys = SectSystem(self.db, self.player_mgr)
        self.ai_generator = AIGenerator(self.db, self.player_mgr)
        self.tribulation_sys = TribulationSystem(self.db, self.player_mgr)

        # 注入天劫系统到突破系统
        self.breakthrough_sys.set_tribulation_system(self.tribulation_sys)

        logger.info("修仙世界插件初始化完成")

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

    # ========== 命令处理器 ==========

    @filter.command("修仙", alias={"开始修仙", "创建角色"})
    async def create_character(self, event: AstrMessageEvent):
        """创建修仙角色"""
        user_id = event.get_sender_id()

        try:
            # 检查插件是否已初始化
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return

            # 1. 检查是否已创建角色
            if await self.player_mgr.player_exists(user_id):
                yield event.plain_result("道友已经踏上修仙之路，无需重复创建角色。\n使用 /属性 查看角色信息")
                return

            # 2. 提示输入道号
            yield event.plain_result(
                "欢迎来到修仙世界！\n\n"
                "请输入您的道号（角色名称）："
            )

            # 3. 等待用户输入道号
            name_event = await self.context.session_waiter.wait(
                event,
                timeout=60  # 60秒超时
            )

            if name_event is None:
                yield event.plain_result("创建角色超时，请重新使用 /修仙 命令")
                return

            # 获取道号
            name = name_event.get_plain_text().strip()

            # 验证道号
            if not name or len(name) > 20:
                yield event.plain_result("道号不合法！请使用1-20个字符的道号，重新使用 /修仙 命令创建")
                return

            # 4. 创建角色
            yield event.plain_result(f"正在为道友 {name} 检测灵根...")

            player = await self.player_mgr.create_player(user_id, name)

            # 5. 格式化展示信息
            player_info = MessageFormatter.format_player_info(player)
            spirit_info = MessageFormatter.format_spirit_root_info(player)

            result_text = (
                f"恭喜！道友 {name} 已踏上修仙之路！\n\n"
                f"{player_info}\n\n"
                f"{spirit_info}\n\n"
                f"💡 提示：使用 /修炼 开始修炼，使用 /修仙帮助 查看所有命令"
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
            # 检查插件是否已初始化
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return

            # 获取玩家信息
            player = await self.player_mgr.get_player_or_error(user_id)

            # 格式化玩家信息
            player_info = MessageFormatter.format_player_info(player)

            # 获取修炼信息
            cult_info = await self.cultivation_sys.get_cultivation_info(user_id)

            # 构建额外信息
            extra_info = []

            # 冷却信息
            if cult_info['can_cultivate']:
                extra_info.append("✅ 可以修炼")
                extra_info.append(f"💡 预计获得修为: {cult_info['next_cultivation_gain']}")
            else:
                hours = cult_info['cooldown_remaining'] // 3600
                minutes = (cult_info['cooldown_remaining'] % 3600) // 60
                seconds = cult_info['cooldown_remaining'] % 60
                time_str = ""
                if hours > 0:
                    time_str += f"{hours}小时"
                if minutes > 0:
                    time_str += f"{minutes}分钟"
                if seconds > 0 or not time_str:
                    time_str += f"{seconds}秒"
                extra_info.append(f"⏰ 修炼冷却中，还需 {time_str}")

            # 突破信息
            if cult_info['can_breakthrough']:
                next_realm = cult_info['next_realm']['name']
                extra_info.append(f"⚡ 可以突破至 {next_realm}！使用 /突破 进行突破")

            result_text = player_info
            if extra_info:
                result_text += "\n\n" + "\n".join(extra_info)

            result_text += "\n\n💡 使用 /灵根 查看灵根详情"

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

    @filter.command("修炼", alias={"打坐", "闭关"})
    async def cultivate_cmd(self, event: AstrMessageEvent):
        """进行修炼"""
        user_id = event.get_sender_id()

        try:
            # 检查插件是否已初始化
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return

            # 执行修炼
            result = await self.cultivation_sys.cultivate(user_id)

            # 构建结果消息
            message_lines = [
                "✨ 修炼完成！",
                "",
                f"📈 获得修为：+{result['cultivation_gained']}",
                f"📊 当前修为：{result['total_cultivation']}",
            ]

            # 检查是否可以突破
            if result['can_breakthrough']:
                message_lines.append("")
                message_lines.append(f"⚡ 恭喜！道友已可突破至 {result['next_realm']}！")
                message_lines.append(f"   所需修为：{result['required_cultivation']}")
                message_lines.append(f"💡 使用 /突破 尝试突破境界")

            result_text = "\n".join(message_lines)
            yield event.plain_result(result_text)

            logger.info(f"用户 {user_id} 修炼: +{result['cultivation_gained']} 修为")

        except PlayerNotFoundError as e:
            yield event.plain_result(str(e))
        except CooldownNotReadyError as e:
            yield event.plain_result(f"⏰ {str(e)}\n\n💡 使用 /属性 查看冷却时间")
        except Exception as e:
            logger.error(f"修炼失败: {e}", exc_info=True)
            yield event.plain_result(f"修炼失败：{str(e)}")

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

            info_lines.extend([
                "",
                "⚠️ 突破失败将损失20%当前修为",
                "是否确认突破？请回复 '确认' 或 '取消'"
            ])

            yield event.plain_result("\n".join(info_lines))

            # 等待用户确认
            confirm_event = await self.context.session_waiter.wait(
                event,
                timeout=30  # 30秒超时
            )

            if confirm_event is None:
                yield event.plain_result("⏰ 突破确认超时，操作已取消")
                return

            confirm_text = confirm_event.get_plain_text().strip().lower()
            if confirm_text not in ['确认', '是', 'y', 'yes']:
                yield event.plain_result("❌ 突破操作已取消")
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
            message_text = event.get_plain_text()

            # 尝试从消息中提取@用户
            import re
            at_pattern = r'@(\S+)'
            matches = re.findall(at_pattern, message_text)

            if not matches:
                yield event.plain_result(
                    "⚠️ 请@要切磋的玩家！\n\n"
                    "💡 使用方法：/切磋 @玩家名"
                )
                return

            defender_name = matches[0]

            # 3. 获取被@用户的ID（这里简化处理，实际应该根据平台获取用户ID）
            # 由于无法直接从@用户名获取用户ID，这里使用简化处理
            yield event.plain_result(
                f"⚠️ 功能暂未完全实现\n\n"
                f"📋 切磋信息：\n"
                f"   攻击者：{attacker.name}\n"
                f"   目标：@{defender_name}\n\n"
                f"💡 请等待后续版本完善@用户解析功能"
            )

        except PlayerNotFoundError as e:
            yield event.plain_result(str(e))
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
            power_lines = [
                "⚔️ 战力信息",
                "─" * 30,
                f"👤 道号：{player.name}",
                f"🏆 战力：{power}",
                f"🎯 境界：{player.realm} {combat_stats['realm_level_name'] if 'realm_level_name' in combat_stats else ''}",
                "",
                "📊 属性详情：",
                f"   ❤️ 生命值：{player.hp}/{player.max_hp}",
                f"   💙 法力值：{player.mp}/{player.max_mp}",
                f"   ⚔️ 攻击力：{player.attack}",
                f"   🛡️ 防御力：{player.defense}",
                f"   🍀 幸运值：{player.luck}",
                "",
                "💡 使用 /切磋 @玩家 发起切磋"
            ]

            yield event.plain_result("\n".join(power_lines))

        except PlayerNotFoundError as e:
            yield event.plain_result(str(e))
        except Exception as e:
            logger.error(f"查看战力失败: {e}", exc_info=True)
            yield event.plain_result(f"查看战力失败：{str(e)}")

    @filter.command("背包", alias={"bag", "inventory"})
    async def inventory_cmd(self, event: AstrMessageEvent):
        """查看背包装备"""
        user_id = event.get_sender_id()

        try:
            # 检查插件是否已初始化
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return

            # 获取装备列表
            inventory_text = await self.equipment_sys.format_equipment_list(user_id)

            yield event.plain_result(inventory_text)

        except PlayerNotFoundError as e:
            yield event.plain_result(str(e))
        except Exception as e:
            logger.error(f"查看背包失败: {e}", exc_info=True)
            yield event.plain_result(f"查看背包失败：{str(e)}")

    @filter.command("装备", alias={"equip", "穿戴"})
    async def equip_cmd(self, event: AstrMessageEvent):
        """穿戴装备"""
        user_id = event.get_sender_id()
        message_text = event.get_plain_text().strip()

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
                    "💡 使用 /背包 查看物品编号"
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
        message_text = event.get_plain_text().strip()

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
                f"💡 使用 /背包 查看装备状态"
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
            message_text = event.get_plain_text().strip()
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

    @filter.command("AI生成", alias={"ai", "生成", "create"})
    async def ai_generate_cmd(self, event: AstrMessageEvent):
        """AI内容生成"""
        user_id = event.get_sender_id()
        message_text = event.get_plain_text().strip()

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
        message_text = event.get_plain_text().strip()

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
        message_text = event.get_plain_text().strip()

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
        message_text = event.get_plain_text().strip()

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
        message_text = event.get_plain_text().strip()

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

    @filter.command("创建宗门", alias={"create_sect", "建立宗门"})
    async def create_sect_cmd(self, event: AstrMessageEvent):
        """创建宗门"""
        user_id = event.get_sender_id()

        try:
            # 检查插件是否已初始化
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return

            # 提示输入宗门名称
            yield event.plain_result(
                "🏛️ 创建宗门\n\n"
                "请输入宗门名称（1-20个字符）："
            )

            # 等待输入宗门名称
            name_event = await self.context.session_waiter.wait(event, timeout=60)
            if name_event is None:
                yield event.plain_result("⏰ 创建宗门超时")
                return

            sect_name = name_event.get_plain_text().strip()
            if not sect_name or len(sect_name) > 20:
                yield event.plain_result("❌ 宗门名称不合法！请使用1-20个字符")
                return

            # 提示输入宗门描述
            yield event.plain_result("请输入宗门描述（1-100个字符）：")

            desc_event = await self.context.session_waiter.wait(event, timeout=60)
            if desc_event is None:
                yield event.plain_result("⏰ 创建宗门超时")
                return

            sect_desc = desc_event.get_plain_text().strip()
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
        message_text = event.get_plain_text().strip()

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

            # 确认离开
            yield event.plain_result(
                "⚠️ 确认要离开宗门吗？\n\n"
                "离开后您将失去所有宗门贡献度和职位\n"
                "请回复 '确认' 或 '取消'"
            )

            confirm_event = await self.context.session_waiter.wait(event, timeout=30)
            if confirm_event is None:
                yield event.plain_result("⏰ 操作超时，已取消")
                return

            confirm_text = confirm_event.get_plain_text().strip().lower()
            if confirm_text not in ['确认', '是', 'y', 'yes']:
                yield event.plain_result("❌ 操作已取消")
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
        message_text = event.get_plain_text().strip()

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

👥 职位系统：
宗主 👑 - 最高权限，可管理一切
长老 🎖️ - 可升级建筑、管理成员
执事 🏅 - 可管理普通成员
精英弟子 ⭐ - 核心成员
弟子 📚 - 普通成员

🏗️ 宗门建筑：
大殿 - 宗门核心建筑
藏经阁 - 提升功法获取率
练功房 - 提升修炼效率
炼丹房 - 提升丹药品质
炼器房 - 提升装备品质

📈 宗门升级：
捐献灵石可获得贡献度和宗门经验
宗门升级可增加成员上限
建筑升级需要消耗宗门灵石

💡 提示：
• 加入宗门可获得各种加成
• 积极捐献可提升个人地位
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

    @filter.command("修仙帮助", alias={"xiuxian", "help"})
    async def help_cmd(self, event: AstrMessageEvent):
        """显示帮助信息"""
        help_text = """
【修仙世界 - 命令列表】

基础命令:
/修仙 - 创建修仙角色
/属性 - 查看角色信息
/灵根 - 查看灵根详情
/修炼 - 进行修炼
/突破 - 境界突破

天劫命令:
/渡劫 - 开始渡劫或继续渡劫
/天劫信息 - 查看当前天劫信息
/天劫历史 - 查看天劫历史记录
/天劫统计 - 查看天劫统计信息

功法命令:
/功法 - 查看功法簿
/已装备功法 - 查看已装备功法
/功法装备 [编号] [槽位] - 装备功法
/功法卸下 [槽位] - 卸下功法
/功法详情 [编号] - 查看功法详情
/获得功法 [类型] [品质] - 获得随机功法(测试)
/功法帮助 - 功法使用说明

宗门命令:
/创建宗门 - 创建新宗门
/宗门信息 - 查看宗门详情
/加入宗门 [名称] - 加入指定宗门
/离开宗门 - 离开当前宗门
/宗门列表 - 查看所有宗门
/宗门捐献 [数量] - 捐献灵石给宗门
/宗门帮助 - 宗门使用说明

战斗命令:
/切磋 @用户 - 与其他玩家切磋
/战力 - 查看战力信息

装备命令:
/背包 - 查看装备
/装备 [编号] - 穿戴装备
/卸下 [槽位] - 卸下装备
/获得装备 [类型] - 获得随机装备(测试)

AI命令:
/AI生成 [类型] - AI生成内容
/AI历史 - 查看生成历史
/AI帮助 - AI使用说明

提示: 更多功能正在开发中...
        """.strip()
        yield event.plain_result(help_text)
