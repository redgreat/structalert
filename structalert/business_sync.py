import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from loguru import logger

from .database import DatabaseManager


class BusinessDataSynchronizer:
    """按水位增量同步业务表数据。"""

    def __init__(
        self,
        source_db: DatabaseManager,
        target_db: DatabaseManager,
        state_file: str,
        table_name: str = "tb_workbussinessjsoninfo",
        watermark_column: str = "LastUpdateTimeStamp",
        id_column: str = "Id",
    ):
        self.source = source_db
        self.target = target_db
        self.table_name = table_name
        self.watermark_column = watermark_column
        self.id_column = id_column
        self.state_file = state_file
        self.state_lock = threading.Lock()

    def sync_incremental(
        self,
        batch_size: int = 2000,
        max_workers: int = 4,
        dry_run: bool = False,
        queue_limit: int = 32,
    ):
        logger.info(
            f"开始业务数据增量同步: table={self.table_name}, "
            f"batch_size={batch_size}, max_workers={max_workers}, dry_run={dry_run}"
        )

        columns = self._get_physical_columns()
        if not columns:
            raise RuntimeError(f"无法获取表 {self.table_name} 的真实列信息")

        upsert_sql = self._build_upsert_sql(columns)
        last_ts, last_id = self._load_watermark()

        logger.info(
            f"当前同步水位: {self.watermark_column}={last_ts}, {self.id_column}={last_id}"
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
                    columns, last_ts, last_id, batch_size
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

            self._save_watermark(max_seen_ts, max_seen_id)
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

    def _read_incremental_batches(self, columns: list, start_ts: str, start_id: int, batch_size: int):
        select_columns = ", ".join(f"`{col}`" for col in columns)
        sql = f"""
            SELECT {select_columns}
            FROM `{self.table_name}`
            WHERE (`{self.watermark_column}` > %s)
               OR (`{self.watermark_column}` = %s AND `{self.id_column}` > %s)
            ORDER BY `{self.watermark_column}`, `{self.id_column}`
            LIMIT %s
        """

        current_ts = start_ts
        current_id = start_id

        while True:
            rows = self.source.fetch_all(sql, (current_ts, current_ts, current_id, batch_size))
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

    def _write_batch(self, sql: str, rows: list) -> int:
        return self.target.execute_many(sql, rows)

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

    def _load_watermark(self):
        default_ts = "1970-01-01 00:00:00.000"
        default_id = 0
        if not os.path.exists(self.state_file):
            return default_ts, default_id

        try:
            with self.state_lock:
                with open(self.state_file, "r", encoding="utf-8") as fp:
                    state = json.load(fp)
        except Exception as exc:
            logger.warning(f"读取水位文件失败，将从初始水位开始同步: {exc}")
            return default_ts, default_id

        table_state = state.get(self.table_name, {})
        return (
            table_state.get("last_timestamp", default_ts),
            int(table_state.get("last_id", default_id)),
        )

    def _save_watermark(self, last_ts: str, last_id: int):
        state_dir = os.path.dirname(self.state_file)
        if state_dir:
            os.makedirs(state_dir, exist_ok=True)
        with self.state_lock:
            state = {}
            if os.path.exists(self.state_file):
                try:
                    with open(self.state_file, "r", encoding="utf-8") as fp:
                        state = json.load(fp)
                except Exception:
                    state = {}

            state[self.table_name] = {
                "last_timestamp": last_ts,
                "last_id": int(last_id),
                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }

            with open(self.state_file, "w", encoding="utf-8") as fp:
                json.dump(state, fp, ensure_ascii=False, indent=2)

    def _pick_max_watermark(self, left: tuple, right: tuple):
        return right if right > left else left

    def _normalize_ts(self, value):
        if value is None:
            return "1970-01-01 00:00:00.000"
        if hasattr(value, "strftime"):
            return value.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        return str(value)
