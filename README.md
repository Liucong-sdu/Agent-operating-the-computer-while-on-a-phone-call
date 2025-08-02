
---

## **协同语音与操作双智能体系统 - 开发文档**

### 1. 项目概述

#### 1.1 项目目标

本项目旨在解决一个复杂的人机交互场景：AI智能体需要同时通过语音与用户沟通，并操作电脑上的图形界面（如填写网页表单）。传统的单体智能体难以胜任这种高实时性、高并发性的“一心二用”任务。

为应对此挑战，我们设计并实现了一个多智能体协同系统的核心部分——**电话Agent (Voice Agent)**。它被设计成可以与一个独立的**电脑Agent**进行高效通信，共同完成复杂任务。

#### 1.2 核心理念

本系统的核心是**职责分离**与**异步通信**。
*   **职责分离**：电话Agent专注于处理所有与语音相关的任务（听、理解、说），电脑Agent（本项目中为模拟接口）专注于执行具体的操作。
*   **异步通信**：两个Agent之间通过消息队列和工具调用进行解耦的、非阻塞的通信，确保一方在执行耗时任务时，另一方仍能保持响应。

### 2. 系统核心架构

系统围绕 `VoiceAgent` 类构建，它作为总指挥，协调以下几个核心模块的工作：

*   **Audio Handler (耳朵)**: 持续监听麦克风，利用VAD（Voice Activity Detection）技术检测用户的语音起止，并捕获完整的语音数据。
*   **LLM Handler (大脑)**: 与大语言模型（LLM）进行交互，负责理解用户意图、生成回复、以及决定是否调用工具。
*   **TTS Handler (嘴巴)**: 将LLM生成的文本回复转换为流畅的语音并进行播放。
*   **双LLM引擎 (决策中枢)**:
    *   **Large LLM (如GPT-4o)**: 负责处理核心对话逻辑、理解复杂意图和执行工具调用。
    *   **Small LLM (本地Ollama模型)**: 负责在AI说话时，对用户的插入语进行快速、低成本的意图分类（判断是有效打断还是无意义的附和）。
*   **通信接口 (信使)**:
    *   `computer_agent_interface`: 模拟了与电脑Agent的双向通信通道。



### 3. 关键机制详解

#### 3.1 双LLM协同策略

为了兼顾响应速度与对话质量，我们采用了“一大一小”双模型策略：

*   **Small LLM (`qwen3:14b-q4_K_M`)**:
    *   **作用**: 专门用于“快速打断检测”。
    *   **优势**: 本地运行，响应极快，成本几乎为零。对于“判断是否打断”这种简单的分类任务，性能绰绰有余。
    *   **触发时机**: 仅当AI正在说话（`large_llm_busy`为`True`）且用户开始说话时触发。

*   **Large LLM (`gpt-4o`)**:
    *   **作用**: 负责所有主要的对话理解和生成任务。
    *   **优势**: 模型能力强，能理解上下文、遵循指令、并以结构化的方式调用工具。
    *   **触发时机**: 在处理用户的完整语音输入，或收到来自电脑Agent的消息时触发。

#### 3.2 核心工作流程：并发打断机制 (路径A/B)

这是整个系统最核心、最精巧的设计，它确保了流畅的打断体验。

1.  **逻辑分叉点**: `on_speech_start` 函数是所有逻辑的起点。它首先检查 `large_llm_busy` 事件。

2.  **场景一：AI空闲 (`large_llm_busy` is `False`)**
    *   用户开始说话。
    *   系统判断AI空闲，认为这是一次正常的对话输入。
    *   **不执行**任何快速检测。
    *   **只执行路径B**: `audio_handler` 会安靜地录下用户的整句话，直到用户说完。
    *   `on_speech_end` 将完整的音频放入 `user_speech_queue`。
    *   `_main_loop` 从队列中取出音频，交给大模型处理。

3.  **场景二：AI正忙 (`large_llm_busy` is `True`)**
    *   用户在AI说话时插入。
    *   系统判断AI正忙，认为这可能是一次打断。
    *   **同时启动路径A和路径B**。
    *   **路径A (快速打断检测)**:
        *   `_fast_interrupt_check` 线程启动。
        *   它会等待一个在 `config.py` 中定义的固定时长 `FAST_CHECK_DURATION_S`（例如2秒）。
        *   等待结束后，它从 `audio_handler` 的实时缓冲区中截取这段固定时长的音频快照。
        *   将快照STT转录后，发给**Small LLM**。
        *   根据Small LLM返回的 `interrupt` 或 `disinterrupt`，决定是否设置 `interrupt_event` 事件。这个事件会直接命令 `tts_handler` 停止当前播放。
    *   **路径B (完整录音)**:
        *   与场景一完全相同，`audio_handler` 不受路径A影响，继续完整地录下用户的整句话。
        *   用户说完后，`on_speech_end` 将**完整的**音频放入 `user_speech_queue`。
    *   **最终处理**: `_main_loop` 最终会处理这条来自路径B的完整录音。由于路径A可能已经设置了 `interrupt_event` 提前终止了AI的上一句话，使得交互体验非常流畅。

#### 3.3 稳健的音频处理

`audio_handler.py` 采用了事件驱动和智能缓冲机制，以应对复杂的现实环境：

*   **VAD为核心**: 使用Silero VAD模型实时分析音频流，判断每一小块音频是语音还是静音。
*   **智能缓冲**:
    *   `ring_buffer`: 在未检测到语音时，它像一个小的“行车记录仪”，持续保留最近的几块静音音频。一旦检测到语音，这些静音块会被拼接到录音的开头，确保不会因为VAD的微小延迟而丢失句首的音节。
    *   `speech_buffer`: 一旦检测到语音，所有后续的音频块（包括语音和可能的句中停顿）都会被加入这个缓冲区，直到VAD检测到持续的静音超过预设阈值。
*   **参数化调优**: `config.py` 中的 `VAD_THRESHOLD` 和 `VAD_MAX_SILENCE_DURATION_MS` 是调优的关键。开发者可以根据实际麦克风和环境噪音水平，调整这些参数，以达到最佳的语音捕获效果。

#### 3.4 Agent间通信

*   **电话Agent -> 电脑Agent**: 通过`send_message_to_computer_agent`工具实现。当大模型认为需要通知电脑Agent时（例如，获取到了用户名），它会在生成的回复中包含一个对此工具的调用。
*   **电脑Agent -> 电话Agent**: 通过一个共享的 `queue_2` 队列实现。`_queue_2_watcher` 线程在后台持续监听此队列。为了避免冲突，它只在 `large_llm_busy` 为 `False`（即AI空闲）时，才从队列中取出消息并触发大模型进行处理。

### 4. 代码模块解析

*   **`main.py`**: **程序入口**。负责初始化并启动 `VoiceAgent`，并处理 `Ctrl+C` 中断以实现优雅退出。
*   **`config.py`**: **全局配置中心**。所有可调参数，如API密钥、模型名称、VAD阈值、采样时长等，都在此定义，便于集中管理和修改。
*   **`agent.py`**: **系统总指挥**。实现了所有核心业务逻辑，包括：
    *   `__init__`: 初始化所有模块和状态变量。
    *   `on_speech_start`/`on_speech_end`: 事件回调函数，是A/B路径逻辑的分叉点和汇合点。
    *   `_fast_interrupt_check`: 路径A的实现，负责快速打断。
    *   `_main_loop`: 路径B的主要处理流程，负责处理完整的用户语音。
    *   `_queue_2_watcher`: 监听来自电脑Agent消息的独立线程。
    *   `_trigger_large_llm`: 封装了调用大模型、处理回复（文本或工具）、以及调用TTS的完整流程。
    *   `_apply_input_guardrails`: 输入护栏的实现，用于过滤无效输入。
*   **`audio_handler.py`**: **音频处理器**。封装了所有与PyAudio和VAD模型的底层交互，向上层提供干净的 `on_speech_start` 和 `on_speech_end` 事件回调。
*   **`llm_handler.py`**: **大模型交互器**。负责与OpenAI API进行流式通信，并加入了句子缓冲逻辑，确保向TTS输送的是完整的句子，优化听感。
*   **`tts_handler.py`**: **语音合成器**。负责接收文本，调用TTS API，并通过PyAudio将返回的音频流播放出来。它也监听 `interrupt_event` 以实现即时停止。
*   **`computer_agent_interface.py`**: **模拟通信接口**。定义了两个Agent间通信的函数和队列。
*   **`utils/text_processor.py`**: **文本预处理器**。在文本送入TTS前，对其进行清理（如移除Markdown标记、转换特殊字符等），确保语音合成质量。

### 5. 安装与运行指南

1.  **环境准备**:
    *   安装 Python 3.8+。
    *   在项目根目录创建 `.env` 文件，并填入 `OPENAI_API_KEY="sk-..."`。
    *   安装并运行 [Ollama](https://ollama.com/)。
    *   在终端运行 `ollama pull qwen3:14b-q4_K_M` (或您在`config.py`中指定的其他模型)。
    *   将 `silero_vad.onnx` 模型文件放入 `models` 文件夹。
2.  **安装依赖**:
    ```bash
    pip install -r requirements.txt
    ```
3.  **启动程序**:
    ```bash
    python main.py
    ```

### 6. 自定义与扩展

*   **更换模型**: 在 `config.py` 中修改 `LARGE_LLM_MODEL` 和 `SMALL_LLM_MODEL` 的值即可。
*   **调整灵敏度**:
    *   **打断灵敏度**: 修改 `config.py` 中的 `FAST_CHECK_DURATION_S` (秒)，增加时长会让小模型识别更准，但会略微增加打断的延迟。
    *   **语音检测灵敏度**: 修改 `config.py` 中的 `VAD_THRESHOLD` (建议范围0.5-0.7) 和 `VAD_MAX_SILENCE_DURATION_MS` (建议范围500-1000)。
*   **增强护栏**: 在 `agent.py` 的 `_apply_input_guardrails` 函数中，可以引入更复杂的逻辑，例如调用一个专门的分类模型来判断用户意图是否与任务相关。
*   **添加新工具**:
    1.  在 `agent.py` 的 `__init__` 方法中，向 `self.tools` 列表中添加新的工具定义JSON。
    2.  在 `_trigger_large_llm` 方法中，为新的工具名称添加一个 `elif chunk_type == "tool_call" and tool_name == "your_new_tool"` 的处理分支。
    3.  在项目其他地方实现新工具的具体功能函数。

---
