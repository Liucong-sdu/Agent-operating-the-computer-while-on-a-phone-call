"""
Computer Tool 完整集成演示
展示基于Browser-Use框架的浏览器自动化系统的完整工作流程

模拟场景：
1. 语音Agent将用户指令放入queue1
2. Computer Tool监听并处理指令
3. 使用Browser-Use执行浏览器操作
4. 输出操作状态和结果
"""

import asyncio
import queue
import logging
import os
from typing import Dict, Any
from dotenv import load_dotenv

# 导入Computer Tool组件
from computer_tool import (
    create_queue_processor,
    create_status_reporter,
    create_web_launcher
)

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ComputerToolDemo:
    """Computer Tool完整演示类"""
    
    def __init__(self, test_url: str = "https://www.baidu.com"):
        """
        初始化演示系统
        
        Args:
            test_url: 测试网址
        """
        self.test_url = test_url
        
        # 创建通信队列
        self.voice_command_queue = queue.Queue()  # queue1 - 语音指令队列
        self.status_output_queue = queue.Queue()  # 状态输出队列
        
        # 初始化组件
        self.queue_processor = None
        self.status_reporter = None
        self.web_launcher = None
        
        # 运行状态
        self.is_running = False
        
        logger.info(f"Computer Tool演示系统初始化完成 - 测试网址: {test_url}")
    
    async def initialize_components(self):
        """初始化所有组件"""
        try:
            logger.info("正在初始化Computer Tool组件...")
            
            # 创建状态报告器
            self.status_reporter = create_status_reporter(
                output_queue=self.status_output_queue,
                enable_console=True,
                enable_file_log=False
            )
            
            # 创建网页启动器
            self.web_launcher = create_web_launcher(
                default_url=self.test_url,
                auto_launch=True
            )
            
            # 创建队列处理器
            self.queue_processor = create_queue_processor(
                queue1=self.voice_command_queue,
                output_queue=self.status_output_queue,
                test_url=self.test_url
            )
            
            # 不再自动启动WebLauncher浏览器，由Browser-Use统一管理浏览器
            await self.status_reporter.report_status({
                "message": f"系统已准备就绪，将使用Browser-Use访问: {self.test_url}",
                "url": self.test_url
            })
            
            logger.info("所有组件初始化完成")
            
        except Exception as e:
            logger.error(f"组件初始化失败: {e}")
            raise
    
    async def start_system(self):
        """启动Computer Tool系统"""
        try:
            self.is_running = True
            
            await self.status_reporter.report_status({
                "message": "Computer Tool系统启动中...",
                "status": "starting"
            })
            
            # 启动队列处理器（这将开始监听语音指令）
            processor_task = asyncio.create_task(
                self.queue_processor.start_processing()
            )
            
            # 启动状态监控
            monitor_task = asyncio.create_task(
                self._status_monitor()
            )
            
            await self.status_reporter.report_status({
                "message": "✅ Computer Tool系统已启动，等待语音指令...",
                "status": "running"
            })
            
            # 等待任务完成
            await asyncio.gather(processor_task, monitor_task, return_exceptions=True)
            
        except Exception as e:
            logger.error(f"系统启动失败: {e}")
            await self.status_reporter.report_error("系统启动异常", str(e))
    
    async def _status_monitor(self):
        """状态监控器 - 处理输出队列中的状态信息"""
        while self.is_running:
            try:
                # 检查状态输出队列
                while not self.status_output_queue.empty():
                    status_data = self.status_output_queue.get_nowait()
                    # 状态数据已经在StatusReporter中处理了，这里可以做额外处理
                    logger.debug(f"状态监控收到: {status_data.get('message', '')}")
                    
                await asyncio.sleep(0.5)  # 避免过度CPU使用
                
            except Exception as e:
                logger.error(f"状态监控出错: {e}")
                await asyncio.sleep(1)
    
    def simulate_voice_commands(self, commands: list):
        """
        模拟语音Agent发送指令到queue1
        
        Args:
            commands: 语音指令列表
        """
        logger.info(f"模拟发送 {len(commands)} 条语音指令...")
        
        for i, command in enumerate(commands, 1):
            # 模拟语音指令结构
            voice_command = {
                "type": "voice_command",
                "content": command,
                "command_id": i,
                "timestamp": asyncio.get_event_loop().time()
            }
            
            self.voice_command_queue.put(voice_command)
            logger.info(f"已添加语音指令 #{i}: {command}")
    
    async def run_demo_scenario(self):
        """运行演示场景"""
        try:
            print("\n" + "="*60)
            print("🎤 Computer Tool + Browser-Use 演示开始")
            print("📱 现在只使用一个Browser-Use浏览器执行所有操作")
            print("="*60)
            
            # 初始化组件
            await self.initialize_components()
            
            # 准备演示指令 - 现在只使用Browser-Use一个浏览器执行所有操作
            demo_commands = [
                "打开百度首页",  # 明确显示Browser-Use打开网页
                "在搜索框中输入'Python教程'",
                "点击搜索按钮",
                "查看第一个搜索结果的标题",
                "打开第一个搜索结果",
                "返回上一页"
            ]
            
            # 模拟语音输入
            self.simulate_voice_commands(demo_commands)
            
            # 启动系统处理（运行一段时间后自动停止）
            system_task = asyncio.create_task(self.start_system())
            
            # 等待指令处理完成（给足够时间处理所有指令）
            await asyncio.sleep(30)  # 等待30秒处理完所有任务
            
            # 停止系统
            await self.stop_system()
            
            print("\n" + "="*60)
            print("✅ Computer Tool 演示完成")
            print("="*60)
            
        except KeyboardInterrupt:
            print("\n用户中断演示")
            await self.stop_system()
        except Exception as e:
            logger.error(f"演示运行出错: {e}")
            await self.stop_system()
    
    async def stop_system(self):
        """停止Computer Tool系统"""
        try:
            self.is_running = False
            
            if self.queue_processor:
                await self.queue_processor.stop_processing()
            
            if self.status_reporter:
                await self.status_reporter.cleanup()
            
            if self.web_launcher:
                self.web_launcher.cleanup()
            
            logger.info("Computer Tool系统已停止")
            
        except Exception as e:
            logger.error(f"系统停止出错: {e}")
    
    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        status = {
            "is_running": self.is_running,
            "test_url": self.test_url,
            "voice_queue_size": self.voice_command_queue.qsize(),
            "status_queue_size": self.status_output_queue.qsize(),
        }
        
        if self.queue_processor:
            status["processor_status"] = self.queue_processor.get_status()
        
        if self.web_launcher:
            status["launcher_status"] = self.web_launcher.get_status()
        
        return status


class VoiceAgentSimulator:
    """语音Agent模拟器 - 模拟语音输入和处理"""
    
    def __init__(self, command_queue: queue.Queue):
        self.command_queue = command_queue
        self.is_listening = False
    
    def start_listening(self):
        """开始模拟语音监听"""
        self.is_listening = True
        logger.info("语音监听已启动（模拟）")
    
    def process_voice_input(self, voice_text: str):
        """处理语音输入并发送到队列"""
        if not self.is_listening:
            return
        
        # 模拟语音识别和处理
        processed_command = {
            "type": "voice_command",
            "content": voice_text,
            "confidence": 0.95,  # 模拟识别置信度
            "timestamp": asyncio.get_event_loop().time()
        }
        
        self.command_queue.put(processed_command)
        logger.info(f"语音指令已处理并发送: {voice_text}")
    
    def stop_listening(self):
        """停止语音监听"""
        self.is_listening = False
        logger.info("语音监听已停止")


async def run_interactive_demo():
    """运行交互式演示"""
    print("\n🎯 Computer Tool 交互式演示")
    print("输入语音指令，系统将使用Browser-Use执行浏览器操作")
    print("输入 'quit' 或 'exit' 退出演示\n")
    
    # 检查API密钥
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("⚠️  警告: 未设置OPENAI_API_KEY环境变量")
        print("请在.env文件中设置API密钥，或者将使用模拟模式")
        print()
    
    # 创建演示系统
    demo = ComputerToolDemo()
    await demo.initialize_components()
    
    # 启动系统（在后台运行）
    system_task = asyncio.create_task(demo.start_system())
    
    try:
        while True:
            # 获取用户输入
            user_input = input("🎤 请输入语音指令: ").strip()
            
            if user_input.lower() in ['quit', 'exit', '退出']:
                break
            
            if not user_input:
                continue
            
            # 发送指令到队列
            demo.voice_command_queue.put({
                "type": "voice_command",
                "content": user_input,
                "timestamp": asyncio.get_event_loop().time()
            })
            
            print(f"✅ 指令已发送: {user_input}")
            print("请等待浏览器操作完成...\n")
    
    except KeyboardInterrupt:
        print("\n用户中断")
    finally:
        await demo.stop_system()
        system_task.cancel()


def main():
    """主函数"""
    print("🌐 Computer Tool - Browser-Use 浏览器自动化演示")
    print("基于Browser-Use框架的语音控制浏览器系统\n")
    
    # 选择演示模式
    print("请选择演示模式:")
    print("1. 自动演示 - 运行预设的演示场景")
    print("2. 交互演示 - 手动输入语音指令")
    print("3. 退出")
    
    choice = input("\n请输入选择 (1/2/3): ").strip()
    
    if choice == "1":
        print("\n🚀 启动自动演示...")
        demo = ComputerToolDemo()
        asyncio.run(demo.run_demo_scenario())
    
    elif choice == "2":
        print("\n🎮 启动交互演示...")
        asyncio.run(run_interactive_demo())
    
    elif choice == "3":
        print("退出演示")
        return
    
    else:
        print("无效选择，退出")
        return


if __name__ == "__main__":
    main()