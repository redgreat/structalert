import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pymysql


HOST = "pc-bp12w06s36qnlt5i2.rwlb.rds.aliyuncs.com"
PORT = 3306
USER = "user_service"
PASSWORD = "kI0zXaM5"
CHARSET = "utf8mb4"

SOURCE_DB = "serviceordercenter"
TARGET_DB = "serviceordercenterhis"
TABLE = "tb_workbussinessjsoninfo"

THREADS = 6
BATCH_SIZE = 2000
RANGE_SIZE = 200000

START_ID = None
END_ID = None

CLEAN_KEYS = ["tireNeedOuterTireRemoval"]

IGNORE_DUPLICATES = False
SKIP_BAD_ROWS = True


def connect_mysql(host, port, user, password, charset, autocommit=False):
    """创建 MySQL 连接，并设置常用的迁移会话参数以减少校验开销。"""
    conn = pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        charset=charset,
        autocommit=autocommit,
    )
    with conn.cursor() as cur:
        cur.execute("SET SESSION foreign_key_checks = 0")
        cur.execute("SET SESSION unique_checks = 0")
    return conn


def build_clean_expr(base_expr, clean_keys):
    """构造可嵌套的 MySQL 表达式，用于将指定 JSON key 的 ''/'null' 脏值清洗为“删除该 key”。"""
    expr = base_expr
    for key in clean_keys:
        key = key.strip()
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


def get_id_bounds(conn, source_db, table):
    """读取源表的最小/最大 Id，用于生成迁移分片范围。"""
    sql = f"SELECT MIN(Id) AS min_id, MAX(Id) AS max_id FROM `{source_db}`.`{table}`"
    with conn.cursor() as cur:
        cur.execute(sql)
        row = cur.fetchone()
    return (row[0], row[1])


def iter_ranges(start_id, end_id_inclusive, range_size):
    """按 range_size 生成闭区间 [start_id, end_id_inclusive] 的连续分片范围。"""
    if start_id is None or end_id_inclusive is None:
        return
    cur = start_id
    while cur <= end_id_inclusive:
        r_start = cur
        r_end = min(end_id_inclusive + 1, cur + range_size)
        yield (r_start, r_end)
        cur = r_end


def insert_batch(dst_conn, insert_sql, rows, skip_bad_rows):
    """将一个批次写入目标库；遇到写入异常时可逐行定位并按需跳过坏数据。"""
    if not rows:
        return (0, 0)

    inserted = 0
    skipped = 0

    try:
        with dst_conn.cursor() as cur:
            cur.executemany(insert_sql, rows)
        dst_conn.commit()
        return (len(rows), 0)
    except Exception:
        dst_conn.rollback()
        if not skip_bad_rows:
            raise

    for row in rows:
        try:
            with dst_conn.cursor() as cur:
                cur.execute(insert_sql, row)
            dst_conn.commit()
            inserted += 1
        except Exception as e:
            dst_conn.rollback()
            skipped += 1
            row_id = row[0] if row else None
            print(f"[WARN] 写入失败已跳过: Id={row_id}, err={e}")

    return (inserted, skipped)


def migrate_range(task_id, host, port, user, password, charset, source_db, target_db, table, r_start, r_end, batch_size, clean_keys, ignore_duplicates, skip_bad_rows):
    """迁移单个 ID 分片范围 [r_start, r_end)，按主键递增分页读取并分批写入目标表。"""
    thread_name = threading.current_thread().name
    src_conn = connect_mysql(host, port, user, password, charset, autocommit=True)
    dst_conn = connect_mysql(host, port, user, password, charset, autocommit=False)

    clean_expr = build_clean_expr("BussinessJson", clean_keys)
    select_sql = (
        f"SELECT Id, WorkOrderId, {clean_expr} AS BussinessJson, InsertTime, Deleted "
        f"FROM `{source_db}`.`{table}` "
        "WHERE Id >= %s AND Id < %s AND Id > %s "
        "ORDER BY Id "
        "LIMIT %s"
    )

    insert_prefix = "INSERT IGNORE" if ignore_duplicates else "INSERT"
    insert_sql = (
        f"{insert_prefix} INTO `{target_db}`.`{table}` "
        "(Id, WorkOrderId, BussinessJson, InsertTime, Deleted) "
        "VALUES (%s, %s, %s, %s, %s)"
    )

    last_id = r_start - 1
    total_read = 0
    total_inserted = 0
    total_skipped = 0
    started_at = time.time()

    try:
        while True:
            with src_conn.cursor() as cur:
                cur.execute(select_sql, (r_start, r_end, last_id, batch_size))
                rows = cur.fetchall()
            if not rows:
                break

            total_read += len(rows)
            last_id = rows[-1][0]

            inserted, skipped = insert_batch(dst_conn, insert_sql, rows, skip_bad_rows)
            total_inserted += inserted
            total_skipped += skipped

            if total_read % (batch_size * 10) == 0:
                elapsed = max(time.time() - started_at, 0.001)
                speed = int(total_read / elapsed)
                print(
                    f"[{thread_name}] task={task_id} range=[{r_start},{r_end}) "
                    f"read={total_read} inserted={total_inserted} skipped={total_skipped} "
                    f"last_id={last_id} speed={speed}/s"
                )

        elapsed = max(time.time() - started_at, 0.001)
        speed = int(total_read / elapsed) if total_read else 0
        print(
            f"[{thread_name}] task={task_id} 完成 range=[{r_start},{r_end}) "
            f"read={total_read} inserted={total_inserted} skipped={total_skipped} speed={speed}/s"
        )
        return (r_start, r_end, total_read, total_inserted, total_skipped)
    finally:
        try:
            src_conn.close()
        finally:
            dst_conn.close()


def main():
    """脚本入口：计算分片范围并并发执行迁移任务，最后输出汇总结果。"""
    clean_keys = [k.strip() for k in (CLEAN_KEYS or []) if str(k).strip()]
    if not clean_keys:
        clean_keys = ["tireNeedOuterTireRemoval"]

    meta_conn = connect_mysql(HOST, PORT, USER, PASSWORD, CHARSET, autocommit=True)
    try:
        min_id, max_id = get_id_bounds(meta_conn, SOURCE_DB, TABLE)
    finally:
        meta_conn.close()

    if min_id is None or max_id is None:
        print("源表为空，无需迁移")
        return

    start_id = START_ID if START_ID is not None else int(min_id)
    end_id = END_ID if END_ID is not None else int(max_id)
    if start_id > end_id:
        print(f"start-id({start_id}) 大于 end-id({end_id})，无需迁移")
        return

    ranges = list(iter_ranges(start_id, end_id, RANGE_SIZE))
    print(
        f"准备迁移: host={HOST}:{PORT} src={SOURCE_DB}.{TABLE} -> "
        f"dst={TARGET_DB}.{TABLE} "
        f"threads={THREADS} batch={BATCH_SIZE} range_size={RANGE_SIZE} "
        f"id=[{start_id},{end_id}] tasks={len(ranges)} clean_keys={clean_keys}"
    )

    started_at = time.time()
    total_read = 0
    total_inserted = 0
    total_skipped = 0

    with ThreadPoolExecutor(max_workers=max(1, THREADS)) as pool:
        futures = []
        for idx, (r_start, r_end) in enumerate(ranges, start=1):
            futures.append(
                pool.submit(
                    migrate_range,
                    idx,
                    HOST,
                    PORT,
                    USER,
                    PASSWORD,
                    CHARSET,
                    SOURCE_DB,
                    TARGET_DB,
                    TABLE,
                    r_start,
                    r_end,
                    BATCH_SIZE,
                    clean_keys,
                    IGNORE_DUPLICATES,
                    SKIP_BAD_ROWS,
                )
            )

        for fut in as_completed(futures):
            r_start, r_end, read_cnt, inserted_cnt, skipped_cnt = fut.result()
            total_read += read_cnt
            total_inserted += inserted_cnt
            total_skipped += skipped_cnt
            print(
                f"[MAIN] 已完成 range=[{r_start},{r_end}) "
                f"read={read_cnt} inserted={inserted_cnt} skipped={skipped_cnt}"
            )

    elapsed = max(time.time() - started_at, 0.001)
    speed = int(total_read / elapsed) if total_read else 0
    print(
        f"全部完成: read={total_read} inserted={total_inserted} skipped={total_skipped} "
        f"elapsed={int(elapsed)}s speed={speed}/s"
    )


if __name__ == "__main__":
    main()
