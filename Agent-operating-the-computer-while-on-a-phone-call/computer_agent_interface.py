
import queue2
import queue1
# 这个队列代表了从“电脑Agent”到“电话Agent”的通信通道
q2_queue = queue2.q2_queue
q1_queue = queue1.q1_queue
def send_message_to_phone_agent(message: str):
    """
    一个模拟工具，供（假想的）电脑Agent向本电话Agent发送消息。
    """
    print(f"📦 [电脑Agent -> 电话Agent]: 收到消息: {message}")
    q2_queue.put(message)
    return f"📞 消息已成功发送给电话Agent: {message}"

def send_message_to_computer_agent(message: str):
    """
    一个工具，供电话Agent调用，以向电脑Agent发送消息或指令。
    """
    print(f"📞 -> 💻 [电话Agent -> 电脑Agent]: 发送指令: {message}")
    q1_queue.put(message)
    return f"消息已成功发送给电脑Agent: {message}"