import time
from agent import VoiceAgent

def main():
    """主函数，用于运行语音智能体"""
    agent = VoiceAgent()
    agent.start()

    print("\n智能体正在运行。按 Ctrl+C 停止。\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n检测到 Ctrl+C，正在优雅地停止智能体...")
        agent.stop()
        print("程序已退出。")

if __name__ == "__main__":
    main()