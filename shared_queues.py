# shared_queues.py (简化版)

import queue

# 队列1: Voice -> Computer
q1_queue = queue.Queue()

# 队列2: Computer -> Voice
q2_queue = queue.Queue()