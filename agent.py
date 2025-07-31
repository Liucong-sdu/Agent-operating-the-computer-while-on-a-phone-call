import threading
import queue
import openai
import config
from audio_handler import AudioHandler
from llm_handler import LLMHandler
from tts_handler import TTSHandler
import wave # 导入wave库
import io   # 导入io库用于内存文件处理
import time
class VoiceAgent:
    """
    The main agent class that orchestrates the audio input, LLM, and TTS handlers.
    """
    def __init__(self):
        self.client = openai.OpenAI(api_key=config.OPENAI_API_KEY)
        # self.ollama_client = openai.OpenAI(api_key=config.OPENAI_API_KEY,base_url='http://localhost:11434/v1/')
        self.conversation_history = [{"role": "system", "content": config.SYSTEM_PROMPT}]
        
        self.audio_input_queue = queue.Queue()
        self.interrupt_event = threading.Event()
        self.is_agent_busy = threading.Event()
        self.stop_event = threading.Event()

        self.audio_handler = AudioHandler(self.audio_input_queue, self.interrupt_event)
        self.llm_handler = LLMHandler(self.client)
        self.tts_handler = TTSHandler(self.client)

        self.main_thread = threading.Thread(target=self._main_loop)
        self.audio_thread = threading.Thread(target=self._audio_loop)

    def _audio_loop(self):
        """The loop for the audio handler thread."""
        self.audio_handler.listen_and_detect(self.is_agent_busy)

    def _main_loop(self):
        """The main processing loop for the agent."""
        print("Agent: Main loop started.")
        while not self.stop_event.is_set():
            try:
                audio_data = self.audio_input_queue.get(timeout=1)
                self.is_agent_busy.set()
                self.interrupt_event.clear()

                # 1. Transcribe Audio
                print("Agent: Transcribing audio...")
                
                # Create a WAV file in memory to avoid slow disk I/O
                wav_buffer = io.BytesIO()
                with wave.open(wav_buffer, "wb") as wf:
                    wf.setnchannels(config.AUDIO_CHANNELS)
                    wf.setsampwidth(2)  # 2 bytes for paInt16
                    wf.setframerate(config.AUDIO_SAMPLING_RATE)
                    wf.writeframes(audio_data)
                wav_buffer.seek(0)
                
                # The file needs a name for the OpenAI API
                wav_buffer.name = "audio.wav"
                
                transcription = self.client.audio.transcriptions.create(
                    model=config.STT_MODEL,
                    file=wav_buffer
                )
                user_text = transcription.text
                print(f"Agent: User said: {user_text}")
                self.conversation_history.append({"role": "user", "content": user_text})

                # 2. Get LLM Response and Play TTS
                full_response = ""
                for sentence in self.llm_handler.get_llm_response_stream(self.conversation_history, self.interrupt_event):
                    if self.interrupt_event.is_set():
                        break
                    self.tts_handler.play_audio_stream(sentence, self.interrupt_event)
                    full_response += sentence + " "
            
                self.tts_handler.wait_for_completion()

                if not self.interrupt_event.is_set() and full_response.strip():
                    self.conversation_history.append({"role": "assistant", "content": full_response.strip()})

            except queue.Empty:
                continue
            except Exception as e:
                print(f"Agent: Error in main loop: {e}")
            finally:
                time.sleep(0.025)
                self.is_agent_busy.clear()

    def start(self):
        """Starts the agent's threads."""
        print("Agent: Starting...")
        self.audio_thread.start()
        self.main_thread.start()

    def stop(self):
        """Stops the agent's threads and cleans up."""
        print("Agent: Stopping...")
        self.stop_event.set()
        self.audio_handler.stop()
        self.tts_handler.cleanup()
        self.audio_thread.join()
        self.main_thread.join()
        print("Agent: Stopped.")