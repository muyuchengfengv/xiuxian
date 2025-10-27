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
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

    async def _create_indexes(self):
        """创建索引以优化查询性能"""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_players_realm ON players(realm)",
            "CREATE INDEX IF NOT EXISTS idx_equipment_user ON equipment(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_equipment_equipped ON equipment(user_id, is_equipped)",
            "CREATE INDEX IF NOT EXISTS idx_skills_user ON skills(user_id)",
        ]

        for index_sql in indexes:
            await self.execute(index_sql)

        logger.info("索引创建完成")

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
