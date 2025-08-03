# audio_handler.py

import pyaudio
import collections
import numpy as np
import onnxruntime as ort
import threading
import time
import os
import config

class AudioHandler:
    ## 主要修改 ##：在初始化时接收 fast_check_in_progress_event
    def __init__(self, on_speech_start, on_speech_end, fast_check_in_progress_event=None):
        self.on_speech_start = on_speech_start
        self.on_speech_end = on_speech_end
        self.stop_event = threading.Event()
        self.fast_check_in_progress = fast_check_in_progress_event

        self.vad_threshold = config.VAD_THRESHOLD
        self.min_speech_duration_samples = int(config.VAD_MIN_SPEECH_DURATION_MS / 1000 * config.AUDIO_SAMPLING_RATE)
        
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

        self.listen_thread = threading.Thread(target=self.listen_and_detect)

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
                    if not self.is_speaking:
                        print("🎤 音频处理器: 检测到语音开始。")
                        self.is_speaking = True
                        threading.Thread(target=self.on_speech_start).start()
                        
                        for prev_chunk in self.ring_buffer:
                            self.speech_buffer.append(prev_chunk)
                        self.ring_buffer.clear()
                    
                    self.speech_buffer.append(chunk)
                    self.silence_chunks_after_speech = 0
                else:
                    if self.is_speaking:
                        self.speech_buffer.append(chunk)
                        self.silence_chunks_after_speech += 1
                        
                        silence_duration_ms = self.silence_chunks_after_speech * config.VAD_FRAME_MS
                        if silence_duration_ms >= config.VAD_MAX_SILENCE_DURATION_MS:
                            print("🎤 音频处理器: 检测到语音结束。")
                            
                            ## 主要修改 ##：在处理结束前，等待快速检测完成
                            if self.fast_check_in_progress and self.fast_check_in_progress.is_set():
                                print("🎤 音频处理器: 等待快速检测完成...")
                                # 等待最多2秒，以防万一快速检测线程卡死
                                self.fast_check_in_progress.wait(timeout=2.0)
                            
                            final_audio = b''.join(list(self.speech_buffer))
                            
                            # 重置状态现在是安全的了
                            self.is_speaking = False
                            self.speech_buffer.clear()
                            self.ring_buffer.clear()
                            self.silence_chunks_after_speech = 0
                            
                            if len(final_audio) >= self.min_speech_duration_samples * 2:
                                threading.Thread(target=self.on_speech_end, args=(final_audio,)).start()
                    else:
                        self.ring_buffer.append(chunk)

            except Exception as e:
                print(f"🎤 音频处理器: 监听循环出错: {e}")
                self.is_speaking = False
                self.speech_buffer.clear()
                self.ring_buffer.clear()

    def start(self):
        self.listen_thread.start()

    def stop(self):
        self.stop_event.set()
        print("🎤 音频处理器: 正在停止...")
        if self.listen_thread.is_alive():
            self.listen_thread.join()
        if self.stream.is_active():
            self.stream.stop_stream()
        self.stream.close()
        self.p.terminate()
        print("🎤 音频处理器: 已停止。")