"""
队列处理器 - Computer Tool核心组件
负责监听语音agent传递的用户指令队列，并协调浏览器操作任务的执行
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from queue import Queue, Empty
import threading

from .task_executor import TaskExecutor
from .status_reporter import StatusReporter

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QueueProcessor:
    """队列处理器 - 监听queue1中的语音指令并执行相应的浏览器操作"""
    
    def __init__(self, 
                 input_queue: Queue, 
                 output_queue: Optional[Queue] = None,
                 test_url: str = "https://www.baidu.com"):
        """
        初始化队列处理器
        
        Args:
            input_queue: 来自语音agent的指令队列 (queue1)
            output_queue: 输出状态的队列 (可选)
            test_url: 默认测试网址
        """
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.test_url = test_url
        
        # 初始化核心组件
        self.task_executor = TaskExecutor(test_url=test_url)
        self.status_reporter = StatusReporter(output_queue=output_queue)
        
        # 控制标志
        self.is_running = False
        self.current_task = None
        
        logger.info("队列处理器初始化完成")
    
    async def start_processing(self):
        """启动队列处理循环"""
        self.is_running = True
        logger.info("开始监听语音指令队列...")
        
        await self.status_reporter.report_status({
            "type": "system",
            "status": "started",
            "message": "Computer Tool已启动，等待语音指令...",
            "timestamp": datetime.now().isoformat()
        })
        
        while self.is_running:
            try:
                # 监听队列中的新指令
                await self._process_queue_messages()
                
                # 短暂休眠，避免过度消耗CPU
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"队列处理出错: {e}")
                await self.status_reporter.report_error("队列处理异常", str(e))
                await asyncio.sleep(1)  # 错误后稍长时间休眠
    
    async def _process_queue_messages(self):
        """处理队列中的消息"""
        try:
            # 非阻塞方式获取队列消息
            message = self.input_queue.get_nowait()
            
            logger.info(f"收到语音指令: {message}")
            
            # 解析消息
            parsed_message = self._parse_message(message)
            
            if parsed_message:
                await self._handle_user_command(parsed_message)
            
            # 标记任务完成
            self.input_queue.task_done()
            
        except Empty:
            # 队列为空，继续监听
            pass
        except Exception as e:
            logger.error(f"消息处理错误: {e}")
            await self.status_reporter.report_error("消息处理失败", str(e))
    
    def _parse_message(self, message: Any) -> Optional[Dict[str, Any]]:
        """解析来自语音agent的消息"""
        try:
            if isinstance(message, str):
                # 简单文本指令
                return {
                    "type": "voice_command",
                    "content": message,
                    "timestamp": datetime.now().isoformat()
                }
            elif isinstance(message, dict):
                # 结构化消息
                return message
            else:
                logger.warning(f"无法识别的消息格式: {type(message)}")
                return None
                
        except Exception as e:
            logger.error(f"消息解析错误: {e}")
            return None
    
    async def _handle_user_command(self, command: Dict[str, Any]):
        """处理用户语音指令"""
        try:
            # 报告开始处理
            await self.status_reporter.report_status({
                "type": "task_started",
                "command": command.get("content", ""),
                "message": "开始执行浏览器操作...",
                "timestamp": datetime.now().isoformat()
            })
            
            # 提取指令内容
            user_instruction = command.get("content", "")
            
            if not user_instruction.strip():
                await self.status_reporter.report_error("空指令", "收到的语音指令为空")
                return
            
            # 设置当前任务
            self.current_task = {
                "instruction": user_instruction,
                "start_time": datetime.now(),
                "status": "executing"
            }
            
            # 执行浏览器操作任务
            result = await self.task_executor.execute_task(
                task_description=user_instruction,
                progress_callback=self._on_task_progress
            )
            
            # 处理执行结果
            if result.get("success", False):
                await self.status_reporter.report_success({
                    "instruction": user_instruction,
                    "result": result.get("result", ""),
                    "duration": self._get_task_duration(),
                    "message": "浏览器操作执行成功！"
                })
            else:
                await self.status_reporter.report_error(
                    "浏览器操作失败", 
                    result.get("error", "未知错误")
                )
            
            # 清理当前任务
            self.current_task = None
            
        except Exception as e:
            logger.error(f"指令处理异常: {e}")
            await self.status_reporter.report_error("指令执行异常", str(e))
            self.current_task = None
    
    async def _on_task_progress(self, progress_info: Dict[str, Any]):
        """任务进度回调函数"""
        await self.status_reporter.report_progress(progress_info)
    
    def _get_task_duration(self) -> float:
        """计算当前任务执行时长（秒）"""
        if self.current_task and self.current_task.get("start_time"):
            duration = datetime.now() - self.current_task["start_time"]
            return duration.total_seconds()
        return 0.0
    
    async def stop_processing(self):
        """停止队列处理"""
        self.is_running = False
        
        # 如果有正在执行的任务，尝试停止
        if self.current_task:
            logger.info("正在停止当前任务...")
            await self.task_executor.stop_current_task()
        
        await self.status_reporter.report_status({
            "type": "system",
            "status": "stopped",
            "message": "Computer Tool已停止",
            "timestamp": datetime.now().isoformat()
        })
        
        logger.info("队列处理器已停止")
    
    def get_status(self) -> Dict[str, Any]:
        """获取当前状态信息"""
        return {
            "is_running": self.is_running,
            "current_task": self.current_task,
            "queue_size": self.input_queue.qsize(),
            "test_url": self.test_url,
            "timestamp": datetime.now().isoformat()
        }


def create_queue_processor(queue1: Queue, 
                          output_queue: Optional[Queue] = None,
                          test_url: str = "https://www.baidu.com") -> QueueProcessor:
    """工厂函数：创建队列处理器实例"""
    return QueueProcessor(
        input_queue=queue1,
        output_queue=output_queue,
        test_url=test_url
    )


# 示例使用
if __name__ == "__main__":
    import queue
    
    async def demo():
        # 创建测试队列
        test_queue = queue.Queue()
        
        # 创建处理器
        processor = create_queue_processor(test_queue)
        
        # 模拟添加语音指令
        test_queue.put("打开测试网站")
        test_queue.put("在搜索框中输入'Python教程'")
        test_queue.put("点击搜索按钮")
        
        # 启动处理
        try:
            await processor.start_processing()
        except KeyboardInterrupt:
            await processor.stop_processing()
    
    # 运行演示
    asyncio.run(demo())