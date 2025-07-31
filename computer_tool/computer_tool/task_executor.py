"""
任务执行器 - Computer Tool核心组件
基于Browser-Use框架执行浏览器自动化任务
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Callable
import os
from dotenv import load_dotenv

from .browser_agent import BrowserAgent
from .web_launcher import WebLauncher

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TaskExecutor:
    """任务执行器 - 协调Browser-Use代理执行浏览器操作"""
    
    def __init__(self, test_url: str = "https://www.baidu.com"):
        """
        初始化任务执行器
        
        Args:
            test_url: 默认测试网址
        """
        self.test_url = test_url
        self.browser_agent = None
        self.web_launcher = WebLauncher()
        self.current_task = None
        self.is_task_running = False
        
        logger.info(f"任务执行器初始化完成，默认测试网址: {test_url}")
    
    async def execute_task(self, 
                          task_description: str,
                          target_url: Optional[str] = None,
                          progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        执行浏览器自动化任务
        
        Args:
            task_description: 用户的自然语言任务描述
            target_url: 目标网址（可选，默认使用test_url）
            progress_callback: 进度回调函数
            
        Returns:
            任务执行结果
        """
        try:
            self.is_task_running = True
            self.current_task = {
                "description": task_description,
                "start_time": datetime.now(),
                "status": "preparing"
            }
            
            logger.info(f"开始执行任务: {task_description}")
            
            # 回调进度：任务开始
            if progress_callback:
                await progress_callback({
                    "stage": "preparing",
                    "message": "正在准备浏览器环境...",
                    "progress": 10
                })
            
            # 1. 初始化Browser-Use代理
            if not self.browser_agent:
                self.browser_agent = await self._initialize_browser_agent()
            
            # 回调进度：代理准备完成
            if progress_callback:
                await progress_callback({
                    "stage": "agent_ready",
                    "message": "浏览器代理已准备就绪...",
                    "progress": 30
                })
            
            # 2. 确定目标网址
            final_url = target_url or self.test_url
            
            # 3. 构建完整任务描述（包含网址信息）
            full_task = self._build_full_task_description(task_description, final_url)
            
            # 回调进度：开始执行
            if progress_callback:
                await progress_callback({
                    "stage": "executing",
                    "message": f"正在执行浏览器操作: {task_description}",
                    "progress": 50
                })
            
            # 4. 执行Browser-Use任务
            self.current_task["status"] = "executing"
            result = await self.browser_agent.execute_web_task(full_task)
            
            # 5. 处理执行结果
            if result.get("success", False):
                self.current_task["status"] = "completed"
                
                # 回调进度：任务完成
                if progress_callback:
                    await progress_callback({
                        "stage": "completed",
                        "message": "浏览器操作执行完成！",
                        "progress": 100
                    })
                
                logger.info(f"任务执行成功: {task_description}")
                
                return {
                    "success": True,
                    "result": result.get("result", ""),
                    "message": "任务执行成功",
                    "duration": self._get_task_duration(),
                    "url": final_url,
                    "task_description": task_description
                }
            else:
                self.current_task["status"] = "failed"
                error_msg = result.get("error", "未知错误")
                
                logger.error(f"任务执行失败: {error_msg}")
                
                return {
                    "success": False,
                    "error": error_msg,
                    "message": "任务执行失败",
                    "duration": self._get_task_duration(),
                    "url": final_url,
                    "task_description": task_description
                }
                
        except Exception as e:
            self.current_task["status"] = "error" if self.current_task else "error"
            error_msg = f"任务执行异常: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            # 回调进度：错误
            if progress_callback:
                await progress_callback({
                    "stage": "error",
                    "message": f"执行出错: {str(e)}",
                    "progress": 0
                })
            
            return {
                "success": False,
                "error": error_msg,
                "message": "任务执行异常",
                "duration": self._get_task_duration(),
                "task_description": task_description
            }
        finally:
            self.is_task_running = False
    
    async def _initialize_browser_agent(self) -> BrowserAgent:
        """初始化Browser-Use代理"""
        try:
            # 获取API密钥
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("未找到OPENAI_API_KEY环境变量，请检查.env文件配置")
            
            # 创建Browser-Use代理
            agent = BrowserAgent(
                api_key=api_key,
                model="gpt-4o-mini",  # 默认使用性价比高的模型
                temperature=0.7
            )
            
            logger.info("Browser-Use代理初始化成功")
            return agent
            
        except Exception as e:
            logger.error(f"Browser-Use代理初始化失败: {e}")
            raise
    
    def _build_full_task_description(self, task_description: str, target_url: str) -> str:
        """构建包含网址信息的完整任务描述"""
        # 检查任务描述中是否已经包含打开网址的指令
        task_lower = task_description.lower()
        if any(keyword in task_lower for keyword in ["打开", "访问", "导航到", "跳转到", "进入"]):
            # 如果已经包含导航指令，直接返回原始描述
            return task_description
        else:
            # 如果没有，添加打开网址的指令
            return f"首先打开网址: {target_url}，然后{task_description}"
    
    def _get_task_duration(self) -> float:
        """获取当前任务执行时长（秒）"""
        if self.current_task and self.current_task.get("start_time"):
            duration = datetime.now() - self.current_task["start_time"]
            return duration.total_seconds()
        return 0.0
    
    async def stop_current_task(self):
        """停止当前正在执行的任务"""
        if self.is_task_running and self.current_task:
            logger.info(f"正在停止任务: {self.current_task.get('description', '未知任务')}")
            
            self.current_task["status"] = "stopped"
            self.is_task_running = False
            
            # 注意：Browser-Use框架本身可能不支持任务中断
            # 这里主要是更新状态，实际的浏览器操作可能会继续执行
            if self.browser_agent:
                await self.browser_agent.cleanup()
            
            logger.info("任务停止请求已发送")
    
    async def cleanup(self):
        """清理资源"""
        try:
            if self.browser_agent:
                await self.browser_agent.cleanup()
                self.browser_agent = None
            
            self.current_task = None
            logger.info("任务执行器资源清理完成")
            
        except Exception as e:
            logger.error(f"资源清理出错: {e}")
    
    def get_current_status(self) -> Dict[str, Any]:
        """获取当前任务状态"""
        return {
            "is_running": self.is_task_running,
            "current_task": self.current_task,
            "test_url": self.test_url,
            "agent_ready": self.browser_agent is not None,
            "timestamp": datetime.now().isoformat()
        }
    
    async def test_browser_connection(self) -> Dict[str, Any]:
        """测试浏览器连接和Browser-Use框架"""
        try:
            logger.info("开始测试浏览器连接...")
            
            # 初始化代理
            if not self.browser_agent:
                self.browser_agent = await self._initialize_browser_agent()
            
            # 执行简单测试任务
            test_result = await self.browser_agent.execute_web_task(
                f"打开网址 {self.test_url} 并获取页面标题"
            )
            
            if test_result.get("success", False):
                return {
                    "success": True,
                    "message": "浏览器连接测试成功",
                    "result": test_result.get("result", ""),
                    "test_url": self.test_url
                }
            else:
                return {
                    "success": False,
                    "message": "浏览器连接测试失败",
                    "error": test_result.get("error", "未知错误")
                }
                
        except Exception as e:
            logger.error(f"浏览器连接测试异常: {e}")
            return {
                "success": False,
                "message": "浏览器连接测试异常",
                "error": str(e)
            }


# 工厂函数
def create_task_executor(test_url: str = "https://www.baidu.com") -> TaskExecutor:
    """创建任务执行器实例"""
    return TaskExecutor(test_url=test_url)


# 示例使用
if __name__ == "__main__":
    async def demo():
        # 创建任务执行器
        executor = create_task_executor()
        
        # 测试浏览器连接
        test_result = await executor.test_browser_connection()
        print("连接测试结果:", test_result)
        
        if test_result.get("success"):
            # 执行示例任务
            tasks = [
                "在搜索框中输入'Python教程'",
                "点击搜索按钮",
                "查看搜索结果"
            ]
            
            for task in tasks:
                print(f"\n执行任务: {task}")
                result = await executor.execute_task(task)
                print(f"结果: {result}")
                
                if not result.get("success"):
                    print("任务失败，停止后续任务")
                    break
        
        # 清理资源
        await executor.cleanup()
    
    # 运行演示
    asyncio.run(demo())