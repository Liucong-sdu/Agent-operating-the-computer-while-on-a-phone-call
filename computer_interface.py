# computer_interface.py (最终优化版)

from shared_queues import q1_queue, q2_queue
from typing import List, Dict

def send_goal_to_computer_agent(task_id: str, goal_description: str):
    """Voice Agent 使用此工具向 Computer Agent 发送一个全新的、单一的任务目标。"""
    payload = {"goal": goal_description}
    q1_queue.put({"task_id": task_id, "type": "goal", "payload": payload})
    return "目标已成功发送给电脑Agent。"

def send_info_to_computer_agent(task_id: str, info_list: List[Dict[str, str]]):
    """【新】Voice Agent 使用此工具将在用户处获得的【一个或多个】信息点打包发送给 Computer Agent。"""
    payload = {"info_list": info_list}
    q1_queue.put({"task_id": task_id, "type": "info", "payload": payload})
    return "用户信息包已成功发送给电脑Agent。"

def send_status_to_voice_agent(task_id: str, message_type: str, content: str):
    """【新】Computer Agent 使用此工具向 Voice Agent 发送标准化的状态回执。"""
    if task_id:
        # message_type 可以是 "OBSERVATION_RESULT", "EXECUTION_SUCCESS", "EXECUTION_FAILURE"
        payload = f"[{message_type}] {content}"
        q2_queue.put({"task_id": task_id, "payload": payload})