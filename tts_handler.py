import pyaudio
import config
import queue
import threading
import time
from langdetect import detect
from utils.text_processor import preprocess_sentence

class TTSHandler:
    """
    Handles text-to-speech (TTS) conversion and audio playback.
    It takes text, converts it to an audio stream, and plays it.
    """
    def __init__(self, client):
        """
        Initializes the TTS Handler.

        Args:
            client (openai.OpenAI): The OpenAI client instance.
        """
        self.client = client
        self.p = pyaudio.PyAudio()
        self.tts_queue = queue.Queue() # Queue for TTS requests
        self.is_processing_tts = threading.Event() # Flag to indicate if TTS is currently processing
        self.stop_event = threading.Event()

        self.tts_thread = threading.Thread(target=self._process_tts_queue) # Thread to process TTS queue
        self.tts_thread.start()

    def _process_tts_queue(self):
        """Processes items from the TTS queue."""
        while not self.stop_event.is_set():
            try:
                text, interrupt_event = self.tts_queue.get(timeout=0.1)
                self.is_processing_tts.set()
                
                # Language detection
                try:
                    detected_lang = detect(text)
                except Exception:
                    detected_lang = 'en' # Default to English if detection fails

                # Preprocess the text
                processed_text = preprocess_sentence(text, detected_lang)

                if not processed_text.strip():
                    print("TTSHandler: Skipping empty preprocessed text.")
                    self.is_processing_tts.clear()
                    self.tts_queue.task_done()
                    continue

                print(f"TTSHandler: Processing queued text (lang: {detected_lang}) -> {processed_text}")
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
                            rate=24000,  # OpenAI TTS response format is 24kHz
                            output=True
                        )

                        for chunk in response.iter_bytes(chunk_size=1024):
                            if interrupt_event.is_set():
                                print("TTSHandler: Interrupted during playback.")
                                
                                # ---【重要修改】---
                                # 错误的方式：直接清空，导致死锁
                                # with self.tts_queue.mutex:
                                #     self.tts_queue.queue.clear()

                                # 正确的方式：排干队列，为每个被丢弃的任务调用 task_done()
                                while not self.tts_queue.empty():
                                    try:
                                        # 从队列中取出一个项目，但不处理它
                                        self.tts_queue.get_nowait()
                                        # 立即标记为任务完成，以解除主线程的 join() 等待
                                        self.tts_queue.task_done()
                                    except queue.Empty:
                                        break # 理论上不会发生，作为安全措施
                                # ---【修改结束】---
                                
                                break # 跳出当前音频块的播放循环
                            stream.write(chunk)
                
                except Exception as e:
                    print(f"TTSHandler: Error playing audio stream: {e}")
                
                finally:
                    if stream:
                        stream.stop_stream()
                        stream.close()
                    self.is_processing_tts.clear()
                self.tts_queue.task_done()

            except queue.Empty:
                continue
            except Exception as e:
                print(f"TTSHandler: Error in TTS queue processing: {e}")
                self.is_processing_tts.clear()

    def play_audio_stream(self, text, interrupt_event):
        """
        Adds text to the TTS queue for conversion and playback.

        Args:
            text (str): The text to be converted to speech.
            interrupt_event (threading.Event): Event to signal an interruption.
        """
        if not text.strip():
            return
        print(f"TTSHandler: Adding to queue -> {text}")
        self.tts_queue.put((text, interrupt_event))

    def wait_for_completion(self):
        """Blocks until the TTS queue is empty and all items have been processed."""
        print("TTSHandler: Waiting for queue to complete...")
        self.tts_queue.join()
        print("TTSHandler: Queue completed.")

    def cleanup(self):
        """Cleans up the PyAudio instance and stops the TTS thread."""
        self.stop_event.set()
        self.tts_thread.join()
        self.p.terminate()

