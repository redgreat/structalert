import pymysql
from pymysql.cursors import DictCursor
from loguru import logger
import threading
import time
from queue import Queue

class DatabaseManager:
    """数据库管理及连接包装器，支持连接池和重试机制"""
    _instances = {}
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls, name_db: str, config: dict):
        """单例获取不同配置(source/his/cfg)的连接包装"""
        with cls._lock:
            if name_db not in cls._instances:
                cls._instances[name_db] = cls(config)
        return cls._instances[name_db]

    def __init__(self, config: dict):
        self.config = config
        self.host = config.get("host", "127.0.0.1")
        self.port = config.get("port", 3306)
        self.user = config.get("user", "user")
        self.password = config.get("password", "password")
        self.database = config.get("database", "db")
        self.charset = config.get("charset", "utf8mb4")
        self.connect_timeout = config.get("connect_timeout", 10)
        self.read_timeout = config.get("read_timeout", 30)
        self.write_timeout = config.get("write_timeout", 30)

        # 连接池配置
        self.max_connections = config.get("max_connections", 10)
        self.connection_pool = Queue(maxsize=self.max_connections)
        self.pool_lock = threading.Lock()

        # 初始化连接池
        self._init_pool()

    def _init_pool(self):
        """初始化连接池"""
        for _ in range(min(3, self.max_connections)):  # 预先创建3个连接
            try:
                conn = self._create_connection()
                self.connection_pool.put(conn)
            except Exception as e:
                logger.warning(f"初始化连接池失败: {e}")

    def _create_connection(self):
        """创建新的数据库连接"""
        return pymysql.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.database,
            charset=self.charset,
            cursorclass=DictCursor,
            autocommit=True,
            connect_timeout=self.connect_timeout,
            read_timeout=self.read_timeout,
            write_timeout=self.write_timeout
        )

    def _get_connection(self):
        """从连接池获取连接"""
        try:
            # 尝试从池中获取连接，超时5秒
            conn = self.connection_pool.get(timeout=5)
            # 测试连接是否有效
            try:
                conn.ping(reconnect=True)
                return conn
            except Exception:
                # 连接失效，创建新连接
                return self._create_connection()
        except Exception:
            # 连接池为空或超时，创建新连接
            return self._create_connection()

    def _return_connection(self, conn):
        """归还连接到连接池"""
        try:
            if conn and conn.open:
                # 测试连接是否仍然有效
                try:
                    conn.ping(reconnect=False)
                    # 尝试归还到池中
                    self.connection_pool.put_nowait(conn)
                except Exception:
                    # 连接失效，直接关闭
                    conn.close()
            elif conn:
                conn.close()
        except Exception:
            # 连接池已满，直接关闭连接
            if conn:
                conn.close()

    def _execute_with_retry(self, func, max_retries=3, retry_delay=1):
        """带重试机制的执行函数"""
        last_error = None
        for attempt in range(max_retries):
            try:
                return func()
            except (pymysql.OperationalError, pymysql.InterfaceError) as e:
                last_error = e
                if attempt < max_retries - 1:
                    logger.warning(f"数据库操作失败，第{attempt + 1}次重试: {e}")
                    time.sleep(retry_delay * (attempt + 1))  # 递增延迟
                else:
                    logger.error(f"数据库操作失败，已达最大重试次数: {e}")
                    raise
            except Exception as e:
                logger.error(f"数据库操作失败: {e}")
                raise

    def fetch_all(self, sql: str, params: tuple = None) -> list:
        def _fetch():
            conn = None
            try:
                conn = self._get_connection()
                with conn.cursor() as cursor:
                    cursor.execute(sql, params)
                    return cursor.fetchall()
            finally:
                if conn:
                    self._return_connection(conn)

        return self._execute_with_retry(_fetch)

    def fetch_one(self, sql: str, params: tuple = None) -> dict:
        def _fetch():
            conn = None
            try:
                conn = self._get_connection()
                with conn.cursor() as cursor:
                    cursor.execute(sql, params)
                    return cursor.fetchone()
            finally:
                if conn:
                    self._return_connection(conn)

        return self._execute_with_retry(_fetch)

    def execute(self, sql: str, params: tuple = None) -> int:
        def _exec():
            conn = None
            try:
                conn = self._get_connection()
                with conn.cursor() as cursor:
                    affected = cursor.execute(sql, params)
                    return affected
            finally:
                if conn:
                    self._return_connection(conn)

        return self._execute_with_retry(_exec)

    def execute_many(self, sql: str, params: list) -> int:
        def _exec():
            conn = None
            try:
                conn = self._get_connection()
                with conn.cursor() as cursor:
                    affected = cursor.executemany(sql, params)
                    return affected
            finally:
                if conn:
                    self._return_connection(conn)

        return self._execute_with_retry(_exec)

    def get_primary_keys(self, table_name: str) -> list:
        """获取表的主键列名列表"""
        sql = f"SHOW KEYS FROM `{table_name}` WHERE Key_name = 'PRIMARY'"
        res = self.fetch_all(sql)
        res_sorted = sorted(res, key=lambda x: x['Seq_in_index'])
        return [row['Column_name'] for row in res_sorted]

    def test_connection(self):
        """测试连接是否畅通"""
        try:
            res = self.fetch_one("SELECT 1 as test")
            if res and res.get("test") == 1:
                return True
            return False
        except Exception as e:
            logger.warning(f"Connection test failed for {self.database}: {e}")
            return False
