"""
数据库管理器
使用aiosqlite提供异步数据库操作
"""

import aiosqlite
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from contextlib import asynccontextmanager
from astrbot.api import logger


class DatabaseManager:
    """数据库管理器"""

    def __init__(self, db_path: str):
        """
        初始化数据库管理器

        Args:
            db_path: 数据库文件路径
        """
        self.db_path = Path(db_path)
        self.db: Optional[aiosqlite.Connection] = None

    async def init_db(self):
        """初始化数据库连接并创建表"""
        try:
            # 确保数据目录存在
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

            # 建立连接
            self.db = await aiosqlite.connect(str(self.db_path))
            self.db.row_factory = aiosqlite.Row  # 使结果可以通过列名访问

            logger.info(f"数据库连接成功: {self.db_path}")

            # 备份现有数据
            await self._backup_existing_data()

            # 创建表结构（不删除现有表，只创建新表和添加新字段）
            await self._create_or_update_tables()

            # 还原备份数据
            await self._restore_backup_data()

            # 创建索引
            await self._create_indexes()

            # 初始化基础地点数据
            await self._seed_initial_locations()

            # 修复现有玩家的属性（如果有突破系统bug导致的属性异常）
            await self._fix_player_attributes()

            logger.info("数据库初始化完成")

        except Exception as e:
            logger.error(f"数据库初始化失败: {e}", exc_info=True)
            raise

    async def _backup_existing_data(self):
        """备份现有数据"""
        if not await self.table_exists("players"):
            logger.info("数据库为空，无需备份")
            return

        logger.info("开始备份现有数据...")
        
        # 备份所有表的数据
        tables_to_backup = [
            "players", "equipment", "skills", "professions", "recipes",
            "crafting_logs", "tools", "profession_skills", "active_formations",
            "items", "sects", "sect_members", "ai_generation_history",
            "tribulations", "profession_exams", "locations", "player_locations",
            "cultivation_methods", "player_cultivation_methods", "method_skills",
            "market_items", "market_transactions",
            "pets", "player_pets", "pet_secret_realms"
        ]
        
        for table in tables_to_backup:
            if await self.table_exists(table):
                try:
                    await self.execute(f"DROP TABLE IF EXISTS {table}_backup")
                    await self.execute(f"CREATE TABLE {table}_backup AS SELECT * FROM {table}")
                    logger.info(f"已备份表: {table}")
                except Exception as e:
                    logger.error(f"备份表 {table} 失败: {e}")
            else:
                logger.debug(f"表 {table} 不存在，跳过备份")
        
        logger.info("数据备份完成")

    async def _restore_backup_data(self):
        """还原备份数据"""
        logger.info("开始还原备份数据...")
        
        # 还原所有表的数据
        tables_to_restore = [
            "players", "equipment", "skills", "professions", "recipes",
            "crafting_logs", "tools", "profession_skills", "active_formations",
            "items", "sects", "sect_members", "ai_generation_history",
            "tribulations", "profession_exams", "locations", "player_locations",
            "cultivation_methods", "player_cultivation_methods", "method_skills",
            "market_items", "market_transactions",
            "pets", "player_pets", "pet_secret_realms"
        ]
        
        for table in tables_to_restore:
            if await self.table_exists(f"{table}_backup"):
                try:
                    logger.info(f"开始还原表: {table}")
                    # 清空目标表
                    await self.execute(f"DELETE FROM {table}")
                    logger.info(f"已清空表: {table}")

                    # 获取备份表的列信息
                    backup_columns = await self.fetchall(f"PRAGMA table_info({table}_backup)")
                    backup_column_names = [col[1] for col in backup_columns]
                    logger.info(f"备份表 {table}_backup 列: {backup_column_names}")

                    # 获取目标表的列信息
                    target_columns = await self.fetchall(f"PRAGMA table_info({table})")
                    target_column_names = [col[1] for col in target_columns]
                    logger.info(f"目标表 {table} 列: {target_column_names}")

                    # 确定共同的列
                    common_columns = [col for col in backup_column_names if col in target_column_names]

                    if common_columns:
                        # 只还原共同的列
                        columns_str = ", ".join(common_columns)
                        logger.info(f"还原表 {table} 的共同列: {columns_str}")
                        await self.execute(f"INSERT INTO {table} ({columns_str}) SELECT {columns_str} FROM {table}_backup")
                        logger.info(f"✓ 已还原表: {table}")
                    else:
                        logger.warning(f"表 {table} 没有共同列，跳过还原")
                except Exception as e:
                    logger.error(f"还原表 {table} 失败: {e}", exc_info=True)

  
        # 删除备份表
        for table in tables_to_restore:
            await self.execute(f"DROP TABLE IF EXISTS {table}_backup")
        logger.info("备份表清理完成")

    async def _ensure_table_exists(self, table_name: str, schema: str):
        """确保表存在，如果不存在则创建，如果存在则添加缺失的列"""
        try:
            logger.info(f"正在处理表: {table_name}")
            cursor = await self.execute("SELECT name FROM sqlite_master WHERE type='table'")
            existing_tables = [row[0] for row in await cursor.fetchall()]

            if table_name not in existing_tables:
                # 表不存在，直接创建
                create_sql = f"CREATE TABLE {table_name} ({schema})"
                await self.execute(create_sql)
                logger.info(f"创建表: {table_name}")
            else:
                # 表已存在，检查并添加缺失的列
                await self._add_missing_columns(table_name, schema)
                logger.info(f"更新表结构: {table_name}")
            logger.info(f"✓ 表 {table_name} 处理完成")
        except Exception as e:
            logger.error(f"处理表 {table_name} 时出错: {e}", exc_info=True)
            raise

    async def _add_missing_columns(self, table_name: str, schema: str):
        """为现有表添加缺失的列"""
        try:
            logger.info(f"检查表 {table_name} 的列...")
            # 获取现有表的列信息
            cursor = await self.execute(f"PRAGMA table_info({table_name})")
            existing_columns = {row[1] for row in await cursor.fetchall()}
            logger.info(f"表 {table_name} 现有列: {existing_columns}")

            # 解析新schema中的列定义（正确处理括号内的逗号）
            columns = []
            current_parts = []
            paren_count = 0

            for part in schema.split(','):
                current_parts.append(part)
                paren_count += part.count('(') - part.count(')')

                if paren_count == 0:
                    # 括号匹配，这是一个完整的列定义或约束
                    full_column = ','.join(current_parts).strip()
                    if full_column:
                        columns.append(full_column)
                    current_parts = []

            # 处理剩余部分（如果有）
            if current_parts:
                full_column = ','.join(current_parts).strip()
                if full_column:
                    columns.append(full_column)

            for column in columns:
                # 跳过表级约束（ALTER TABLE ADD COLUMN不支持添加约束）
                constraint_keywords = ['UNIQUE(', 'PRIMARY', 'FOREIGN', 'CHECK(', 'CONSTRAINT']
                if any(column.upper().startswith(kw) or column.upper().startswith(kw.replace('(', ' (')) for kw in constraint_keywords):
                    logger.info(f"跳过表级约束: {column[:50]}...")
                    continue

                # 提取列名（第一个词）
                column_name = column.split()[0]

                if column_name not in existing_columns:
                    # 添加缺失的列
                    logger.info(f"为表 {table_name} 添加新列: {column_name}")
                    alter_sql = f"ALTER TABLE {table_name} ADD COLUMN {column}"
                    await self.execute(alter_sql)
                    logger.info(f"✓ 为表 {table_name} 添加列成功: {column_name}")

            logger.info(f"✓ 表 {table_name} 列检查完成")
        except Exception as e:
            logger.error(f"为表 {table_name} 添加列时出错: {e}", exc_info=True)
            raise

    async def _create_or_update_tables(self):
        """创建或更新所有表结构（保持现有数据）"""
        try:
            logger.info("开始创建或更新数据库表结构...")

            # 获取现有表列表
            existing_tables = []
            cursor = await self.execute("SELECT name FROM sqlite_master WHERE type='table'")
            rows = await cursor.fetchall()
            existing_tables = [row[0] for row in rows]
            logger.info(f"现有表: {existing_tables}")

            # 玩家表
            await self._ensure_table_exists("players", """
            user_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            realm TEXT DEFAULT '炼气期',
            realm_level INTEGER DEFAULT 1,
            cultivation INTEGER DEFAULT 0,

            spirit_root_type TEXT,
            spirit_root_quality TEXT,
            spirit_root_value INTEGER DEFAULT 50,
            spirit_root_purity INTEGER DEFAULT 50,

            constitution INTEGER DEFAULT 10,
            spiritual_power INTEGER DEFAULT 10,
            comprehension INTEGER DEFAULT 10,
            luck INTEGER DEFAULT 10,
            root_bone INTEGER DEFAULT 10,

            hp INTEGER DEFAULT 100,
            max_hp INTEGER DEFAULT 100,
            mp INTEGER DEFAULT 100,
            max_mp INTEGER DEFAULT 100,
            attack INTEGER DEFAULT 10,
            defense INTEGER DEFAULT 10,

            spirit_stone INTEGER DEFAULT 1000,
            contribution INTEGER DEFAULT 0,

            sect_id INTEGER,
            sect_position TEXT,

            current_location TEXT DEFAULT '新手村',

            last_cultivation TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            in_retreat INTEGER DEFAULT 0,
            retreat_start TIMESTAMP,
            retreat_duration INTEGER DEFAULT 0
        """)

            # 装备表
            await self._ensure_table_exists("equipment", """
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                sub_type TEXT,
                quality TEXT NOT NULL,
                level INTEGER NOT NULL,
                enhance_level INTEGER DEFAULT 0,
                attack INTEGER DEFAULT 0,
                defense INTEGER DEFAULT 0,
                hp_bonus INTEGER DEFAULT 0,
                mp_bonus INTEGER DEFAULT 0,
                extra_attrs TEXT,
                special_effect TEXT,
                skill_id INTEGER,
                is_equipped INTEGER DEFAULT 0,
                is_bound INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            """)

            # 技能表
            await self._ensure_table_exists("skills", """
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                skill_name TEXT NOT NULL,
                skill_type TEXT,
                element TEXT,
                level INTEGER DEFAULT 1,
                proficiency INTEGER DEFAULT 0,
                base_damage INTEGER DEFAULT 0,
                mp_cost INTEGER DEFAULT 10,
                cooldown INTEGER DEFAULT 0,
                effect_description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            """)

            # 职业信息表
            await self._ensure_table_exists("professions", """
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                profession_type TEXT NOT NULL,
                rank INTEGER DEFAULT 1,
                experience INTEGER DEFAULT 0,
                reputation INTEGER DEFAULT 0,
                reputation_level TEXT DEFAULT '无名小卒',
                success_rate_bonus INTEGER DEFAULT 0,
                quality_bonus INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            """)

            # 配方/图纸/阵法/符箓表
            await self._ensure_table_exists("recipes", """
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                recipe_type TEXT NOT NULL,
                name TEXT NOT NULL,
                rank INTEGER DEFAULT 1,
                description TEXT,
                materials TEXT,
                output_name TEXT,
                output_quality TEXT,
                base_success_rate INTEGER DEFAULT 50,
                special_requirements TEXT,
                source TEXT,
                is_ai_generated BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            """)

            # 炼制记录表
            await self._ensure_table_exists("crafting_logs", """
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                craft_type TEXT NOT NULL,
                recipe_id INTEGER,
                success BOOLEAN DEFAULT 0,
                output_quality TEXT,
                output_item_id INTEGER,
                materials_used TEXT,
                spirit_stone_cost INTEGER DEFAULT 0,
                experience_gained INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            """)

            # 工具表（丹炉、器炉等）
            await self._ensure_table_exists("tools", """
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                tool_type TEXT NOT NULL,
                name TEXT NOT NULL,
                quality TEXT DEFAULT '凡品',
                success_rate_bonus INTEGER DEFAULT 0,
                quality_bonus INTEGER DEFAULT 0,
                special_effects TEXT,
                durability INTEGER DEFAULT 100,
                max_durability INTEGER DEFAULT 100,
                is_active BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            """)

            # 职业技能表
            await self._ensure_table_exists("profession_skills", """
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                profession_type TEXT NOT NULL,
                skill_name TEXT NOT NULL,
                skill_level INTEGER DEFAULT 1,
                effect_type TEXT,
                effect_value INTEGER DEFAULT 0,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            """)

            # 活跃阵法表
            await self._ensure_table_exists("active_formations", """
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                formation_name TEXT NOT NULL,
                location_id INTEGER,
                formation_type TEXT,
                strength INTEGER DEFAULT 1,
                range INTEGER DEFAULT 10,
                effects TEXT,
                energy_cost INTEGER DEFAULT 10,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP
            """)

            # 物品表 (用于存储符箓等消耗品)
            await self._ensure_table_exists("items", """
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                item_type TEXT NOT NULL,
                item_name TEXT NOT NULL,
                quality TEXT,
                quantity INTEGER DEFAULT 1,
                description TEXT,
                effect TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            """)

            # 功法表
            await self._ensure_table_exists("cultivation_methods", """
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                method_type TEXT NOT NULL,
                element_type TEXT NOT NULL,
                cultivation_type TEXT NOT NULL,
                quality TEXT NOT NULL,
                grade INTEGER NOT NULL,
                min_realm TEXT NOT NULL,
                min_realm_level INTEGER NOT NULL,
                min_level INTEGER NOT NULL,
                attack_bonus INTEGER DEFAULT 0,
                defense_bonus INTEGER DEFAULT 0,
                speed_bonus INTEGER DEFAULT 0,
                hp_bonus INTEGER DEFAULT 0,
                mp_bonus INTEGER DEFAULT 0,
                cultivation_speed_bonus REAL DEFAULT 0.0,
                breakthrough_rate_bonus REAL DEFAULT 0.0,
                special_effects TEXT,
                skill_damage INTEGER DEFAULT 0,
                cooldown_reduction REAL DEFAULT 0.0,
                owner_id TEXT,
                is_equipped INTEGER DEFAULT 0,
                equip_slot TEXT,
                proficiency INTEGER DEFAULT 0,
                max_proficiency INTEGER DEFAULT 1000,
                mastery_level INTEGER DEFAULT 0,
                source_type TEXT,
                source_detail TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                equipped_at TIMESTAMP,
                last_practiced_at TIMESTAMP
            """)

            # 宗门表
            await self._ensure_table_exists("sects", """
                id TEXT PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                announcement TEXT,
                sect_type TEXT NOT NULL,
                sect_style TEXT NOT NULL,
                level INTEGER DEFAULT 1,
                experience INTEGER DEFAULT 0,
                max_experience INTEGER DEFAULT 1000,
                spirit_stone INTEGER DEFAULT 0,
                contribution INTEGER DEFAULT 0,
                reputation INTEGER DEFAULT 0,
                power INTEGER DEFAULT 0,
                leader_id TEXT NOT NULL,
                member_count INTEGER DEFAULT 0,
                max_members INTEGER DEFAULT 20,
                buildings TEXT,
                sect_skills TEXT,
                is_recruiting INTEGER DEFAULT 1,
                join_requirement TEXT,
                in_war INTEGER DEFAULT 0,
                war_target_id TEXT,
                war_score INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            """)

            # 宗门成员表
            await self._ensure_table_exists("sect_members", """
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT UNIQUE NOT NULL,
                sect_id TEXT NOT NULL,
                position TEXT NOT NULL,
                position_level INTEGER NOT NULL,
                contribution INTEGER DEFAULT 0,
                total_contribution INTEGER DEFAULT 0,
                activity INTEGER DEFAULT 0,
                last_active_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            """)

            # AI生成历史表
            await self._ensure_table_exists("ai_generation_history", """
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                content_type TEXT NOT NULL,
                content_id TEXT NOT NULL,
                generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            """)

            # 天劫表
            await self._ensure_table_exists("tribulations", """
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                tribulation_type TEXT NOT NULL,
                realm TEXT NOT NULL,
                realm_level INTEGER NOT NULL,
                tribulation_level INTEGER NOT NULL,
                difficulty TEXT NOT NULL,
                total_waves INTEGER NOT NULL,
                current_wave INTEGER DEFAULT 0,
                damage_per_wave INTEGER NOT NULL,
                damage_reduction REAL DEFAULT 0.0,
                status TEXT NOT NULL,
                success INTEGER DEFAULT 0,
                initial_hp INTEGER DEFAULT 0,
                current_hp INTEGER DEFAULT 0,
                total_damage_taken INTEGER DEFAULT 0,
                rewards TEXT,
                penalties TEXT,
                wave_logs TEXT,
                started_at TEXT,
                completed_at TEXT,
                created_at TEXT NOT NULL
            """)

            # 职业考核表
            await self._ensure_table_exists("profession_exams", """
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                profession_type TEXT NOT NULL,
                target_rank INTEGER NOT NULL,
                exam_title TEXT NOT NULL,
                tasks TEXT,
                results TEXT,
                status TEXT DEFAULT 'in_progress',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            """)

            # 地点表
            await self._ensure_table_exists("locations", """
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT NOT NULL,
                region_type TEXT NOT NULL,
                danger_level INTEGER DEFAULT 1,
                spirit_energy_density INTEGER DEFAULT 50,
                min_realm TEXT DEFAULT '炼气期',
                coordinates_x INTEGER DEFAULT 0,
                coordinates_y INTEGER DEFAULT 0,
                resources TEXT,
                connected_locations TEXT,
                is_safe_zone INTEGER DEFAULT 0,
                discovered_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            """)

            # 玩家位置表
            await self._ensure_table_exists("player_locations", """
                user_id TEXT PRIMARY KEY,
                current_location_id INTEGER NOT NULL,
                last_move_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_moves INTEGER DEFAULT 0,
                total_exploration_score INTEGER DEFAULT 0
            """)

            # 玩家功法表
            await self._ensure_table_exists("player_cultivation_methods", """
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                method_id TEXT NOT NULL,
                is_main INTEGER DEFAULT 0,
                proficiency INTEGER DEFAULT 0,
                proficiency_stage TEXT DEFAULT '初窥门径',
                compatibility INTEGER DEFAULT 50,
                learned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_practice TIMESTAMP
            """)

            # 功法技能关联表
            await self._ensure_table_exists("method_skills", """
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                method_id TEXT NOT NULL,
                skill_name TEXT NOT NULL,
                skill_type TEXT,
                unlock_proficiency INTEGER DEFAULT 0,
                element TEXT,
                mp_cost INTEGER DEFAULT 10,
                cooldown INTEGER DEFAULT 0,
                base_damage INTEGER DEFAULT 0,
                effect_description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            """)

            # 坊市物品表
            await self._ensure_table_exists("market_items", """
                id TEXT PRIMARY KEY,
                seller_id TEXT NOT NULL,
                item_type TEXT NOT NULL,
                item_id TEXT NOT NULL,
                item_name TEXT NOT NULL,
                quality TEXT,
                description TEXT,
                price INTEGER NOT NULL,
                quantity INTEGER DEFAULT 1,
                attributes TEXT,
                status TEXT DEFAULT 'active',
                listed_at TEXT NOT NULL,
                created_at TEXT,
                sold_at TEXT
            """)

            # 坊市交易记录表
            await self._ensure_table_exists("market_transactions", """
                id TEXT PRIMARY KEY,
                listing_id TEXT NOT NULL,
                seller_id TEXT NOT NULL,
                buyer_id TEXT NOT NULL,
                item_type TEXT NOT NULL,
                item_id TEXT NOT NULL,
                price INTEGER NOT NULL,
                quantity INTEGER NOT NULL,
                tax INTEGER DEFAULT 0,
                transaction_time TEXT NOT NULL
            """)

            # ===== 灵宠系统表 =====
            # 灵宠模板表
            logger.info("开始创建/更新表: pets")
            await self._ensure_table_exists("pets", """
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                pet_type TEXT NOT NULL,
                rarity TEXT NOT NULL,
                description TEXT,
                base_attributes TEXT NOT NULL,
                growth_rate REAL DEFAULT 1.0,
                max_level INTEGER DEFAULT 50,
                element TEXT,
                evolution_to INTEGER,
                capture_difficulty INTEGER DEFAULT 50,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            """)

            # 玩家灵宠表
            await self._ensure_table_exists("player_pets", """
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                pet_id INTEGER NOT NULL,
                pet_name TEXT NOT NULL,
                level INTEGER DEFAULT 1,
                experience INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 0,
                intimacy INTEGER DEFAULT 0,
                battle_count INTEGER DEFAULT 0,
                acquired_from TEXT NOT NULL,
                acquired_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            """)

            # 灵宠秘境记录表
            await self._ensure_table_exists("pet_secret_realms", """
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT UNIQUE NOT NULL,
                realm_level INTEGER DEFAULT 1,
                exploration_count INTEGER DEFAULT 0,
                last_exploration_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            """)

            # 探索故事历史表
            await self._ensure_table_exists("exploration_stories", """
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                location_id INTEGER NOT NULL,
                story_type TEXT NOT NULL,
                story_title TEXT NOT NULL,
                story_content TEXT NOT NULL,
                choices TEXT,
                selected_choice TEXT,
                outcome TEXT,
                rewards TEXT,
                consequences TEXT,
                is_completed INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            """)

            # 玩家故事状态表（用于跨多次探索的连续剧情）
            await self._ensure_table_exists("player_story_states", """
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                story_arc_id TEXT NOT NULL,
                current_chapter INTEGER DEFAULT 1,
                total_chapters INTEGER DEFAULT 1,
                state_data TEXT,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, story_arc_id)
            """)

            # 探索后果记录表（记录玩家选择的长期影响）
            await self._ensure_table_exists("exploration_consequences", """
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                story_id TEXT NOT NULL,
                consequence_type TEXT NOT NULL,
                consequence_value TEXT NOT NULL,
                expires_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            """)

            logger.info("✓ 所有表结构创建/更新完成")
        except Exception as e:
            logger.error(f"创建或更新表结构时出错: {e}", exc_info=True)
            raise

    async def _create_indexes(self):
        """创建索引以优化查询性能"""
        try:
            logger.info("开始创建索引...")
            indexes = [
            "CREATE INDEX IF NOT EXISTS idx_players_realm ON players(realm)",
            "CREATE INDEX IF NOT EXISTS idx_equipment_user ON equipment(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_equipment_equipped ON equipment(user_id, is_equipped)",
            "CREATE INDEX IF NOT EXISTS idx_skills_user ON skills(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_professions_user ON professions(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_recipes_type ON recipes(recipe_type)",
            "CREATE INDEX IF NOT EXISTS idx_items_user ON items(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_items_type ON items(user_id, item_type)",
            "CREATE INDEX IF NOT EXISTS idx_cultivation_methods_user ON cultivation_methods(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_cultivation_methods_equipped ON cultivation_methods(user_id, is_equipped)",
            "CREATE INDEX IF NOT EXISTS idx_sect_members_sect ON sect_members(sect_id)",
            "CREATE INDEX IF NOT EXISTS idx_sect_members_user ON sect_members(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_tribulations_user ON tribulations(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_tribulations_status ON tribulations(user_id, status)",
            "CREATE INDEX IF NOT EXISTS idx_active_formations_user ON active_formations(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_active_formations_location ON active_formations(location_id, is_active)",
            "CREATE INDEX IF NOT EXISTS idx_player_pets_user ON player_pets(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_player_pets_active ON player_pets(user_id, is_active)",
            "CREATE INDEX IF NOT EXISTS idx_pet_secret_realms_user ON pet_secret_realms(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_locations_region ON locations(region_type)",
            "CREATE INDEX IF NOT EXISTS idx_locations_danger ON locations(danger_level)",
            "CREATE INDEX IF NOT EXISTS idx_player_locations_user ON player_locations(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_player_locations_location ON player_locations(current_location_id)",
            "CREATE INDEX IF NOT EXISTS idx_player_cultivation_methods_user ON player_cultivation_methods(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_player_cultivation_methods_method ON player_cultivation_methods(method_id)",
            "CREATE INDEX IF NOT EXISTS idx_player_cultivation_methods_main ON player_cultivation_methods(user_id, is_main)",
            "CREATE INDEX IF NOT EXISTS idx_method_skills_method ON method_skills(method_id)",
            "CREATE INDEX IF NOT EXISTS idx_market_items_type ON market_items(item_type, status)",
            "CREATE INDEX IF NOT EXISTS idx_market_items_seller ON market_items(seller_id)",
            "CREATE INDEX IF NOT EXISTS idx_market_transactions_buyer ON market_transactions(buyer_id)",
            "CREATE INDEX IF NOT EXISTS idx_market_transactions_seller ON market_transactions(seller_id)",
            "CREATE INDEX IF NOT EXISTS idx_exploration_stories_user ON exploration_stories(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_exploration_stories_location ON exploration_stories(location_id)",
            "CREATE INDEX IF NOT EXISTS idx_exploration_stories_completed ON exploration_stories(user_id, is_completed)",
            "CREATE INDEX IF NOT EXISTS idx_player_story_states_user ON player_story_states(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_exploration_consequences_user ON exploration_consequences(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_exploration_consequences_story ON exploration_consequences(story_id)",
        ]

            for index_sql in indexes:
                await self.execute(index_sql)

            logger.info("索引创建完成")
        except Exception as e:
            logger.error(f"创建索引时出错: {e}", exc_info=True)
            raise


    async def _seed_initial_locations(self):
        """初始化基础地点数据"""
        try:
            # 检查是否已经有地点数据
            cursor = await self.execute("SELECT COUNT(*) as count FROM locations")
            row = await cursor.fetchone()

            if row and row['count'] > 0:
                # 已有地点数据，跳过初始化
                return

            logger.info("开始初始化基础地点...")

            # 初始地点列表
            initial_locations = [
                {
                    'name': '新手村',
                    'description': '一个宁静祥和的小村落，灵气稀薄但十分安全，是众多修仙者踏上修仙之路的起点。村中有简陋的修炼场和基础的药材商铺。',
                    'region_type': 'city',
                    'danger_level': 1,
                    'spirit_energy_density': 20,
                    'min_realm': '炼气期',
                    'coordinates_x': 0,
                    'coordinates_y': 0,
                    'is_safe_zone': 1,
                    'connected_locations': '[2,3]'
                },
                {
                    'name': '青云山',
                    'description': '一座云雾缭绕的灵山，山间灵气充沛，适合低阶修士修炼。山中偶有低阶妖兽出没，需要小心应对。',
                    'region_type': 'mountain',
                    'danger_level': 3,
                    'spirit_energy_density': 45,
                    'min_realm': '炼气期',
                    'coordinates_x': 10,
                    'coordinates_y': 20,
                    'is_safe_zone': 0,
                    'connected_locations': '[1,4,5]'
                },
                {
                    'name': '灵泉谷',
                    'description': '山谷深处有一眼灵泉，常年喷涌着富含灵气的泉水。谷中药草丰茂，是采集灵药的好去处。',
                    'region_type': 'forest',
                    'danger_level': 2,
                    'spirit_energy_density': 40,
                    'min_realm': '炼气期',
                    'coordinates_x': -15,
                    'coordinates_y': 10,
                    'is_safe_zone': 0,
                    'connected_locations': '[1,6]'
                },
                {
                    'name': '天元城',
                    'description': '修仙界繁华的交易中心，城中有各种店铺、拍卖行和任务大厅。城内禁止私斗，是修士们的安全港湾。',
                    'region_type': 'city',
                    'danger_level': 1,
                    'spirit_energy_density': 35,
                    'min_realm': '筑基期',
                    'coordinates_x': 50,
                    'coordinates_y': 0,
                    'is_safe_zone': 1,
                    'connected_locations': '[2,5,7]'
                },
                {
                    'name': '紫雷峰',
                    'description': '常年雷霆轰鸣的险峰，峰顶灵气浓郁但危机四伏。适合筑基期修士突破境界，但需警惕雷劫。',
                    'region_type': 'mountain',
                    'danger_level': 5,
                    'spirit_energy_density': 60,
                    'min_realm': '筑基期',
                    'coordinates_x': 30,
                    'coordinates_y': 40,
                    'is_safe_zone': 0,
                    'connected_locations': '[2,4,8]'
                },
                {
                    'name': '幽暗森林',
                    'description': '古老而神秘的原始森林，林中妖兽众多，灵药珍稀。深处传说有上古修士的洞府遗迹。',
                    'region_type': 'forest',
                    'danger_level': 4,
                    'spirit_energy_density': 50,
                    'min_realm': '筑基期',
                    'coordinates_x': -30,
                    'coordinates_y': 25,
                    'is_safe_zone': 0,
                    'connected_locations': '[3,9]'
                },
                {
                    'name': '碧波湖',
                    'description': '广阔无垠的灵湖，湖水蕴含水系灵气，湖底有水晶矿脉。水系修士在此修炼事半功倍。',
                    'region_type': 'ocean',
                    'danger_level': 3,
                    'spirit_energy_density': 55,
                    'min_realm': '筑基期',
                    'coordinates_x': 40,
                    'coordinates_y': -20,
                    'is_safe_zone': 0,
                    'connected_locations': '[4]'
                },
                {
                    'name': '烈焰山',
                    'description': '终年喷发岩浆的活火山，火系灵气极为浓郁。火系修士的修炼圣地，但常人难以靠近。',
                    'region_type': 'mountain',
                    'danger_level': 6,
                    'spirit_energy_density': 70,
                    'min_realm': '金丹期',
                    'coordinates_x': 60,
                    'coordinates_y': 60,
                    'is_safe_zone': 0,
                    'connected_locations': '[5,10]'
                },
                {
                    'name': '迷雾沼泽',
                    'description': '终年笼罩在毒雾中的危险沼泽，瘴气弥漫，毒虫横行。但沼泽深处生长着珍贵的炼丹灵药。',
                    'region_type': 'forest',
                    'danger_level': 7,
                    'spirit_energy_density': 45,
                    'min_realm': '金丹期',
                    'coordinates_x': -50,
                    'coordinates_y': 50,
                    'is_safe_zone': 0,
                    'connected_locations': '[6]'
                },
                {
                    'name': '虚空裂隙',
                    'description': '空间法则紊乱的神秘区域，时有空间风暴肆虐。传说中通往其他世界的通道，只有元婴期以上修士才敢涉足。',
                    'region_type': 'void',
                    'danger_level': 9,
                    'spirit_energy_density': 85,
                    'min_realm': '元婴期',
                    'coordinates_x': 100,
                    'coordinates_y': 100,
                    'is_safe_zone': 0,
                    'connected_locations': '[8]'
                }
            ]

            # 插入初始地点
            for loc in initial_locations:
                await self.execute("""
                    INSERT INTO locations (
                        name, description, region_type, danger_level,
                        spirit_energy_density, min_realm, coordinates_x, coordinates_y,
                        is_safe_zone, connected_locations
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    loc['name'], loc['description'], loc['region_type'],
                    loc['danger_level'], loc['spirit_energy_density'],
                    loc['min_realm'], loc['coordinates_x'], loc['coordinates_y'],
                    loc['is_safe_zone'], loc['connected_locations']
                ))

            logger.info(f"成功初始化 {len(initial_locations)} 个基础地点")

        except Exception as e:
            logger.error(f"初始化基础地点失败: {e}", exc_info=True)
            pass

    async def _fix_player_attributes(self):
        """修复现有玩家的属性异常问题"""
        try:
            # 检查是否有玩家数据
            cursor = await self.execute("SELECT COUNT(*) as count FROM players")
            row = await cursor.fetchone()

            if not row or row['count'] == 0:
                logger.info("没有玩家数据，跳过属性修复")
                return

            logger.info(f"开始修复 {row['count']} 个玩家的属性...")

            # 获取所有玩家
            players_data = await self.fetchall("SELECT * FROM players")
            fixed_count = 0

            for player_data in players_data:
                try:
                    # 转换为Player对象
                    from ..models.player_model import Player
                    player = Player.from_dict(dict(player_data))

                    # 计算正确属性
                    correct_attrs = self._calculate_correct_attributes(player)

                    # 检查是否需要修复
                    needs_fix = (
                        player.max_hp != correct_attrs['max_hp'] or
                        player.max_mp != correct_attrs['max_mp'] or
                        player.attack != correct_attrs['attack'] or
                        player.defense != correct_attrs['defense']
                    )

                    if needs_fix:
                        # 更新玩家属性
                        await self.execute("""
                            UPDATE players
                            SET max_hp = ?, hp = ?, max_mp = ?, mp = ?,
                                attack = ?, defense = ?, updated_at = CURRENT_TIMESTAMP
                            WHERE user_id = ?
                        """, (
                            correct_attrs['max_hp'],
                            correct_attrs['hp'],
                            correct_attrs['max_mp'],
                            correct_attrs['mp'],
                            correct_attrs['attack'],
                            correct_attrs['defense'],
                            player.user_id
                        ))
                        fixed_count += 1

                        logger.debug(f"修复玩家 {player.name} 的属性: "
                                   f"HP {player.max_hp}->{correct_attrs['max_hp']}, "
                                   f"MP {player.max_mp}->{correct_attrs['max_mp']}, "
                                   f"攻击 {player.attack}->{correct_attrs['attack']}, "
                                   f"防御 {player.defense}->{correct_attrs['defense']}")

                except Exception as e:
                    logger.error(f"修复玩家 {player_data.get('name', 'Unknown')} 属性失败: {e}")
                    continue

            logger.info(f"玩家属性修复完成，共修复 {fixed_count} 个玩家")

        except Exception as e:
            logger.error(f"玩家属性修复过程出错: {e}", exc_info=True)

    def _calculate_correct_attributes(self, player) -> dict:
        """
        计算玩家的正确属性值

        Args:
            player: 玩家对象

        Returns:
            正确的属性值字典
        """
        # 1. 从初始属性开始（玩家创建时的属性）
        initial_attrs = {
            'constitution': player.constitution,
            'spiritual_power': player.spiritual_power,
            'comprehension': player.comprehension,
            'luck': player.luck,
            'root_bone': player.root_bone
        }

        # 2. 计算初始战斗属性（炼气期初期的基础���性）
        from ..utils.constants import INITIAL_COMBAT_STATS

        base_hp = INITIAL_COMBAT_STATS['max_hp']
        base_mp = INITIAL_COMBAT_STATS['max_mp']
        base_attack = INITIAL_COMBAT_STATS['attack']
        base_defense = INITIAL_COMBAT_STATS['defense']

        # 体质影响生命值
        hp_bonus_from_constitution = initial_attrs['constitution'] * 50
        base_hp += hp_bonus_from_constitution

        # 灵力影响法力值和攻击力
        mp_bonus_from_spiritual = initial_attrs['spiritual_power'] * 30
        attack_bonus_from_spiritual = initial_attrs['spiritual_power'] * 2
        base_mp += mp_bonus_from_spiritual
        base_attack += attack_bonus_from_spiritual

        # 根骨影响防御力
        defense_bonus_from_root = initial_attrs['root_bone'] * 1
        base_defense += defense_bonus_from_root

        # 3. 应用灵根战斗加成
        if player.spirit_root_type:
            from .spirit_root import SpiritRootFactory
            spirit_root = {
                'type': player.spirit_root_type,
                'quality': player.spirit_root_quality,
                'value': player.spirit_root_value,
                'purity': player.spirit_root_purity
            }
            bonuses = SpiritRootFactory.calculate_bonuses(spirit_root)
            combat_bonus = bonuses.get('combat_bonus', {})

            if 'attack' in combat_bonus:
                base_attack = int(base_attack * (1 + combat_bonus['attack']))
            if 'defense' in combat_bonus:
                base_defense = int(base_defense * (1 + combat_bonus['defense']))
            if 'max_hp' in combat_bonus:
                bonus_hp = int(base_hp * combat_bonus['max_hp'])
                base_hp += bonus_hp
            if 'max_mp' in combat_bonus:
                bonus_mp = int(base_mp * combat_bonus['max_mp'])
                base_mp += bonus_mp

        # 4. 计算所有境界提升带来的属性加成
        from ..utils.constants import REALMS, REALM_ORDER
        current_realm_index = REALMS[player.realm]['index']

        total_hp_bonus = 0
        total_mp_bonus = 0
        total_attack_bonus = 0
        total_defense_bonus = 0

        # 遍历所有已经突破过的境界
        for realm_name in REALM_ORDER:
            realm_config = REALMS[realm_name]
            realm_index = realm_config['index']

            # 如果是当前境界之前的境界，计算完整加成
            if realm_index < current_realm_index:
                # 大境界突破：获得完整的境界属性加成 * 4（因为有4个小境界）
                attribute_bonus = realm_config.get('attribute_bonus', {})
                total_hp_bonus += attribute_bonus.get('max_hp', 0) * 4
                total_mp_bonus += attribute_bonus.get('max_mp', 0) * 4
                total_attack_bonus += attribute_bonus.get('attack', 0) * 4
                total_defense_bonus += attribute_bonus.get('defense', 0) * 4

            # 如果是当前境界，根据小等级计算
            elif realm_index == current_realm_index:
                attribute_bonus = realm_config.get('attribute_bonus', {})
                # 小境界提升：每级25%的境界属性加成
                level_ratio = 0.25
                levels_passed = player.realm_level  # 当前小境界 1-4

                total_hp_bonus += int(attribute_bonus.get('max_hp', 0) * level_ratio * levels_passed)
                total_mp_bonus += int(attribute_bonus.get('max_mp', 0) * level_ratio * levels_passed)
                total_attack_bonus += int(attribute_bonus.get('attack', 0) * level_ratio * levels_passed)
                total_defense_bonus += int(attribute_bonus.get('defense', 0) * level_ratio * levels_passed)

        # 5. 计算最��属性
        final_max_hp = base_hp + total_hp_bonus
        final_max_mp = base_mp + total_mp_bonus
        final_attack = base_attack + total_attack_bonus
        final_defense = base_defense + total_defense_bonus

        return {
            'max_hp': final_max_hp,
            'hp': final_max_hp,  # 满血
            'max_mp': final_max_mp,
            'mp': final_max_mp,  # 满蓝
            'attack': final_attack,
            'defense': final_defense
        }

    async def execute(
        self,
        sql: str,
        params: Optional[Tuple[Any, ...]] = None
    ) -> aiosqlite.Cursor:
        """
        执行SQL语句

        Args:
            sql: SQL语句
            params: 参数元组

        Returns:
            Cursor对象
        """
        if self.db is None:
            raise RuntimeError("数据库未初始化,请先调用init_db()")

        try:
            if params:
                cursor = await self.db.execute(sql, params)
            else:
                cursor = await self.db.execute(sql)
            await self.db.commit()
            return cursor
        except Exception as e:
            logger.error(f"SQL执行失败: {sql[:100]}..., 错误: {e}", exc_info=True)
            raise

    async def fetchone(
        self,
        sql: str,
        params: Optional[Tuple[Any, ...]] = None
    ) -> Optional[aiosqlite.Row]:
        """
        查询单行数据

        Args:
            sql: SQL查询语句
            params: 参数元组

        Returns:
            单行数据或None
        """
        if self.db is None:
            raise RuntimeError("数据库未初始化,请先调用init_db()")

        try:
            if params:
                cursor = await self.db.execute(sql, params)
            else:
                cursor = await self.db.execute(sql)
            row = await cursor.fetchone()
            await cursor.close()
            return row
        except Exception as e:
            logger.error(f"查询失败: {sql[:100]}..., 错误: {e}", exc_info=True)
            raise

    async def fetchall(
        self,
        sql: str,
        params: Optional[Tuple[Any, ...]] = None
    ) -> List[aiosqlite.Row]:
        """
        查询多行数据

        Args:
            sql: SQL查询语句
            params: 参数元组

        Returns:
            数据行列表
        """
        if self.db is None:
            raise RuntimeError("数据库未初始化,请先调用init_db()")

        try:
            if params:
                cursor = await self.db.execute(sql, params)
            else:
                cursor = await self.db.execute(sql)
            rows = await cursor.fetchall()
            await cursor.close()
            return rows
        except Exception as e:
            logger.error(f"查询失败: {sql[:100]}..., 错误: {e}", exc_info=True)
            raise

    @asynccontextmanager
    async def transaction(self):
        """
        事务上下文管理器

        使用方式:
            async with db.transaction():
                await db.execute(...)
                await db.execute(...)
        """
        if self.db is None:
            raise RuntimeError("数据库未初始化,请先调用init_db()")

        try:
            await self.db.execute("BEGIN")
            yield self.db
            await self.db.commit()
            logger.debug("事务提交成功")
        except Exception as e:
            await self.db.rollback()
            logger.error(f"事务回滚: {e}", exc_info=True)
            raise

    async def close(self):
        """关闭数据库连接"""
        if self.db:
            await self.db.close()
            self.db = None
            logger.info("数据库连接已关闭")

    async def table_exists(self, table_name: str) -> bool:
        """
        检查表是否存在

        Args:
            table_name: 表名

        Returns:
            是否存在
        """
        row = await self.fetchone(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,)
        )
        return row is not None

    async def get_table_info(self, table_name: str) -> List[Dict[str, Any]]:
        """
        获取表结构信息

        Args:
            table_name: 表名

        Returns:
            列信息列表
        """
        rows = await self.fetchall(f"PRAGMA table_info({table_name})")
        return [dict(row) for row in rows]

    async def vacuum(self):
        """优化数据库,回收空间"""
        try:
            await self.execute("VACUUM")
            logger.info("数据库优化完成")
        except Exception as e:
            logger.error(f"数据库优化失败: {e}", exc_info=True)

    def __repr__(self) -> str:
        """字符串表示"""
        status = "已连接" if self.db else "未连接"
        return f"DatabaseManager(path={self.db_path}, status={status})"
