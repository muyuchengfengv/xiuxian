"""
灵宠系统
负责灵宠的获取、管理、培养等功能
"""

import json
import random
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
from astrbot.api import logger

from .database import DatabaseManager
from .player import PlayerManager
from ..models.pet_model import Pet, PlayerPet, PetSecretRealm
from ..utils.exceptions import XiuxianException


class PetError(XiuxianException):
    """灵宠系统异常"""
    pass


class PetNotFoundError(PetError):
    """灵宠不存在异常"""
    pass


class AlreadyHasPetError(PetError):
    """已拥有灵宠异常"""
    pass


class PetSystem:
    """灵宠系统类"""

    # 初始灵宠配置（宗门可领取）
    STARTER_PETS = [
        {
            "id": 1,
            "name": "青羽鸟",
            "pet_type": "辅助型",
            "rarity": "普通",
            "description": "灵巧的青色小鸟，能够提升主人的修炼速度",
            "base_attributes": json.dumps({
                "cultivation_speed_bonus": 0.2,  # +20%修炼速度
                "combat_power": 10
            }),
            "growth_rate": 1.0,
            "max_level": 50,
            "element": "风",
            "capture_difficulty": 30
        },
        {
            "id": 2,
            "name": "福运兔",
            "pet_type": "辅助型",
            "rarity": "稀有",
            "description": "据说能带来好运的灵兔，提升主人的幸运值",
            "base_attributes": json.dumps({
                "luck_bonus": 15,  # +15幸运
                "breakthrough_bonus": 0.05,  # +5%突破成功率
                "combat_power": 5
            }),
            "growth_rate": 1.2,
            "max_level": 60,
            "capture_difficulty": 40
        },
        {
            "id": 3,
            "name": "炎狼幼崽",
            "pet_type": "战斗型",
            "rarity": "稀有",
            "description": "火焰狼的幼崽，拥有强大的战斗能力",
            "base_attributes": json.dumps({
                "attack_bonus": 0.15,  # +15%攻击力
                "defense_bonus": 0.10,  # +10%防御力
                "combat_power": 25
            }),
            "growth_rate": 1.5,
            "max_level": 70,
            "element": "火",
            "capture_difficulty": 50
        }
    ]

    # 秘境灵宠配置
    SECRET_REALM_PETS = [
        # 普通灵宠
        {
            "id": 10,
            "name": "灵草蛇",
            "pet_type": "采集型",
            "rarity": "普通",
            "description": "擅长寻找灵草的小蛇",
            "base_attributes": json.dumps({
                "material_find_bonus": 0.15,
                "combat_power": 8
            }),
            "growth_rate": 0.8,
            "max_level": 40,
            "element": "木",
            "capture_difficulty": 25
        },
        {
            "id": 11,
            "name": "寻宝鼠",
            "pet_type": "采集型",
            "rarity": "普通",
            "description": "天生能嗅到宝物的气息",
            "base_attributes": json.dumps({
                "treasure_find_bonus": 0.20,
                "spirit_stone_bonus": 0.10,
                "combat_power": 5
            }),
            "growth_rate": 0.9,
            "max_level": 45,
            "capture_difficulty": 30
        },
        # 稀有灵宠
        {
            "id": 12,
            "name": "雷霆豹",
            "pet_type": "战斗型",
            "rarity": "稀有",
            "description": "速度极快的雷系灵兽",
            "base_attributes": json.dumps({
                "attack_bonus": 0.20,
                "speed_bonus": 0.30,
                "combat_power": 35
            }),
            "growth_rate": 1.3,
            "max_level": 65,
            "element": "雷",
            "capture_difficulty": 55
        },
        {
            "id": 13,
            "name": "玄冰龟",
            "pet_type": "防御型",
            "rarity": "稀有",
            "description": "拥有坚硬冰甲的灵龟",
            "base_attributes": json.dumps({
                "defense_bonus": 0.30,
                "hp_bonus": 0.20,
                "combat_power": 30
            }),
            "growth_rate": 1.1,
            "max_level": 60,
            "element": "冰",
            "capture_difficulty": 50
        },
        # 史诗灵宠
        {
            "id": 14,
            "name": "紫金猿",
            "pet_type": "全能型",
            "rarity": "史诗",
            "description": "传说中的神猿后裔",
            "base_attributes": json.dumps({
                "cultivation_speed_bonus": 0.30,
                "attack_bonus": 0.20,
                "comprehension_bonus": 10,
                "combat_power": 50
            }),
            "growth_rate": 1.8,
            "max_level": 80,
            "capture_difficulty": 70
        },
        {
            "id": 15,
            "name": "凤凰雏鸟",
            "pet_type": "辅助型",
            "rarity": "史诗",
            "description": "浴火凤凰的幼崽，拥有涅槃之力",
            "base_attributes": json.dumps({
                "hp_regen": 0.15,  # +15%生命恢复
                "revive_chance": 0.10,  # 10%复活几率
                "combat_power": 45
            }),
            "growth_rate": 2.0,
            "max_level": 90,
            "element": "火",
            "evolution_to": 16,  # 可进化成凤凰
            "capture_difficulty": 75
        },
        # 传说灵宠
        {
            "id": 16,
            "name": "涅槃凤凰",
            "pet_type": "全能型",
            "rarity": "传说",
            "description": "浴火重生的神鸟",
            "base_attributes": json.dumps({
                "cultivation_speed_bonus": 0.50,
                "attack_bonus": 0.35,
                "hp_regen": 0.25,
                "revive_chance": 0.25,
                "combat_power": 100
            }),
            "growth_rate": 2.5,
            "max_level": 100,
            "element": "火",
            "capture_difficulty": 95
        },
        {
            "id": 17,
            "name": "青龙",
            "pet_type": "全能型",
            "rarity": "传说",
            "description": "四灵之一，掌控木之法则",
            "base_attributes": json.dumps({
                "cultivation_speed_bonus": 0.60,
                "all_attributes_bonus": 0.20,
                "hp_bonus": 0.40,
                "combat_power": 120
            }),
            "growth_rate": 3.0,
            "max_level": 100,
            "element": "木",
            "capture_difficulty": 98
        }
    ]

    def __init__(self, db: DatabaseManager, player_mgr: PlayerManager):
        """
        初始化灵宠系统

        Args:
            db: 数据库管理器
            player_mgr: 玩家管理器
        """
        self.db = db
        self.player_mgr = player_mgr
        self.sect_sys = None  # 宗门系统（可选）

    def set_sect_system(self, sect_sys):
        """
        设置宗门系统（用于宗门检查）

        Args:
            sect_sys: 宗门系统实例
        """
        self.sect_sys = sect_sys

    async def init_pet_templates(self):
        """初始化灵宠模板"""
        all_pets = self.STARTER_PETS + self.SECRET_REALM_PETS

        for pet_data in all_pets:
            # 检查是否已存在
            existing = await self.db.fetchone(
                "SELECT id FROM pets WHERE id = ?",
                (pet_data['id'],)
            )

            if not existing:
                await self.db.execute(
                    """
                    INSERT INTO pets (
                        id, name, pet_type, rarity, description,
                        base_attributes, growth_rate, max_level,
                        element, evolution_to, capture_difficulty
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        pet_data['id'],
                        pet_data['name'],
                        pet_data['pet_type'],
                        pet_data['rarity'],
                        pet_data['description'],
                        pet_data['base_attributes'],
                        pet_data['growth_rate'],
                        pet_data['max_level'],
                        pet_data.get('element'),
                        pet_data.get('evolution_to'),
                        pet_data['capture_difficulty']
                    )
                )

        logger.info(f"灵宠模板初始化完成，共 {len(all_pets)} 种灵宠")

    async def get_starter_pets(self) -> List[Pet]:
        """
        获取初始灵宠列表

        Returns:
            初始灵宠列表
        """
        rows = await self.db.fetchall(
            "SELECT * FROM pets WHERE id IN (1, 2, 3) ORDER BY id"
        )

        pets = []
        for row in rows:
            pet = Pet.from_db_row(dict(row))
            pets.append(pet)

        return pets

    async def claim_starter_pet(self, user_id: str, pet_id: int) -> PlayerPet:
        """
        领取初始灵宠（宗门福利）

        Args:
            user_id: 用户ID
            pet_id: 灵宠ID（1-3）

        Returns:
            玩家灵宠对象

        Raises:
            PetNotFoundError: 灵宠不存在
            AlreadyHasPetError: 已领取过初始灵宠
            ValueError: 无效的灵宠ID
            PetError: 未加入宗门
        """
        # 检查玩家是否加入宗门
        if self.sect_sys:
            player_sect = await self.sect_sys.get_player_sect(user_id)
            if not player_sect:
                raise PetError("您还未加入宗门，无法领取初始灵宠。请先使用 /加入宗门 加入一个宗门")

        # 检查玩家是否已领取过初始灵宠
        existing_pet = await self.db.fetchone(
            "SELECT id FROM player_pets WHERE user_id = ? AND acquired_from = 'sect_starter'",
            (user_id,)
        )

        if existing_pet:
            raise AlreadyHasPetError("您已经领取过初始灵宠了")

        # 验证灵宠ID
        if pet_id not in [1, 2, 3]:
            raise ValueError("无效的灵宠ID，请选择1-3之间的灵宠")

        # 获取灵宠模板
        pet_template = await self._get_pet_template(pet_id)
        if not pet_template:
            raise PetNotFoundError(f"灵宠 {pet_id} 不存在")

        # 创建玩家灵宠
        player_pet = await self._create_player_pet(
            user_id=user_id,
            pet_id=pet_id,
            pet_name=pet_template.name,
            acquired_from="sect_starter"
        )

        logger.info(f"玩家 {user_id} 领取了初始灵宠: {pet_template.name}")

        return player_pet

    async def explore_secret_realm(self, user_id: str, use_pet_bag: bool = False) -> Dict[str, Any]:
        """
        探索灵宠秘境

        Args:
            user_id: 用户ID
            use_pet_bag: 是否使用灵宠袋

        Returns:
            探索结果字典
        """
        # 获取玩家信息
        player = await self.player_mgr.get_player_or_error(user_id)

        # 获取或创建秘境记录
        realm_record = await self._get_or_create_secret_realm_record(user_id)

        # 检查冷却时间（1小时）
        if realm_record.last_exploration_at:
            last_time = datetime.fromisoformat(realm_record.last_exploration_at)
            cooldown_end = last_time + timedelta(hours=1)
            if datetime.now() < cooldown_end:
                remaining = (cooldown_end - datetime.now()).total_seconds() / 60
                return {
                    'success': False,
                    'message': f"秘境探索冷却中，还需 {int(remaining)} 分钟"
                }

        # 随机遇到灵宠
        encounter_chance = 0.6  # 60%遇到灵宠
        if random.random() > encounter_chance:
            # 未遇到灵宠
            await self._update_exploration_record(user_id)
            return {
                'success': False,
                'message': "在秘境中搜索了一番，但没有遇到灵宠",
                'exploration_count': realm_record.exploration_count + 1
            }

        # 根据秘境等级和玩家境界确定可遇到的灵宠
        available_pets = await self._get_available_secret_realm_pets(player.realm, realm_record.realm_level)

        if not available_pets:
            await self._update_exploration_record(user_id)
            return {
                'success': False,
                'message': "秘境中空无一物",
                'exploration_count': realm_record.exploration_count + 1
            }

        # 随机选择一只灵宠
        encountered_pet = random.choice(available_pets)

        result = {
            'success': True,
            'encountered_pet': encountered_pet,
            'exploration_count': realm_record.exploration_count + 1
        }

        # 如果使用灵宠袋，尝试捕获
        if use_pet_bag:
            capture_result = await self._attempt_capture(user_id, encountered_pet, player)
            result.update(capture_result)
        else:
            result['message'] = f"遇到了 {encountered_pet.get_rarity_color()}{encountered_pet.name}！\n使用 /灵宠袋 进行捕获"

        # 更新探索记录
        await self._update_exploration_record(user_id)

        return result

    async def _attempt_capture(self, user_id: str, pet: Pet, player) -> Dict[str, Any]:
        """
        尝试捕获灵宠

        Args:
            user_id: 用户ID
            pet: 灵宠模板
            player: 玩家对象

        Returns:
            捕获结果
        """
        # 计算捕获成功率
        base_rate = 100 - pet.capture_difficulty  # 基础成功率
        luck_bonus = player.luck * 0.5  # 幸运加成
        capture_rate = min(95, base_rate + luck_bonus) / 100

        # 尝试捕获
        if random.random() < capture_rate:
            # 捕获成功
            player_pet = await self._create_player_pet(
                user_id=user_id,
                pet_id=pet.id,
                pet_name=pet.name,
                acquired_from="secret_realm_capture"
            )

            return {
                'captured': True,
                'capture_rate': capture_rate,
                'message': f"🎉 成功捕获 {pet.get_rarity_color()}{pet.name}！",
                'player_pet': player_pet
            }
        else:
            return {
                'captured': False,
                'capture_rate': capture_rate,
                'message': f"💔 捕获失败！{pet.name} 逃走了..."
            }

    async def get_player_pets(self, user_id: str) -> List[PlayerPet]:
        """
        获取玩家的所有灵宠

        Args:
            user_id: 用户ID

        Returns:
            玩家灵宠列表
        """
        rows = await self.db.fetchall(
            "SELECT * FROM player_pets WHERE user_id = ? ORDER BY is_active DESC, level DESC",
            (user_id,)
        )

        pets = []
        for row in rows:
            player_pet = PlayerPet.from_db_row(dict(row))
            # 加载灵宠模板
            player_pet.pet_template = await self._get_pet_template(player_pet.pet_id)
            pets.append(player_pet)

        return pets

    async def activate_pet(self, user_id: str, pet_id: int) -> PlayerPet:
        """
        激活/出战灵宠

        Args:
            user_id: 用户ID
            pet_id: 玩家灵宠ID

        Returns:
            激活的灵宠

        Raises:
            PetNotFoundError: 灵宠不存在
        """
        # 先取消所有灵宠的激活状态
        await self.db.execute(
            "UPDATE player_pets SET is_active = 0 WHERE user_id = ?",
            (user_id,)
        )

        # 激活指定灵宠
        await self.db.execute(
            "UPDATE player_pets SET is_active = 1, updated_at = ? WHERE id = ? AND user_id = ?",
            (datetime.now().isoformat(), pet_id, user_id)
        )

        # 获取灵宠信息
        row = await self.db.fetchone(
            "SELECT * FROM player_pets WHERE id = ? AND user_id = ?",
            (pet_id, user_id)
        )

        if not row:
            raise PetNotFoundError("灵宠不存在")

        player_pet = PlayerPet.from_db_row(dict(row))
        player_pet.pet_template = await self._get_pet_template(player_pet.pet_id)

        logger.info(f"玩家 {user_id} 激活了灵宠: {player_pet.pet_name}")

        return player_pet

    async def get_active_pet(self, user_id: str) -> Optional[PlayerPet]:
        """
        获取当前激活的灵宠

        Args:
            user_id: 用户ID

        Returns:
            激活的灵宠，如果没有则返回None
        """
        row = await self.db.fetchone(
            "SELECT * FROM player_pets WHERE user_id = ? AND is_active = 1",
            (user_id,)
        )

        if not row:
            return None

        player_pet = PlayerPet.from_db_row(dict(row))
        player_pet.pet_template = await self._get_pet_template(player_pet.pet_id)

        return player_pet

    # ========== 内部辅助方法 ==========

    async def _get_pet_template(self, pet_id: int) -> Optional[Pet]:
        """获取灵宠模板"""
        row = await self.db.fetchone(
            "SELECT * FROM pets WHERE id = ?",
            (pet_id,)
        )

        return Pet.from_db_row(dict(row)) if row else None

    async def _create_player_pet(
        self,
        user_id: str,
        pet_id: int,
        pet_name: str,
        acquired_from: str
    ) -> PlayerPet:
        """创建玩家灵宠"""
        await self.db.execute(
            """
            INSERT INTO player_pets (
                user_id, pet_id, pet_name, level, experience,
                is_active, intimacy, battle_count, acquired_from, acquired_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id, pet_id, pet_name, 1, 0,
                0, 0, 0, acquired_from, datetime.now().isoformat()
            )
        )

        # 获取新创建的灵宠
        row = await self.db.fetchone(
            "SELECT * FROM player_pets WHERE user_id = ? AND pet_id = ? ORDER BY id DESC LIMIT 1",
            (user_id, pet_id)
        )

        player_pet = PlayerPet.from_db_row(dict(row))
        player_pet.pet_template = await self._get_pet_template(pet_id)

        return player_pet

    async def _get_or_create_secret_realm_record(self, user_id: str) -> PetSecretRealm:
        """获取或创建秘境记录"""
        row = await self.db.fetchone(
            "SELECT * FROM pet_secret_realms WHERE user_id = ?",
            (user_id,)
        )

        if row:
            return PetSecretRealm.from_db_row(dict(row))

        # 创建新记录
        await self.db.execute(
            """
            INSERT INTO pet_secret_realms (
                user_id, realm_level, exploration_count, created_at
            ) VALUES (?, ?, ?, ?)
            """,
            (user_id, 1, 0, datetime.now().isoformat())
        )

        row = await self.db.fetchone(
            "SELECT * FROM pet_secret_realms WHERE user_id = ?",
            (user_id,)
        )

        return PetSecretRealm.from_db_row(dict(row))

    async def _update_exploration_record(self, user_id: str):
        """更新探索记录"""
        await self.db.execute(
            """
            UPDATE pet_secret_realms
            SET exploration_count = exploration_count + 1,
                last_exploration_at = ?
            WHERE user_id = ?
            """,
            (datetime.now().isoformat(), user_id)
        )

    async def _get_available_secret_realm_pets(self, player_realm: str, realm_level: int) -> List[Pet]:
        """获取秘境中可遇到的灵宠"""
        # 根据玩家境界和秘境等级确定稀有度范围
        rarity_weights = {
            "普通": 0.60,
            "稀有": 0.30,
            "史诗": 0.08,
            "传说": 0.02
        }

        # 查询所有秘境灵宠
        rows = await self.db.fetchall(
            "SELECT * FROM pets WHERE id >= 10"
        )

        all_pets = [Pet.from_db_row(dict(row)) for row in rows]

        # 根据稀有度权重随机选择
        available_pets = []
        for pet in all_pets:
            weight = rarity_weights.get(pet.rarity, 0)
            if random.random() < weight:
                available_pets.append(pet)

        return available_pets if available_pets else all_pets[:2]  # 至少返回两只普通灵宠

    async def get_active_pet_bonuses(self, user_id: str) -> Dict[str, float]:
        """
        获取激活灵宠的加成效果

        返回字典包含以下可能的键：
        - cultivation_speed_bonus: 修炼速度加成
        - luck_bonus: 幸运值加成
        - breakthrough_bonus: 突破成功率加成
        - attack_bonus: 攻击力加成
        - defense_bonus: 防御力加成
        - material_find_bonus: 材料获取加成
        """
        bonuses = {
            "cultivation_speed_bonus": 0.0,
            "luck_bonus": 0.0,
            "breakthrough_bonus": 0.0,
            "attack_bonus": 0.0,
            "defense_bonus": 0.0,
            "material_find_bonus": 0.0
        }

        try:
            # 获取激活的灵宠
            row = await self.db.fetchone(
                """
                SELECT pp.*, p.*
                FROM player_pets pp
                JOIN pets p ON pp.pet_id = p.id
                WHERE pp.user_id = ? AND pp.is_active = 1
                """,
                (user_id,)
            )

            if not row:
                return bonuses

            # 解析灵宠的基础属性
            base_attributes = json.loads(row['base_attributes'])

            # 计算等级加成系数（每级增加2%效果）
            level = row['level']
            level_multiplier = 1.0 + (level - 1) * 0.02

            # 计算亲密度加成系数（满亲密度额外增加30%效果）
            intimacy = row['intimacy']
            intimacy_multiplier = 1.0 + (intimacy / 100) * 0.3

            # 总加成系数
            total_multiplier = level_multiplier * intimacy_multiplier

            # 应用加成到各项属性
            for key in bonuses.keys():
                if key in base_attributes:
                    base_value = base_attributes[key]
                    bonuses[key] = base_value * total_multiplier

            logger.debug(f"用户 {user_id} 的灵宠加成: {bonuses}")
            return bonuses

        except Exception as e:
            logger.error(f"获取灵宠加成失败: {e}", exc_info=True)
            return bonuses
