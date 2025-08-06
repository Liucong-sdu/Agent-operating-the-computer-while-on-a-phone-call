# audio_handler.py (最终优化版 - 根治线程饿死问题)

import pyaudio
import collections
import numpy as np
import onnxruntime as ort
import threading
import time
import os
import config

class AudioHandler:
    def __init__(self, on_speech_start, on_speech_end):
        self.on_speech_start = on_speech_start
        self.on_speech_end = on_speech_end
        self.stop_event = threading.Event()
        self.buffer_lock = threading.Lock() # 新增：用于保护共享缓冲区的锁

        self.vad_threshold = config.VAD_THRESHOLD
        self.min_speech_duration_samples = int(config.VAD_MIN_SPEECH_DURATION_MS / 1000 * config.AUDIO_SAMPLING_RATE)
        
        self.cooldown_until = 0
        self.cooldown_duration_s = 0.5 

        model_path = os.path.join(os.path.dirname(__file__), 'models', 'silero_vad.onnx')
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Silero VAD 模型未在 {model_path} 找到")
            
        self.vad_session = ort.InferenceSession(model_path)
        self._state = np.zeros((2, 1, 128), dtype=np.float32)
        self.sr_input = np.array([config.VAD_SAMPLING_RATE], dtype=np.int64)

        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(
            format=pyaudio.paInt16,
            channels=config.AUDIO_CHANNELS,
            rate=config.AUDIO_SAMPLING_RATE,
            input=True,
            frames_per_buffer=config.AUDIO_CHUNK_SIZE
        )

        self.is_speaking = False
        self.speech_buffer = collections.deque()
        self.silence_chunks_after_speech = 0
        self.ring_buffer = collections.deque(maxlen=5)

        self.listen_thread = threading.Thread(target=self.listen_and_detect, daemon=True)

    def get_speech_buffer_snapshot(self):
        # 线程安全地获取缓冲区的快照
        with self.buffer_lock:
            return b''.join(self.speech_buffer)

    def _process_chunk(self, chunk):
        audio_int16 = np.frombuffer(chunk, dtype=np.int16)
        audio_float32 = audio_int16.astype(np.float32) / 32768.0
        ort_inputs = {
            'input': np.expand_dims(audio_float32, axis=0),
            'sr': self.sr_input,
            'state': self._state
        }
        ort_outs = self.vad_session.run(None, ort_inputs)
        self._state = ort_outs[1]
        speech_prob = ort_outs[0].item()
        return speech_prob > self.vad_threshold

    def listen_and_detect(self):
        print("🎤 音频处理器: 开始监听...")
        while not self.stop_event.is_set():
            try:
                chunk = self.stream.read(config.AUDIO_CHUNK_SIZE, exception_on_overflow=False)
                is_speech = self._process_chunk(chunk)

                if is_speech:
                    if not self.is_speaking and time.time() > self.cooldown_until:
                        print("🎤 音频处理器: 检测到语音开始。")
                        self.is_speaking = True
                        # 启动一个新线程来处理 on_speech_start，避免阻塞 VAD 循环
                        threading.Thread(target=self.on_speech_start).start()
                        
                        # 在锁保护下将 ring_buffer 的内容转移到 speech_buffer
                        with self.buffer_lock:
                            for prev_chunk in self.ring_buffer:
                                self.speech_buffer.append(prev_chunk)
                            self.ring_buffer.clear()
                    
                    if self.is_speaking:
                        # 在锁保护下向 speech_buffer 添加数据
                        with self.buffer_lock:
                            self.speech_buffer.append(chunk)
                        self.silence_chunks_after_speech = 0
                else:
                    if self.is_speaking:
                        with self.buffer_lock:
                            self.speech_buffer.append(chunk)
                        self.silence_chunks_after_speech += 1
                        
                        silence_duration_ms = self.silence_chunks_after_speech * config.VAD_FRAME_MS
                        if silence_duration_ms >= config.VAD_MAX_SILENCE_DURATION_MS:
                            print("🎤 音频处理器: 检测到语音结束。")
                            self.cooldown_until = time.time() + self.cooldown_duration_s
                            
                            with self.buffer_lock:
                                final_audio = b''.join(list(self.speech_buffer))
                                self.speech_buffer.clear()

                            self.is_speaking = False
                            self.ring_buffer.clear()
                            self.silence_chunks_after_speech = 0
                            
                            if len(final_audio) >= self.min_speech_duration_samples * 2:
                                threading.Thread(target=self.on_speech_end, args=(final_audio,)).start()
                    else:
                        self.ring_buffer.append(chunk)

            except Exception as e:
                print(f"🎤 音频处理器: 监听循环出错: {e}")
                self.is_speaking = False
                with self.buffer_lock:
                    self.speech_buffer.clear()
                self.ring_buffer.clear()
            
            # 【终极修复】强制线程休息0.01秒，将CPU时间（和GIL）让给其他线程
            time.sleep(0.01)

    def start(self):
        self.listen_thread.start()

    def stop(self):
        self.stop_event.set()
        print("🎤 音频处理器: 正在停止...")
        if self.listen_thread.is_alive():
            self.listen_thread.join(timeout=2)
        if self.stream.is_active():
            self.stream.stop_stream()
        self.stream.close()
        self.p.terminate()
        print("🎤 音频处理器: 已停止。")