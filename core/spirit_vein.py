"""
灵脉系统
实现灵脉占领、挑战、收益等功能
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import random
from astrbot.api import logger

from .database import DatabaseManager
from .player import PlayerManager
from ..models.spirit_vein_model import SpiritVein
from ..utils.exceptions import PlayerNotFoundError


class SpiritVeinError(Exception):
    """灵脉系统异常"""
    pass


class SpiritVeinSystem:
    """灵脉系统类"""

    # 灵脉等级配置
    VEIN_LEVELS = {
        5: {"count": 3, "base_income": 1000, "name_prefix": "天"},
        4: {"count": 5, "base_income": 800, "name_prefix": "地"},
        3: {"count": 8, "base_income": 640, "name_prefix": "玄"},
        2: {"count": 12, "base_income": 512, "name_prefix": "黄"},
        1: {"count": 20, "base_income": 410, "name_prefix": "人"}
    }

    # 灵脉名称后缀
    VEIN_SUFFIXES = [
        "龙脉", "凤脉", "麒麟脉", "玄武脉", "朱雀脉", "青龙脉", "白虎脉",
        "灵泉", "仙源", "神泉", "圣泉", "仙池", "灵池", "神池",
        "福地", "洞天", "仙境", "秘境", "圣地", "宝地", "仙府"
    ]

    # 位置列表
    LOCATIONS = [
        "东海之滨", "西域荒漠", "南疆丛林", "北境雪原", "中州平原",
        "昆仑山脉", "蓬莱仙岛", "瀛洲海域", "方壶山", "玄天峰",
        "碧落谷", "紫霄崖", "青云岭", "赤焰山", "寒冰涧",
        "幽冥渊", "九天阁", "万妖林", "神魔峡", "太虚境"
    ]

    def __init__(self, db: DatabaseManager, player_mgr: PlayerManager):
        """
        初始化灵脉系统

        Args:
            db: 数据库管理器
            player_mgr: 玩家管理器
        """
        self.db = db
        self.player_mgr = player_mgr
        self.combat_sys = None  # 战斗系统（可选，用于挑战战斗）

    def set_combat_system(self, combat_sys):
        """
        设置战斗系统（依赖注入）

        Args:
            combat_sys: 战斗系统实例
        """
        self.combat_sys = combat_sys

    async def init_spirit_veins(self):
        """初始化灵脉（系统启动时调用）"""
        # 检查是否已有灵脉
        existing = await self.db.fetchone("SELECT COUNT(*) as count FROM spirit_veins")
        if existing and existing['count'] > 0:
            logger.info(f"灵脉已存在，共 {existing['count']} 条")
            return

        logger.info("开始初始化灵脉...")

        vein_id = 1
        used_names = set()

        # 按等级创建灵脉
        for level in sorted(self.VEIN_LEVELS.keys(), reverse=True):
            config = self.VEIN_LEVELS[level]
            count = config['count']
            base_income = config['base_income']
            prefix = config['name_prefix']

            for i in range(count):
                # 生成唯一的灵脉名称
                while True:
                    suffix = random.choice(self.VEIN_SUFFIXES)
                    name = f"{prefix}级{suffix}"
                    if name not in used_names:
                        used_names.add(name)
                        break

                # 随机位置
                location = random.choice(self.LOCATIONS)

                # 插入数据库
                await self.db.execute(
                    """
                    INSERT INTO spirit_veins (
                        id, name, level, location, base_income,
                        owner_id, owner_name, occupied_at, last_collect_at, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        vein_id,
                        name,
                        level,
                        location,
                        base_income,
                        None,  # 初始无主
                        None,
                        None,
                        None,
                        datetime.now().isoformat()
                    )
                )

                vein_id += 1

        total_veins = sum(config['count'] for config in self.VEIN_LEVELS.values())
        logger.info(f"灵脉初始化完成，共创建 {total_veins} 条灵脉")

    async def get_all_veins(self) -> List[SpiritVein]:
        """获取所有灵脉"""
        rows = await self.db.fetchall(
            "SELECT * FROM spirit_veins ORDER BY level DESC, id ASC"
        )

        veins = []
        for row in rows:
            vein = SpiritVein.from_dict(dict(row))
            veins.append(vein)

        return veins

    async def get_vein_by_id(self, vein_id: int) -> Optional[SpiritVein]:
        """根据ID获取灵脉"""
        row = await self.db.fetchone(
            "SELECT * FROM spirit_veins WHERE id = ?",
            (vein_id,)
        )

        if not row:
            return None

        return SpiritVein.from_dict(dict(row))

    async def get_player_veins(self, user_id: str) -> List[SpiritVein]:
        """获取玩家占领的所有灵脉"""
        rows = await self.db.fetchall(
            "SELECT * FROM spirit_veins WHERE owner_id = ? ORDER BY level DESC",
            (user_id,)
        )

        veins = []
        for row in rows:
            vein = SpiritVein.from_dict(dict(row))
            veins.append(vein)

        return veins

    async def occupy_vein(self, user_id: str, vein_id: int) -> Dict[str, Any]:
        """
        占领无主灵脉

        Args:
            user_id: 用户ID
            vein_id: 灵脉ID

        Returns:
            Dict: 占领结果

        Raises:
            PlayerNotFoundError: 玩家不存在
            SpiritVeinError: 灵脉异常
        """
        # 获取玩家信息
        player = await self.player_mgr.get_player_or_error(user_id)

        # 获取灵脉信息
        vein = await self.get_vein_by_id(vein_id)
        if not vein:
            raise SpiritVeinError(f"灵脉不存在: {vein_id}")

        # 检查灵脉是否已被占领
        if vein.is_occupied():
            raise SpiritVeinError(f"{vein.name} 已被 {vein.owner_name} 占领，请使用挑战功能")

        # 检查玩家已占领的灵脉数量
        player_veins = await self.get_player_veins(user_id)

        # 检查总数量限制（最多5个）
        if len(player_veins) >= 5:
            raise SpiritVeinError("您已占领5个灵脉，无法继续占领！请先放弃或被夺取后再尝试")

        # 检查5级灵脉限制（最多1个）
        if vein.level == 5:
            level5_count = sum(1 for v in player_veins if v.level == 5)
            if level5_count >= 1:
                raise SpiritVeinError("您已占领1个5级灵脉，无法再占领更多5级灵脉！")

        # 占领灵脉
        now = datetime.now()
        await self.db.execute(
            """
            UPDATE spirit_veins
            SET owner_id = ?, owner_name = ?, occupied_at = ?, last_collect_at = ?
            WHERE id = ?
            """,
            (user_id, player.name, now.isoformat(), now.isoformat(), vein_id)
        )

        logger.info(f"玩家 {player.name} 占领了 {vein.name}")

        return {
            'success': True,
            'message': f"成功占领 {vein.name}！\n每小时可获得 {vein.base_income} 灵石\n当前占领: {len(player_veins) + 1}/5",
            'vein': vein
        }

    async def challenge_vein(self, challenger_id: str, vein_id: int) -> Dict[str, Any]:
        """
        挑战灵脉占领者

        Args:
            challenger_id: 挑战者user_id
            vein_id: 灵脉ID

        Returns:
            Dict: 战斗结果

        Raises:
            PlayerNotFoundError: 玩家不存在
            SpiritVeinError: 灵脉异常
        """
        # 获取挑战者信息
        challenger = await self.player_mgr.get_player_or_error(challenger_id)

        # 获取灵脉信息
        vein = await self.get_vein_by_id(vein_id)
        if not vein:
            raise SpiritVeinError(f"灵脉不存在: {vein_id}")

        # 检查灵脉是否有主
        if not vein.is_occupied():
            raise SpiritVeinError(f"{vein.name} 尚无主人，请直接占领")

        # 不能挑战自己的灵脉
        if vein.owner_id == challenger_id:
            raise SpiritVeinError("不能挑战自己占领的灵脉")

        # 检查挑战者灵脉数量限制（如果要夺取，必须有空位或者对方也有5个灵脉）
        challenger_veins = await self.get_player_veins(challenger_id)
        if len(challenger_veins) >= 5:
            raise SpiritVeinError("您已占领5个灵脉，无法继续夺取！请先放弃一个灵脉")

        # 检查5级灵脉限制
        if vein.level == 5:
            level5_count = sum(1 for v in challenger_veins if v.level == 5)
            if level5_count >= 1:
                raise SpiritVeinError("您已占领1个5级灵脉，无法再夺取5级灵脉！")

        # 获取占领者信息
        defender = await self.player_mgr.get_player_or_error(vein.owner_id)

        # 执行战斗（使用切磋系统）
        is_challenger_win = False
        combat_log_formatted = ""

        if self.combat_sys:
            # 使用战斗系统进行战斗
            try:
                combat_result = await self.combat_sys.initiate_combat(
                    challenger_id,
                    vein.owner_id
                )

                # 获取胜利者
                winner = combat_result['winner']
                is_challenger_win = (winner == challenger_id or winner == challenger.name)

                # 格式化战斗日志
                combat_log_formatted = await self.combat_sys.format_combat_log(
                    combat_result['combat_log'],
                    challenger,
                    defender
                )

            except Exception as e:
                logger.error(f"灵脉战斗失败: {e}", exc_info=True)
                # 如果战斗系统失败，使用简单对比
                is_challenger_win = self._simple_battle(challenger, defender)
                combat_log_formatted = "战斗系统异常，使用简易判定"
        else:
            # 没有战斗系统，使用简单战力对比
            is_challenger_win = self._simple_battle(challenger, defender)
            combat_log_formatted = "使用简易战力判定"

        result = {
            'success': is_challenger_win,
            'challenger': challenger.name,
            'defender': defender.name,
            'vein': vein,
            'combat_log': combat_log_formatted
        }

        if is_challenger_win:
            # 挑战者胜利，夺取灵脉
            now = datetime.now()
            await self.db.execute(
                """
                UPDATE spirit_veins
                SET owner_id = ?, owner_name = ?, occupied_at = ?, last_collect_at = ?
                WHERE id = ?
                """,
                (challenger_id, challenger.name, now.isoformat(), now.isoformat(), vein_id)
            )

            result['message'] = (
                f"⚔️ {challenger.name} 挑战成功！\n"
                f"击败了 {defender.name}，夺取了 {vein.name}！\n"
                f"每小时可获得 {vein.base_income} 灵石\n\n"
                f"{combat_log_formatted}"
            )

            logger.info(f"玩家 {challenger.name} 挑战成功，从 {defender.name} 手中夺取了 {vein.name}")
        else:
            # 挑战者失败
            result['message'] = (
                f"💔 {challenger.name} 挑战失败！\n"
                f"不敌 {defender.name}，{vein.name} 依然属于对方\n\n"
                f"{combat_log_formatted}"
            )

            logger.info(f"玩家 {challenger.name} 挑战失败，{vein.name} 依然属于 {defender.name}")

        return result

    def _simple_battle(self, challenger, defender) -> bool:
        """
        简单战斗判定（基于战力对比）

        Args:
            challenger: 挑战者
            defender: 防守者

        Returns:
            bool: 挑战者是否胜利
        """
        # 计算战力
        challenger_power = (
            challenger.attack * 2 +
            challenger.defense +
            challenger.max_hp // 10 +
            challenger.spiritual_power * 3
        )

        defender_power = (
            defender.attack * 2 +
            defender.defense +
            defender.max_hp // 10 +
            defender.spiritual_power * 3
        )

        # 防守者有10%加成
        defender_power = int(defender_power * 1.1)

        # 计算胜率（挑战者战力 / 总战力）
        total_power = challenger_power + defender_power
        if total_power == 0:
            return random.random() < 0.5

        win_rate = challenger_power / total_power

        # 随机判定
        return random.random() < win_rate

    async def abandon_vein(self, user_id: str, vein_id: int) -> Dict[str, Any]:
        """
        放弃灵脉

        Args:
            user_id: 用户ID
            vein_id: 灵脉ID

        Returns:
            Dict: 放弃结果

        Raises:
            PlayerNotFoundError: 玩家不存在
            SpiritVeinError: 灵脉异常
        """
        # 获取玩家信息
        player = await self.player_mgr.get_player_or_error(user_id)

        # 获取灵脉信息
        vein = await self.get_vein_by_id(vein_id)
        if not vein:
            raise SpiritVeinError(f"灵脉不存在: {vein_id}")

        # 检查灵脉是否是自己的
        if vein.owner_id != user_id:
            raise SpiritVeinError(f"{vein.name} 不是您的灵脉")

        # 计算未收取的收益
        now = datetime.now()
        if vein.last_collect_at:
            hours_passed = (now - vein.last_collect_at).total_seconds() / 3600
        else:
            hours_passed = (now - vein.occupied_at).total_seconds() / 3600

        hours_passed = min(hours_passed, 24)
        uncollected_income = int(vein.base_income * hours_passed)

        # 放弃灵脉（设置为无主）
        await self.db.execute(
            """
            UPDATE spirit_veins
            SET owner_id = NULL, owner_name = NULL, occupied_at = NULL, last_collect_at = NULL
            WHERE id = ?
            """,
            (vein_id,)
        )

        logger.info(f"玩家 {player.name} 放弃了 {vein.name}")

        message = f"已放弃 {vein.name}"
        if uncollected_income > 0:
            message += f"\n⚠️ 损失了未收取的 {uncollected_income} 灵石"

        return {
            'success': True,
            'message': message,
            'vein': vein,
            'lost_income': uncollected_income
        }

    async def collect_income(self, user_id: str, vein_id: Optional[int] = None) -> Dict[str, Any]:
        """
        收取灵脉收益

        Args:
            user_id: 用户ID
            vein_id: 灵脉ID（如果为None则收取所有灵脉）

        Returns:
            Dict: 收取结果

        Raises:
            PlayerNotFoundError: 玩家不存在
            SpiritVeinError: 灵脉异常
        """
        # 获取玩家信息
        player = await self.player_mgr.get_player_or_error(user_id)

        if vein_id:
            # 收取单个灵脉
            veins = [await self.get_vein_by_id(vein_id)]
            if not veins[0]:
                raise SpiritVeinError(f"灵脉不存在: {vein_id}")
        else:
            # 收取所有灵脉
            veins = await self.get_player_veins(user_id)

        if not veins:
            raise SpiritVeinError("您还没有占领任何灵脉")

        total_income = 0
        vein_details = []

        now = datetime.now()

        for vein in veins:
            # 检查是否是自己的灵脉
            if vein.owner_id != user_id:
                continue

            # 计算可收取的收益
            if vein.last_collect_at:
                hours_passed = (now - vein.last_collect_at).total_seconds() / 3600
            else:
                # 如果从未收取过，从占领时间开始计算
                hours_passed = (now - vein.occupied_at).total_seconds() / 3600

            # 最多累积24小时
            hours_passed = min(hours_passed, 24)

            if hours_passed < 0.01:  # 小于1分钟
                continue

            income = int(vein.base_income * hours_passed)
            total_income += income

            vein_details.append({
                'name': vein.name,
                'level': vein.level,
                'hours': hours_passed,
                'income': income
            })

            # 更新收取时间
            await self.db.execute(
                "UPDATE spirit_veins SET last_collect_at = ? WHERE id = ?",
                (now.isoformat(), vein.id)
            )

        if total_income == 0:
            return {
                'success': False,
                'message': "当前没有可收取的收益（距离上次收取不足1分钟）",
                'total_income': 0
            }

        # 增加玩家灵石
        await self.player_mgr.add_spirit_stone(user_id, total_income)

        logger.info(f"玩家 {player.name} 收取灵脉收益: {total_income} 灵石")

        return {
            'success': True,
            'message': f"成功收取 {total_income} 灵石！",
            'total_income': total_income,
            'vein_details': vein_details
        }

    async def format_vein_list(self, level_filter: Optional[int] = None) -> str:
        """
        格式化灵脉列表显示

        Args:
            level_filter: 等级过滤（可选）

        Returns:
            str: 格式化的灵脉列表
        """
        veins = await self.get_all_veins()

        if level_filter:
            veins = [v for v in veins if v.level == level_filter]

        lines = [
            "🌟 灵脉列表",
            "─" * 40,
            ""
        ]

        if not veins:
            lines.append("当前没有灵脉")
        else:
            # 按等级分组
            veins_by_level = {}
            for vein in veins:
                if vein.level not in veins_by_level:
                    veins_by_level[vein.level] = []
                veins_by_level[vein.level].append(vein)

            for level in sorted(veins_by_level.keys(), reverse=True):
                level_veins = veins_by_level[level]
                lines.append(f"【{level}级灵脉】每小时 {level_veins[0].base_income} 灵石")

                for vein in level_veins:
                    status = f"占领者: {vein.owner_name}" if vein.is_occupied() else "无主"
                    lines.append(
                        f"  {vein.id}. {vein.name} ({vein.location})\n"
                        f"     状态: {status}"
                    )

                lines.append("")

        lines.extend([
            "💡 /占领灵脉 [编号] - 占领无主灵脉",
            "💡 /挑战灵脉 [编号] - 挑战占领者",
            "💡 /收取灵脉 - 收取所有灵脉收益",
            "💡 /我的灵脉 - 查看占领的灵脉"
        ])

        return "\n".join(lines)

    async def format_player_veins(self, user_id: str) -> str:
        """
        格式化玩家的灵脉列表

        Args:
            user_id: 用户ID

        Returns:
            str: 格式化的灵脉列表
        """
        veins = await self.get_player_veins(user_id)

        lines = [
            "🌟 我的灵脉",
            "─" * 40,
            ""
        ]

        if not veins:
            lines.extend([
                "您还没有占领任何灵脉",
                "",
                "💡 /灵脉列表 - 查看所有灵脉",
                "💡 /占领灵脉 [编号] - 占领无主灵脉",
                "",
                "📝 占领规则：",
                "   • 每人最多占领5个灵脉",
                "   • 5级灵脉每人最多占领1个"
            ])
        else:
            total_hourly = 0
            now = datetime.now()
            level5_count = sum(1 for v in veins if v.level == 5)

            for vein in veins:
                # 计算已产生的收益
                if vein.last_collect_at:
                    hours_passed = (now - vein.last_collect_at).total_seconds() / 3600
                else:
                    hours_passed = (now - vein.occupied_at).total_seconds() / 3600

                hours_passed = min(hours_passed, 24)
                uncollected = int(vein.base_income * hours_passed)

                lines.append(
                    f"{vein.id}. {vein.name} ({vein.level}级)\n"
                    f"   位置: {vein.location}\n"
                    f"   收益: {vein.base_income} 灵石/小时\n"
                    f"   待收取: {uncollected} 灵石"
                )

                total_hourly += vein.base_income

            lines.extend([
                "",
                f"总计: {len(veins)}/5 条灵脉",
                f"5级灵脉: {level5_count}/1",
                f"每小时收益: {total_hourly} 灵石",
                "",
                "💡 /收取灵脉 - 收取所有灵脉收益",
                "💡 /放弃灵脉 [编号] - 放弃指定灵脉"
            ])

        return "\n".join(lines)
