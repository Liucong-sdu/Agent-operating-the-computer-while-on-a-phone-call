import asyncio
from dotenv import load_dotenv
from browser_use import Agent
from browser_use.llm import ChatOpenAI, base
import os
import time
from PIL import ImageGrab

# 加载环境变量 (如果您有 .env 文件)
load_dotenv()

async def run_browser_agent_task():
    """
    运行异步的浏览器代理任务。
    """
    # 确保您的任务描述最后一步是“复制到剪贴板”
    task_description = '''打开https://excalidraw.com/ 然后打开工具栏的最后一个按钮：更多工具，然后打开Mermaid 至 Excalidraw按钮，输入:

graph TD
    A[Start] --> B{Is Coffee Ready?};
    B -- Yes --> C[Pour into Cup];
    B -- No --> D[Boil Water];
    D --> E[Stir Coffee];
    E --> B;
    C --> F{Add Sugar?};
    F -- Yes --> G[Add Sugar];
    F -- No --> H[Serve Coffee];
    G --> H;

然后点击generate，再点击insert，再点击左上角的三个横杠按钮，点击导出图片按钮，弹出来的界面再复制到剪切板上就可以立即停止了'''

    agent = Agent(
        task=task_description,
        llm=ChatOpenAI(
            model="gpt-4.1-mini", 
            temperature=0.8,
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL")
        ),
    )
    print("--- 1. 正在启动浏览器代理，请稍候... ---")
    await agent.run()
    print("--- 浏览器代理任务已完成。---")


def wait_for_and_save_image_from_clipboard(timeout_seconds=15):
    """
    在指定时间内轮询检查剪贴板，发现图片后立即保存。
    """
    print(f"\n--- 2. 开始监测剪贴板中的图片（最长等待 {timeout_seconds} 秒）---")
    start_time = time.time()
    
    while time.time() - start_time < timeout_seconds:
        try:
            # 尝试从剪贴板获取图片
            image = ImageGrab.grabclipboard()
            
            # 检查返回的是否是有效的 Pillow Image 对象
            if isinstance(image, ImageGrab.Image.Image):
                print("成功在剪贴板中检测到图片！")
                timestamp = time.strftime("%Y%m%d-%H%M%S")
                filename = f"clipboard_output_{timestamp}.png"
                
                # 保存图片
                image.save(filename, "PNG")
                print(f"图片已成功保存为: {filename}")
                return # 任务完成，退出函数
        except Exception as e:
            # 某些情况下，剪贴板内容格式可能导致Pillow出错，可以忽略
            print(f"检查剪贴板时遇到临时错误，将重试: {e}")

        print("剪贴板中暂无图片，1秒后重试...")
        time.sleep(1)
    
    print(f"--- 等待超时（{timeout_seconds}秒），未在剪贴板中检测到图片。程序结束。 ---")


# --- 主程序入口 ---
if __name__ == "__main__":
    # 第一步：运行异步的浏览器自动化任务
    # 这个任务会一直运行直到完成
    asyncio.run(run_browser_agent_task())
    
    # 第二步：浏览器任务结束后，执行同步的剪贴板监测任务
    wait_for_and_save_image_from_clipboard()