"""
Browser-Use代理封装 - Computer Tool核心组件
封装Browser-Use框架，提供统一的浏览器自动化接口
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Dict, Any, Optional

try:
    from browser_use import Agent
    from browser_use.llm import ChatAnthropic
    BROWSER_USE_AVAILABLE = True
except ImportError:
    BROWSER_USE_AVAILABLE = False
    Agent = None
    ChatAnthropic = None

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BrowserAgent:
    """Browser-Use代理封装类 - 提供统一的浏览器自动化接口"""
    
    def __init__(self, 
                 api_key: str,
                 model: str = "claude-sonnet-4-20250514",
                 temperature: float = 1.0,
                 max_retries: int = 3):
        """
        初始化Browser-Use代理
        
        Args:
            api_key: Anthropic API密钥
            model: 使用的LLM模型
            temperature: 模型温度参数
            max_retries: 最大重试次数
        """
        if not BROWSER_USE_AVAILABLE:
            raise ImportError(
                "Browser-Use框架未安装。请运行: pip install browser-use"
            )
        
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_retries = max_retries
        
        # 初始化LLM
        self.llm = ChatAnthropic(
            api_key=api_key,
            model=model,
            temperature=temperature
        )
        
        # 运行时状态
        self.current_agent = None
        self.is_busy = False
        self.last_task = None
        
        logger.info(f"Browser-Use代理初始化完成 - 模型: {model}, 温度: {temperature}")
    
    async def execute_web_task(self, task_description: str) -> Dict[str, Any]:
        """
        执行浏览器自动化任务
        
        Args:
            task_description: 自然语言任务描述
            
        Returns:
            任务执行结果
        """
        if self.is_busy:
            return {
                "success": False,
                "error": "代理正忙，请稍后重试",
                "message": "Browser-Use代理正在执行其他任务"
            }
        
        retry_count = 0
        last_error = None
        
        while retry_count < self.max_retries:
            try:
                self.is_busy = True
                self.last_task = {
                    "description": task_description,
                    "start_time": datetime.now(),
                    "retry_count": retry_count
                }
                
                logger.info(f"开始执行Browser-Use任务 (尝试 {retry_count + 1}/{self.max_retries}): {task_description}")
                
                # 创建Browser-Use代理，使用临时配置文件避免锁定问题
                logger.info(f"创建Browser-Use代理，任务描述: {task_description}")
                agent = Agent(
                    task=task_description,
                    llm=self.llm,
                    # 使用临时配置文件避免锁定问题
                    browser_config={
                        "headless": False,
                        "use_persistent_profile": False,  # 强制使用临时配置文件
                        "args": [
                            "--disable-blink-features=AutomationControlled",
                            "--disable-extensions",
                            "--no-default-browser-check",
                            "--disable-default-apps",
                            "--disable-background-timer-throttling",
                            "--disable-backgrounding-occluded-windows",
                            "--disable-renderer-backgrounding",
                            "--user-data-dir=" + os.path.join(os.path.expanduser("~"), "AppData", "Local", "Temp", f"browser_use_temp_{os.getpid()}")
                        ]
                    }
                )
                self.current_agent = agent
                logger.info("Browser-Use代理创建完成")
                
                # 执行任务
                logger.info("开始执行Browser-Use任务...")
                result = await agent.run()
                logger.info(f"Browser-Use任务执行完成，结果: {result}")
                
                # 成功完成
                logger.info(f"Browser-Use任务执行成功: {task_description}")
                
                return {
                    "success": True,
                    "result": str(result) if result else "任务执行完成",
                    "message": "浏览器操作执行成功",
                    "retry_count": retry_count,
                    "duration": self._get_task_duration()
                }
                
            except Exception as e:
                retry_count += 1
                last_error = str(e)
                
                logger.warning(f"Browser-Use任务执行失败 (尝试 {retry_count}/{self.max_retries}): {e}")
                
                if retry_count < self.max_retries:
                    # 等待后重试
                    wait_time = min(2 ** retry_count, 10)  # 指数退避，最大10秒
                    logger.info(f"等待 {wait_time} 秒后重试...")
                    await asyncio.sleep(wait_time)
                else:
                    # 超过最大重试次数
                    logger.error(f"Browser-Use任务执行失败，已达最大重试次数: {e}")
                    
                    return {
                        "success": False,
                        "error": last_error,
                        "message": f"浏览器操作执行失败（重试{self.max_retries}次后放弃）",
                        "retry_count": retry_count,
                        "duration": self._get_task_duration()
                    }
            finally:
                self.is_busy = False
                self.current_agent = None
        
        # 不应该到达这里，但作为安全网
        return {
            "success": False,
            "error": last_error or "未知错误",
            "message": "任务执行异常结束",
            "retry_count": retry_count
        }
    
    def _get_task_duration(self) -> float:
        """获取当前任务执行时长（秒）"""
        if self.last_task and self.last_task.get("start_time"):
            duration = datetime.now() - self.last_task["start_time"]
            return duration.total_seconds()
        return 0.0
    
    async def test_connection(self) -> Dict[str, Any]:
        """测试Browser-Use框架连接"""
        try:
            logger.info("开始测试Browser-Use连接...")
            
            # 执行简单测试任务
            test_result = await self.execute_web_task(
                "打开百度首页并获取页面标题"
            )
            
            if test_result.get("success", False):
                return {
                    "success": True,
                    "message": "Browser-Use连接测试成功",
                    "model": self.model,
                    "framework_status": "正常"
                }
            else:
                return {
                    "success": False,
                    "message": "Browser-Use连接测试失败",
                    "error": test_result.get("error", "未知错误"),
                    "model": self.model
                }
                
        except Exception as e:
            logger.error(f"Browser-Use连接测试异常: {e}")
            return {
                "success": False,
                "message": "Browser-Use连接测试异常",
                "error": str(e),
                "model": self.model
            }
    
    async def get_capabilities(self) -> Dict[str, Any]:
        """获取Browser-Use代理能力信息"""
        return {
            "framework": "Browser-Use",
            "model": self.model,
            "temperature": self.temperature,
            "max_retries": self.max_retries,
            "supported_operations": [
                "网页导航和打开",
                "表单填写和提交",
                "按钮点击和链接跳转",
                "页面元素查找和交互",
                "文本输入和选择",
                "页面滚动和导航",
                "数据提取和内容获取",
                "复杂多步骤工作流",
                "智能元素识别",
                "自适应页面处理"
            ],
            "features": [
                "自然语言任务描述",
                "智能元素定位",
                "自动错误恢复",
                "多步骤任务执行",
                "实时页面适应"
            ],
            "is_available": BROWSER_USE_AVAILABLE,
            "is_busy": self.is_busy
        }
    
    async def cleanup(self):
        """清理资源"""
        try:
            self.is_busy = False
            self.current_agent = None
            self.last_task = None
            
            logger.info("Browser-Use代理资源清理完成")
            
        except Exception as e:
            logger.error(f"Browser-Use代理资源清理出错: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """获取当前状态"""
        return {
            "model": self.model,
            "temperature": self.temperature,
            "is_busy": self.is_busy,
            "current_task": self.last_task,
            "framework_available": BROWSER_USE_AVAILABLE,
            "timestamp": datetime.now().isoformat()
        }


class MockBrowserAgent:
    """Browser-Use代理的模拟实现（用于测试和开发）"""
    
    def __init__(self, *args, **kwargs):
        self.is_busy = False
        self.last_task = None
        logger.warning("使用MockBrowserAgent - Browser-Use框架未安装")
    
    async def execute_web_task(self, task_description: str) -> Dict[str, Any]:
        """模拟执行浏览器任务"""
        self.is_busy = True
        self.last_task = {"description": task_description, "start_time": datetime.now()}
        
        # 模拟执行时间
        await asyncio.sleep(2)
        
        self.is_busy = False
        
        return {
            "success": True,
            "result": f"模拟执行任务: {task_description}",
            "message": "模拟执行成功（请安装browser-use获得真实功能）",
            "duration": 2.0
        }
    
    async def test_connection(self) -> Dict[str, Any]:
        return {
            "success": False,
            "message": "使用模拟代理 - 请安装browser-use框架",
            "model": "mock"
        }
    
    async def get_capabilities(self) -> Dict[str, Any]:
        return {
            "framework": "Mock Browser-Use",
            "is_available": False,
            "message": "请安装browser-use框架获得完整功能"
        }
    
    async def cleanup(self):
        self.is_busy = False
        self.last_task = None
    
    def get_status(self) -> Dict[str, Any]:
        return {
            "model": "mock",
            "is_busy": self.is_busy,
            "framework_available": False,
            "timestamp": datetime.now().isoformat()
        }


def create_browser_agent(api_key: str, 
                        model: str = "claude-sonnet-4-20250514",
                        temperature: float = 1.0) -> BrowserAgent:
    """
    工厂函数：创建Browser-Use代理
    
    Args:
        api_key: Anthropic API密钥
        model: 使用的LLM模型
        temperature: 模型温度参数
        
    Returns:
        Browser-Use代理实例
    """
    if BROWSER_USE_AVAILABLE:
        return BrowserAgent(
            api_key=api_key,
            model=model,
            temperature=temperature
        )
    else:
        logger.warning("Browser-Use框架未安装，使用模拟代理")
        return MockBrowserAgent()


# 示例使用
if __name__ == "__main__":
    async def demo():
        # 从环境变量获取API密钥
        api_key = os.getenv("OPENAI_API_KEY")
        
        if not api_key:
            print("请设置OPENAI_API_KEY环境变量")
            return
        
        # 创建代理
        agent = create_browser_agent(api_key)
        
        # 测试连接
        connection_result = await agent.test_connection()
        print("连接测试:", connection_result)
        
        # 获取能力信息
        capabilities = await agent.get_capabilities()
        print("代理能力:", capabilities)
        
        if connection_result.get("success"):
            # 执行示例任务
            tasks = [
                "打开百度首页",
                "在搜索框中输入'Python教程'并搜索",
                "查看第一个搜索结果的标题"
            ]
            
            for task in tasks:
                print(f"\n执行任务: {task}")
                result = await agent.execute_web_task(task)
                print(f"结果: {result}")
        
        # 清理资源
        await agent.cleanup()
    
    # 运行演示
    asyncio.run(demo())