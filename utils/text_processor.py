import re

def remove_emoji(sentence):
    """
    使用一个标准的Unicode正则表达式，移除字符串中所有的表情符号。
    """
    emoji_pattern = re.compile("["
        u"\U0001F600-\U0001F64F"  # emoticons
        u"\U0001F300-\U0001F5FF"  # symbols & pictographs
        u"\U0001F680-\U0001F6FF"  # transport & map symbols
        u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
        u"\u2600-\u26FF"  # miscellaneous symbols
        u"\u2700-\u27BF"  # dingbats
        u"\U0001F900-\U0001F9FF"  # supplemental symbols and pictographs
                                "]+", flags=re.UNICODE)
    return emoji_pattern.sub(r' ', sentence).strip()

def markdown_to_text(markdown):
    """
    将常见的Markdown标记转换为纯文本，以便TTS朗读。
    """
    text = markdown
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)  # 移除链接，保留链接文本
    text = re.sub(r'^#+\s*', '', text, flags=re.MULTILINE)  # 移除标题
    text = re.sub(r'\*\*|__', '', text)  # 移除粗体
    text = re.sub(r'\*|_', '', text)  # 移除斜体
    text = re.sub(r'^>\s*', '', text, flags=re.MULTILINE)  # 移除引用
    text = re.sub(r'[-*_]{3,}', '', text)  # 移除水平线
    text = re.sub(r'^[-*+]\s*', '', text, flags=re.MULTILINE)  # 移除列表项标记
    text = re.sub(r'```', '', text)  # 移除代码块标记
    return text.strip()

def _number_to_words_en(num):
    """
    一个内部辅助函数，将整数转换为对应的英文单词。
    处理0-999,999,999,999范围内的数字。
    """
    ones = ['', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine']
    tens = ['', '', 'twenty', 'thirty', 'forty', 'fifty', 'sixty', 'seventy', 'eighty', 'ninety']
    teens = ['ten', 'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen', 'sixteen', 'seventeen', 'eighteen', 'nineteen']
    scales = ['', 'thousand', 'million', 'billion']

    if num == 0: return 'zero'

    def convert_group(n):
        """转换一个小于1000的数组"""
        result = ''
        if n >= 100:
            result += ones[n // 100] + ' hundred '
            n %= 100
        if n >= 20:
            result += tens[n // 10]
            n %= 10
            if n > 0:
                result += '-' + ones[n]
        elif n >= 10:
            result += teens[n - 10]
        elif n > 0:
            result += ones[n]
        return result.strip()

    result = ''
    group_index = 0
    while num > 0:
        group = num % 1000
        if group != 0:
            result = convert_group(group) + ' ' + scales[group_index] + ' ' + result
        num //= 1000
        group_index += 1
    return result.strip()

def pronounce_special_characters(text, is_code_block=False):
    """
    将特殊字符和标点符号替换为它们的可读英文单词。
    如果 is_code_block 为 True，则会替换更多的标点符号。
    """
    special_char_map = {
        '@': 'at', '#': 'hash', '$': 'dollar', '%': 'percent', '^': 'caret', '&': 'ampersand',
        '*': 'asterisk', '_': 'underscore', '=': 'equals', '+': 'plus', '[': 'left square bracket',
        ']': 'right square bracket', '{': 'left curly brace', '}': 'right curly brace',
        '|': 'vertical bar', '\\': 'backslash', '<': 'less than', '>': 'greater than',
        '/': 'slash', '`': 'backtick', '~': 'tilde',
    }

    # 这些标点只在代码块中被明确念出
    punctuation_map = {
        '!': 'exclamation', '.': 'dot', ',': 'comma', '?': 'question mark', ';': 'semicolon',
        ':': 'colon', '"': 'double quote', "'": 'single quote', '-': 'minus',
        '(': 'left parenthesis', ')': 'right parenthesis',
    }

    processed_text = text
    for char, pronunciation in special_char_map.items():
        processed_text = processed_text.replace(char, f' {pronunciation} ')

    if is_code_block:
        for char, pronunciation in punctuation_map.items():
            processed_text = processed_text.replace(char, f' {pronunciation} ')

    return processed_text

def pronounce_numbers(text, language):
    """
    在文本中查找数字，并将其替换为英文单词形式。
    中文则不作处理。
    """
    if language.startswith('zh'):
        return text

    def replace_func(match):
        num_str = match.group(0)
        try:
            if '.' in num_str:
                integer_part, decimal_part = num_str.split('.')
                integer_words = _number_to_words_en(int(integer_part))
                decimal_words = ' '.join([_number_to_words_en(int(d)) for d in decimal_part])
                return f'{integer_words} point {decimal_words}'
            return _number_to_words_en(int(num_str))
        except (ValueError, IndexError): # 如果转换失败，返回原字符串
            return num_str

    return re.sub(r'(\d+\.?\d*)', replace_func, text)

def remove_emotions(text):
    """
    移除由星号包围的情感或动作描述，例如 *叹气*。
    """
    return re.sub(r'\*[a-zA-Z0-9 -]+\*', '', text).strip()

def pronounce_code_block(text):
    """
    查找行内代码和代码块，并对其内容应用特殊的发音规则。
    """
    def replace_func(match):
        # 匹配 `...` 或 ```...```
        content = match.group(1) if match.group(1) else match.group(2)
        return pronounce_special_characters(content, is_code_block=True)

    # Regex to match inline code (`) or code blocks (```)
    return re.sub(r'`([^`\n]+)`|```([\s\S]*?)```', replace_func, text)

def preprocess_sentence(sentence, language='en'):
    """
    对单句进行全面的预处理，是供 tts_handler.py 调用的主函数。
    它按照特定顺序调用其他辅助函数。
    """
    processed = sentence
    
    # 步骤 1: 优先处理代码块，因为它们有特殊的发音规则
    processed = pronounce_code_block(processed)
    
    # 步骤 2: 将剩余的Markdown转为纯文本
    processed = markdown_to_text(processed)
    
    # 步骤 3: 将数字转为单词（主要对英文有效）
    processed = pronounce_numbers(processed, language)
    
    # 步骤 4: 移除情感描述
    processed = remove_emotions(processed)
    
    # 步骤 5: 处理剩余的特殊字符
    processed = pronounce_special_characters(processed, is_code_block=False)
    
    # 步骤 6: 移除表情符号
    processed = remove_emoji(processed)
    
    # 步骤 7: 返回最终清理过的、准备好进行TTS的文本
    return " ".join(processed.split()) # 将多个空格合并为一个