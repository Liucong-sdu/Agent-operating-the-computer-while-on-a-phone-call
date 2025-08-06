# llm_handler.py (已更新)
import json
import config
import openai
import threading


class LLMHandler:
    def __init__(self, client):
        self.client = client
        self._is_active = False
        self._lock = threading.Lock()

    def is_active(self):
        with self._lock:
            return self._is_active
            
    def _set_active(self, active):
        with self._lock:
            self._is_active = active

    def _is_complete_sentence(self, text):
        if text.strip().endswith(('.', '?', '!', '。', '？', '！', ':', '：')):
            return True
        return False

    def get_llm_response_stream(self, history, tools=None): # <--- 【改造】允许 tools 为 None
        """
        从大模型获取流式响应，缓冲文本直到形成完整句子再yield。
        """
        self._set_active(True)
        print("🧠 LLM处理器: 正在获取大模型响应流...")
        
        sentence_buffer = ""
        
        try:
            # 【改造】根据 tools 是否存在，构造不同的请求参数
            request_params = {
                "model": config.LARGE_LLM_MODEL,
                "messages": history,
                "stream": True,
            }
            if tools:
                request_params["tools"] = tools
                request_params["tool_choice"] = "auto"

            stream = self.client.chat.completions.create(**request_params)

            tool_calls = []
            for chunk in stream:
                delta = chunk.choices[0].delta
                
                if delta and delta.content:
                    sentence_buffer += delta.content
                    
                    if self._is_complete_sentence(sentence_buffer):
                        print(f"🧠 LLM处理器: 产出一个完整句子 -> '{sentence_buffer.strip()}'")
                        yield "text", sentence_buffer.strip()
                        sentence_buffer = ""

                if delta and delta.tool_calls:
                    for tool_call_chunk in delta.tool_calls:
                        if len(tool_calls) <= tool_call_chunk.index:
                            tool_calls.append({"id": "", "type": "function", "function": {"name": "", "arguments": ""}})
                        
                        tc = tool_calls[tool_call_chunk.index]
                        if tool_call_chunk.id:
                            tc["id"] = tool_call_chunk.id
                        if tool_call_chunk.function.name:
                            tc["function"]["name"] = tool_call_chunk.function.name
                        if tool_call_chunk.function.arguments:
                            tc["function"]["arguments"] += tool_call_chunk.function.arguments

            if sentence_buffer.strip():
                print(f"🧠 LLM处理器: 产出流末尾的剩余文本 -> '{sentence_buffer.strip()}'")
                yield "text", sentence_buffer.strip()

            for tool_call in tool_calls:
                 if tool_call["id"] and tool_call["function"]["name"] and tool_call["function"]["arguments"]:
                    try:
                        json.loads(tool_call["function"]["arguments"])
                        yield "tool_call", openai.types.chat.chat_completion_message_tool_call.ChatCompletionMessageToolCall(**tool_call)
                    except json.JSONDecodeError:
                        print(f"🧠 LLM处理器: 警告 - 工具调用的参数不是一个完整的JSON: {tool_call['function']['arguments']}")
                        continue

        except Exception as e:
            print(f"🧠 LLM处理器: 获取LLM响应时出错: {e}")
        finally:
            self._set_active(False)
            print("🧠 LLM处理器: 响应流处理完成，状态已重置")