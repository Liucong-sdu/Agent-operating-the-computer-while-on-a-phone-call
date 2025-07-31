import re

def remove_emoji(sentence):
    # 使用一个更安全、更标准的Emoji正则表达式
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
    text = markdown
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)  # Remove links
    text = re.sub(r'^#+\s*', '', text, flags=re.MULTILINE)  # Remove headers
    text = re.sub(r'\*\*|__', '', text)  # Remove bold
    text = re.sub(r'\*|_', '', text)  # Remove italics
    text = re.sub(r'^>\s*', '', text, flags=re.MULTILINE)  # Remove blockquotes
    text = re.sub(r'[-*_]{3,}', '', text)  # Remove horizontal rules
    text = re.sub(r'^[-*+]\s*', '', text, flags=re.MULTILINE)  # Remove list markers
    text = re.sub(r'```', '', text)  # Remove code block markers
    return text.strip()

def _number_to_words_en(num):
    ones = ['', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine']
    tens = ['', '', 'twenty', 'thirty', 'forty', 'fifty', 'sixty', 'seventy', 'eighty', 'ninety']
    teens = ['ten', 'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen', 'sixteen', 'seventeen', 'eighteen', 'nineteen']
    scales = ['', 'thousand', 'million', 'billion']

    if num == 0: return 'zero'

    def convert_group(n):
        result = ''
        if n >= 100:
            result += ones[n // 100] + ' hundred '
            n %= 100
        if n >= 20:
            result += tens[n // 10] + ' '
            n %= 10
            if n > 0:
                result += ones[n] + ' '
        elif n >= 10:
            result += teens[n - 10] + ' '
        elif n > 0:
            result += ones[n] + ' '
        return result

    result = ''
    group_index = 0
    while num > 0:
        group = num % 1000
        if group != 0:
            result = convert_group(group) + scales[group_index] + ' ' + result
        num //= 1000
        group_index += 1
    return result.strip()

def pronounce_special_characters(text, is_code_block=False):
    special_char_map = {
        '@': 'at',
        '#': 'hash',
        '$': 'dollar',
        '%': 'percent',
        '^': 'caret',
        '&': 'ampersand',
        '*': 'asterisk',
        '_': 'underscore',
        '=': 'equals',
        '+': 'plus',
        '[': 'left square bracket',
        ']': 'right square bracket',
        '{': 'left curly brace',
        '}': 'right curly brace',
        '|': 'vertical bar',
        '\\': 'backslash',
        '<': 'less than',
        '>': 'greater than',
        '/': 'slash',
        '`': 'backtick',
        '~': 'tilde',
    }

    punctuation_map = {
        '!': 'exclamation',
        '.': 'dot',
        ',': 'comma',
        '?': 'question mark',
        ';': 'semicolon',
        ':': 'colon',
        '"': 'double quote',
        "'": 'single quote',
        '-': 'minus',
        '(': 'left parenthesis',
        ')': 'right parenthesis',
    }

    processed_text = text
    for char, pronunciation in special_char_map.items():
        processed_text = processed_text.replace(char, f' {pronunciation} ')

    if is_code_block:
        for char, pronunciation in punctuation_map.items():
            processed_text = processed_text.replace(char, f' {pronunciation} ')

    return processed_text

def pronounce_numbers(text, language):
    if language.startswith('zh'): return text

    def replace_func(match):
        num_str = match.group(0)
        if '.' in num_str:
            integer, decimal = num_str.split('.')
            decimal_words = ' '.join([_number_to_words_en(int(d)) for d in decimal])
            return f'{_number_to_words_en(int(integer))} point {decimal_words}'
        return _number_to_words_en(int(num_str))

    return re.sub(r'(\d+\.?\d*)', replace_func, text)

def remove_emotions(text):
    return re.sub(r'\*[a-zA-Z0-9 -]*\*', '', text).strip()

def pronounce_code_block(text):
    def replace_func(match):
        content = match.group(1) if match.group(1) else match.group(2)
        return pronounce_special_characters(content, True)

    # Regex to match inline code (`)` or code blocks (```)``
    return re.sub(r'`([^`\n]+)`|```([\s\S]*?)```', replace_func, text)

def preprocess_sentence(sentence, language='en'):
    processed = sentence
    processed = pronounce_code_block(processed)
    processed = markdown_to_text(processed)
    processed = pronounce_numbers(processed, language)
    processed = remove_emotions(processed)
    processed = pronounce_special_characters(processed)
    processed = remove_emoji(processed)
    return processed.strip()