#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Docker调度器启动脚本
用于在Docker容器中启动调度器并保持运行
"""

import sys
import os
import signal
import time
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from .scheduler import DockerScheduler
from loguru import logger

class DockerSchedulerApp:
    """Docker调度器应用程序"""
    
    def __init__(self):
        self.scheduler = None
        self.running = False
        
    def setup_logging(self):
        """设置日志配置 - 已在__main__.py中统一配置，这里保留兼容性"""
        # 日志配置已在 __main__.py 的 setup_logging() 中完成
        # 这里保留方法以保持兼容性，但不重复配置
        logger.info("日志配置已由主程序完成")
        pass
    
    def signal_handler(self, signum, frame):
        """信号处理器"""
        logger.info(f"接收到信号 {signum}，正在关闭调度器...")
        self.stop()
    
    def start(self):
        """启动调度器"""
        try:
            self.setup_logging()
            logger.info("=" * 50)
            logger.info("Docker调度器启动中...")
            logger.info("=" * 50)
            
            # 注册信号处理器
            signal.signal(signal.SIGINT, self.signal_handler)
            signal.signal(signal.SIGTERM, self.signal_handler)
            
            # 创建调度器实例
            config_path = project_root / "config" / "config.yaml"
            self.scheduler = DockerScheduler(str(config_path))
            
            # 启动调度器
            self.scheduler.start()
            self.running = True
            
            logger.info("调度器启动成功，等待任务执行...")
            
            # 打印任务状态
            self.print_job_status()
            
            # 保持运行
            while self.running:
                time.sleep(10)
                
        except Exception as e:
            logger.error(f"启动调度器失败: {e}")
            sys.exit(1)
    
    def stop(self):
        """停止调度器"""
        self.running = False
        if self.scheduler:
            self.scheduler.stop()
        logger.info("调度器已停止")
    
    def print_job_status(self):
        """打印任务状态"""
        if self.scheduler:
            jobs = self.scheduler.get_job_status()
            if jobs:
                logger.info("当前调度任务:")
                for job in jobs:
                    logger.info(f"  - {job['name']} (ID: {job['id']})")
                    logger.info(f"    下次执行: {job['next_run_time']}")
                    logger.info(f"    触发器: {job['trigger']}")
            else:
                logger.warning("没有找到任何调度任务")

def main():
    """主函数"""
    app = DockerSchedulerApp()
    app.start()

if __name__ == '__main__':
    main()