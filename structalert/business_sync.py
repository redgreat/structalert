from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
import time

from loguru import logger

from .database import DatabaseManager


class BusinessDataSynchronizer:
    """按水位增量同步业务表数据。"""

    def __init__(
        self,
        source_db: DatabaseManager,
        target_db: DatabaseManager,
        cfg_db: DatabaseManager,
        table_name: str = "tb_workbussinessjsoninfo",
        watermark_column: str = "LastUpdateTimeStamp",
        id_column: str = "Id",
        state_table: str = "cfg_business_sync_state",
        delete_log_table: str = "cfg_business_sync_delete_log",
    ):
        self.source = source_db
        self.target = target_db
        self.cfg_db = cfg_db
        self.table_name = table_name
        self.watermark_column = watermark_column
        self.id_column = id_column
        self.state_table = state_table
        self.delete_log_table = delete_log_table

    def sync_incremental(
        self,
        batch_size: int = 2000,
        max_workers: int = 4,
        dry_run: bool = False,
        queue_limit: int = 32,
        sync_days_per_run: int = 1,
        delete_batch_size: int = 2000,
        delete_sleep_ms: int = 0,
        delete_lag_days: int = 30,
        strict_delete_guard_enabled: bool = True,
        min_delete_lag_days: int = 7,
    ):
        logger.info(
            f"开始业务数据增量同步: table={self.table_name}, "
            f"batch_size={batch_size}, max_workers={max_workers}, dry_run={dry_run}"
        )

        columns = self._get_physical_columns()
        if not columns:
            raise RuntimeError(f"无法获取表 {self.table_name} 的真实列信息")

        self._ensure_state_table()
        self._ensure_delete_log_table()
        upsert_sql = self._build_upsert_sql(columns)
        last_ts, last_id, last_delete_ts, last_delete_id = self._load_watermark()
        run_upper_ts = self._calc_run_upper_ts(last_ts, sync_days_per_run)

        logger.info(
            f"当前同步水位: {self.watermark_column}={last_ts}, {self.id_column}={last_id}, "
            f"run_upper_ts={run_upper_ts}, delete_watermark={last_delete_ts}/{last_delete_id}"
        )

        total_read = 0
        submitted = 0
        max_seen_ts = last_ts
        max_seen_id = last_id

        futures = []
        future_ranges = {}

        try:
            self.target.set_session_overrides(
                {
                    "FOREIGN_KEY_CHECKS": 0,
                    "UNIQUE_CHECKS": 0,
                }
            )
        except Exception as exc:
            logger.warning(f"设置目标库会话参数失败: {exc}")

        try:
            with ThreadPoolExecutor(max_workers=max(1, max_workers)) as executor:
                for rows, batch_max_ts, batch_max_id in self._read_incremental_batches(
                    columns, last_ts, last_id, batch_size, run_upper_ts
                ):
                    total_read += len(rows)
                    max_seen_ts, max_seen_id = self._pick_max_watermark(
                        (max_seen_ts, max_seen_id), (batch_max_ts, batch_max_id)
                    )

                    if dry_run:
                        logger.info(
                            f"【试运行】读取批次 {len(rows)} 条，批次最大水位="
                            f"{batch_max_ts}/{batch_max_id}"
                        )
                        continue

                    future = executor.submit(self._write_batch, upsert_sql, rows)
                    futures.append(future)
                    future_ranges[future] = (batch_max_ts, batch_max_id, len(rows))
                    submitted += len(rows)

                    # 限制在途任务数量，避免堆积过多批次占用内存
                    if len(futures) >= max_workers * max(1, queue_limit):
                        self._drain_some_futures(futures, future_ranges, max_workers)

                if not dry_run:
                    self._wait_all_futures(futures, future_ranges)

            if dry_run:
                logger.info(f"【试运行】业务数据读取完成，共读取 {total_read} 条")
                return

            self._save_sync_watermark(max_seen_ts, max_seen_id)
            self._delete_source_data(
                last_delete_ts=last_delete_ts,
                last_delete_id=last_delete_id,
                sync_ts=max_seen_ts,
                sync_id=max_seen_id,
                delete_batch_size=delete_batch_size,
                delete_sleep_ms=delete_sleep_ms,
                delete_lag_days=delete_lag_days,
                strict_delete_guard_enabled=strict_delete_guard_enabled,
                min_delete_lag_days=min_delete_lag_days,
            )
            logger.info(
                f"业务数据同步完成: read={total_read}, written={submitted}, "
                f"new_watermark={max_seen_ts}/{max_seen_id}"
            )
        finally:
            try:
                self.target.set_session_overrides({})
            except Exception as exc:
                logger.warning(f"恢复目标库会话参数失败: {exc}")

    def _get_physical_columns(self) -> list:
        rows = self.source.fetch_all(f"SHOW COLUMNS FROM `{self.table_name}`")
        columns = []
        for row in rows:
            extra = str(row.get("Extra", "")).upper()
            if "VIRTUAL GENERATED" in extra or "STORED GENERATED" in extra or "GENERATED ALWAYS" in extra:
                continue
            columns.append(row["Field"])
        return columns

    def _build_upsert_sql(self, columns: list) -> str:
        column_sql = ", ".join(f"`{col}`" for col in columns)
        value_sql = ", ".join(["%s"] * len(columns))
        update_sql = ", ".join(
            f"`{col}`=VALUES(`{col}`)" for col in columns if col not in {self.id_column}
        )
        return (
            f"INSERT INTO `{self.table_name}` ({column_sql}) "
            f"VALUES ({value_sql}) "
            f"ON DUPLICATE KEY UPDATE {update_sql}"
        )

    def _read_incremental_batches(self, columns: list, start_ts: str, start_id: int, batch_size: int, upper_ts: str):
        select_columns = ", ".join(f"`{col}`" for col in columns)
        sql = f"""
            SELECT {select_columns}
            FROM `{self.table_name}`
            WHERE (
                    (`{self.watermark_column}` > %s)
                 OR (`{self.watermark_column}` = %s AND `{self.id_column}` > %s)
                  )
              AND `{self.watermark_column}` <= %s
            ORDER BY `{self.watermark_column}`, `{self.id_column}`
            LIMIT %s
        """

        current_ts = start_ts
        current_id = start_id

        while True:
            rows = self.source.fetch_all(sql, (current_ts, current_ts, current_id, upper_ts, batch_size))
            if not rows:
                break

            normalized_rows = [
                tuple(row.get(col) for col in columns)
                for row in rows
            ]

            last_row = rows[-1]
            current_ts = self._normalize_ts(last_row[self.watermark_column])
            current_id = int(last_row[self.id_column])
            yield normalized_rows, current_ts, current_id

    def _drain_some_futures(self, futures: list, future_ranges: dict, max_workers: int):
        done_count = max(1, max_workers)
        completed = []
        for future in as_completed(list(futures)):
            future.result()
            ts, row_id, count = future_ranges.pop(future)
            logger.info(f"批次写入完成: count={count}, batch_watermark={ts}/{row_id}")
            completed.append(future)
            if len(completed) >= done_count:
                break

        for future in completed:
            futures.remove(future)

    def _wait_all_futures(self, futures: list, future_ranges: dict):
        for future in as_completed(list(futures)):
            future.result()
            ts, row_id, count = future_ranges.pop(future)
            logger.info(f"批次写入完成: count={count}, batch_watermark={ts}/{row_id}")
            futures.remove(future)

    def _ensure_state_table(self):
        sql = f"""
            CREATE TABLE IF NOT EXISTS `{self.state_table}` (
              `id` int(11) NOT NULL AUTO_INCREMENT,
              `table_name` varchar(128) NOT NULL COMMENT '业务同步表名',
              `last_timestamp` datetime(3) NOT NULL DEFAULT '1970-01-01 00:00:00.000' COMMENT '增量水位时间戳',
              `last_id` bigint(20) NOT NULL DEFAULT 0 COMMENT '同时间戳下的主键水位',
              `last_delete_timestamp` datetime(3) NOT NULL DEFAULT '1970-01-01 00:00:00.000' COMMENT '删除水位时间戳',
              `last_delete_id` bigint(20) NOT NULL DEFAULT 0 COMMENT '同时间戳下删除ID水位',
              `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
              PRIMARY KEY (`id`),
              UNIQUE KEY `uk_table_name` (`table_name`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='业务数据增量同步水位表'
        """
        self.cfg_db.execute(sql)
        self.cfg_db.execute(
            f"ALTER TABLE `{self.state_table}` "
            "ADD COLUMN IF NOT EXISTS `last_delete_timestamp` datetime(3) NOT NULL "
            "DEFAULT '1970-01-01 00:00:00.000' COMMENT '删除水位时间戳'"
        )
        self.cfg_db.execute(
            f"ALTER TABLE `{self.state_table}` "
            "ADD COLUMN IF NOT EXISTS `last_delete_id` bigint(20) NOT NULL "
            "DEFAULT 0 COMMENT '同时间戳下删除ID水位'"
        )

    def _ensure_delete_log_table(self):
        sql = f"""
            CREATE TABLE IF NOT EXISTS `{self.delete_log_table}` (
              `id` bigint(20) NOT NULL AUTO_INCREMENT,
              `table_name` varchar(128) NOT NULL COMMENT '业务表名',
              `old_timestamp` datetime(3) NOT NULL COMMENT '删除起始时间水位',
              `old_id` bigint(20) NOT NULL COMMENT '删除起始ID水位',
              `new_timestamp` datetime(3) NOT NULL COMMENT '删除结束时间水位',
              `new_id` bigint(20) NOT NULL COMMENT '删除结束ID水位',
              `deleted_rows` bigint(20) NOT NULL DEFAULT 0 COMMENT '累计删除行数',
              `batch_size` int(11) NOT NULL DEFAULT 0 COMMENT '删除批次大小',
              `sleep_ms` int(11) NOT NULL DEFAULT 0 COMMENT '每批删除后休眠毫秒数',
              `elapsed_ms` bigint(20) NOT NULL DEFAULT 0 COMMENT '删除耗时毫秒',
              `status` varchar(20) NOT NULL DEFAULT 'SUCCESS' COMMENT '执行状态',
              `error_message` varchar(1000) DEFAULT NULL COMMENT '失败原因',
              `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
              PRIMARY KEY (`id`),
              KEY `idx_table_created` (`table_name`, `created_at`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='业务表源库删除审计日志'
        """
        self.cfg_db.execute(sql)

    def _load_watermark(self):
        default_ts = "1970-01-01 00:00:00.000"
        default_id = 0
        sql = f"""
            SELECT last_timestamp, last_id, last_delete_timestamp, last_delete_id
            FROM `{self.state_table}`
            WHERE table_name = %s
            LIMIT 1
        """
        row = self.cfg_db.fetch_one(sql, (self.table_name,))
        if not row:
            return default_ts, default_id, default_ts, default_id

        return (
            self._normalize_ts(row.get("last_timestamp", default_ts)),
            int(row.get("last_id", default_id)),
            self._normalize_ts(row.get("last_delete_timestamp", default_ts)),
            int(row.get("last_delete_id", default_id)),
        )

    def _save_sync_watermark(self, last_ts: str, last_id: int):
        sql = f"""
            INSERT INTO `{self.state_table}` (table_name, last_timestamp, last_id, last_delete_timestamp, last_delete_id)
            VALUES (%s, %s, %s, '1970-01-01 00:00:00.000', 0)
            ON DUPLICATE KEY UPDATE
              last_timestamp = VALUES(last_timestamp),
              last_id = VALUES(last_id)
        """
        self.cfg_db.execute(sql, (self.table_name, last_ts, int(last_id)))

    def _save_delete_watermark(self, last_delete_ts: str, last_delete_id: int):
        sql = f"""
            INSERT INTO `{self.state_table}` (table_name, last_timestamp, last_id, last_delete_timestamp, last_delete_id)
            VALUES (%s, '1970-01-01 00:00:00.000', 0, %s, %s)
            ON DUPLICATE KEY UPDATE
              last_delete_timestamp = VALUES(last_delete_timestamp),
              last_delete_id = VALUES(last_delete_id)
        """
        self.cfg_db.execute(sql, (self.table_name, last_delete_ts, int(last_delete_id)))

    def _pick_max_watermark(self, left: tuple, right: tuple):
        return right if right > left else left

    def _normalize_ts(self, value):
        if value is None:
            return "1970-01-01 00:00:00.000"
        if hasattr(value, "strftime"):
            return value.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        return str(value)

    def _calc_run_upper_ts(self, last_ts: str, sync_days_per_run: int) -> str:
        try:
            base_dt = datetime.strptime(last_ts, "%Y-%m-%d %H:%M:%S.%f")
        except ValueError:
            base_dt = datetime.strptime(last_ts, "%Y-%m-%d %H:%M:%S")

        days = max(1, int(sync_days_per_run))
        upper_dt = base_dt + timedelta(days=days)
        now_dt = datetime.now()
        if upper_dt > now_dt:
            upper_dt = now_dt
        return upper_dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

    def _delete_source_data(
        self,
        last_delete_ts: str,
        last_delete_id: int,
        sync_ts: str,
        sync_id: int,
        delete_batch_size: int,
        delete_sleep_ms: int,
        delete_lag_days: int,
        strict_delete_guard_enabled: bool,
        min_delete_lag_days: int,
    ):
        if strict_delete_guard_enabled and int(delete_lag_days) < int(min_delete_lag_days):
            message = (
                f"触发删除强保护: delete_lag_days={delete_lag_days} "
                f"< min_delete_lag_days={min_delete_lag_days}，已跳过源库删除"
            )
            logger.warning(message)
            self._log_delete_audit(
                old_ts=last_delete_ts,
                old_id=last_delete_id,
                new_ts=last_delete_ts,
                new_id=last_delete_id,
                deleted_rows=0,
                batch_size=max(100, int(delete_batch_size)),
                sleep_ms=int(delete_sleep_ms),
                elapsed_ms=0,
                status="SKIPPED_GUARD",
                error_message=message,
            )
            return

        delete_upper_ts = self._calc_delete_upper_ts(sync_ts, delete_lag_days)
        upper_delete_id = 9223372036854775807

        if (delete_upper_ts, upper_delete_id) <= (last_delete_ts, int(last_delete_id)):
            logger.info("删除上界未超过当前删除水位，跳过源库删除。")
            return

        total_deleted = 0
        batch_size = max(100, int(delete_batch_size))
        sleep_seconds = max(0, int(delete_sleep_ms)) / 1000.0
        started = time.time()
        delete_sql = f"""
            DELETE FROM `{self.table_name}`
            WHERE (
                    (`{self.watermark_column}` > %s)
                 OR (`{self.watermark_column}` = %s AND `{self.id_column}` > %s)
                  )
              AND (
                    (`{self.watermark_column}` < %s)
                 OR (`{self.watermark_column}` = %s AND `{self.id_column}` <= %s)
                  )
            ORDER BY `{self.watermark_column}`, `{self.id_column}`
            LIMIT %s
        """

        try:
            while True:
                affected = self.source.execute(
                    delete_sql,
                    (
                        last_delete_ts,
                        last_delete_ts,
                        int(last_delete_id),
                        delete_upper_ts,
                        delete_upper_ts,
                        upper_delete_id,
                        batch_size,
                    ),
                )
                if not affected:
                    break
                total_deleted += int(affected)
                if total_deleted % (batch_size * 10) == 0:
                    logger.info(f"源库删除进行中: deleted={total_deleted}")
                if sleep_seconds > 0:
                    time.sleep(sleep_seconds)

            elapsed_ms = int((time.time() - started) * 1000)
            self._save_delete_watermark(delete_upper_ts, upper_delete_id)
            self._log_delete_audit(
                old_ts=last_delete_ts,
                old_id=last_delete_id,
                new_ts=delete_upper_ts,
                new_id=upper_delete_id,
                deleted_rows=total_deleted,
                batch_size=batch_size,
                sleep_ms=int(delete_sleep_ms),
                elapsed_ms=elapsed_ms,
                status="SUCCESS",
                error_message=None,
            )
            logger.info(
                f"源库分批删除完成: deleted={total_deleted}, "
                f"delete_to={delete_upper_ts}/{upper_delete_id}, sync_watermark={sync_ts}/{sync_id}"
            )
        except Exception as exc:
            elapsed_ms = int((time.time() - started) * 1000)
            self._log_delete_audit(
                old_ts=last_delete_ts,
                old_id=last_delete_id,
                new_ts=delete_upper_ts,
                new_id=upper_delete_id,
                deleted_rows=total_deleted,
                batch_size=batch_size,
                sleep_ms=int(delete_sleep_ms),
                elapsed_ms=elapsed_ms,
                status="FAILED",
                error_message=str(exc)[:1000],
            )
            raise

    def _calc_delete_upper_ts(self, sync_ts: str, delete_lag_days: int) -> str:
        try:
            sync_dt = datetime.strptime(sync_ts, "%Y-%m-%d %H:%M:%S.%f")
        except ValueError:
            sync_dt = datetime.strptime(sync_ts, "%Y-%m-%d %H:%M:%S")

        lag_days = max(0, int(delete_lag_days))
        upper_dt = sync_dt - timedelta(days=lag_days)
        return upper_dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

    def _write_batch(self, sql: str, rows: list) -> int:
        conn = None
        try:
            conn = self.target._get_connection()
            conn.autocommit(False)
            with conn.cursor() as cursor:
                affected = cursor.executemany(sql, rows)
            conn.commit()
            return affected
        except Exception:
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.autocommit(True)
                self.target._return_connection(conn)

    def _log_delete_audit(
        self,
        old_ts: str,
        old_id: int,
        new_ts: str,
        new_id: int,
        deleted_rows: int,
        batch_size: int,
        sleep_ms: int,
        elapsed_ms: int,
        status: str,
        error_message: str,
    ):
        sql = f"""
            INSERT INTO `{self.delete_log_table}` (
                table_name, old_timestamp, old_id, new_timestamp, new_id,
                deleted_rows, batch_size, sleep_ms, elapsed_ms, status, error_message
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        self.cfg_db.execute(
            sql,
            (
                self.table_name,
                old_ts,
                int(old_id),
                new_ts,
                int(new_id),
                int(deleted_rows),
                int(batch_size),
                int(sleep_ms),
                int(elapsed_ms),
                status,
                error_message,
            ),
        )
