"""
按工单 CreatedAt 水位，将归档范围内的业务表数据迁移到 his 库，并可选分批删除源库数据。
水位与删除审计复用 cfg_business_sync_state / cfg_business_sync_delete_log（table_name 存各对象的 state_key）。
"""

from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, time as dt_time, timedelta
from typing import Any

from loguru import logger

from .database import DatabaseManager


def _normalize_ts(value) -> str:
    if value is None:
        return "1970-01-01 00:00:00.000"
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    s = str(value).strip()
    return s if s else "1970-01-01 00:00:00.000"


def _parse_dt(value) -> datetime:
    if value is None:
        return datetime(1970, 1, 1, 0, 0, 0, 0)
    if isinstance(value, datetime):
        return value
    s = str(value).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(s, fmt)
            if fmt == "%Y-%m-%d":
                dt = datetime.combine(dt.date(), dt_time(23, 59, 59, 999000))
            return dt
        except ValueError:
            continue
    raise ValueError(f"无法解析时间: {value!r}")


def _cutoff_upper_datetime(cfg: dict) -> datetime:
    """a.CreatedAt <= 该时刻（含）视为在「可归档」时间窗内。"""
    cut = cfg or {}
    fixed = (cut.get("fixed_datetime") or cut.get("datetime") or "").strip()
    if fixed:
        return _parse_dt(fixed)
    days_ago = max(0, int(cut.get("days_ago", 730)))
    d = date.today() - timedelta(days=days_ago)
    return datetime.combine(d, dt_time(23, 59, 59, 999000))


def _build_json_clean_sql_expr(base_expr: str, clean_keys: list[str]) -> str:
    """与 scripts/migrate_bussinessjson.py 一致的 MySQL JSON 脏值清洗表达式。"""
    expr = base_expr
    for key in clean_keys:
        key = (key or "").strip()
        if not key:
            continue
        path = f"$.{key}"
        expr = (
            "CASE "
            f"WHEN json_unquote(json_extract({expr},'{path}')) IN ('','null') "
            f"THEN json_remove({expr},'{path}') "
            f"ELSE {expr} "
            "END"
        )
    return expr


def _python_json_clean(value: Any, clean_keys: list[str]) -> Any:
    if not clean_keys or value is None:
        return value
    if isinstance(value, (bytes, bytearray)):
        try:
            value = value.decode("utf-8")
        except Exception:
            return value
    if isinstance(value, dict):
        data = dict(value)
        for key in clean_keys:
            k = (key or "").strip()
            if not k or k not in data:
                continue
            v = data.get(k)
            if v in ("", "null", None) or (isinstance(v, str) and v.strip() == ""):
                data.pop(k, None)
        return json.dumps(data, ensure_ascii=False)
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return value
        try:
            data = json.loads(s)
        except json.JSONDecodeError:
            return value
        if not isinstance(data, dict):
            return value
        for key in clean_keys:
            k = (key or "").strip()
            if not k or k not in data:
                continue
            v = data.get(k)
            if v in ("", "null", None) or (isinstance(v, str) and v.strip() == ""):
                data.pop(k, None)
        return json.dumps(data, ensure_ascii=False)
    return value


def _ensure_state_table(cfg_db: DatabaseManager, state_table: str):
    sql = f"""
        CREATE TABLE IF NOT EXISTS `{state_table}` (
          `id` int(11) NOT NULL AUTO_INCREMENT,
          `table_name` varchar(128) NOT NULL COMMENT '业务同步对象键',
          `last_timestamp` datetime(3) NOT NULL DEFAULT '1970-01-01 00:00:00.000' COMMENT '工单 CreatedAt 水位',
          `last_id` varchar(128) NOT NULL DEFAULT '' COMMENT '同 CreatedAt 下目标行主键水位',
          `last_delete_timestamp` datetime(3) NOT NULL DEFAULT '1970-01-01 00:00:00.000' COMMENT '源库删除 CreatedAt 水位',
          `last_delete_id` varchar(128) NOT NULL DEFAULT '' COMMENT '同 CreatedAt 下删除主键水位',
          `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
          PRIMARY KEY (`id`),
          UNIQUE KEY `uk_table_name` (`table_name`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='归档/业务数据同步水位表'
    """
    cfg_db.execute(sql)


def _ensure_delete_log_table(cfg_db: DatabaseManager, delete_log_table: str):
    sql = f"""
        CREATE TABLE IF NOT EXISTS `{delete_log_table}` (
          `id` bigint(20) NOT NULL AUTO_INCREMENT,
          `table_name` varchar(128) NOT NULL COMMENT '对象键',
          `old_timestamp` datetime(3) NOT NULL COMMENT '删除区间下界 CreatedAt',
          `old_id` varchar(128) NOT NULL COMMENT '删除区间下界主键',
          `new_timestamp` datetime(3) NOT NULL COMMENT '删除区间上界 CreatedAt',
          `new_id` varchar(128) NOT NULL COMMENT '删除区间上界主键',
          `deleted_rows` bigint(20) NOT NULL DEFAULT 0 COMMENT '累计删除行数',
          `batch_size` int(11) NOT NULL DEFAULT 0 COMMENT '删除批次大小',
          `sleep_ms` int(11) NOT NULL DEFAULT 0 COMMENT '每批休眠毫秒',
          `elapsed_ms` bigint(20) NOT NULL DEFAULT 0 COMMENT '删除耗时毫秒',
          `status` varchar(20) NOT NULL DEFAULT 'SUCCESS' COMMENT '执行状态',
          `error_message` varchar(1000) DEFAULT NULL COMMENT '失败原因',
          `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
          PRIMARY KEY (`id`),
          KEY `idx_table_created` (`table_name`, `created_at`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='源库删除审计日志'
    """
    cfg_db.execute(sql)


def _ensure_state_string_ids(cfg_db: DatabaseManager, state_table: str):
    for col, comment in (
        ("last_id", "同时间戳下的主键水位"),
        ("last_delete_id", "同时间戳下删除ID水位"),
    ):
        row = cfg_db.fetch_one(
            """
            SELECT DATA_TYPE
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = %s
              AND COLUMN_NAME = %s
            LIMIT 1
            """,
            (state_table, col),
        )
        if not row:
            continue
        if str(row.get("DATA_TYPE", "")).lower() == "varchar":
            continue
        cfg_db.execute(
            f"ALTER TABLE `{state_table}` "
            f"MODIFY COLUMN `{col}` varchar(128) NOT NULL DEFAULT '' COMMENT '{comment}'"
        )


def _ensure_delete_log_id_columns(cfg_db: DatabaseManager, delete_log_table: str):
    for col, comment in (
        ("old_id", "删除起始ID水位"),
        ("new_id", "删除结束ID水位"),
    ):
        row = cfg_db.fetch_one(
            """
            SELECT DATA_TYPE
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = %s
              AND COLUMN_NAME = %s
            LIMIT 1
            """,
            (delete_log_table, col),
        )
        if not row:
            continue
        if str(row.get("DATA_TYPE", "")).lower() == "varchar":
            continue
        cfg_db.execute(
            f"ALTER TABLE `{delete_log_table}` "
            f"MODIFY COLUMN `{col}` varchar(128) NOT NULL COMMENT '{comment}'"
        )


def _load_watermark(cfg_db: DatabaseManager, state_table: str, state_key: str) -> tuple[str, str, str, str]:
    default_ts = "1970-01-01 00:00:00.000"
    default_id = ""
    row = cfg_db.fetch_one(
        f"""
        SELECT last_timestamp, last_id, last_delete_timestamp, last_delete_id
        FROM `{state_table}` WHERE table_name = %s LIMIT 1
        """,
        (state_key,),
    )
    if not row:
        return default_ts, default_id, default_ts, default_id
    return (
        _normalize_ts(row.get("last_timestamp", default_ts)),
        str(row.get("last_id", default_id) or ""),
        _normalize_ts(row.get("last_delete_timestamp", default_ts)),
        str(row.get("last_delete_id", default_id) or ""),
    )


def _save_sync_watermark(cfg_db: DatabaseManager, state_table: str, state_key: str, ts: str, row_id: str):
    cfg_db.execute(
        f"""
        INSERT INTO `{state_table}` (table_name, last_timestamp, last_id, last_delete_timestamp, last_delete_id)
        VALUES (%s, %s, %s, '1970-01-01 00:00:00.000', '')
        ON DUPLICATE KEY UPDATE last_timestamp = VALUES(last_timestamp), last_id = VALUES(last_id)
        """,
        (state_key, ts, str(row_id)),
    )


def _save_delete_watermark(cfg_db: DatabaseManager, state_table: str, state_key: str, ts: str, row_id: str):
    cfg_db.execute(
        f"""
        INSERT INTO `{state_table}` (table_name, last_timestamp, last_id, last_delete_timestamp, last_delete_id)
        VALUES (%s, '1970-01-01 00:00:00.000', '', %s, %s)
        ON DUPLICATE KEY UPDATE
          last_delete_timestamp = VALUES(last_delete_timestamp),
          last_delete_id = VALUES(last_delete_id)
        """,
        (state_key, ts, str(row_id)),
    )


def _log_delete_audit(
    cfg_db: DatabaseManager,
    delete_log_table: str,
    state_key: str,
    old_ts: str,
    old_id: str,
    new_ts: str,
    new_id: str,
    deleted_rows: int,
    batch_size: int,
    sleep_ms: int,
    elapsed_ms: int,
    status: str,
    error_message: str | None,
):
    cfg_db.execute(
        f"""
        INSERT INTO `{delete_log_table}` (
          table_name, old_timestamp, old_id, new_timestamp, new_id,
          deleted_rows, batch_size, sleep_ms, elapsed_ms, status, error_message
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            state_key,
            old_ts,
            str(old_id),
            new_ts,
            str(new_id),
            int(deleted_rows),
            int(batch_size),
            int(sleep_ms),
            int(elapsed_ms),
            status,
            error_message,
        ),
    )


def _get_columns_for_table(db: DatabaseManager, table: str) -> list[str]:
    rows = db.fetch_all(f"SHOW COLUMNS FROM `{table}`")
    cols = []
    for row in rows:
        extra = str(row.get("Extra", "")).upper()
        if "VIRTUAL GENERATED" in extra or "STORED GENERATED" in extra or "GENERATED ALWAYS" in extra:
            continue
        cols.append(row["Field"])
    return cols


def _build_upsert_sql(table: str, columns: list[str], pk: str) -> str:
    column_sql = ", ".join(f"`{c}`" for c in columns)
    value_sql = ", ".join(["%s"] * len(columns))
    update_sql = ", ".join(f"`{c}`=VALUES(`{c}`)" for c in columns if c != pk)
    return (
        f"INSERT INTO `{table}` ({column_sql}) VALUES ({value_sql}) ON DUPLICATE KEY UPDATE {update_sql}"
    )


def _write_batch(target_db: DatabaseManager, sql: str, rows: list[tuple]) -> None:
    conn = None
    try:
        conn = target_db._get_connection()
        conn.autocommit(False)
        with conn.cursor() as cursor:
            cursor.executemany(sql, rows)
        conn.commit()
    except Exception:
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.autocommit(True)
            target_db._return_connection(conn)


class WorkorderArchiveObject:
    """单归档对象：工单过滤 + JOIN 到目标行，按 (a.CreatedAt, 目标主键) 推进水位。"""

    def __init__(
        self,
        source_db: DatabaseManager,
        target_db: DatabaseManager,
        spec: dict,
        source_db_name: str,
    ):
        self.source = source_db
        self.target = target_db
        self.spec = spec
        self.source_db_name = source_db_name
        self.target_table = spec["target_table"]
        self.state_key = spec.get("state_key") or spec.get("key") or f"archive_{self.target_table}"
        self.kind = spec.get("kind", "workbusiness_json")
        self.pk = spec.get("pk", "Id")
        self.json_clean = spec.get("json_clean") or {}
        self.enabled = bool(spec.get("enabled", True))

    def select_columns_sql(self) -> str:
        keys = [str(k).strip() for k in (self.json_clean.get("keys") or []) if str(k).strip()]
        col = (self.json_clean.get("column") or "").strip()
        alias = self._row_alias()
        if keys and col:
            expr = _build_json_clean_sql_expr(f"`{alias}`.`{col}`", keys)
            other_cols = _get_columns_for_table(self.source, self.target_table)
            parts = []
            for c in other_cols:
                if c == col:
                    parts.append(f"{expr} AS `{col}`")
                else:
                    parts.append(f"`{alias}`.`{c}` AS `{c}`")
            return ", ".join(parts)
        return f"`{alias}`.*"

    def _row_alias(self) -> str:
        if self.kind == "basic_resourceitem":
            return "c"
        return "b"

    def build_select_sql(self) -> str:
        sel = self.select_columns_sql()
        if self.kind == "workbusiness_json":
            return f"""
                SELECT {sel}, `a`.`CreatedAt` AS `_wm_created_at`
                FROM `{self.source_db_name}`.`tb_workorderinfo` `a`
                INNER JOIN `{self.source_db_name}`.`tb_workbussinessjsoninfo` `b`
                  ON `b`.`WorkOrderId` = `a`.`Id`
                WHERE `a`.`WorkStatus` = 9
                  AND (`a`.`ServiceProviderCode` IS NULL OR `a`.`ServiceProviderCode` = '1003')
                  AND `a`.`CreatedAt` <= %s
                  AND (
                        `a`.`CreatedAt` > %s
                     OR (`a`.`CreatedAt` = %s AND `b`.`{self.pk}` > %s)
                      )
                ORDER BY `a`.`CreatedAt`, `b`.`{self.pk}`
                LIMIT %s
            """
        if self.kind == "basic_resourceitem":
            return f"""
                SELECT {sel}, `a`.`CreatedAt` AS `_wm_created_at`
                FROM `{self.source_db_name}`.`tb_workorderinfo` `a`
                INNER JOIN `{self.source_db_name}`.`tb_workresourceinfo` `wr`
                  ON `wr`.`WorkOrderId` = `a`.`Id`
                INNER JOIN `{self.source_db_name}`.`basic_resourceitem` `c`
                  ON `c`.`Id` = `wr`.`ResourceId`
                WHERE `a`.`WorkStatus` = 9
                  AND (`a`.`ServiceProviderCode` IS NULL OR `a`.`ServiceProviderCode` = '1003')
                  AND `a`.`CreatedAt` <= %s
                  AND (
                        `a`.`CreatedAt` > %s
                     OR (`a`.`CreatedAt` = %s AND `c`.`{self.pk}` > %s)
                      )
                ORDER BY `a`.`CreatedAt`, `c`.`{self.pk}`
                LIMIT %s
            """
        raise ValueError(f"未知 archive kind: {self.kind}")


def run_workorder_archive_sync_job(
    source_db: DatabaseManager,
    target_db: DatabaseManager,
    cfg_db: DatabaseManager,
    config: dict,
):
    root = config.get("archive_sync") or {}
    if not root.get("enabled", False):
        logger.info("archive_sync.enabled 为 false，跳过工单归档同步。")
        return

    state_table = root.get("state_table", "cfg_business_sync_state")
    delete_log_table = root.get("delete_log_table", "cfg_business_sync_delete_log")
    batch_size = max(1, int(root.get("batch_size", 2000)))
    max_workers = max(1, int(root.get("concurrency", 4)))
    queue_limit = max(1, int(root.get("queue_limit", 8)))
    dry_run = bool(root.get("dry_run", False))
    skip_if_struct_diff = bool(root.get("skip_if_struct_diff", True))
    max_rows_per_run = root.get("max_rows_per_run")
    max_rows_per_run = int(max_rows_per_run) if max_rows_per_run is not None else None

    del_cfg = root.get("delete") or {}
    delete_enabled = bool(del_cfg.get("enabled", True))
    delete_batch_size = max(100, int(del_cfg.get("batch_size", 2000)))
    delete_sleep_ms = int(del_cfg.get("sleep_ms", 0))
    delete_lag_days = int(del_cfg.get("lag_days", 30))
    strict_guard = bool(del_cfg.get("strict_guard", True))
    min_lag_days = int(del_cfg.get("min_lag_days", 7))

    cutoff_cfg = root.get("cutoff") or {}
    upper_dt = _cutoff_upper_datetime(cutoff_cfg)
    upper_ts = upper_dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

    window_days = max(1, int(root.get("window_days_per_run", 7)))

    source_db_name = (config.get("databases") or {}).get("source", {}).get("database") or ""

    _ensure_state_table(cfg_db, state_table)
    _ensure_state_string_ids(cfg_db, state_table)
    _ensure_delete_log_table(cfg_db, delete_log_table)
    _ensure_delete_log_id_columns(cfg_db, delete_log_table)

    objects_raw = root.get("objects") or []
    if not objects_raw:
        logger.warning("archive_sync.objects 为空，未配置任何归档对象。")
        return

    today_str = datetime.now().strftime("%Y-%m-%d")

    for spec in objects_raw:
        obj = WorkorderArchiveObject(source_db, target_db, spec, source_db_name)
        if not obj.enabled:
            logger.info(f"归档对象已禁用，跳过: {obj.state_key}")
            continue

        if skip_if_struct_diff:
            try:
                diff_row = cfg_db.fetch_one(
                    """
                    SELECT 1 AS has_diff FROM cfg_compare_diff
                    WHERE compare_date = %s AND object_type = 'TABLE' AND object_name = %s
                    LIMIT 1
                    """,
                    (today_str, obj.target_table),
                )
            except Exception as e:
                logger.error(f"[{obj.state_key}] 查询 cfg_compare_diff 失败: {e}")
                continue
            if diff_row:
                logger.error(
                    f"[{obj.state_key}] 表 {obj.target_table} 今日结构对比有差异，跳过归档同步。"
                )
                continue

        last_ts, last_id, del_ts, del_id = _load_watermark(cfg_db, state_table, obj.state_key)
        init_dt = _parse_dt(last_ts)
        run_end_date = init_dt.date() + timedelta(days=window_days)
        run_ceiling_dt = datetime.combine(run_end_date, dt_time(23, 59, 59, 999000))
        now_dt = datetime.now()
        run_ceiling_dt = min(run_ceiling_dt, upper_dt, now_dt)
        run_ceiling_ts = run_ceiling_dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

        logger.info(
            f"[{obj.state_key}] 开始归档: 全局上界CreatedAt={upper_ts}, "
            f"本窗口上界CreatedAt={run_ceiling_ts} (window_days_per_run={window_days}), "
            f"sync_wm=({last_ts},{last_id!r}), delete_wm=({del_ts},{del_id!r}), "
            f"batch_size={batch_size}, workers={max_workers}, dry_run={dry_run}"
        )

        columns = _get_columns_for_table(target_db, obj.target_table)
        if not columns:
            logger.error(f"[{obj.state_key}] 目标表无列信息: {obj.target_table}")
            continue
        upsert_sql = _build_upsert_sql(obj.target_table, columns, obj.pk)

        select_sql = obj.build_select_sql()
        clean_keys = [str(k).strip() for k in (obj.json_clean.get("keys") or []) if str(k).strip()]
        clean_col = (obj.json_clean.get("column") or "").strip()

        rows_migrated = 0
        cur_ts, cur_id = last_ts, last_id
        max_seen_ts, max_seen_id = last_ts, last_id

        try:
            target_db.set_session_overrides({"FOREIGN_KEY_CHECKS": 0, "UNIQUE_CHECKS": 0})
        except Exception as exc:
            logger.warning(f"[{obj.state_key}] 设置目标库会话参数失败: {exc}")

        futures: list = []
        future_meta: dict = {}

        try:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                while True:
                    batch = source_db.fetch_all(
                        select_sql,
                        (run_ceiling_ts, cur_ts, cur_ts, cur_id, batch_size),
                    )
                    if not batch:
                        break

                    last_row = batch[-1]
                    cur_ts = _normalize_ts(last_row.get("_wm_created_at"))
                    cur_id = str(last_row.get(obj.pk) or "")
                    max_seen_ts, max_seen_id = cur_ts, cur_id

                    if dry_run:
                        rows_migrated += len(batch)
                        if max_rows_per_run and rows_migrated >= max_rows_per_run:
                            break
                        continue

                    tuples_out = []
                    for raw in batch:
                        row = dict(raw)
                        row.pop("_wm_created_at", None)
                        if clean_col and clean_keys and clean_col in row:
                            row[clean_col] = _python_json_clean(row.get(clean_col), clean_keys)
                        tuples_out.append(tuple(row.get(c) for c in columns))

                    fut = executor.submit(_write_batch, target_db, upsert_sql, tuples_out)
                    futures.append(fut)
                    future_meta[fut] = (len(batch), max_seen_ts, max_seen_id)

                    rows_migrated += len(batch)

                    if len(futures) >= max_workers * queue_limit:
                        _drain_futures(futures, future_meta, max_workers)

                    if max_rows_per_run and rows_migrated >= max_rows_per_run:
                        break

                if not dry_run:
                    _drain_all(futures, future_meta)

        finally:
            try:
                target_db.set_session_overrides({})
            except Exception as exc:
                logger.warning(f"[{obj.state_key}] 恢复目标库会话参数失败: {exc}")

        if dry_run:
            logger.info(f"[{obj.state_key}] dry_run 完成，扫描约 {rows_migrated} 行（未写库、未推进水位）。")
            continue

        if rows_migrated <= 0:
            logger.info(f"[{obj.state_key}] 本周期无新数据，保持原同步水位。")
        else:
            _save_sync_watermark(cfg_db, state_table, obj.state_key, max_seen_ts, max_seen_id)
        logger.info(
            f"[{obj.state_key}] 迁移完成: rows={rows_migrated}, new_sync_wm=({max_seen_ts},{max_seen_id!r})"
        )

        if not delete_enabled:
            logger.info(f"[{obj.state_key}] 已配置跳过源库删除。")
            continue

        if strict_guard and delete_lag_days < min_lag_days:
            msg = (
                f"删除强保护: lag_days={delete_lag_days} < min_lag_days={min_lag_days}，跳过删除"
            )
            logger.warning(f"[{obj.state_key}] {msg}")
            _log_delete_audit(
                cfg_db,
                delete_log_table,
                obj.state_key,
                del_ts,
                del_id,
                del_ts,
                del_id,
                0,
                delete_batch_size,
                delete_sleep_ms,
                0,
                "SKIPPED_GUARD",
                msg,
            )
            continue

        max_seen_dt = _parse_dt(max_seen_ts)
        archive_upper_dt = _parse_dt(upper_ts)
        delete_by_lag_dt = max_seen_dt - timedelta(days=delete_lag_days)
        delete_cap_dt = min(archive_upper_dt, delete_by_lag_dt)
        delete_cap_ts = delete_cap_dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

        sleep_sec = max(0, delete_sleep_ms) / 1000.0
        total_deleted = 0
        t0 = time.time()
        orig_del_ts, orig_del_id = del_ts, del_id
        run_ts, run_id = del_ts, del_id
        new_del_ts, new_del_id = del_ts, del_id

        ids_sql = _delete_ids_select_sql(obj)
        try:
            while True:
                ids_rows = source_db.fetch_all(
                    ids_sql,
                    (delete_cap_ts, run_ts, run_ts, run_id, delete_batch_size),
                )
                if not ids_rows:
                    break
                ids = [str(r["rid"]) for r in ids_rows]
                if not ids:
                    break
                placeholders = ",".join(["%s"] * len(ids))
                affected = source_db.execute(
                    f"DELETE FROM `{source_db_name}`.`{obj.target_table}` WHERE `{obj.pk}` IN ({placeholders})",
                    tuple(ids),
                )
                total_deleted += int(affected or 0)
                last_row = ids_rows[-1]
                new_del_ts = _normalize_ts(last_row["ca"])
                new_del_id = str(last_row["rid"])
                run_ts, run_id = new_del_ts, new_del_id
                _save_delete_watermark(cfg_db, state_table, obj.state_key, new_del_ts, new_del_id)
                if sleep_sec:
                    time.sleep(sleep_sec)

            elapsed_ms = int((time.time() - t0) * 1000)
            _log_delete_audit(
                cfg_db,
                delete_log_table,
                obj.state_key,
                orig_del_ts,
                orig_del_id,
                new_del_ts,
                new_del_id,
                total_deleted,
                delete_batch_size,
                delete_sleep_ms,
                elapsed_ms,
                "SUCCESS",
                None,
            )
            logger.info(
                f"[{obj.state_key}] 源库删除完成: deleted={total_deleted}, "
                f"delete_wm=({new_del_ts},{new_del_id!r}), cap_CreatedAt={delete_cap_ts}"
            )
        except Exception as exc:
            elapsed_ms = int((time.time() - t0) * 1000)
            _log_delete_audit(
                cfg_db,
                delete_log_table,
                obj.state_key,
                orig_del_ts,
                orig_del_id,
                new_del_ts,
                new_del_id,
                total_deleted,
                delete_batch_size,
                delete_sleep_ms,
                elapsed_ms,
                "FAILED",
                str(exc)[:1000],
            )
            logger.error(f"[{obj.state_key}] 源库删除失败: {exc}")
            raise


def _delete_ids_select_sql(obj: WorkorderArchiveObject) -> str:
    """选取一批待删主键：CreatedAt <= delete_cap，且 (CreatedAt, pk) 大于删除水位（字典序）。"""
    dbn = obj.source_db_name
    pk = obj.pk
    if obj.kind == "workbusiness_json":
        return f"""
            SELECT `b`.`{pk}` AS rid, `a`.`CreatedAt` AS ca
            FROM `{dbn}`.`tb_workorderinfo` `a`
            INNER JOIN `{dbn}`.`tb_workbussinessjsoninfo` `b` ON `b`.`WorkOrderId` = `a`.`Id`
            WHERE `a`.`WorkStatus` = 9
              AND (`a`.`ServiceProviderCode` IS NULL OR `a`.`ServiceProviderCode` = '1003')
              AND `a`.`CreatedAt` <= %s
              AND (
                    `a`.`CreatedAt` > %s
                 OR (`a`.`CreatedAt` = %s AND `b`.`{pk}` > %s)
                  )
            ORDER BY `a`.`CreatedAt`, `b`.`{pk}`
            LIMIT %s
        """
    if obj.kind == "basic_resourceitem":
        return f"""
            SELECT `c`.`{pk}` AS rid, `a`.`CreatedAt` AS ca
            FROM `{dbn}`.`tb_workorderinfo` `a`
            INNER JOIN `{dbn}`.`tb_workresourceinfo` `wr` ON `wr`.`WorkOrderId` = `a`.`Id`
            INNER JOIN `{dbn}`.`basic_resourceitem` `c` ON `c`.`Id` = `wr`.`ResourceId`
            WHERE `a`.`WorkStatus` = 9
              AND (`a`.`ServiceProviderCode` IS NULL OR `a`.`ServiceProviderCode` = '1003')
              AND `a`.`CreatedAt` <= %s
              AND (
                    `a`.`CreatedAt` > %s
                 OR (`a`.`CreatedAt` = %s AND `c`.`{pk}` > %s)
                  )
            ORDER BY `a`.`CreatedAt`, `c`.`{pk}`
            LIMIT %s
        """
    raise ValueError(obj.kind)


def _drain_futures(futures: list, future_meta: dict, n: int):
    done = 0
    completed: list = []
    for fut in as_completed(list(futures)):
        fut.result()
        cnt, ts, rid = future_meta.pop(fut, (0, "", ""))
        logger.info(f"批次写入完成: n={cnt}, wm=({ts},{rid!r})")
        completed.append(fut)
        done += 1
        if done >= n:
            break
    for fut in completed:
        if fut in futures:
            futures.remove(fut)


def _drain_all(futures: list, future_meta: dict):
    for fut in as_completed(list(futures)):
        fut.result()
        cnt, ts, rid = future_meta.pop(fut, (0, "", ""))
        logger.info(f"批次写入完成: n={cnt}, wm=({ts},{rid!r})")
        if fut in futures:
            futures.remove(fut)
