# tts_handler.py (健壮的队列清理)

import pyaudio
import config
import queue
import threading
from langdetect import detect
from utils.text_processor import preprocess_sentence

class TTSHandler:
    def __init__(self, client):
        self.client = client
        self.p = pyaudio.PyAudio()
        self.tts_queue = queue.Queue()
        self.stop_event = threading.Event()
        self._is_processing_audio = threading.Event()
        
        self.playback_stop_event = threading.Event()
        
        self.tts_thread = threading.Thread(target=self._process_tts_queue, daemon=True)
        self.tts_thread.start()

    def is_speaking(self):
        return self._is_processing_audio.is_set() or not self.tts_queue.empty()

    def clear_queue(self):
        """
        【核心修复】清空所有待播放的语音队列，并正确处理任务计数器以避免死锁。
        """
        print("🔊 TTS处理器: 清空待办语音队列...")
        while not self.tts_queue.empty():
            try:
                self.tts_queue.get_nowait()
                self.tts_queue.task_done()
            except queue.Empty:
                break
        # 双重保险，直接清空底层队列
        with self.tts_queue.mutex:
            self.tts_queue.queue.clear()


    def stop_current_playback(self):
        print("🔊 TTS处理器: 收到外部指令，请求中断当前播放。")
        self.playback_stop_event.set()

    def _process_tts_queue(self):
        while not self.stop_event.is_set():
            try:
                text, interrupt_event = self.tts_queue.get(timeout=0.1)
                self._is_processing_audio.set()

                try:
                    detected_lang = detect(text)
                except:
                    detected_lang = 'zh'

                processed_text = preprocess_sentence(text, detected_lang)

                if not processed_text.strip():
                    self.tts_queue.task_done()
                    continue

                print(f"🔊 TTS处理器: 正在播放 -> {processed_text}")
                stream = None
                try:
                    with self.client.audio.speech.with_streaming_response.create(
                        model=config.TTS_MODEL,
                        voice=config.TTS_VOICE,
                        response_format="pcm",
                        input=processed_text,
                    ) as response:
                        stream = self.p.open(
                            format=pyaudio.paInt16,
                            channels=config.AUDIO_CHANNELS,
                            rate=24000,
                            output=True
                        )
                        for chunk in response.iter_bytes(chunk_size=1024):
                            if interrupt_event.is_set() or self.playback_stop_event.is_set():
                                print("🔊 TTS处理器: 播放被中断。")
                                break
                            stream.write(chunk)
                
                except Exception as e:
                    print(f"🔊 TTS处理器: 播放音频流时出错: {e}")
                
                finally:
                    if stream:
                        stream.stop_stream()
                        stream.close()
                    # 确保task_done在任何情况下都会被调用
                    self.tts_queue.task_done()
                    
            except queue.Empty:
                continue

            finally:
                self.playback_stop_event.clear()
                self._is_processing_audio.clear()


    def play_audio_stream(self, text, interrupt_event):
        if not text.strip():
            return
        self.tts_queue.put((text, interrupt_event))

    def wait_for_completion(self):
        self.tts_queue.join()

    def cleanup(self):
        print("🔊 TTS处理器: 正在清理...")
        self.stop_current_playback()
        # 在清理前确保队列为空
        self.clear_queue()
        self.wait_for_completion()

        self.stop_event.set()
        if self.tts_thread.is_alive():
            self.tts_thread.join()
        self.p.terminate()
        print("🔊 TTS处理器: 已清理。")