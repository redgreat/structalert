import pymysql
from pymysql.cursors import SSDictCursor
from loguru import logger
import concurrent.futures
from datetime import datetime, timedelta
from .database import DatabaseManager

class DataSynchronizer:
    def __init__(self, source_db: DatabaseManager, target_db: DatabaseManager):
        self.source = source_db
        self.target = target_db

    def sync_table(self, table_name: str, date_column: str = None, 
                   days_before: int = None, batch_size: int = 5000, max_workers: int = 4,
                   dry_run: bool = False):
        """
        同步表数据
        
        Args:
            table_name: 表名
            date_column: 日期字段名，用于增量同步筛选
            days_before: 同步多少天前的数据（从今天开始计算），None表示全量同步
            batch_size: 批量写入大小
            max_workers: 并发写入线程数
            dry_run: 试运行模式，True表示只模拟不实际执行
        """
        logger.info(f"开始同步表数据: {table_name}")
        if dry_run:
            logger.warning("【试运行模式】不会实际写入数据")
        
        # 判断是增量同步还是全量同步
        is_incremental = date_column and days_before is not None
        if is_incremental:
            logger.info(f"增量同步模式: 按 {date_column} 字段同步 {days_before} 天前的数据")
        else:
            logger.info(f"全量同步模式")

        # 禁用外键检查，防止写入时因外键限制失败
        try:
            self.target.execute("SET FOREIGN_KEY_CHECKS = 0")
        except Exception as e:
            logger.warning(f"禁用外键检查失败: {e}")

        try:
            # 1. 获取主键
            pks = self.source.get_primary_keys(table_name)
            if not pks:
                logger.warning(f"表 {table_name} 没有主键，UPSERT 可能无法完美支持，请确认。")

            # 2. 获取表列名以构建 UPSERT 语句
            columns = self._get_table_columns(table_name)
            if not columns:
                logger.error(f"无法获取表 {table_name} 的字段信息，同步终止。")
                return

            upsert_sql = self._build_upsert_sql(table_name, columns)

            # 3. 流式读取和多线程写入
            self._sync_upsert_data(table_name, columns, upsert_sql, batch_size, max_workers, 
                                   date_column, days_before, dry_run)

            logger.info(f"表 {table_name} 数据同步完成。")
        finally:
            # 恢复外键检查
            try:
                self.target.execute("SET FOREIGN_KEY_CHECKS = 1")
            except Exception as e:
                logger.warning(f"恢复外键检查失败: {e}")

    def _get_table_columns(self, table_name: str) -> list:
        # 获取表结构信息，过滤掉虚拟列
        res = self.source.fetch_all(f"SHOW COLUMNS FROM `{table_name}`")
        columns = []
        for row in res:
            field_name = row['Field']
            extra = row.get('Extra', '').upper()
            # 跳过虚拟列和生成列
            if 'VIRTUAL GENERATED' in extra or 'STORED GENERATED' in extra or 'GENERATED ALWAYS' in extra:
                logger.debug(f"跳过虚拟列 {field_name}，不进行数据迁移")
                continue
            columns.append(field_name)
        return columns

    def _build_upsert_sql(self, table_name: str, columns: list) -> str:
        # 构建 INSERT ... ON DUPLICATE KEY UPDATE 语句
        cols_str = ", ".join([f"`{c}`" for c in columns])
        vals_str = ", ".join(["%s"] * len(columns))
        updates = ", ".join([f"`{c}`=VALUES(`{c}`)" for c in columns])
        
        sql = f"INSERT INTO `{table_name}` ({cols_str}) VALUES ({vals_str}) ON DUPLICATE KEY UPDATE {updates}"
        return sql

    def _sync_upsert_data(self, table_name: str, columns: list, upsert_sql: str, 
                          batch_size: int, max_workers: int, 
                          date_column: str = None, days_before: int = None, dry_run: bool = False):
        conn = None
        futures = []
        total_upserted = 0
        
        try:
            # 构建查询SQL，支持增量同步
            if date_column and days_before is not None:
                # 增量同步：查询指定日期范围的数据
                # 计算日期范围：[今天-days_before-7, 今天-days_before)
                today = datetime.now().date()
                end_date = today - timedelta(days=days_before)
                start_date = end_date - timedelta(days=7)
                
                logger.info(f"增量同步日期范围: {start_date} <= {date_column} < {end_date}")
                
                query_sql = f"""
                    SELECT * FROM `{table_name}` 
                    WHERE `{date_column}` >= %s AND `{date_column}` < %s
                """
                query_params = (start_date, end_date)
            else:
                # 全量同步
                query_sql = f"SELECT * FROM `{table_name}`"
                query_params = None
            
            # 必须用独立连接和流式游标从 Source 拉取数据
            conn = self.source._get_connection()
            with conn.cursor(SSDictCursor) as cursor:
                if query_params:
                    cursor.execute(query_sql, query_params)
                else:
                    cursor.execute(query_sql)
                
                with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                    batch = []
                    for row in cursor:
                        # 转换成 tuple
                        row_tuple = tuple(row[c] for c in columns)
                        batch.append(row_tuple)
                        
                        if len(batch) >= batch_size:
                            if dry_run:
                                # 试运行模式：只记录不执行
                                logger.info(f"【试运行】将批量写入 {len(batch)} 条记录")
                                total_upserted += len(batch)
                            else:
                                futures.append(executor.submit(self._do_batch_upsert, upsert_sql, batch))
                                total_upserted += len(batch)
                            batch = []
                            
                    # 处理最后一批
                    if batch:
                        if dry_run:
                            logger.info(f"【试运行】将批量写入 {len(batch)} 条记录")
                            total_upserted += len(batch)
                        else:
                            futures.append(executor.submit(self._do_batch_upsert, upsert_sql, batch))
                            total_upserted += len(batch)
                        
                    # 等待所有写入完成并检测异常
                    if not dry_run:
                        for future in concurrent.futures.as_completed(futures):
                            try:
                                future.result()
                            except Exception as e:
                                logger.error(f"批量 UPSERT 执行中发生错误: {e}")
                            
        except Exception as e:
            logger.error(f"读取源表数据失败 {table_name}: {e}")
        finally:
            if conn:
                conn.close()
                
        logger.info(f"[{table_name}] 累计读取并分发更新记录: {total_upserted} 条。")

    def _do_batch_upsert(self, sql: str, batch_data: list):
        # 目标端批量写入
        affected = self.target.execute_many(sql, batch_data)
        return affected
