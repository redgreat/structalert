# structalert

壹好车服数据库架构变更预警与数据同步系统

## 项目简介

structalert 是一个数据库结构监控和数据同步工具，主要用于：

1. **结构对比**：每日自动检测源库和目标库的表结构差异，及时发现架构变更
2. **预警通知**：通过企业微信机器人发送结构变更预警消息
3. **数据同步**：支持全量和增量数据同步，将源库数据迁移到历史库

## 核心功能

### 1. 数据库结构对比

- 支持对比 TABLE、VIEW、PROCEDURE、FUNCTION 等数据库对象
- 自动检测字段类型、索引、约束等结构差异
- 生成目标库修复 DDL 语句
- 记录差异日志到数据库

### 2. 企业微信预警

- 发送模板卡片消息到企业微信群
- 包含差异详情、统计信息、处理建议
- 支持一键跳转到差异记录

### 3. 数据同步

- **全量同步**：首次运行时同步所有数据
- **增量同步**：按日期字段筛选，只同步指定时间范围的数据
- **并发写入**：多线程批量写入，提高同步效率
- **删除检测**：自动检测并清理源库已删除的数据
- **试运行模式**：支持 dry-run，验证逻辑不实际执行

## 技术架构

```
structalert/
├── structalert/           # 核心代码
│   ├── __main__.py        # 命令行入口
│   ├── database.py        # 数据库连接管理
│   ├── comparator.py      # 结构对比逻辑
│   ├── sync_module.py     # 数据同步模块
│   ├── alert_wecom.py     # 企业微信通知
│   ├── tasks.py           # 定时任务定义
│   ├── scheduler.py       # 调度器
│   └── docker_scheduler.py # Docker调度器
├── config/                # 配置文件
│   ├── config.yml         # 主配置文件
│   └── config.yml.example # 配置示例
├── scripts/               # 脚本
│   ├── init_structalert.sql  # 初始化SQL
│   └── add_date_column_migration.sql  # 增量同步迁移脚本
├── logs/                  # 日志目录
└── docker-compose-local.yml  # Docker编排文件
```

## 快速开始

### 1. 环境要求

- Python 3.8+
- MySQL 5.7+
- Docker (可选)

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置文件

复制配置示例并修改：

```bash
cp config/config.yml.example config/config.yml
```

编辑 `config/config.yml`，配置数据库连接：

```yaml
databases:
  source:
    host: "源库地址"
    port: 3306
    user: "用户名"
    password: "密码"
    database: "serviceordercenter"
  his:
    host: "历史库地址"
    port: 3306
    user: "用户名"
    password: "密码"
    database: "serviceordercenterhis"
  cfg:
    host: "配置库地址"
    port: 3306
    user: "用户名"
    password: "密码"
    database: "serviceordercenter"

wecom:
  webhook_key: "企业微信机器人key"
```

### 4. 初始化数据库

执行初始化脚本创建配置表：

```bash
mysql -u root -p < scripts/init_structalert.sql
```

### 5. 运行方式

#### 方式一：命令行运行

```bash
# 验证配置文件
python -m structalert validate-config -c config/config.yml

# 启动调度器（定时任务）
python -m structalert run-scheduler -c config/config.yml

# 手动执行一次对比和同步
python -m structalert compare-now -c config/config.yml
```

#### 方式二：Docker运行

```bash
# 构建镜像
docker-compose -f docker-compose-local.yml build

# 启动服务
docker-compose -f docker-compose-local.yml up -d

# 查看日志
docker-compose -f docker-compose-local.yml logs -f
```

## 配置说明

### 数据同步配置

```yaml
sync:
  # 增量同步：同步多少天前的数据（从今天开始计算）
  # 例如：days_before: 30 表示同步30天前的那一周的数据（7天时间窗口）
  # 设置为 null 或删除此配置项表示全量同步
  days_before: null

  # 批量写入大小：每次批量INSERT/UPDATE的记录数
  # 值越大，性能越好，但内存消耗也越大
  batch_size: 500

  # 并发线程数：数据写入的并发工作线程数
  # 建议设置为2-4，过大会增加数据库压力
  concurrency: 2

  # 删除批量大小：批量删除废弃数据时每批的记录数
  # 用于清理源库已删除但目标库仍存在的数据
  delete_batch_size: 1000

  # 试运行模式：true表示只模拟执行不实际写入数据，false表示实际执行
  # 建议首次运行时设置为true，验证无误后再设置为false
  dry_run: true
```

### 定时任务配置

```yaml
schedule_set:
  daily_struct_compare:
    enabled: true
    schedule: "0 2 * * *"  # 每天凌晨2点执行结构对比
    module: "structalert.tasks"
    function: "run_daily_comparison"
  weekly_data_sync:
    enabled: true
    schedule: "0 3 * * 0"  # 每周日凌晨3点执行数据同步
    module: "structalert.tasks"
    function: "run_weekly_sync"
```

## 增量同步配置

### 1. 为表配置日期字段

在 `cfg_compare_objects` 表中设置 `date_column` 字段：

```sql
-- 为需要增量同步的表设置日期字段
UPDATE cfg_compare_objects 
SET date_column = 'create_time' 
WHERE object_name = 'your_table_name' AND need_sync = 1;

-- 全量同步的表保持 date_column 为 NULL
UPDATE cfg_compare_objects 
SET date_column = NULL 
WHERE object_name = 'config_table';
```

### 2. 配置同步参数

```yaml
sync:
  days_before: 30  # 同步30天前的一周数据
```

### 3. 工作原理

假设今天是 2024-04-03，配置 `days_before: 30`：

- 计算日期范围：
  - `end_date = 2024-04-03 - 30天 = 2024-03-04`
  - `start_date = 2024-03-04 - 7天 = 2024-02-25`
- 同步范围：`2024-02-25 <= create_time < 2024-03-04`

这样每次周同步任务运行时，都会同步一周的数据窗口，逐步完成历史数据迁移。

详细说明请参考：[增量同步使用指南](docs/incremental_sync_guide.md)

## 日志说明

程序运行后会在 `logs` 目录生成以下日志文件：

```
logs/
├── structalert.log          # 所有日志（DEBUG及以上）
├── structalert.log.2024-04-03.zip  # 历史日志（自动压缩）
├── error.log                # 错误日志（ERROR及以上）
└── error.log.2024-04-03     # 历史错误日志
```

日志特性：
- 每天自动轮转
- 保留30天历史日志
- 自动压缩归档
- UTF-8编码

## 数据库表说明

### cfg_compare_objects（配置对比对象表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | 主键ID |
| object_name | varchar(200) | 对象名称（表名、视图名等） |
| object_type | varchar(20) | 对象类型（TABLE, VIEW, PROCEDURE, FUNCTION） |
| is_active | tinyint | 是否开启对比（1是，0否） |
| need_sync | tinyint | 是否需要同步数据（1是，0否） |
| date_column | varchar(100) | 增量同步的日期字段名，NULL表示全量同步 |
| create_time | datetime | 创建时间 |
| update_time | datetime | 更新时间 |

### cfg_compare_diff（差异记录表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | 主键ID |
| compare_date | date | 比对所属日期 |
| object_name | varchar(200) | 存在差异的对象名 |
| object_type | varchar(20) | 对象类型 |
| diff_detail | json | 差异详情（JSON格式） |
| target_ddl | text | 待执行的目标库修复DDL |
| status | varchar(20) | 处理状态（PENDING, RESOLVED, IGNORED） |
| create_time | datetime | 创建时间 |
| update_time | datetime | 更新时间 |

## 常见问题

### 1. 日志文件没有生成？

检查以下几点：
- logs 目录是否有写入权限
- 配置文件中的日志目录配置是否正确
- 程序是否正常启动（查看控制台输出）

### 2. 数据同步失败？

常见原因：
- 表结构不一致：先运行结构对比，修复差异后再同步
- 外键约束：程序会自动禁用外键检查
- 主键缺失：无主键表只能全量同步，无法检测删除

### 3. 增量同步数据量异常？

检查：
- `date_column` 配置是否正确
- 日期字段是否有索引
- 查看日志中的日期范围信息

### 4. 企业微信通知发送失败？

检查：
- webhook_key 是否正确
- 网络是否能访问企业微信API
- 消息内容是否超过限制

## 开发说明

### 项目依赖

主要依赖包：
- `pymysql`：MySQL数据库驱动
- `loguru`：日志库
- `pyyaml`：YAML配置解析
- `apscheduler`：定时任务调度
- `requests`：HTTP请求（企业微信通知）

### 扩展开发

#### 添加新的对比对象类型

1. 在 `comparator.py` 中添加对比方法
2. 在 `tasks.py` 中调用新方法
3. 更新配置表支持新类型

#### 自定义通知渠道

1. 创建新的通知类（参考 `alert_wecom.py`）
2. 在 `tasks.py` 中调用新通知方法

## 许可证

内部项目，仅供壹好车服团队使用。

## 联系方式

如有问题，请联系开发团队。
