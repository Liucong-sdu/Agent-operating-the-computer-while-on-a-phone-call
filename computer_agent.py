# computer_agent.py (V13 - 超时与AI摘要最终版)

import asyncio
import threading
import queue
import functools
import json
import os
import openai

from typing import Union, List, Dict, Any
from concurrent.futures import ThreadPoolExecutor
from playwright.async_api import async_playwright, Browser, Page
from browser_use import Agent
from browser_use.llm import ChatOpenAI

import config
from shared_queues import q1_queue, q2_queue
from computer_interface import send_status_to_voice_agent

class ComputerAgent:
    def __init__(self):
        self.stop_event = threading.Event()
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._start_event_loop, daemon=True)
        self.browser: Union[Browser, None] = None
        self.page: Union[Page, None] = None
        self.internal_task_queue = queue.Queue()
        self.is_busy = False
        self.browser_ready = threading.Event()
        # 为摘要Agent创建一个专用的客户端
        self.summarizer_client = openai.OpenAI(api_key=config.OPENAI_API_KEY, base_url=config.OPENAI_BASE_URL)

    def _summarize_result_with_agent(self, final_result: Any) -> str:
        """
        调用一个AI Agent来读取和总结 browser_use 的原始日志。
        """
        print("--- 开始使用AI代理进行摘要提取 ---")
        try:
            raw_log = str(final_result)
            prompt = config.SUMMARIZER_PROMPT.format(log_text=raw_log)
            
            response = self.summarizer_client.chat.completions.create(
                model=config.LARGE_LLM_MODEL, # 使用 gpt-4.1-mini 作为摘要模型
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=500,
            )
            summary = response.choices[0].message.content.strip()
            # 简单的清洗，去除可能存在的Markdown标记
            if summary.startswith("```json"):
                summary = summary[7:]
            if summary.startswith("```"):
                summary = summary[3:]
            if summary.endswith("```"):
                summary = summary[:-3]
            
            print(f"--- AI代理提取摘要成功: {summary} ---")
            return summary
        except Exception as e:
            print(f"[摘要错误] AI代理提取时发生异常: {e}")
            return "电脑助手已完成操作，但AI摘要提取失败。"

    def _start_event_loop(self):
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self._run_tasks_loop())
        finally:
            self.loop.close()

    async def _initialize_browser_llm(self):
        if self.page:
            return
        print("💻 Computer Agent: 正在启动浏览器...")
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=False)
        context = await self.browser.new_context()
        self.page = await context.new_page()
        print("✅ Computer Agent: 浏览器和 LLM 已就绪。")
        self.browser_ready.set()

    async def _run_tasks_loop(self):
        await self._initialize_browser_llm()
        print("✅ Computer Agent: 任务执行循环已启动，等待指令...")

        while not self.stop_event.is_set():
            try:
                task = self.internal_task_queue.get(timeout=0.5)
                task_id = task.get("task_id")
                try:
                    self.is_busy = True
                    task_type = task.get("type")
                    print(f"🦾 Computer Agent: 收到新任务 (类型: {task_type}, ID: {task_id})")

                    if task_type == "goal":
                        goal = task.get("goal")
                        print(f"🦾 Computer Agent: 开始执行目标 -> '{goal}'")
                        llm_client = ChatOpenAI(model=config.COMPUTER_AGENT_MODEL, temperature=0.0, api_key=os.getenv("OPENAI_API_KEY"), base_url=os.getenv("OPENAI_BASE_URL"))
                        agent_instance = Agent(page=self.page, task=goal, llm=llm_client, extraction_model=llm_client)
                        
                        print("⏳ Computer Agent: 为主要任务设置90秒超时...")
                        final_result = await asyncio.wait_for(agent_instance.run(), timeout=90.0)

                        summary = self._summarize_result_with_agent(final_result)
                        print(f"📄 Computer Agent: 目标 '{goal}' 完成，发送由AI生成的精准摘要: {summary}")

                        if "提取" in goal or "extract" in goal.lower():
                            send_status_to_voice_agent(task_id, "OBSERVATION_RESULT", summary)
                        else:
                            send_status_to_voice_agent(task_id, "EXECUTION_SUCCESS", f"操作 '{goal}' 已成功完成。")

                    elif task_type == "info":
                        info_list = task.get("info_list", [])
                        print(f"🦾 Computer Agent: 开始处理信息包，包含 {len(info_list)} 项。")
                        llm_client = ChatOpenAI(model=config.COMPUTER_AGENT_MODEL, temperature=0.0, api_key=os.getenv("OPENAI_API_KEY"), base_url=os.getenv("OPENAI_BASE_URL"))
                        field_names = []
                        for info_item in info_list:
                            field_name = info_item.get("field_name")
                            user_info = info_item.get("user_info")
                            field_names.append(field_name)
                            sub_task_goal = f"在标签为 '{field_name}' 的输入框或表单字段中填入 '{user_info}'"
                            print(f"   -> 执行子任务: {sub_task_goal}")
                            agent_instance = Agent(page=self.page, task=sub_task_goal, llm=llm_client, extraction_model=llm_client)
                            
                            print(f"⏳ Computer Agent: 为子任务 '{field_name}' 设置45秒超时...")
                            await asyncio.wait_for(agent_instance.run(), timeout=45.0)

                        print(f"📄 Computer Agent: 信息包处理完成。")
                        send_status_to_voice_agent(task_id, "EXECUTION_SUCCESS", f"已成功为您填写 '{'、'.join(field_names)}' 信息。")

                except asyncio.TimeoutError:
                    error_message = f"任务 '{task.get('goal') or task.get('info_list')}' 执行超时，可能已陷入无限循环。"
                    print(f"❌ Computer Agent: {error_message}")
                    if task_id:
                        send_status_to_voice_agent(task_id, "EXECUTION_FAILURE", error_message)
                except Exception as e:
                    print(f"❌ Computer Agent: 任务执行失败 (ID: {task_id})，错误: {e}")
                    if task_id:
                        send_status_to_voice_agent(task_id, "EXECUTION_FAILURE", f"任务执行失败，错误: {e}")
                
                finally:
                    self.is_busy = False
                    self.internal_task_queue.task_done()
                    print("✅ Computer Agent: 已空闲, 可以接受新任务。")

            except queue.Empty:
                continue
    
    def _main_loop_thread(self):
        self.browser_ready.wait()
        while not self.stop_event.is_set():
            try:
                message = q1_queue.get(timeout=0.5)
                task_id = message.get("task_id")
                msg_type = message.get("type")
                payload = message.get("payload")
                if not payload:
                    continue
                if msg_type == "goal":
                    goal_description = payload.get("goal")
                    if goal_description:
                        self.internal_task_queue.put({"task_id": task_id, "goal": goal_description, "type": "goal"})
                elif msg_type == "info":
                    info_list = payload.get("info_list")
                    if info_list:
                        self.internal_task_queue.put({"task_id": task_id, "info_list": info_list, "type": "info"})
            except queue.Empty:
                continue

    def start(self):
        self.thread.start()
        main_loop_thread = threading.Thread(target=self._main_loop_thread, daemon=True)
        main_loop_thread.start()

    def stop(self):
        self.stop_event.set()
        if self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)
        self.thread.join(timeout=2)
        if self.browser:
            try:
                if not self.loop.is_closed():
                    self.loop.run_until_complete(self.browser.close())
                else:
                    asyncio.run(self.browser.close())
            except Exception as e:
                print(f"💻 Computer Agent: 关闭浏览器时出错: {e}")