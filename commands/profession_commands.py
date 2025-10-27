"""
职业系统命令处理器
包含炼丹、炼器、阵法、符箓相关命令
"""

# 这个文件包含了职业系统的额外命令处理器
# 它们需要被复制到main.py中

# 炼丹命令 - 复制到main.py
ALCHEMY_COMMANDS = """
    @filter.command("丹方列表", alias={"丹方", "alchemy_recipes"})
    async def alchemy_recipes_cmd(self, event: AstrMessageEvent):
        \"\"\"查看可用丹方列表\"\"\"
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
        \"\"\"炼制丹药\"\"\"
        user_id = event.get_sender_id()

        try:
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return

            # 获取丹方ID参数
            text = event.get_plain_text().strip()
            args = text.split()

            if len(args) < 2:
                yield event.plain_result(
                    "📜 炼制丹药\\n"
                    "─" * 40 + "\\n\\n"
                    "请指定要炼制的丹方编号\\n\\n"
                    "💡 使用方法: /炼丹 [丹方编号]\\n"
                    "💡 例如: /炼丹 1\\n\\n"
                    "💡 使用 /丹方列表 查看可用丹方"
                )
                return

            try:
                recipe_id = int(args[1])
            except ValueError:
                yield event.plain_result("❌ 丹方编号必须是数字")
                return

            # 炼制丹药
            result = await self.alchemy_sys.refine_pill(user_id, recipe_id)

            if result['success']:
                yield event.plain_result(
                    f"🎉 {result['message']}\\n\\n"
                    f"丹药名称: {result['quality']}{result['pill_name']}\\n"
                    f"消耗灵石: {result['spirit_stone_cost']}\\n"
                    f"获得经验: {result['experience_gained']}\\n"
                    f"获得声望: {result['reputation_gained']}"
                )
            else:
                yield event.plain_result(
                    f"😞 {result['message']}\\n\\n"
                    f"消耗灵石: {result['spirit_stone_cost']}\\n"
                    f"获得经验: {result['experience_gained']}"
                )

        except PlayerNotFoundError:
            yield event.plain_result("您还没有创建角色，请先使用 /修仙 创建角色")
        except ProfessionNotFoundError as e:
            yield event.plain_result(f"❌ {str(e)}\\n\\n💡 使用 /学习职业 炼丹师 学习炼丹")
        except RecipeNotFoundError as e:
            yield event.plain_result(f"❌ {str(e)}")
        except AlchemyError as e:
            yield event.plain_result(f"❌ {str(e)}")
        except Exception as e:
            logger.error(f"炼丹失败: {e}", exc_info=True)
            yield event.plain_result(f"炼丹失败：{str(e)}")
"""

# 炼器命令 - 复制到main.py
REFINING_COMMANDS = """
    @filter.command("图纸列表", alias={"图纸", "refining_blueprints"})
    async def refining_blueprints_cmd(self, event: AstrMessageEvent):
        \"\"\"查看可用图纸列表\"\"\"
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
        \"\"\"炼制装备\"\"\"
        user_id = event.get_sender_id()

        try:
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return

            # 获取图纸ID参数
            text = event.get_plain_text().strip()
            args = text.split()

            if len(args) < 2:
                yield event.plain_result(
                    "📜 炼制装备\\n"
                    "─" * 40 + "\\n\\n"
                    "请指定要炼制的图纸编号\\n\\n"
                    "💡 使用方法: /炼器 [图纸编号]\\n"
                    "💡 例如: /炼器 1\\n\\n"
                    "💡 使用 /图纸列表 查看可用图纸"
                )
                return

            try:
                blueprint_id = int(args[1])
            except ValueError:
                yield event.plain_result("❌ 图纸编号必须是数字")
                return

            # 炼制装备
            result = await self.refining_sys.refine_equipment(user_id, blueprint_id)

            if result['success']:
                yield event.plain_result(
                    f"🎉 {result['message']}\\n\\n"
                    f"装备名称: {result['quality']}{result['equipment_name']}\\n"
                    f"装备ID: {result['equipment_id']}\\n"
                    f"属性:\\n"
                    + "\\n".join([f"  {k}: {v}" for k, v in result['attributes'].items()]) +
                    f"\\n\\n消耗灵石: {result['spirit_stone_cost']}\\n"
                    f"获得经验: {result['experience_gained']}\\n"
                    f"获得声望: {result['reputation_gained']}"
                )
            else:
                yield event.plain_result(
                    f"😞 {result['message']}\\n\\n"
                    f"消耗灵石: {result['spirit_stone_cost']}\\n"
                    f"获得经验: {result['experience_gained']}"
                )

        except PlayerNotFoundError:
            yield event.plain_result("您还没有创建角色，请先使用 /修仙 创建角色")
        except ProfessionNotFoundError as e:
            yield event.plain_result(f"❌ {str(e)}\\n\\n💡 使用 /学习职业 炼器师 学习炼器")
        except BlueprintNotFoundError as e:
            yield event.plain_result(f"❌ {str(e)}")
        except RefiningError as e:
            yield event.plain_result(f"❌ {str(e)}")
        except Exception as e:
            logger.error(f"炼器失败: {e}", exc_info=True)
            yield event.plain_result(f"炼器失败：{str(e)}")

    @filter.command("强化装备", alias={"enhance", "装备强化"})
    async def enhance_equipment_cmd(self, event: AstrMessageEvent):
        \"\"\"强化装备\"\"\"
        user_id = event.get_sender_id()

        try:
            if not self._check_initialized():
                yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
                return

            # 获取装备ID参数
            text = event.get_plain_text().strip()
            args = text.split()

            if len(args) < 2:
                yield event.plain_result(
                    "📜 强化装备\\n"
                    "─" * 40 + "\\n\\n"
                    "请指定要强化的装备ID\\n\\n"
                    "💡 使用方法: /强化装备 [装备ID]\\n"
                    "💡 例如: /强化装备 1\\n\\n"
                    "💡 使用 /背包 查看装备ID"
                )
                return

            try:
                equipment_id = int(args[1])
            except ValueError:
                yield event.plain_result("❌ 装备ID必须是数字")
                return

            # 强化装备
            result = await self.refining_sys.enhance_equipment(user_id, equipment_id)

            if result['success']:
                yield event.plain_result(
                    f"🎉 {result['message']}\\n\\n"
                    f"装备等级: +{result['old_level']} → +{result['new_level']}\\n"
                    f"消耗灵石: {result['spirit_stone_cost']}\\n"
                    f"获得经验: {result['experience_gained']}"
                )
            else:
                yield event.plain_result(
                    f"😞 {result['message']}\\n\\n"
                    f"消耗灵石: {result['spirit_stone_cost']}"
                )

        except PlayerNotFoundError:
            yield event.plain_result("您还没有创建角色，请先使用 /修仙 创建角色")
        except ProfessionNotFoundError as e:
            yield event.plain_result(f"❌ {str(e)}\\n\\n💡 使用 /学习职业 炼器师 学习炼器")
        except RefiningError as e:
            yield event.plain_result(f"❌ {str(e)}")
        except Exception as e:
            logger.error(f"强化装备失败: {e}", exc_info=True)
            yield event.plain_result(f"强化装备失败：{str(e)}")
"""

# 注意：由于命令太多，剩余的阵法和符箓命令已经保存在此文件中
# 请手动将它们添加到main.py的末尾

print("职业命令模板已生成，请将命令复制到main.py中")
