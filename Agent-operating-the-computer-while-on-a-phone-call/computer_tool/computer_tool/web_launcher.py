"""
网页启动器 - Computer Tool核心组件
负责自动打开测试网址和管理浏览器会话
"""

import asyncio
import logging
import webbrowser
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import threading
import time


# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WebLauncher:
    """网页启动器 - 管理测试网址的自动打开和浏览器会话"""
    
    def __init__(self, 
                 default_url: str = "https://www.baidu.com",
                 auto_launch: bool = True,
                 browser_name: Optional[str] = None):
        """
        初始化网页启动器
        
        Args:
            default_url: 默认测试网址
            auto_launch: 是否自动启动浏览器
            browser_name: 指定浏览器名称（如'chrome', 'firefox'等）
        """
        self.default_url = default_url
        self.auto_launch = auto_launch
        self.browser_name = browser_name
        
        # 会话状态
        self.launched_urls = []
        self.last_launch_time = None
        self.is_browser_open = False
        
        logger.info(f"网页启动器初始化完成 - 默认URL: {default_url}")
    
    def launch_url(self, url: Optional[str] = None, new_tab: bool = True) -> Dict[str, Any]:
        """
        启动指定URL
        
        Args:
            url: 要打开的URL（可选，默认使用default_url）
            new_tab: 是否在新标签页中打开
            
        Returns:
            启动结果
        """
        try:
            target_url = url or self.default_url
            
            logger.info(f"正在启动网址: {target_url}")
            
            # 选择浏览器
            browser = self._get_browser()
            
            # 打开网址
            if new_tab and self.is_browser_open:
                browser.open_new_tab(target_url)
            else:
                browser.open(target_url)
                self.is_browser_open = True
            
            # 记录启动信息
            launch_info = {
                "url": target_url,
                "timestamp": datetime.now(),
                "browser": self.browser_name or "default",
                "new_tab": new_tab
            }
            
            self.launched_urls.append(launch_info)
            self.last_launch_time = datetime.now()
            
            logger.info(f"成功启动网址: {target_url}")
            
            return {
                "success": True,
                "url": target_url,
                "message": f"成功打开网址: {target_url}",
                "timestamp": launch_info["timestamp"].isoformat(),
                "browser": launch_info["browser"]
            }
            
        except Exception as e:
            error_msg = f"网址启动失败: {str(e)}"
            logger.error(error_msg)
            
            return {
                "success": False,
                "url": target_url if 'target_url' in locals() else url,
                "error": str(e),
                "message": error_msg
            }
    
    def _get_browser(self):
        """获取浏览器实例"""
        if self.browser_name:
            try:
                return webbrowser.get(self.browser_name)
            except webbrowser.Error:
                logger.warning(f"无法找到指定浏览器 '{self.browser_name}'，使用默认浏览器")
                return webbrowser
        else:
            return webbrowser
    
    async def async_launch_url(self, url: Optional[str] = None, new_tab: bool = True) -> Dict[str, Any]:
        """
        异步启动URL（在线程池中执行以避免阻塞）
        
        Args:
            url: 要打开的URL
            new_tab: 是否在新标签页中打开
            
        Returns:
            启动结果
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.launch_url, url, new_tab)
    
    def launch_on_startup(self) -> Dict[str, Any]:
        """
        启动时自动打开测试网址
        
        Returns:
            启动结果
        """
        if not self.auto_launch:
            return {
                "success": False,
                "message": "自动启动已禁用",
                "auto_launch": False
            }
        
        logger.info("执行启动时自动打开网址...")
        return self.launch_url(self.default_url, new_tab=False)
    
    def get_launch_history(self, limit: int = 10) -> list:
        """
        获取启动历史记录
        
        Args:
            limit: 返回记录数限制
            
        Returns:
            启动历史记录列表
        """
        return self.launched_urls[-limit:] if limit > 0 else self.launched_urls
    
    def get_status(self) -> Dict[str, Any]:
        """获取当前状态"""
        return {
            "default_url": self.default_url,
            "auto_launch": self.auto_launch,
            "browser_name": self.browser_name,
            "is_browser_open": self.is_browser_open,
            "total_launches": len(self.launched_urls),
            "last_launch_time": self.last_launch_time.isoformat() if self.last_launch_time else None,
            "recent_urls": [info["url"] for info in self.launched_urls[-5:]]
        }
    
    def validate_url(self, url: str) -> Dict[str, Any]:
        """
        验证URL格式
        
        Args:
            url: 要验证的URL
            
        Returns:
            验证结果
        """
        try:
            # 基本URL格式检查
            if not url.startswith(('http://', 'https://')):
                if not url.startswith('www.'):
                    url = 'https://www.' + url
                else:
                    url = 'https://' + url
            
            # 简单的URL格式验证
            if '.' not in url:
                return {
                    "valid": False,
                    "url": url,
                    "error": "URL格式无效：缺少域名"
                }
            
            return {
                "valid": True,
                "url": url,
                "message": "URL格式有效"
            }
            
        except Exception as e:
            return {
                "valid": False,
                "url": url,
                "error": f"URL验证失败: {str(e)}"
            }
    
    def update_default_url(self, new_url: str) -> Dict[str, Any]:
        """
        更新默认URL
        
        Args:
            new_url: 新的默认URL
            
        Returns:
            更新结果
        """
        try:
            # 验证新URL
            validation_result = self.validate_url(new_url)
            
            if not validation_result["valid"]:
                return {
                    "success": False,
                    "message": "URL格式无效",
                    "error": validation_result["error"]
                }
            
            old_url = self.default_url
            self.default_url = validation_result["url"]
            
            logger.info(f"默认URL已更新: {old_url} -> {self.default_url}")
            
            return {
                "success": True,
                "old_url": old_url,
                "new_url": self.default_url,
                "message": f"默认URL已更新为: {self.default_url}"
            }
            
        except Exception as e:
            logger.error(f"更新默认URL失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "更新默认URL失败"
            }
    
    def cleanup(self):
        """清理资源"""
        try:
            self.is_browser_open = False
            logger.info("网页启动器清理完成")
        except Exception as e:
            logger.error(f"网页启动器清理出错: {e}")


class DelayedLauncher:
    """延迟启动器 - 支持延迟一段时间后自动打开网址"""
    
    def __init__(self, web_launcher: WebLauncher):
        self.web_launcher = web_launcher
        self.pending_launches = []
        self.timer_thread = None
    
    def schedule_launch(self, url: str, delay_seconds: int = 5) -> Dict[str, Any]:
        """
        计划延迟启动
        
        Args:
            url: 要启动的URL
            delay_seconds: 延迟秒数
            
        Returns:
            计划结果
        """
        try:
            launch_time = datetime.now() + timedelta(seconds=delay_seconds)
            
            launch_task = {
                "url": url,
                "scheduled_time": launch_time,
                "delay_seconds": delay_seconds,
                "status": "pending"
            }
            
            self.pending_launches.append(launch_task)
            
            # 启动定时器线程
            if not self.timer_thread or not self.timer_thread.is_alive():
                self.timer_thread = threading.Thread(target=self._timer_worker, daemon=True)
                self.timer_thread.start()
            
            logger.info(f"已计划 {delay_seconds} 秒后启动: {url}")
            
            return {
                "success": True,
                "url": url,
                "delay_seconds": delay_seconds,
                "scheduled_time": launch_time.isoformat(),
                "message": f"已计划 {delay_seconds} 秒后启动网址"
            }
            
        except Exception as e:
            return {
                "success": False,
                "url": url,
                "error": str(e),
                "message": "计划启动失败"
            }
    
    def _timer_worker(self):
        """定时器工作线程"""
        while self.pending_launches:
            current_time = datetime.now()
            
            # 检查是否有需要执行的任务
            for task in self.pending_launches[:]:  # 复制列表以避免修改时的问题
                if current_time >= task["scheduled_time"] and task["status"] == "pending":
                    logger.info(f"执行计划启动: {task['url']}")
                    
                    result = self.web_launcher.launch_url(task["url"])
                    task["status"] = "completed" if result["success"] else "failed"
                    task["result"] = result
                    
                    self.pending_launches.remove(task)
            
            time.sleep(1)  # 每秒检查一次


def create_web_launcher(default_url: str = "https://www.baidu.com",
                       auto_launch: bool = True,
                       browser_name: Optional[str] = None) -> WebLauncher:
    """
    工厂函数：创建网页启动器
    
    Args:
        default_url: 默认测试网址
        auto_launch: 是否自动启动
        browser_name: 浏览器名称
        
    Returns:
        网页启动器实例
    """
    return WebLauncher(
        default_url=default_url,
        auto_launch=auto_launch,
        browser_name=browser_name
    )


# 示例使用
if __name__ == "__main__":
    async def demo():
        # 创建网页启动器
        launcher = create_web_launcher()
        
        # 获取状态
        status = launcher.get_status()
        print(f"启动器状态: {status}")
        
        # 启动默认网址
        result = launcher.launch_on_startup()
        print(f"启动结果: {result}")
        
        # 等待一会儿
        await asyncio.sleep(2)
        
        # 异步启动另一个网址
        result2 = await launcher.async_launch_url("https://www.google.com", new_tab=True)
        print(f"异步启动结果: {result2}")
        
        # 获取启动历史
        history = launcher.get_launch_history()
        print(f"启动历史: {history}")
        
        # 创建延迟启动器
        delayed_launcher = DelayedLauncher(launcher)
        
        # 计划延迟启动
        schedule_result = delayed_launcher.schedule_launch("https://github.com", delay_seconds=3)
        print(f"计划结果: {schedule_result}")
        
        # 等待延迟启动完成
        await asyncio.sleep(5)
        
        # 清理
        launcher.cleanup()
    
    # 运行演示
    asyncio.run(demo())