from queue import Queue
from typing import List

class Q2MessageQueue:
    """简化的Q2消息队列"""
    
    def __init__(self):
        self.message_queue = Queue()
    
    def put(self, text: str):
        """
        添加文本到队列
        
        Args:
            text: 要添加的文本消息
        """
        self.message_queue.put(text)
        print(f"📥 Q2队列添加消息: {text}")
    
    def get(self) -> List[str]:
        """
        获取队列中的所有消息并清空队列
        
        Returns:
            所有消息的列表
        """
        messages = []
        while not self.message_queue.empty():
            try:
                message = self.message_queue.get_nowait()
                messages.append(message)
            except:
                break
        
        if messages:
            print(f"📤 Q2队列输出 {len(messages)} 条消息")
        
        return messages
    def is_empty(self) -> bool:
        """
        检查队列是否为空
        
        Returns:
            bool: True表示队列为空，False表示有消息
        """
        return self.message_queue.empty()
    
# 创建全局队列实例

# 创建全局队列实例
q2_queue = Q2MessageQueue()
