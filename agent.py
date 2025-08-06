# agent.py (V3 - 工具权限控制最终版)

import threading
import queue
import time
import io
import wave
import openai
import json
import uuid

import config
from audio_handler import AudioHandler
from llm_handler import LLMHandler
from tts_handler import TTSHandler
from computer_interface import send_goal_to_computer_agent, send_info_to_computer_agent

class VoiceAgent:
    def __init__(self):
        self.large_llm_client = openai.OpenAI(api_key=config.OPENAI_API_KEY, base_url=config.OPENAI_BASE_URL)
        self.small_llm_client = openai.OpenAI(api_key="ollama", base_url=config.OLLAMA_BASE_URL)
        
        self.interrupt_event = threading.Event()
        self.stop_event = threading.Event()
        self.user_speech_queue = queue.Queue()
        
        self.conversation_history = [{"role": "system", "content": config.SYSTEM_PROMPT}]
        self.current_task_id: str | None = None
        self.thinking_lock = threading.RLock()
        
        self.tools = [
            {"type": "function", "function": {"name": "send_goal_to_computer_agent", "description": "向电脑Agent发送一个全新的、高级别的任务目标。", "parameters": {"type": "object", "properties": { "goal_description": { "type": "string", "description": "对用户目标的清晰描述。"}}, "required": ["goal_description"]}}},
            {"type": "function", "function": {"name": "send_info_to_computer_agent", "description": "当用户提供一个或多个具体信息点时，用此工具将它们打包回复给电脑Agent。", "parameters": {"type": "object", "properties": { "info_list": { "type": "array", "description": "一个包含用户信息对象的列表，每个对象都应包含'field_name'和'user_info'。", "items": { "type": "object", "properties": { "field_name": { "type": "string", "description": "字段名，例如'姓名'。"}, "user_info": { "type": "string", "description": "用户提供的、经过严格清洗和格式化的具体信息（例如，将'二十岁'转为'20'）。"}}, "required": ["field_name", "user_info"]}}}, "required": ["info_list"]}}}
        ]
        
        self.audio_handler = AudioHandler(on_speech_start=self.on_speech_start, on_speech_end=self.on_speech_end)
        self.llm_handler = LLMHandler(self.large_llm_client)
        self.tts_handler = TTSHandler(self.large_llm_client)

        self.main_thread = threading.Thread(target=self._main_loop, daemon=True)
        self.computer_message_watcher_thread = threading.Thread(target=self._computer_message_watcher, daemon=True)
    
    def _execute_tool_call(self, tool_call):
        tool_name = tool_call.function.name
        tool_args = json.loads(tool_call.function.arguments)
        
        if self.current_task_id is None:
            self.current_task_id = str(uuid.uuid4())

        if tool_name == "send_goal_to_computer_agent":
            goal = tool_args.get("goal_description")
            print(f"🛠️ 电话Agent: 派发新目标 -> '{goal}' (ID: {self.current_task_id})")
            return send_goal_to_computer_agent(self.current_task_id, goal)
        
        elif tool_name == "send_info_to_computer_agent":
            info_list = tool_args.get("info_list", [])
            print(f"🛠️ 电话Agent: 派发信息包 -> {info_list} (ID: {self.current_task_id})")
            return send_info_to_computer_agent(self.current_task_id, info_list)
            
        return f"未知工具: {tool_name}"

    def on_speech_start(self):
        if self.tts_handler.is_speaking():
            print("🎤 用户开始说话，清空AI语音队列并打断...")
            self.interrupt_event.set()
            self.tts_handler.stop_current_playback()
            self.tts_handler.clear_queue()
        
    def on_speech_end(self, audio_data):
        self.user_speech_queue.put(audio_data)
    
    def _is_valid_interrupt(self, text: str) -> bool:
        try:
            print(f"🕵️  安检员(小模型): 正在分析打断文本的有效性...")
            prompt = config.INTERRUPT_PROMPT.format(text=text)
            response = self.small_llm_client.chat.completions.create(
                model=config.SMALL_LLM_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=10,
                timeout=3
            )
            decision = response.choices[0].message.content.strip().lower()
            if "interrupt" in decision:
                print(f"✅ 安检员(小模型): 判断为有效打断。内容: '{text}'")
                return True
            else:
                print(f"❌ 安检员(小模型): 判断为无效打断(噪音/口头禅)，已忽略。内容: '{text}'")
                return False
        except Exception as e:
            print(f"⚠️ 安检员(小模型): 判断时出错 ({e})，为安全起见，默认视为有效打断。")
            return True

    def _main_loop(self):
        while not self.stop_event.is_set():
            try:
                audio_data = self.user_speech_queue.get(block=True, timeout=1)
                
                with self.thinking_lock:
                    user_text = ""
                    try:
                        user_text = self._transcribe(audio_data)
                        print(f"🤫 [主循环-转录完成]: \"{user_text}\"")
                    except Exception as e:
                        print(f"❌ [主循环]: 音频转录失败: {e}，已忽略本次输入。")
                        continue 

                    if not user_text or not user_text.strip():
                        continue 
                    
                    was_interrupted = self.interrupt_event.is_set()
                    if was_interrupted:
                        if not self._is_valid_interrupt(user_text):
                            self.interrupt_event.clear()
                            continue

                    print(f"💬 [主循环-确认指令]: 用户说: '{user_text}'")
                    self.conversation_history.append({"role": "user", "content": user_text})
                    self._trigger_large_llm(allow_tool_calls=True)

            except queue.Empty:
                continue

    def _computer_message_watcher(self):
        from shared_queues import q2_queue
        while not self.stop_event.is_set():
            try:
                message = q2_queue.get(timeout=0.5)
                print(f"📬 电话Agent: 收到电脑回执: {message['payload']}")
                
                with self.thinking_lock:
                    print("📬 电话Agent: 已获得思考锁，正在处理电脑回执...")
                    self.interrupt_event.set() 
                    self.tts_handler.stop_current_playback()
                    self.tts_handler.clear_queue()
                    
                    self.conversation_history.append({"role": "user", "content": f"[FROM_COMPUTER_AGENT] {message['payload']}"})
                    # 【核心改造】处理电脑回执时，只允许LLM说话，不允许再调用工具
                    self._trigger_large_llm(allow_tool_calls=False)

            except queue.Empty:
                continue

    def _transcribe(self, audio_data):
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, "wb") as wf:
            wf.setnchannels(config.AUDIO_CHANNELS)
            wf.setsampwidth(2)
            wf.setframerate(config.AUDIO_SAMPLING_RATE)
            wf.writeframes(audio_data)
        wav_buffer.seek(0)
        wav_buffer.name = "audio.wav"
        transcription = self.large_llm_client.audio.transcriptions.create(model=config.STT_MODEL, file=wav_buffer)
        return transcription.text

    def _trigger_large_llm(self, allow_tool_calls: bool = True): # <--- 【改造】增加权限参数
        try:
            self.tts_handler.clear_queue()
            self.interrupt_event.clear()
            
            # 【改造】根据权限参数决定是否给LLM工具
            active_tools = self.tools if allow_tool_calls else None
            response_stream = self.llm_handler.get_llm_response_stream(history=self.conversation_history, tools=active_tools)

            full_response_text = ""
            tool_calls = []
            
            for chunk_type, content in response_stream:
                if self.interrupt_event.is_set():
                    print("🧠 LLM处理器: 检测到打断事件，终止生成。")
                    break
                if chunk_type == "text":
                    self.tts_handler.play_audio_stream(content, self.interrupt_event)
                    full_response_text += content
                elif chunk_type == "tool_call":
                    tool_calls.append(content)
            
            if tool_calls and not self.interrupt_event.is_set():
                tool_call = tool_calls[0]
                result = self._execute_tool_call(tool_call)
                assistant_message = {"role": "assistant", "content": full_response_text or None}
                if tool_calls:
                   assistant_message["tool_calls"] = [tc.model_dump() for tc in tool_calls]
                
                self.conversation_history.append(assistant_message)
                self.conversation_history.append({"role": "tool", "tool_call_id": tool_call.id, "name": tool_call.function.name, "content": result})
                
                # 【核心改造】在处理完工具结果后，只允许LLM说话，不允许再连续调用工具
                self._trigger_large_llm(allow_tool_calls=False)
                return

            if not self.interrupt_event.is_set():
                self.tts_handler.wait_for_completion()

            if not self.interrupt_event.is_set() and full_response_text.strip():
                self.conversation_history.append({"role": "assistant", "content": full_response_text.strip()})
        finally:
            self.interrupt_event.clear()

    def start(self):
        print("🚀 Voice Agent: 正在启动...")
        self.audio_handler.start()
        self.main_thread.start()
        self.computer_message_watcher_thread.start()

    def stop(self):
        print("🛑 Voice Agent: 正在停止...")
        self.stop_event.set()
        self.audio_handler.stop()
        self.tts_handler.cleanup()
        if self.main_thread.is_alive():
            self.main_thread.join()
        if self.computer_message_watcher_thread.is_alive():
            self.computer_message_watcher_thread.join()
        print("🛑 Voice Agent: 已完全停止。")