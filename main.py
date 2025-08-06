# main.py (最终修复版 - 明确第一步)

import time
from agent import VoiceAgent
from computer_agent import ComputerAgent

def main():
    """主函数，用于启动并协调语音智能体和电脑智能体"""
    
    TARGET_URL = "http://127.0.0.1:1516/index.html"
    
    voice_agent = VoiceAgent()
    computer_agent = ComputerAgent()

    try:
        voice_agent.start()
        computer_agent.start()
        
        print("\n双智能体系统正在运行... 按 Ctrl+C 停止。\n")
        
        computer_agent.browser_ready.wait(20)
        if not computer_agent.browser_ready.is_set():
            print("❌ 电脑Agent浏览器启动超时，程序退出。")
            return
            
        time.sleep(2)

        # 【核心修复】将初始指令简化为最纯粹的第一步观察任务
        initial_user_prompt = f"打开本地网页 {TARGET_URL} ，看看需要填写什么。"
        
        print(f"🚀 系统启动：模拟用户输入 -> '{initial_user_prompt}'")
        
        voice_agent.conversation_history.append({"role": "user", "content": initial_user_prompt})
        voice_agent._trigger_large_llm()
        
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n\n检测到 Ctrl+C，正在优雅地停止所有智能体...")
    finally:
        voice_agent.stop()
        computer_agent.stop()
        print("\n程序已完全退出。")

if __name__ == "__main__":
    main()