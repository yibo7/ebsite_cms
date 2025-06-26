import threading
import time
import os


class OrderIdGenerator:
    def __init__(self):
        self.lock = threading.Lock()
        self.last_timestamp = 0
        self.sequence = 0
        self.machine_id = (os.getpid() % 1000)  # 机器/进程标识

    def generate(self, prefix="ORD"):
        with self.lock:
            current_timestamp = int(time.time() * 1000)  # 毫秒时间戳

            if current_timestamp == self.last_timestamp:
                self.sequence += 1
                if self.sequence >= 999:  # 同一毫秒最多999个订单
                    # 等待下一毫秒
                    while current_timestamp <= self.last_timestamp:
                        current_timestamp = int(time.time() * 1000)
                    self.sequence = 0
            else:
                self.sequence = 0

            self.last_timestamp = current_timestamp

            # 格式：前缀 + 时间戳 + 机器ID + 序号
            return f"{prefix}{current_timestamp}{self.machine_id:03d}{self.sequence:03d}"


# 使用示例
# generator = OrderIdGenerator()
# print(generator.generate("ORD"))  # ORD20240626000001
# print(generator.generate("ORD"))  # ORD20240626000002