"""
Database Base DAO
数据库访问基础类
"""
import asyncpg
from typing import Any, List, Optional, Union
from contextlib import asynccontextmanager

from saturn_mousehunter_shared.log.logger import get_logger

log = get_logger(__name__)


class AsyncDAO:
    """异步数据库访问对象"""

    def __init__(self, database_url: str):
        self.database_url = database_url
        self._pool: Optional[asyncpg.Pool] = None

    async def initialize(self):
        """初始化连接池"""
        if self._pool is None:
            self._pool = await asyncpg.create_pool(
                self.database_url,
                min_size=5,
                max_size=20,
                command_timeout=60
            )
            log.info("Database connection pool initialized")

    async def close(self):
        """关闭连接池"""
        if self._pool:
            await self._pool.close()
            self._pool = None
            log.info("Database connection pool closed")

    @asynccontextmanager
    async def get_connection(self):
        """获取数据库连接"""
        if self._pool is None:
            await self.initialize()

        async with self._pool.acquire() as connection:
            yield connection

    async def fetch_one(self, query: str, *args) -> Optional[asyncpg.Record]:
        """获取单条记录"""
        async with self.get_connection() as conn:
            return await conn.fetchrow(query, *args)

    async def fetch_all(self, query: str, *args) -> List[asyncpg.Record]:
        """获取多条记录"""
        async with self.get_connection() as conn:
            return await conn.fetch(query, *args)

    async def execute(self, query: str, *args) -> int:
        """执行SQL语句，返回受影响的行数"""
        async with self.get_connection() as conn:
            result = await conn.execute(query, *args)
            # 从结果中提取行数
            if result.startswith('INSERT') or result.startswith('UPDATE') or result.startswith('DELETE'):
                return int(result.split()[-1])
            return 0

    async def execute_many(self, query: str, args_list: List[tuple]) -> int:
        """批量执行SQL语句"""
        async with self.get_connection() as conn:
            await conn.executemany(query, args_list)
            return len(args_list)

    @asynccontextmanager
    async def transaction(self):
        """事务上下文管理器"""
        async with self.get_connection() as conn:
            async with conn.transaction():
                yield conn

    async def call_procedure(self, procedure_name: str, *args) -> Any:
        """调用存储过程"""
        async with self.get_connection() as conn:
            return await conn.fetchval(f"SELECT {procedure_name}($1)", *args)

    async def table_exists(self, table_name: str) -> bool:
        """检查表是否存在"""
        query = """
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = $1
        )
        """
        async with self.get_connection() as conn:
            return await conn.fetchval(query, table_name)