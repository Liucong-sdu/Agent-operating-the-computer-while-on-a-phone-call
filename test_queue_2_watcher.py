import unittest
import threading
import time
from unittest.mock import Mock, patch, MagicMock
import queue

from agent import VoiceAgent
from computer_agent_interface import q2_queue


class TestQueue2Watcher(unittest.TestCase):
    def setUp(self):
        """设置测试环境"""
        # 创建一个mock的VoiceAgent实例，避免初始化所有依赖
        with patch('agent.AudioHandler'), \
             patch('agent.LLMHandler'), \
             patch('agent.TTSHandler'), \
             patch('openai.OpenAI'):
            
            self.agent = VoiceAgent()
            
            # Mock掉一些方法和属性
            self.mock_llm_handler = Mock()
            self.agent.llm_handler = self.mock_llm_handler
            
            self.mock_trigger_llm = Mock()
            self.agent._trigger_large_llm = self.mock_trigger_llm
            
            self.agent.conversation_history = []
            
            # 确保stop_event未设置
            self.agent.stop_event.clear()
    
    def tearDown(self):
        """清理测试环境"""
        # 停止agent避免影响其他测试
        self.agent.stop_event.set()
        
        # 清空q2队列
        while not q2_queue.is_empty():
            q2_queue.get()
    
    def test_queue_2_watcher_processes_messages_when_llm_inactive(self):
        """测试当LLM不活跃时，queue_2_watcher能正确处理消息"""
        # 设置LLM为非活跃状态
        self.mock_llm_handler.is_active.return_value = False
        
        # 向队列添加测试消息
        test_messages = ["测试消息1", "测试消息2"]
        for msg in test_messages:
            q2_queue.put(msg)
        
        # 启动_queue_2_watcher在一个单独的线程中
        watcher_thread = threading.Thread(target=self.agent._queue_2_watcher)
        watcher_thread.start()
        
        # 等待一段时间让watcher处理消息
        time.sleep(1)
        
        # 停止watcher
        self.agent.stop_event.set()
        watcher_thread.join(timeout=2)
        
        # 验证消息被正确处理
        # 检查conversation_history是否包含了来自电脑Agent的消息
        added_messages = [msg['content'] for msg in self.agent.conversation_history if msg['role'] == 'user']
        
        self.assertEqual(len(added_messages), 2)
        self.assertIn("[FROM_COMPUTER_AGENT] 测试消息1", added_messages[0])
        self.assertIn("[FROM_COMPUTER_AGENT] 测试消息2", added_messages[1])
        
        # 验证_trigger_large_llm被调用了
        self.mock_trigger_llm.assert_called()
    
    def test_queue_2_watcher_skips_when_llm_active(self):
        """测试当LLM活跃时，queue_2_watcher跳过处理"""
        # 设置LLM为活跃状态
        self.mock_llm_handler.is_active.return_value = True
        
        # 向队列添加测试消息
        q2_queue.put("应该被跳过的消息")
        
        # 启动_queue_2_watcher在一个单独的线程中
        watcher_thread = threading.Thread(target=self.agent._queue_2_watcher)
        watcher_thread.start()
        
        # 等待短时间
        time.sleep(0.8)
        
        # 停止watcher
        self.agent.stop_event.set()
        watcher_thread.join(timeout=2)
        
        # 验证消息没有被处理（conversation_history应该为空）
        self.assertEqual(len(self.agent.conversation_history), 0)
        
        # 验证_trigger_large_llm没有被调用
        self.mock_trigger_llm.assert_not_called()
        
        # 验证消息仍在队列中
        self.assertFalse(q2_queue.is_empty())
    
    def test_queue_2_watcher_handles_empty_queue(self):
        """测试当队列为空时，queue_2_watcher正常等待"""
        # 设置LLM为非活跃状态
        self.mock_llm_handler.is_active.return_value = False
        
        # 确保队列为空
        while not q2_queue.is_empty():
            q2_queue.get()
        
        # 启动_queue_2_watcher在一个单独的线程中
        watcher_thread = threading.Thread(target=self.agent._queue_2_watcher)
        watcher_thread.start()
        
        # 等待短时间
        time.sleep(0.8)
        
        # 停止watcher
        self.agent.stop_event.set()
        watcher_thread.join(timeout=2)
        
        # 验证没有消息被处理
        self.assertEqual(len(self.agent.conversation_history), 0)
        self.mock_trigger_llm.assert_not_called()
    
    def test_queue_2_watcher_handles_multiple_messages_batch(self):
        """测试queue_2_watcher能批量处理多个消息"""
        # 设置LLM为非活跃状态
        self.mock_llm_handler.is_active.return_value = False
        
        # 向队列添加多个测试消息
        test_messages = ["消息A", "消息B", "消息C", "消息D"]
        for msg in test_messages:
            q2_queue.put(msg)
        
        # 启动_queue_2_watcher在一个单独的线程中
        watcher_thread = threading.Thread(target=self.agent._queue_2_watcher)
        watcher_thread.start()
        
        # 等待处理
        time.sleep(1)
        
        # 停止watcher
        self.agent.stop_event.set()
        watcher_thread.join(timeout=2)
        
        # 验证所有消息都被处理
        added_messages = [msg['content'] for msg in self.agent.conversation_history if msg['role'] == 'user']
        
        self.assertEqual(len(added_messages), 4)
        for i, test_msg in enumerate(test_messages):
            self.assertIn(f"[FROM_COMPUTER_AGENT] {test_msg}", added_messages[i])
        
        # 验证_trigger_large_llm只被调用一次（批量处理后触发一次）
        self.mock_trigger_llm.assert_called_once()
    
    def test_queue_2_watcher_stops_when_stop_event_set(self):
        """测试当stop_event被设置时，queue_2_watcher正确停止"""
        # 设置LLM为非活跃状态
        self.mock_llm_handler.is_active.return_value = False
        
        # 启动_queue_2_watcher在一个单独的线程中
        watcher_thread = threading.Thread(target=self.agent._queue_2_watcher)
        watcher_thread.start()
        
        # 让它运行一小会儿
        time.sleep(0.2)
        
        # 设置停止事件
        self.agent.stop_event.set()
        
        # 等待线程结束
        watcher_thread.join(timeout=2)
        
        # 验证线程已经结束
        self.assertFalse(watcher_thread.is_alive())


if __name__ == '__main__':
    # 运行测试
    unittest.main()
