# agent.py (最终完美版)

import threading
import queue
import time
import io
import wave
import openai
import json

import config
from audio_handler import AudioHandler
from llm_handler import LLMHandler
from tts_handler import TTSHandler
from computer_agent_interface import q2_queue, send_message_to_computer_agent

class VoiceAgent:
    def __init__(self):
        self.large_llm_client = openai.OpenAI(api_key=config.OPENAI_API_KEY)
        self.small_llm_client = openai.OpenAI(api_key="ollama", base_url=config.OLLAMA_BASE_URL)

        self.interrupt_event = threading.Event()
        self.stop_event = threading.Event()
        
        self.decision_queue = queue.Queue(maxsize=1)

        self.user_speech_queue = queue.Queue()
        self.conversation_history = [{"role": "system", "content": config.SYSTEM_PROMPT}]
        
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "send_message_to_computer_agent",
                    "description": "向操作浏览器的电脑Agent发送消息或指令。",
                    "parameters": {
                        "type": "object",
                        "properties": { "message": { "type": "string", "description": "要发送给电脑Agent的信息或指令。"}},
                        "required": ["message"],
                    },
                },
            }
        ]
        
        self.audio_handler = AudioHandler(
            on_speech_start=self.on_speech_start, 
            on_speech_end=self.on_speech_end
        )
        self.llm_handler = LLMHandler(self.large_llm_client)
        self.tts_handler = TTSHandler(self.large_llm_client)

        self.main_thread = threading.Thread(target=self._main_loop)
        self.queue_2_watcher_thread = threading.Thread(target=self._queue_2_watcher)

    def _is_system_busy(self):
        return self.llm_handler.is_active() or self.tts_handler.is_speaking()

    def on_speech_start(self):
        print("🎤 音频处理器: 检测到语音开始，启动并行决策...")
        threading.Thread(target=self._fast_decision_thread).start()

    def on_speech_end(self, audio_data):
        print("🎤 [路径B]: 用户已说完，等待路径A的最终决策...")
        try:
            decision = self.decision_queue.get(timeout=10.0)
            print(f"🎤 [路径B]: 收到决策 -> '{decision}'")
            
            if decision == "process":
                duration = len(audio_data) / (config.AUDIO_SAMPLING_RATE * 2)
                print(f"🎤 [路径B]: 决定处理该音频 ({duration:.2f}s)，放入主队列。")
                self.user_speech_queue.put(audio_data)
            else: # "ignore"
                print("🤫 [路径B]: 决定忽略本次录音，AI播报不受影响。")
        except queue.Empty:
            print("🎤 [路径B]: 等待决策超时，为安全起见，默认处理该音频。")
            self.user_speech_queue.put(audio_data)
        finally:
            while not self.decision_queue.empty():
                try: self.decision_queue.get_nowait()
                except queue.Empty: break

    def _fast_decision_thread(self):
        decision = "process" 
        try:
            time.sleep(config.FAST_CHECK_DURATION_S)
            audio_snapshot = b''.join(list(self.audio_handler.speech_buffer))

            if len(audio_snapshot) < 2048:
                print("⚡️ [路径A]: 音频快照过短，判定为->忽略。")
                decision = "ignore"
                return

            text = self._transcribe(audio_snapshot)
            if not text.strip():
                print("⚡️ [路径A]: 转录为空，判定为->忽略。")
                decision = "ignore"
                return

            print(f"⚡️ [路径A]: 小模型分析快照文本: '{text}'")
            
            prompt = config.INTERRUPT_PROMPT.format(text=text)
            response = self.small_llm_client.chat.completions.create(
                model=config.SMALL_LLM_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=10,
                timeout=8,
            )
            model_decision = response.choices[0].message.content.strip().lower()
            print(f"⚡️ [路径A]: 小模型决定 -> {model_decision}")

            if model_decision == "interrupt":
                print("‼️ [路径A]: 决定->打断并处理！")
                self.interrupt_event.set()
                decision = "process"
            else: # disinterrupt
                print("🤫 [路径A]: 决定->不打断并忽略。")
                self.interrupt_event.clear()
                decision = "ignore"

        except Exception as e:
             print(f"⚡️ [路径A]: 快速决策时出错: {e}。默认处理。")
             decision = "process"
             self.interrupt_event.set()
        finally:
            print(f"⚡️ [路径A]: 决策流程结束，将最终决策 '{decision}' 放入队列。")
            self.decision_queue.put(decision)

    def _apply_input_guardrails(self, user_text):
        if "捣乱" in user_text:
            print("🚧 [护栏]: 检测到无关输入，触发护栏。")
            self.interrupt_event.clear()
            self.tts_handler.play_audio_stream("请我们专注于当前任务。", self.interrupt_event)
            self.tts_handler.wait_for_completion()
            return True
        return False

    def _main_loop(self):
        while not self.stop_event.is_set():
            try:
                audio_data = self.user_speech_queue.get(timeout=1)
                print("💬 [主循环]: 正在处理队列中的新音频...")
                user_text = self._transcribe(audio_data)
                print(f"💬 [主循环]: 用户说: '{user_text}'")
                if self._apply_input_guardrails(user_text):
                    continue
                self.conversation_history.append({"role": "user", "content": user_text})
                self._trigger_large_llm()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"💬 [主循环]: 发生错误: {e}")

    def _queue_2_watcher(self):
        while not self.stop_event.is_set():
            try:
                if not self._is_system_busy() and not q2_queue.is_empty():
                    messages = q2_queue.get()
                    for message in messages:
                        print(f"📦 [消息监听]: 从电脑Agent处获得消息: '{message}'")
                        self.conversation_history.append({"role": "user", "content": f"[FROM_COMPUTER_AGENT] {message}"})
                    self._trigger_large_llm()
                else:
                    time.sleep(0.5)
            except Exception as e:
                print(f"📦 [消息监听]: 发生错误: {e}")

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

    def _trigger_large_llm(self):
        """触发大语言模型生成响应。"""
        try:
            ## -------------------- 最终的、关键的修复 -------------------- ##
            # 在生成任何新回复之前，清空TTS的待办列表
            self.tts_handler.clear_queue()
            ## -------------------- 修复结束 -------------------- ##

            self.interrupt_event.clear()
            
            response_stream = self.llm_handler.get_llm_response_stream(
                history=self.conversation_history,
                tools=self.tools
            )
            full_response_text = ""
            tool_call_in_progress = None
            for chunk_type, content in response_stream:
                if self.interrupt_event.is_set():
                    print("🤖 智能体: 大模型响应流被中断！")
                    break
                if chunk_type == "text":
                    self.tts_handler.play_audio_stream(content, self.interrupt_event)
                    full_response_text += content
                elif chunk_type == "tool_call":
                    tool_call_in_progress = content
                    break
            if tool_call_in_progress and not self.interrupt_event.is_set():
                tool_name = tool_call_in_progress.function.name
                tool_args = json.loads(tool_call_in_progress.function.arguments)
                print(f"🛠️ 智能体: 调用工具 '{tool_name}'，参数: {tool_args}")
                result = send_message_to_computer_agent(message=tool_args.get("message"))
                self.conversation_history.append({"role": "assistant", "content": None, "tool_calls": [tool_call_in_progress.model_dump()]})
                self.conversation_history.append({"role": "tool", "tool_call_id": tool_call_in_progress.id, "name": tool_name, "content": result})
                self._trigger_large_llm()
                return
            self.tts_handler.wait_for_completion()
            if not self.interrupt_event.is_set() and full_response_text.strip():
                self.conversation_history.append({"role": "assistant", "content": full_response_text.strip()})
        finally:
            self.interrupt_event.clear()

    def start(self):
        print("🚀 智能体: 正在启动...")
        self.audio_handler.start()
        self.main_thread.start()
        self.queue_2_watcher_thread.start()
        self.conversation_history.append({"role": "user", "content": "你好，请开始进行自我介绍和任务说明。"})
        self._trigger_large_llm()

    def stop(self):
        print("🛑 智能体: 正在停止...")
        self.stop_event.set()
        self.audio_handler.stop()
        self.tts_handler.cleanup()
        if self.main_thread.is_alive():
            self.main_thread.join()
        if self.queue_2_watcher_thread.is_alive():
            self.queue_2_watcher_thread.join()
        print("🛑 智能体: 已完全停止。")