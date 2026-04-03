import argparse
import sys
import yaml
import os
from pathlib import Path
from loguru import logger
from .docker_scheduler import DockerScheduler
from .tasks import run_daily_comparison, run_manual_sync_with_compare

def setup_logging(config_path=None):
    """设置日志配置"""
    # 移除默认的logger配置
    logger.remove()
    
    # 添加控制台输出（带颜色）
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO"
    )
    
    # 确定日志目录
    if config_path and os.path.exists(config_path):
        # 从配置文件读取日志目录
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            log_dir_config = config.get('logging', {}).get('directory', './logs')
            
            # 如果是相对路径，相对于配置文件所在目录
            if not os.path.isabs(log_dir_config):
                config_dir = os.path.dirname(os.path.abspath(config_path))
                log_dir = os.path.join(config_dir, log_dir_config)
            else:
                log_dir = log_dir_config
        except:
            # 默认使用当前目录下的logs
            log_dir = os.path.join(os.getcwd(), 'logs')
    else:
        # 默认使用当前目录下的logs
        log_dir = os.path.join(os.getcwd(), 'logs')
    
    # 创建日志目录
    os.makedirs(log_dir, exist_ok=True)
    
    # 添加文件输出 - 所有日志
    logger.add(
        os.path.join(log_dir, 'structalert.log'),
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG",
        rotation="1 day",
        retention="30 days",
        compression="zip",
        encoding="utf-8"
    )
    
    # 添加文件输出 - 错误日志
    logger.add(
        os.path.join(log_dir, 'error.log'),
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="ERROR",
        rotation="1 day",
        retention="30 days",
        encoding="utf-8"
    )
    
    logger.info(f"日志配置完成，日志目录: {log_dir}")

def validate_config(config_path):
    """验证配置文件是否有效"""
    # 先配置日志
    setup_logging(config_path)
    
    if not os.path.exists(config_path):
        logger.error(f"配置文件未找到: {config_path}")
        sys.exit(1)
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # 简单校验关键字段
        required_sections = ['databases', 'wecom', 'schedule_set']
        for section in required_sections:
            if section not in config:
                logger.error(f"配置文件缺失必要部分: {section}")
                sys.exit(1)
        
        logger.info(f"✅ 配置文件验证成功: {config_path}")
        return config
    except Exception as e:
        logger.error(f"配置文件解析失败: {e}")
        sys.exit(1)

def run_scheduler(config_path):
    """启动调度器任务"""
    # 先配置日志
    setup_logging(config_path)
    
    validate_config(config_path)
    logger.info("🚀 正在启动 structalert 调度器...")
    scheduler = DockerScheduler(config_path)
    try:
        scheduler.start()
        # 保持主进程运行
        import time
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        scheduler.stop()
        logger.info("👋 调度器已安全停止")

def run_compare_now(config_path):
    """立即执行一次对比和数据迁移任务"""
    # 先配置日志
    setup_logging(config_path)
    
    # 这里我们设置环境变量让 tasks 知道配置路径
    os.environ["CONFIG_PATH"] = config_path
    logger.info("⚡ 正在手动触发结构对比和数据迁移任务...")
    run_manual_sync_with_compare()
    logger.info("✅ 手动对比和数据迁移任务执行完成")

def main():
    parser = argparse.ArgumentParser(description="structalert 命令行工具")
    parser.add_argument('command', choices=['validate-config', 'run-scheduler', 'compare-now'], 
                        help='执行命令 (validate-config, run-scheduler 或 compare-now)')
    parser.add_argument('--config', '-c', type=str, required=True, help='配置文件路径')
    
    args = parser.parse_args()
    
    if args.command == 'validate-config':
        validate_config(args.config)
    elif args.command == 'run-scheduler':
        run_scheduler(args.config)
    elif args.command == 'compare-now':
        run_compare_now(args.config)

if __name__ == '__main__':
    main()
