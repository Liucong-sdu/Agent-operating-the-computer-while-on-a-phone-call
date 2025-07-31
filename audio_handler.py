import pyaudio
import collections
import numpy as np
import onnxruntime as ort
import threading
import time
import os
import config

class AudioHandler:
    """
    Handles audio input, voice activity detection (VAD), and buffering.
    It listens to the microphone, detects speech using the Silero VAD model,
    and puts complete speech segments into a queue for further processing.
    """
    def __init__(self, output_queue, interrupt_event):
        """
        Initializes the Audio Handler.

        Args:
            output_queue (queue.Queue): A queue to put the recorded audio data into.
            interrupt_event (threading.Event): An event to signal an interruption.
        """
        self.output_queue = output_queue
        self.interrupt_event = interrupt_event
        self.stop_event = threading.Event()

        # --- VAD Initialization ---
        self.vad_threshold = config.VAD_THRESHOLD
        self.min_speech_duration_samples = int(config.VAD_MIN_SPEECH_DURATION_MS / 1000 * config.VAD_SAMPLING_RATE)
        self.max_silence_samples = int(config.VAD_MAX_SILENCE_DURATION_MS / 1000 * config.VAD_SAMPLING_RATE)
        
        model_path = os.path.join(os.path.dirname(__file__), 'models', 'silero_vad.onnx')
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Silero VAD model not found at {model_path}")
            
        self.vad_session = ort.InferenceSession(model_path)
        self.reset_vad_state()

        # --- Audio Stream Initialization ---
        # 打开麦克风,这里配置了音频的格式（16位整数）、通道数（单声道）、采样率（16000Hz）和块大小。input=True 表示这是个录音流
        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(
            format=pyaudio.paInt16,
            channels=config.AUDIO_CHANNELS,
            rate=config.AUDIO_SAMPLING_RATE,
            input=True,
            frames_per_buffer=config.AUDIO_CHUNK_SIZE
        )

        # --- State Variables ---
        self.is_speaking = False
        self.speech_buffer = bytearray() #一个字节数组，像一个录音带，用来拼接当前正在说的这一整句话的音频
        self.silence_samples_after_speech = 0
        
        # Ring buffer to catch audio just before speech starts
        self.ring_buffer_size = 15  # Number of frames to keep,这是一个非常巧妙的设计。它是一个固定大小的队列，总是在内存中保留着最近的 15 块音频。它的作用是捕捉到用户说话前的一小段音频，这样可以防止因为 VAD 模型反应稍慢而导致一句话开头的音节被切掉
        self.ring_buffer = collections.deque(maxlen=self.ring_buffer_size)

    def reset_vad_state(self):
        """Resets the VAD model's internal state for a new detection session."""
        # 使用一个统一的 state 张量，以匹配新版模型的接口
        self._state = np.zeros((2, 1, 128), dtype=np.float32)

    def _process_chunk(self, chunk):
        """Processes a single audio chunk through the VAD model."""
        audio_int16 = np.frombuffer(chunk, dtype=np.int16)
        audio_float32 = audio_int16.astype(np.float32) / 32768.0

        # 1. 创建模型需要的采样率输入
        sr_input = np.array([config.VAD_SAMPLING_RATE], dtype=np.int64)

        # 2. 构建正确的输入字典
        ort_inputs = {
            'input': np.expand_dims(audio_float32, axis=0), # 确保input是二维的 [1, n_samples]
            'sr': sr_input,
            'state': self._state
        }
        
        # 3. 运行模型并获取新的输出
        ort_outs = self.vad_session.run(None, ort_inputs)
        speech_prob = float(np.array(ort_outs[0]).squeeze())# 第一个输出是语音概率
        self._state = ort_outs[1]      # 第二个输出是更新后的 state
        
        return speech_prob > self.vad_threshold

    def listen_and_detect(self, is_agent_busy):
        """
        Main loop to listen for audio and detect speech.
        This should be run in a separate thread.

        Args:
            is_agent_busy (threading.Event): An event indicating if the agent is currently speaking.
        """
        print("AudioHandler: Listening...")
        self.reset_vad_state()
        
        while not self.stop_event.is_set():
            try:
                chunk = self.stream.read(config.AUDIO_CHUNK_SIZE, exception_on_overflow=False)
                
                if self.is_speaking:
                    self.speech_buffer.extend(chunk)
                else:
                    self.ring_buffer.append(chunk)

                is_speech = self._process_chunk(chunk)

                if is_speech and not self.is_speaking:
                    self.is_speaking = True
                    print("AudioHandler: Speech started.")
                    if is_agent_busy.is_set():
                        print("AudioHandler: Interrupt detected!")
                        self.interrupt_event.set()
                    
                    self.speech_buffer.extend(b''.join(self.ring_buffer))
                    self.ring_buffer.clear()
                    self.silence_samples_after_speech = 0
                
                elif not is_speech and self.is_speaking:
                    self.silence_samples_after_speech += config.AUDIO_CHUNK_SIZE
                    if self.silence_samples_after_speech >= self.max_silence_samples:
                        print("AudioHandler: Speech ended.")
                        if len(self.speech_buffer) >= self.min_speech_duration_samples * 2:
                            self.output_queue.put(bytes(self.speech_buffer))
                        
                        self.is_speaking = False
                        self.speech_buffer = bytearray()
                        self.reset_vad_state()

            except Exception as e:
                print(f"AudioHandler: Error in listening loop: {e}")
                time.sleep(1)

    def stop(self):
        """Stops the listening loop and cleans up resources."""
        self.stop_event.set()
        print("AudioHandler: Stopping...")
        if self.stream.is_active():
            self.stream.stop_stream()
        self.stream.close()
        self.p.terminate()
        print("AudioHandler: Stopped.")