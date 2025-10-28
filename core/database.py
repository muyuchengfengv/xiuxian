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

            # 创建表
            await self._create_tables()

  
            # 创建索引
            await self._create_indexes()

            # 初始化基础地点数据
            await self._seed_initial_locations()

            logger.info("数据库初始化完成")

        except Exception as e:
            logger.error(f"数据库初始化失败: {e}", exc_info=True)
            raise

    async def _create_tables(self):
        """创建所有表"""

        # 玩家表
        await self.execute("""
            CREATE TABLE IF NOT EXISTS players (
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
            )
        """)
        logger.info("创建表: players")

        # 装备表
        await self.execute("""
            CREATE TABLE IF NOT EXISTS equipment (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                sub_type TEXT,
                quality TEXT DEFAULT '凡品',
                level INTEGER DEFAULT 1,
                enhance_level INTEGER DEFAULT 0,

                attack INTEGER DEFAULT 0,
                defense INTEGER DEFAULT 0,
                hp_bonus INTEGER DEFAULT 0,
                mp_bonus INTEGER DEFAULT 0,

                extra_attrs TEXT,
                special_effect TEXT,
                skill_id INTEGER,

                is_equipped BOOLEAN DEFAULT 0,
                is_bound BOOLEAN DEFAULT 0,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES players(user_id)
            )
        """)
        logger.info("创建表: equipment")

        # 技能表
        await self.execute("""
            CREATE TABLE IF NOT EXISTS skills (
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

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES players(user_id)
            )
        """)
        logger.info("创建表: skills")

        # 职业信息表
        await self.execute("""
            CREATE TABLE IF NOT EXISTS professions (
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
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES players(user_id)
            )
        """)
        logger.info("创建表: professions")

        # 配方/图纸/阵法/符箓表
        await self.execute("""
            CREATE TABLE IF NOT EXISTS recipes (
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
            )
        """)
        logger.info("创建表: recipes")

        # 炼制记录表
        await self.execute("""
            CREATE TABLE IF NOT EXISTS crafting_logs (
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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES players(user_id),
                FOREIGN KEY (recipe_id) REFERENCES recipes(id)
            )
        """)
        logger.info("创建表: crafting_logs")

        # 工具表（丹炉、器炉等）
        await self.execute("""
            CREATE TABLE IF NOT EXISTS tools (
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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES players(user_id)
            )
        """)
        logger.info("创建表: tools")

        # 职业技能表
        await self.execute("""
            CREATE TABLE IF NOT EXISTS profession_skills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                profession_type TEXT NOT NULL,
                skill_name TEXT NOT NULL,
                skill_level INTEGER DEFAULT 1,
                effect_type TEXT,
                effect_value INTEGER DEFAULT 0,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES players(user_id)
            )
        """)
        logger.info("创建表: profession_skills")

        # 活跃阵法表
        await self.execute("""
            CREATE TABLE IF NOT EXISTS active_formations (
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
                expires_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES players(user_id)
            )
        """)
        logger.info("创建表: active_formations")

        # 物品表 (用于存储符箓等消耗品)
        await self.execute("""
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                item_type TEXT NOT NULL,
                item_name TEXT NOT NULL,
                quality TEXT,
                quantity INTEGER DEFAULT 1,
                description TEXT,
                effect TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES players(user_id)
            )
        """)
        logger.info("创建表: items")

        # 注意: cultivation_methods 表由 CultivationMethodSystem 自行管理
        # 见 core/cultivation_method.py::_ensure_methods_table()
        # 该系统使用独立的表结构定义以支持更复杂的功法系统功能

        # 宗门表
        await self.execute("""
            CREATE TABLE IF NOT EXISTS sects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                founder_id TEXT NOT NULL,
                level INTEGER DEFAULT 1,
                reputation INTEGER DEFAULT 0,
                resource_pool INTEGER DEFAULT 0,
                max_members INTEGER DEFAULT 50,
                member_count INTEGER DEFAULT 1,
                description TEXT,
                announcement TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (founder_id) REFERENCES players(user_id)
            )
        """)
        logger.info("创建表: sects")

        # 宗门成员表
        await self.execute("""
            CREATE TABLE IF NOT EXISTS sect_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sect_id INTEGER NOT NULL,
                user_id TEXT NOT NULL,
                position TEXT DEFAULT '外门弟子',
                contribution INTEGER DEFAULT 0,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (sect_id) REFERENCES sects(id),
                FOREIGN KEY (user_id) REFERENCES players(user_id),
                UNIQUE(sect_id, user_id)
            )
        """)
        logger.info("创建表: sect_members")

        # AI生成历史表
        await self.execute("""
            CREATE TABLE IF NOT EXISTS ai_generation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                generation_type TEXT NOT NULL,
                prompt TEXT,
                result TEXT,
                metadata TEXT,
                success BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES players(user_id)
            )
        """)
        logger.info("创建表: ai_generation_history")

        # 天劫表
        await self.execute("""
            CREATE TABLE IF NOT EXISTS tribulations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                tribulation_type TEXT NOT NULL,
                from_realm TEXT NOT NULL,
                to_realm TEXT NOT NULL,
                difficulty INTEGER DEFAULT 1,
                current_wave INTEGER DEFAULT 0,
                max_waves INTEGER DEFAULT 9,
                damage_taken INTEGER DEFAULT 0,
                cultivation_bonus REAL DEFAULT 0,
                status TEXT DEFAULT 'active',
                success BOOLEAN,
                rewards TEXT,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES players(user_id)
            )
        """)
        logger.info("创建表: tribulations")

        # 职业考核表
        await self.execute("""
            CREATE TABLE IF NOT EXISTS profession_exams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                profession_type TEXT NOT NULL,
                target_rank INTEGER NOT NULL,
                status TEXT DEFAULT 'in_progress',
                tasks_completed TEXT,
                score INTEGER DEFAULT 0,
                passed BOOLEAN,
                rewards TEXT,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES players(user_id)
            )
        """)
        logger.info("创建表: profession_exams")

        # 地点表
        await self.execute("""
            CREATE TABLE IF NOT EXISTS locations (
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
            )
        """)
        logger.info("创建表: locations")

        # 玩家位置表
        await self.execute("""
            CREATE TABLE IF NOT EXISTS player_locations (
                user_id TEXT PRIMARY KEY,
                current_location_id INTEGER NOT NULL,
                last_move_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_moves INTEGER DEFAULT 0,
                total_exploration_score INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES players(user_id),
                FOREIGN KEY (current_location_id) REFERENCES locations(id)
            )
        """)
        logger.info("创建表: player_locations")

    async def _create_indexes(self):
        """创建索引以优化查询性能"""
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
            "CREATE INDEX IF NOT EXISTS idx_locations_region ON locations(region_type)",
            "CREATE INDEX IF NOT EXISTS idx_locations_danger ON locations(danger_level)",
            "CREATE INDEX IF NOT EXISTS idx_player_locations_user ON player_locations(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_player_locations_location ON player_locations(current_location_id)",
        ]

        for index_sql in indexes:
            await self.execute(index_sql)

        logger.info("索引创建完成")

    async def _migrate_database(self):
        """数据库迁移：为现有表添加新字段"""
        try:
            logger.info("开始检查数据库迁移...")

            # 检查 players 表是否需要添加闭关相关字段
            await self._add_column_if_not_exists(
                "players",
                "in_retreat",
                "INTEGER DEFAULT 0"
            )
            await self._add_column_if_not_exists(
                "players",
                "retreat_start",
                "TIMESTAMP"
            )
            await self._add_column_if_not_exists(
                "players",
                "retreat_duration",
                "INTEGER DEFAULT 0"
            )

            # 检查 sects 表是否需要添加 power 字段
            # power 字段用于存储宗门实力值(所有成员战力总和)
            await self._add_column_if_not_exists(
                "sects",
                "power",
                "INTEGER DEFAULT 0"
            )

            # 检查 cultivation_methods 表是否需要添加 owner_id 字段
            # owner_id 用于标识功法拥有者
            await self._add_column_if_not_exists(
                "cultivation_methods",
                "owner_id",
                "TEXT"
            )

            # 如果 cultivation_methods 表中存在 user_id 列但没有 owner_id，
            # 需要将 user_id 的值复制到 owner_id
            if await self.table_exists("cultivation_methods"):
                table_info = await self.get_table_info("cultivation_methods")
                has_user_id = any(col['name'] == 'user_id' for col in table_info)
                has_owner_id = any(col['name'] == 'owner_id' for col in table_info)

                if has_user_id and has_owner_id:
                    # 将 user_id 的值复制到 owner_id (如果 owner_id 为空)
                    await self.execute(
                        "UPDATE cultivation_methods SET owner_id = user_id WHERE owner_id IS NULL"
                    )
                    logger.info("已将 cultivation_methods 表中的 user_id 复制到 owner_id")

            logger.info("数据库迁移完成")

        except Exception as e:
            logger.error(f"数据库迁移失败: {e}", exc_info=True)
            # 迁移失败不应该中断初始化，只记录错误
            pass

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

    async def _add_column_if_not_exists(self, table_name: str, column_name: str, column_type: str):
        """
        如果列不存在，则添加列

        Args:
            table_name: 表名
            column_name: 列名
            column_type: 列类型和约束
        """
        try:
            # 检查列是否存在
            table_info = await self.get_table_info(table_name)
            column_exists = any(col['name'] == column_name for col in table_info)

            if not column_exists:
                # 添加列
                sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
                await self.execute(sql)
                logger.info(f"添加列: {table_name}.{column_name}")
            else:
                logger.debug(f"列已存在: {table_name}.{column_name}")

        except Exception as e:
            logger.error(f"添加列失败 {table_name}.{column_name}: {e}")
            raise

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
