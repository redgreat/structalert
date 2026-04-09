import yaml
import os
import json
from datetime import datetime
from loguru import logger
from .database import DatabaseManager
from .comparator import DatabaseComparator
from .alert_wecom import WeComAlert
from .sync_module import DataSynchronizer

def load_config():
    config_path = os.environ.get("CONFIG_PATH", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config', 'config.yml'))
    if not os.path.exists(config_path):
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'config.yml.example')
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def run_daily_comparison():
    """主调度任务入口"""
    logger.info("开始执行数据库结构异动检测...")
    config = load_config()

    try:
        source_db = DatabaseManager.get_instance("source", config['databases']['source'])
        his_db = DatabaseManager.get_instance("his", config['databases']['his'])
        cfg_db = DatabaseManager.get_instance("cfg", config['databases']['cfg'])
    except Exception as e:
        logger.error(f"数据库连接初始化失败: {e}")
        return

    # 获取对比名单
    try:
        cfg_objs = cfg_db.fetch_all("SELECT object_name, object_type, need_sync FROM cfg_compare_objects WHERE is_active=1")
    except Exception as e:
        logger.error(f"无法获取配置比对表 cfg_compare_objects: {e}")
        return

    if not cfg_objs:
        logger.info("未配置任何需要对比的对象，任务结束。")
        return

    # 去重处理：根据 object_name 和 object_type 组合去重
    seen_objects = set()
    unique_cfg_objs = []
    for obj in cfg_objs:
        obj_key = (obj['object_name'], obj['object_type'])
        if obj_key not in seen_objects:
            seen_objects.add(obj_key)
            unique_cfg_objs.append(obj)
        else:
            logger.warning(f"发现重复配置的对比对象: {obj['object_type']} {obj['object_name']}，已跳过重复项")

    cfg_objs = unique_cfg_objs

    comparator = DatabaseComparator(source_db=source_db, target_db=his_db)

    today_str = datetime.now().strftime("%Y-%m-%d")
    diff_records = []

    for obj in cfg_objs:
        o_name = obj['object_name']
        o_type = obj['object_type']

        diff_detail = None
        target_ddl = None

        if o_type == 'TABLE':
            diff_detail, target_ddl = comparator.compare_table(o_name)
        elif o_type in ('VIEW', 'PROCEDURE', 'FUNCTION'):
            diff_detail, target_ddl = comparator.compare_routine(o_name, o_type)
        else:
            logger.warning(f"未知对象类型: {o_type}")
            continue

        if diff_detail:
            # 检查是否是源库不存在的情况
            if diff_detail.get('source_missing'):
                logger.info(f"源库不存在 {o_type}: {o_name}，跳过该对象的对比")
                continue

            # 有差异，准备插入记录
            diff_msg = diff_detail.get('diff_msg', '结构存在差异')
            diff_records.append({
                "object_name": o_name,
                "object_type": o_type,
                "diff_detail": diff_detail,
                "target_ddl": target_ddl,
                "diff_msg": diff_msg
            })

            # 将差异写入日志表
            try:
                insert_sql = """
                    INSERT INTO cfg_compare_diff
                    (compare_date, object_name, object_type, diff_detail, target_ddl, status)
                    VALUES (%s, %s, %s, %s, %s, 'PENDING')
                """
                cfg_db.execute(insert_sql, (
                    today_str, o_name, o_type,
                    json.dumps(diff_detail, ensure_ascii=False),
                    target_ddl
                ))
            except Exception as e:
                logger.error(f"日志记录失败 [{o_name}]: {e}")

    # 给企微发消息
    if diff_records:
        logger.info(f"检测到 {len(diff_records)} 处数据库结构异常，正在发送预警...")
        wecom_key = config.get('wecom', {}).get('webhook_key', '')
        wecom_client = WeComAlert(wecom_key)

        # 生成统计信息
        stats = generate_statistics(cfg_objs, diff_records)
        wecom_client.send_template_card(today_str, diff_records, len(diff_records), stats)
    else:
        logger.info("所有比对对象结构一致，没有异常。")

def run_weekly_sync():
    """每周数据同步任务入口"""
    logger.info("开始执行周数据同步...")

    # 检查今天是否是周日
    today = datetime.now()
    if today.weekday() != 6:  # 0=周一, 6=周日
        logger.info("今天不是周日，跳过周数据同步任务。")
        return

    logger.info("今天是周日，开始执行周数据同步任务。")

    config = load_config()

    try:
        source_db = DatabaseManager.get_instance("source", config['databases']['source'])
        his_db = DatabaseManager.get_instance("his", config['databases']['his'])
        cfg_db = DatabaseManager.get_instance("cfg", config['databases']['cfg'])
    except Exception as e:
        logger.error(f"数据库连接初始化失败: {e}")
        return

    # 获取需要同步的表
    try:
        sync_tables = cfg_db.fetch_all(
            "SELECT object_name, date_column FROM cfg_compare_objects WHERE object_type='TABLE' AND need_sync=1 AND is_active=1"
        )
    except Exception as e:
        logger.error(f"无法获取需要同步的表配置: {e}")
        return

    if not sync_tables:
        logger.info("没有配置需要同步的表，任务结束。")
        return

    # 使用当天凌晨2点的结构对比结果，避免重复验证
    logger.info("检查当天凌晨2点的结构对比结果...")
    today_str = today.strftime("%Y-%m-%d")

    try:
        # 查询当天是否存在表结构差异
        diff_tables = cfg_db.fetch_all(
            f"SELECT object_name FROM cfg_compare_diff WHERE compare_date = %s AND object_type = 'TABLE'",
            (today_str,)
        )
    except Exception as e:
        logger.error(f"查询当天结构对比结果失败: {e}")
        return

    if diff_tables:
        diff_table_names = [row['object_name'] for row in diff_tables]
        logger.error(f"以下表在今天凌晨2点的结构对比中发现差异: {', '.join(diff_table_names)}")
        logger.error("存在表结构差异，取消今天的周数据同步任务。")
        return

    logger.info("所有需要同步的表在今天凌晨2点的结构对比中均验证通过，开始执行数据同步...")

    # 获取同步配置参数
    sync_config = config.get('sync', {})
    days_before = sync_config.get('days_before', None)  # None表示全量同步
    batch_size = sync_config.get('batch_size', 5000)
    concurrency = sync_config.get('concurrency', 4)
    dry_run = sync_config.get('dry_run', False)
    
    if days_before is not None:
        logger.info(f"增量同步模式: 同步 {days_before} 天前的数据")
    else:
        logger.info("全量同步模式")
    
    logger.info(f"同步参数: batch_size={batch_size}, concurrency={concurrency}, dry_run={dry_run}")

    # 执行数据同步
    synchronizer = DataSynchronizer(source_db=source_db, target_db=his_db)

    for st in sync_tables:
        tb_name = st['object_name']
        date_col = st.get('date_column')  # 可能为None
        
        try:
            logger.info(f"开始同步表 {tb_name} 的数据...")
            synchronizer.sync_table(
                table_name=tb_name, 
                date_column=date_col, 
                days_before=days_before,
                batch_size=batch_size,
                max_workers=concurrency,
                dry_run=dry_run
            )
            logger.info(f"表 {tb_name} 数据同步完成。")
        except Exception as e:
            logger.error(f"表 {tb_name} 数据同步过程中发生异常: {e}")

    logger.info("周数据同步任务完成。")

def run_manual_sync_with_compare():
    """手动执行结构对比和数据迁移(带结构验证)"""
    logger.info("开始执行手动结构对比和数据迁移任务...")
    config = load_config()

    try:
        source_db = DatabaseManager.get_instance("source", config['databases']['source'])
        his_db = DatabaseManager.get_instance("his", config['databases']['his'])
        cfg_db = DatabaseManager.get_instance("cfg", config['databases']['cfg'])
    except Exception as e:
        logger.error(f"数据库连接初始化失败: {e}")
        return

    # 获取对比名单
    try:
        cfg_objs = cfg_db.fetch_all("SELECT object_name, object_type, need_sync FROM cfg_compare_objects WHERE is_active=1")
    except Exception as e:
        logger.error(f"无法获取配置比对表 cfg_compare_objects: {e}")
        return

    if not cfg_objs:
        logger.info("未配置任何需要对比的对象，任务结束。")
        return

    # 去重处理：根据 object_name 和 object_type 组合去重
    seen_objects = set()
    unique_cfg_objs = []
    for obj in cfg_objs:
        obj_key = (obj['object_name'], obj['object_type'])
        if obj_key not in seen_objects:
            seen_objects.add(obj_key)
            unique_cfg_objs.append(obj)
        else:
            logger.warning(f"发现重复配置的对比对象: {obj['object_type']} {obj['object_name']}，已跳过重复项")

    cfg_objs = unique_cfg_objs

    comparator = DatabaseComparator(source_db=source_db, target_db=his_db)

    today_str = datetime.now().strftime("%Y-%m-%d")
    diff_records = []

    # 第一步: 执行结构对比
    logger.info("=== 第一步: 开始执行结构对比 ===")
    for obj in cfg_objs:
        o_name = obj['object_name']
        o_type = obj['object_type']

        diff_detail = None
        target_ddl = None

        if o_type == 'TABLE':
            diff_detail, target_ddl = comparator.compare_table(o_name)
        elif o_type in ('VIEW', 'PROCEDURE', 'FUNCTION'):
            diff_detail, target_ddl = comparator.compare_routine(o_name, o_type)
        else:
            logger.warning(f"未知对象类型: {o_type}")
            continue

        if diff_detail:
            # 检查是否是源库不存在的情况
            if diff_detail.get('source_missing'):
                logger.info(f"源库不存在 {o_type}: {o_name}，跳过该对象的对比")
                continue

            # 有差异，准备插入记录
            diff_msg = diff_detail.get('diff_msg', '结构存在差异')
            diff_records.append({
                "object_name": o_name,
                "object_type": o_type,
                "diff_detail": diff_detail,
                "target_ddl": target_ddl,
                "diff_msg": diff_msg
            })

            # 将差异写入日志表
            try:
                insert_sql = """
                    INSERT INTO cfg_compare_diff
                    (compare_date, object_name, object_type, diff_detail, target_ddl, status)
                    VALUES (%s, %s, %s, %s, %s, 'PENDING')
                """
                cfg_db.execute(insert_sql, (
                    today_str, o_name, o_type,
                    json.dumps(diff_detail, ensure_ascii=False),
                    target_ddl
                ))
            except Exception as e:
                logger.error(f"日志记录失败 [{o_name}]: {e}")

    # 给企微发消息
    if diff_records:
        logger.info(f"检测到 {len(diff_records)} 处数据库结构异常，正在发送预警...")
        wecom_key = config.get('wecom', {}).get('webhook_key', '')
        wecom_client = WeComAlert(wecom_key)

        # 生成统计信息
        stats = generate_statistics(cfg_objs, diff_records)
        wecom_client.send_template_card(today_str, diff_records, len(diff_records), stats)
    else:
        logger.info("所有比对对象结构一致，没有异常。")

    # 第二步: 检查表结构差异并决定是否执行数据迁移
    logger.info("=== 第二步: 检查表结构差异 ===")
    
    # 重新获取需要同步的表（包含date_column信息）
    try:
        sync_tables = cfg_db.fetch_all(
            "SELECT object_name, date_column FROM cfg_compare_objects WHERE object_type='TABLE' AND need_sync=1 AND is_active=1"
        )
    except Exception as e:
        logger.error(f"无法获取需要同步的表配置: {e}")
        return

    if not sync_tables:
        logger.info("没有需要同步数据的表，任务结束。")
        return

    diff_table_names = {r['object_name'] for r in diff_records if r['object_type'] == 'TABLE'}

    if diff_table_names:
        logger.error(f"以下表存在结构差异，不能执行数据迁移: {', '.join(diff_table_names)}")
        logger.error("请先修复表结构差异后再执行数据迁移。")
        return

    logger.info("所有需要同步的表结构验证通过，开始执行数据迁移...")

    # 第三步: 执行数据迁移
    logger.info("=== 第三步: 开始执行数据迁移 ===")
    
    # 获取同步配置参数
    sync_config = config.get('sync', {})
    days_before = sync_config.get('days_before', None)  # None表示全量同步
    batch_size = sync_config.get('batch_size', 5000)
    concurrency = sync_config.get('concurrency', 4)
    dry_run = sync_config.get('dry_run', False)
    
    if days_before is not None:
        logger.info(f"增量同步模式: 同步 {days_before} 天前的数据")
    else:
        logger.info("全量同步模式")
    
    logger.info(f"同步参数: batch_size={batch_size}, concurrency={concurrency}, dry_run={dry_run}")
    
    synchronizer = DataSynchronizer(source_db=source_db, target_db=his_db)

    for st in sync_tables:
        tb_name = st['object_name']
        date_col = st.get('date_column')  # 可能为None
        
        try:
            logger.info(f"开始同步表 {tb_name} 的数据...")
            synchronizer.sync_table(
                table_name=tb_name, 
                date_column=date_col, 
                days_before=days_before,
                batch_size=batch_size,
                max_workers=concurrency,
                dry_run=dry_run
            )
            logger.info(f"表 {tb_name} 数据同步完成。")
        except Exception as e:
            logger.error(f"表 {tb_name} 数据同步过程中发生异常: {e}")

    logger.info("手动结构对比和数据迁移任务完成。")

def generate_statistics(all_objects, diff_objects):
    """生成统计信息"""
    # 按类型统计总数和差异数
    stats = {}
    object_types = ['TABLE', 'VIEW', 'PROCEDURE', 'FUNCTION']

    for obj_type in object_types:
        total = len([obj for obj in all_objects if obj['object_type'] == obj_type])
        diff = len([obj for obj in diff_objects if obj['object_type'] == obj_type])
        stats[obj_type] = {
            'total': total,
            'diff': diff
        }

    return stats

if __name__ == "__main__":
    run_daily_comparison()
