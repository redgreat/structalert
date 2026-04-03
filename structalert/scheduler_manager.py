#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调度器管理脚本
用于查看任务状态、执行日志等信息
"""

import sys
import os
import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from .scheduler import DockerScheduler
from loguru import logger

class SchedulerManager:
    """调度器管理器"""
    
    def __init__(self, config_path: str = None):
        if not config_path:
            config_path = project_root / "config" / "config.yaml"
        self.scheduler = DockerScheduler(str(config_path))
        self.log_dir = project_root / "logs"
    
    def show_status(self):
        """显示调度器状态"""
        print("\n" + "=" * 60)
        print("调度器状态信息")
        print("=" * 60)
        
        try:
            # 检查调度器是否运行
            if self.scheduler.scheduler.running:
                print("📊 调度器状态: 运行中")
            else:
                print("📊 调度器状态: 已停止")
            
            # 获取任务列表
            jobs = self.scheduler.get_job_status()
            
            if jobs:
                print(f"\n📋 已注册任务数量: {len(jobs)}")
                print("\n任务详情:")
                print("-" * 60)
                
                for i, job in enumerate(jobs, 1):
                    print(f"{i}. 任务名称: {job['name']}")
                    print(f"   任务ID: {job['id']}")
                    print(f"   下次执行: {job['next_run_time']}")
                    print(f"   触发器: {job['trigger']}")
                    print(f"   状态: {'启用' if job.get('enabled', True) else '禁用'}")
                    print("-" * 40)
            else:
                print("\n⚠️  没有找到任何调度任务")
                
        except Exception as e:
            print(f"❌ 获取状态失败: {e}")
    
    def show_logs(self, lines: int = 50, log_type: str = "all"):
        """显示日志信息"""
        print("\n" + "=" * 60)
        print(f"最近 {lines} 行日志 ({log_type})")
        print("=" * 60)
        
        try:
            if log_type == "error":
                log_file = self.log_dir / "scheduler_error.log"
            else:
                log_file = self.log_dir / "scheduler.log"
            
            if not log_file.exists():
                print(f"❌ 日志文件不存在: {log_file}")
                return
            
            # 读取最后N行
            with open(log_file, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
                recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
            
            if recent_lines:
                for line in recent_lines:
                    print(line.rstrip())
            else:
                print("📝 日志文件为空")
                
        except Exception as e:
            print(f"❌ 读取日志失败: {e}")
    
    def show_config(self):
        """显示配置信息"""
        print("\n" + "=" * 60)
        print("调度器配置信息")
        print("=" * 60)
        
        try:
            config = self.scheduler.config
            schedule_set = config.get('schedule_set', {})
            
            print(f"📁 配置文件路径: {self.scheduler.config_path}")
            print(f"📋 配置的任务数量: {len(schedule_set)}")
            
            if schedule_set:
                print("\n任务配置详情:")
                print("-" * 60)
                
                for task_name, task_config in schedule_set.items():
                    print(f"任务名称: {task_name}")
                    print(f"  启用状态: {'是' if task_config.get('enabled', False) else '否'}")
                    print(f"  调度表达式: {task_config.get('schedule', 'N/A')}")
                    print(f"  模块路径: {task_config.get('module', 'N/A')}")
                    print(f"  函数名称: {task_config.get('function', 'N/A')}")
                    print("-" * 40)
            else:
                print("\n⚠️  没有配置任何任务")
                
        except Exception as e:
            print(f"❌ 读取配置失败: {e}")
    
    def reload_config(self):
        """重新加载配置"""
        print("\n🔄 重新加载配置...")
        
        try:
            self.scheduler.reload_config()
            print("✅ 配置重新加载成功")
            self.show_status()
        except Exception as e:
            print(f"❌ 重新加载配置失败: {e}")
    
    def export_status(self, output_file: str = None):
        """导出状态信息到JSON文件"""
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"scheduler_status_{timestamp}.json"
        
        try:
            status_data = {
                "timestamp": datetime.now().isoformat(),
                "scheduler_running": self.scheduler.scheduler.running,
                "jobs": self.scheduler.get_job_status(),
                "config": self.scheduler.config
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(status_data, f, ensure_ascii=False, indent=2, default=str)
            
            print(f"✅ 状态信息已导出到: {output_file}")
            
        except Exception as e:
            print(f"❌ 导出状态失败: {e}")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="调度器管理工具")
    parser.add_argument('command', choices=['status', 'logs', 'config', 'reload', 'export'],
                       help='执行的命令')
    parser.add_argument('--lines', '-n', type=int, default=50,
                       help='显示日志行数 (默认: 50)')
    parser.add_argument('--log-type', choices=['all', 'error'], default='all',
                       help='日志类型 (默认: all)')
    parser.add_argument('--output', '-o', type=str,
                       help='导出文件路径')
    parser.add_argument('--config', '-c', type=str,
                       help='配置文件路径')
    
    args = parser.parse_args()
    
    try:
        manager = SchedulerManager(args.config)
        
        if args.command == 'status':
            manager.show_status()
        elif args.command == 'logs':
            manager.show_logs(args.lines, args.log_type)
        elif args.command == 'config':
            manager.show_config()
        elif args.command == 'reload':
            manager.reload_config()
        elif args.command == 'export':
            manager.export_status(args.output)
            
    except KeyboardInterrupt:
        print("\n👋 操作已取消")
    except Exception as e:
        print(f"❌ 执行失败: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()