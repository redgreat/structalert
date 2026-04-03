from loguru import logger

class DatabaseComparator:
    def __init__(self, source_db, target_db):
        self.source_db = source_db
        self.target_db = target_db

    def compare_table(self, table_name: str):
        """对比单张表的外在结构，生成增量的 Alter Table DDL"""
        diff_detail = {}
        target_ddl_list = []

        # 1. 检查目标库是否存在该表
        check_target_sql = "SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s"
        target_exists = self.target_db.fetch_one(check_target_sql, (self.target_db.database, table_name))

        # 获取源库表的 SHOW CREATE TABLE (即使它不在那边，也要确认源库是否存在)
        source_create = None
        try:
            source_create = self.source_db.fetch_one(f"SHOW CREATE TABLE `{table_name}`")
        except Exception as e:
            # 源库不存在该表，返回特殊标记
            logger.info(f"源库未找到表 {table_name}，跳过对比")
            return {"diff_msg": f"源库不存在表: {table_name}", "source_missing": True}, None

        if not target_exists:
            # 目标库缺失整张表
            diff_detail["missing_table"] = True
            if source_create and 'Create Table' in source_create:
                return {"diff_msg": f"目标库缺失表: {table_name}", "missing_table": True}, source_create['Create Table']

        # 2. 如果存在，对比信息架构的字段 (简单对比 Column 的有无和数据类型)
        # 使用基础查询，通过EXTRA字段判断虚拟列
        col_sql = """
            SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT, COLUMN_COMMENT, EXTRA
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s
            ORDER BY ORDINAL_POSITION
        """
        source_cols = self.source_db.fetch_all(col_sql, (self.source_db.database, table_name))
        target_cols = self.target_db.fetch_all(col_sql, (self.target_db.database, table_name))

        src_col_dict = {c['COLUMN_NAME']: c for c in source_cols}
        tgt_col_dict = {c['COLUMN_NAME']: c for c in target_cols}

        missing_columns = []
        modified_columns = []

        # 遍历源库列，查看目标库是否有变更或者缺失
        for col_name, src_col in src_col_dict.items():
            if col_name not in tgt_col_dict:
                # 生成 ADD COLUMN DDL (简化为使用 source 字段构建, 这里提取不易，用基础字符串拼凑，最好还是能通过 parse 拼凑)
                # 为简单起见，拼装基础的类型和约束

                # 检查是否是虚拟列（通过EXTRA字段判断）
                extra = src_col['EXTRA'].upper()
                is_virtual = 'VIRTUAL GENERATED' in extra
                is_stored = 'STORED GENERATED' in extra

                if is_virtual or is_stored:
                    # 对于虚拟列，建议跳过或者生成简单的占位DDL
                    # 因为无法从information_schema获取完整的生成表达式
                    logger.warning(f"检测到虚拟列 {col_name}，无法生成完整的DDL，建议手动处理")
                    # 生成一个简单的占位DDL，用户需要手动补充表达式
                    storage_type = "VIRTUAL" if is_virtual else "STORED"
                    comment_str = f"COMMENT '{src_col['COLUMN_COMMENT']}'" if src_col['COLUMN_COMMENT'] else ""
                    ddl = f"-- 虚拟列 {col_name} 需要手动处理，类型: {src_col['COLUMN_TYPE']}, 存储: {storage_type}"
                    target_ddl_list.append(ddl)
                else:
                    # 处理普通列
                    null_str = "NOT NULL" if src_col['IS_NULLABLE'] == 'NO' else "NULL"

                    # 检查是否是TEXT/BLOB类型
                    column_type = src_col['COLUMN_TYPE'].upper()
                    is_text_blob = any(t in column_type for t in ['TEXT', 'BLOB'])

                    if is_text_blob:
                        # TEXT/BLOB类型字段需要手动处理，生成描述信息
                        comment_str = f"COMMENT '{src_col['COLUMN_COMMENT']}'" if src_col['COLUMN_COMMENT'] else ""
                        ddl = f"-- TEXT/BLOB类型字段 {col_name} 需要手动处理，类型: {src_col['COLUMN_TYPE']}, 允许NULL: {src_col['IS_NULLABLE'] == 'YES'}, {comment_str}"
                        target_ddl_list.append(ddl)
                    else:
                        # 处理普通列
                        # 处理默认值，特殊处理CURRENT_TIMESTAMP相关函数
                        default_str = ""
                        if src_col['COLUMN_DEFAULT'] is not None:
                            default_val = src_col['COLUMN_DEFAULT']
                            # 检查是否是CURRENT_TIMESTAMP相关函数
                            if default_val.startswith('CURRENT_TIMESTAMP') or default_val == 'NULL':
                                default_str = f"DEFAULT {default_val}"
                            else:
                                default_str = f"DEFAULT '{default_val}'"

                        # 处理EXTRA字段，移除DEFAULT_GENERATED等MySQL内部标记
                        extra_str = src_col['EXTRA'].replace('DEFAULT_GENERATED', '').strip()
                        comment_str = f"COMMENT '{src_col['COLUMN_COMMENT']}'" if src_col['COLUMN_COMMENT'] else ""

                        target_ddl_list.append(f"ALTER TABLE `{table_name}` ADD COLUMN `{col_name}` {src_col['COLUMN_TYPE']} {null_str} {default_str} {extra_str} {comment_str};")

                missing_columns.append(col_name)
            else:
                tgt_col = tgt_col_dict[col_name]
                # 对比类型或Null属性等 (这里只进行简单的比较类型即可，类型变更较重要)
                if src_col['COLUMN_TYPE'] != tgt_col['COLUMN_TYPE'] or src_col['IS_NULLABLE'] != tgt_col['IS_NULLABLE']:
                    # 检查是否是虚拟列（通过EXTRA字段判断）
                    extra = src_col['EXTRA'].upper()
                    is_virtual = 'VIRTUAL GENERATED' in extra
                    is_stored = 'STORED GENERATED' in extra

                    if is_virtual or is_stored:
                        # 对于虚拟列，建议跳过或者生成简单的占位DDL
                        logger.warning(f"检测到虚拟列 {col_name} 的变更，无法生成完整的DDL，建议手动处理")
                        storage_type = "VIRTUAL" if is_virtual else "STORED"
                        comment_str = f"COMMENT '{src_col['COLUMN_COMMENT']}'" if src_col['COLUMN_COMMENT'] else ""
                        ddl = f"-- 虚拟列 {col_name} 变更需要手动处理，类型: {src_col['COLUMN_TYPE']}, 存储: {storage_type}"
                        target_ddl_list.append(ddl)
                    else:
                        # 处理普通列
                        null_str = "NOT NULL" if src_col['IS_NULLABLE'] == 'NO' else "NULL"

                        # 检查是否是TEXT/BLOB类型
                        column_type = src_col['COLUMN_TYPE'].upper()
                        is_text_blob = any(t in column_type for t in ['TEXT', 'BLOB'])

                        if is_text_blob:
                            # TEXT/BLOB类型字段需要手动处理，生成描述信息
                            comment_str = f"COMMENT '{src_col['COLUMN_COMMENT']}'" if src_col['COLUMN_COMMENT'] else ""
                            ddl = f"-- TEXT/BLOB类型字段 {col_name} 变更需要手动处理，类型: {src_col['COLUMN_TYPE']}, 允许NULL: {src_col['IS_NULLABLE'] == 'YES'}, {comment_str}"
                            target_ddl_list.append(ddl)
                        else:
                            # 处理普通列
                            # 处理默认值，特殊处理CURRENT_TIMESTAMP相关函数
                            default_str = ""
                            if src_col['COLUMN_DEFAULT'] is not None:
                                default_val = src_col['COLUMN_DEFAULT']
                                # 检查是否是CURRENT_TIMESTAMP相关函数
                                if default_val.startswith('CURRENT_TIMESTAMP') or default_val == 'NULL':
                                    default_str = f"DEFAULT {default_val}"
                                else:
                                    default_str = f"DEFAULT '{default_val}'"

                            # 处理EXTRA字段，移除DEFAULT_GENERATED等MySQL内部标记
                            extra_str = src_col['EXTRA'].replace('DEFAULT_GENERATED', '').strip()
                            comment_str = f"COMMENT '{src_col['COLUMN_COMMENT']}'" if src_col['COLUMN_COMMENT'] else ""

                            target_ddl_list.append(f"ALTER TABLE `{table_name}` MODIFY COLUMN `{col_name}` {src_col['COLUMN_TYPE']} {null_str} {default_str} {extra_str} {comment_str};")

                    modified_columns.append(f"{col_name}({tgt_col['COLUMN_TYPE']} -> {src_col['COLUMN_TYPE']})")

        if missing_columns or modified_columns:
            diff_detail["missing_columns"] = missing_columns
            diff_detail["modified_columns"] = modified_columns
            diff_msg = []
            if missing_columns:
                diff_msg.append(f"缺失 {len(missing_columns)} 个字段")
            if modified_columns:
                diff_msg.append(f"有 {len(modified_columns)} 个字段类型变化")
            diff_detail['diff_msg'] = "，".join(diff_msg)
            return diff_detail, "\n".join(target_ddl_list)

        return None, None

    def compare_routine(self, obj_name: str, obj_type: str):
        """对比视图、函数、存储过程等结构"""
        # obj_type 可选 VIEW, PROCEDURE, FUNCTION
        show_cmd_map = {
            "VIEW": f"SHOW CREATE VIEW `{obj_name}`",
            "PROCEDURE": f"SHOW CREATE PROCEDURE `{obj_name}`",
            "FUNCTION": f"SHOW CREATE FUNCTION `{obj_name}`"
        }
        res_key_map = {
            "VIEW": "Create View",
            "PROCEDURE": "Create Procedure",
            "FUNCTION": "Create Function"
        }

        sql = show_cmd_map.get(obj_type)
        if not sql:
            return None, None

        try:
            src_res = self.source_db.fetch_one(sql)
            if not src_res:
                logger.info(f"源库未找到 {obj_type}: {obj_name}，跳过对比")
                return {"diff_msg": f"源库不存在{obj_type}: {obj_name}", "source_missing": True}, None
            src_def = src_res.get(res_key_map[obj_type])
        except Exception as e:
            # 源库不存在该对象，返回特殊标记
            logger.info(f"源库未找到 {obj_type}: {obj_name}，跳过对比")
            return {"diff_msg": f"源库不存在{obj_type}: {obj_name}", "source_missing": True}, None

        # 尝试获取目标库定义，如果不存在则为None
        tgt_def = None
        try:
            tgt_res = self.target_db.fetch_one(sql)
            if tgt_res:
                tgt_def = tgt_res.get(res_key_map[obj_type])
        except Exception:
            # 目标库对象不存在是正常情况，不记录错误日志
            tgt_def = None

        # 标准化后进行对比，去除空格、换行符等格式差异
        src_def_normalized = self._normalize_sql(src_def) if src_def else None
        tgt_def_normalized = self._normalize_sql(tgt_def) if tgt_def else None

        if src_def_normalized != tgt_def_normalized:
            diff_detail = {"diff_msg": f"目标库 {obj_type} 定义不存在或与源库不一致"}

            # 生成重建 DDL
            if obj_type == "VIEW":
                # VIEW 的替换，使用DROP + CREATE方式
                # 这样可以确保视图属性完全同步
                drop_ddl = f"DROP VIEW IF EXISTS `{obj_name}`;"
                create_ddl = src_def + ";"
                target_ddl = drop_ddl + "\n" + create_ddl
            else:
                target_ddl = f"DROP {obj_type} IF EXISTS `{obj_name}`;\nDELIMITER $\n{src_def}$\nDELIMITER ;"

            return diff_detail, target_ddl

        return None, None

    def _normalize_sql(self, sql: str) -> str:
        """标准化SQL语句，去除格式差异"""
        if not sql:
            return None

        # 去除首尾空格
        sql = sql.strip()

        # 统一换行符
        sql = sql.replace('\r\n', '\n').replace('\r', '\n')

        # 去除多余的空行
        lines = [line.strip() for line in sql.split('\n') if line.strip()]
        sql = '\n'.join(lines)

        # 去除多余的空格
        sql = ' '.join(sql.split())

        return sql
