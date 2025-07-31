import re
import openai
import config

class LLMHandler:
    """
    Handles interactions with the Large Language Model (LLM), including streaming
    responses and splitting them into complete sentences for real-time processing.
    """
    def __init__(self, client):
        """
        Initializes the LLM Handler.

        Args:
            client (openai.OpenAI): The OpenAI client instance.
        """
        self.client = client

    def _is_complete_sentence(self, text, is_first_sentence=False):
        """Checks if the text forms a complete sentence."""
        trimmed_sentence = text.strip()

        # Check if we're inside a markdown code block
        if '```' in trimmed_sentence:
            count = trimmed_sentence.count('```')
            # If the count is odd, we're still inside a code block
            if count % 2 != 0:
                return False

        # Check if the sentence is a function call
        if '<function>' in trimmed_sentence:
            return '</function>' in trimmed_sentence

        # Check for newline
        if text.endswith('\n'):
            return True

        # Check for period, but not if it's a numbered list item
        if trimmed_sentence.endswith('.'):
            if re.search(r'[0-9]+\.$', trimmed_sentence):
                return False
            return True

        # Check for question mark or exclamation mark
        if trimmed_sentence.endswith('?') or trimmed_sentence.endswith('!'):
            return True

        # Check for Chinese punctuation
        if trimmed_sentence.endswith('。') or trimmed_sentence.endswith('？') or trimmed_sentence.endswith('！'):
            return True

        # Check for semicolons (both English and Chinese)
        if trimmed_sentence.endswith(';') or trimmed_sentence.endswith('；'):
            return True

        # Check if sentence ends with an emoji
        if len(trimmed_sentence) > 0:
            # Python's re module handles Unicode well, but for complex emoji sequences,
            # a dedicated library like 'emoji' might be more robust.
            # For now, a simple regex for common emoji ranges.
            # This regex might need adjustment for full Unicode emoji support.
            emoji_regex = re.compile(r'[\U0001F300-\U0001F9FF]|\u2600-\u26FF')
            if emoji_regex.search(trimmed_sentence[-2:]):
                return True

        # First sentence should be as short as possible
        if is_first_sentence:
            if trimmed_sentence.endswith(',') or trimmed_sentence.endswith('，'):
                return True

        return False

    def get_llm_response_stream(self, history, interrupt_event):
        """
        Gets a streaming response from the LLM and yields complete sentences.

        Args:
            history (list): The conversation history.
            interrupt_event (threading.Event): Event to signal an interruption.

        Yields:
            str: A complete sentence from the LLM's response.
        """
        print("LLMHandler: Getting response stream...")
        sentence_buffer = ""
        is_first_sentence = True # Track if it's the first sentence

        try:
            stream = self.client.chat.completions.create(
                model=config.LLM_MODEL,
                messages=history,
                stream=True
            )

            for chunk in stream:
                if interrupt_event.is_set():
                    print("LLMHandler: Interrupted.")
                    break

                delta = chunk.choices[0].delta.content
                if delta:
                    sentence_buffer += delta
                    
                    if self._is_complete_sentence(sentence_buffer, is_first_sentence):
                        yield sentence_buffer.strip()
                        sentence_buffer = ""
                        is_first_sentence = False # After the first sentence, set to False
            
            # Yield any remaining content in the buffer
            if sentence_buffer.strip() and not interrupt_event.is_set():
                yield sentence_buffer.strip()

        except Exception as e:
            print(f"LLMHandler: Error getting LLM response: {e}")