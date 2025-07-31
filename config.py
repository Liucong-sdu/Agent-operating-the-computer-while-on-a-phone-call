import os
from dotenv import load_dotenv

load_dotenv(override=True)

# --- API Keys ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# --- LLM Configuration ---
# LLM_MODEL = "gpt-4.1-nano-2025-04-14"
LLM_MODEL="gpt-4.1-nano-2025-04-14"

# --- Transcription Configuration ---
STT_MODEL = "gpt-4o-mini-transcribe"

# --- TTS Configuration ---
TTS_MODEL = "gpt-4o-mini-tts"
TTS_VOICE = "alloy"

# --- VAD Configuration (based on Silero VAD) ---
VAD_SAMPLING_RATE = 16000
VAD_FRAME_MS = 30  # Frame duration in milliseconds
VAD_FRAME_SAMPLES = int(VAD_SAMPLING_RATE * (VAD_FRAME_MS / 1000.0))
VAD_THRESHOLD = 0.35  # Speech probability threshold
VAD_MIN_SPEECH_DURATION_MS = 250  # Minimum duration for a speech segment
VAD_MAX_SILENCE_DURATION_MS = 500  # End speech after this duration of silence

# --- Audio Configuration ---
AUDIO_FORMAT = "int16" # Corresponds to pyaudio.paInt16
AUDIO_CHANNELS = 1
AUDIO_SAMPLING_RATE = 16000 # Must match VAD_SAMPLING_RATE
AUDIO_CHUNK_SIZE = VAD_FRAME_SAMPLES

# --- System Configuration ---
# 全新优化后的提示 (鼓励多样性):
SYSTEM_PROMPT = """你是一个乐于助人的AI助手。请让你的回复简洁明了。
为了让对话更自然、更有人情味，请在回答主要内容前，使用一个多样化、不重复的简短口语作为开头。
请根据对话的上下文，在下面这些例子中自由选择或创造新的开头，避免每次都一样：
- "好的，"
- "没问题，"
- "是这样的，"
- "这么说吧，"
- "嗯，可以，"
- "行，"
- "了解。"
- "我看看，"
- "这么理解："
- "简单来说，"
"""