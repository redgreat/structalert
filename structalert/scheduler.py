import yaml
import os
import sys
import importlib
import asyncio
from typing import Dict, Any, Callable
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR, EVENT_JOB_MISSED
from loguru import logger


class DockerScheduler:
    """Docker常驻任务调度器，专门用于根据配置文件自动调度任务"""
    
    def __init__(self, config_path: str = None):
        self.config_path = config_path or os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'config.yaml')
        self.scheduler = None
        self.task_registry = {}
        self.config = {}
        self._load_config()
        self._setup_scheduler()
    
    def _load_config(self):
        """加载配置文件"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
            logger.info(f"配置文件加载成功: {self.config_path}")
        except Exception as e:
            logger.error(f"配置文件加载失败: {e}")
            self.config = {}
    
    def _setup_scheduler(self):
        """设置调度器"""
        self.scheduler = BackgroundScheduler(
            executors={'default': ThreadPoolExecutor(max_workers=10)},
            job_defaults={
                'coalesce': True,
                'max_instances': 1,
                'misfire_grace_time': 30
            }
        )
        
        self.scheduler.add_listener(self._job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR | EVENT_JOB_MISSED)
    
    def register_task(self, task_name: str, task_func: Callable):
        """注册任务函数"""
        self.task_registry[task_name] = task_func
        logger.info(f"任务已注册: {task_name}")
    
    def _parse_cron_schedule(self, schedule_str: str) -> Dict[str, Any]:
        """解析cron表达式为APScheduler格式"""
        parts = schedule_str.split()
        if len(parts) != 5:
            raise ValueError(f"无效的cron表达式: {schedule_str}")
        
        minute, hour, day, month, day_of_week = parts
        
        cron_config = {}
        if minute != '*':
            cron_config['minute'] = minute
        if hour != '*':
            cron_config['hour'] = hour
        if day != '*':
            cron_config['day'] = day
        if month != '*':
            cron_config['month'] = month
        if day_of_week != '*':
            cron_config['day_of_week'] = day_of_week
        
        return cron_config
    
    def _import_task_function(self, module_path: str, function_name: str) -> Callable:
        """动态导入任务函数"""
        try:
            # 添加项目根目录到sys.path
            project_root = os.path.dirname(os.path.dirname(__file__))
            if project_root not in sys.path:
                sys.path.insert(0, project_root)
            
            module = importlib.import_module(module_path)
            func = getattr(module, function_name)
            
            # 如果是异步函数，包装为同步函数
            if asyncio.iscoroutinefunction(func):
                def sync_wrapper(*args, **kwargs):
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        return loop.run_until_complete(func(*args, **kwargs))
                    finally:
                        loop.close()
                return sync_wrapper
            
            return func
        except Exception as e:
            logger.error(f"导入任务函数失败: {module_path}.{function_name}, 错误: {e}")
            return None
    
    def load_scheduled_tasks(self):
        """从配置文件加载定时任务"""
        schedule_set = self.config.get('schedule_set', {})
        
        for task_name, task_config in schedule_set.items():
            if not task_config.get('enabled', False):
                logger.info(f"任务已禁用，跳过: {task_name}")
                continue
            
            schedule = task_config.get('schedule')
            if not schedule:
                logger.warning(f"任务缺少调度配置，跳过: {task_name}")
                continue
            
            # 尝试从配置中获取模块和函数信息
            module_path = task_config.get('module')
            function_name = task_config.get('function', 'main')
            
            task_func = None
            
            # 如果配置中指定了模块路径，则动态导入
            if module_path:
                task_func = self._import_task_function(module_path, function_name)
            # 否则检查是否已手动注册
            elif task_name in self.task_registry:
                task_func = self.task_registry[task_name]
            
            if not task_func:
                logger.warning(f"任务函数未找到，跳过: {task_name}")
                continue
            
            try:
                cron_config = self._parse_cron_schedule(schedule)
                
                self.scheduler.add_job(
                    func=task_func,
                    trigger='cron',
                    id=task_name,
                    name=f"定时任务-{task_name}",
                    **cron_config
                )
                
                logger.info(f"定时任务已添加: {task_name}, 调度: {schedule}")
                
            except Exception as e:
                logger.error(f"添加定时任务失败: {task_name}, 错误: {e}")
    
    def start(self):
        """启动调度器"""
        try:
            self.load_scheduled_tasks()
            self.scheduler.start()
            logger.info("Docker调度器已启动")
        except Exception as e:
            logger.error(f"启动调度器失败: {e}")
            raise e
    
    def stop(self):
        """停止调度器"""
        try:
            if self.scheduler and self.scheduler.running:
                self.scheduler.shutdown(wait=True)
                logger.info("Docker调度器已停止")
        except Exception as e:
            logger.error(f"停止调度器失败: {e}")
    
    def _job_listener(self, event):
        """作业事件监听器"""
        job_id = event.job_id
        
        if event.code == EVENT_JOB_EXECUTED:
            logger.info(f"定时任务执行完成: {job_id}")
        elif event.code == EVENT_JOB_ERROR:
            logger.error(f"定时任务执行出错: {job_id}, 错误: {event.exception}")
        elif event.code == EVENT_JOB_MISSED:
            logger.warning(f"定时任务错过执行: {job_id}")
    
    def get_job_status(self):
        """获取所有任务状态"""
        jobs = self.scheduler.get_jobs()
        return [
            {
                "id": job.id,
                "name": job.name,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger)
            }
            for job in jobs
        ]
    
    def reload_config(self):
        """重新加载配置"""
        logger.info("重新加载配置文件...")
        self._load_config()
        
        for job in self.scheduler.get_jobs():
            self.scheduler.remove_job(job.id)
        
        self.load_scheduled_tasks()
        logger.info("配置重新加载完成")


def create_docker_scheduler(config_path: str = None) -> DockerScheduler:
    """创建Docker调度器实例"""
    return DockerScheduler(config_path)