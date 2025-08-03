"""
Computer Tool - 基于Browser-Use框架的浏览器自动化工具

核心组件：
- QueueProcessor: 队列处理器，监听语音指令
- TaskExecutor: 任务执行器，协调浏览器操作
- BrowserAgent: Browser-Use代理封装
- StatusReporter: 状态报告器，输出操作状态
- WebLauncher: 网页启动器，管理测试网址
"""

from .queue_processor import QueueProcessor, create_queue_processor
from .task_executor import TaskExecutor, create_task_executor
from .browser_agent import BrowserAgent, create_browser_agent
from .status_reporter import StatusReporter, create_status_reporter
from .web_launcher import WebLauncher, create_web_launcher

__version__ = "1.0.0"
__author__ = "Computer Tool Team"

# 导出主要类和工厂函数
__all__ = [
    # 核心类
    "QueueProcessor",
    "TaskExecutor", 
    "BrowserAgent",
    "StatusReporter",
    "WebLauncher",
    
    # 工厂函数
    "create_queue_processor",
    "create_task_executor",
    "create_browser_agent", 
    "create_status_reporter",
    "create_web_launcher"
]