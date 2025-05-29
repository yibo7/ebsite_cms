import smtplib
from email.mime.text import MIMEText
from email.header import Header
from queue import Queue
from threading import Thread

class EmailUtils:
    """
    一个处理电子邮件发送的类，支持并发发送和队列管理。

    属性:
        smtp_server (str): SMTP服务器地址
        smtp_port (int): SMTP服务器端口
        sender_email (str): 发件人邮箱地址
        password (str): 发件人邮箱密码
        use_ssl (bool): 是否使用SSL/TLS连接
        max_workers (int): 最大工作线程数
        queue (Queue): 存储待发送邮件的队列
        workers (list): 存储工作线程的列表
    """

    def __init__(self, smtp_server: str, smtp_port: int, sender_email: str, password: str,
                 use_ssl: bool = False, max_workers: int = 1):
        """
        初始化EmailSender实例。

        参数:
            smtp_server (str): SMTP服务器地址
            smtp_port (int): SMTP服务器端口
            sender_email (str): 发件人邮箱地址
            password (str): 发件人邮箱密码
            use_ssl (bool, 可选): 是否使用SSL/TLS连接，默认为False
            max_workers (int, 可选): 最大工作线程数，默认为1
        """
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.sender_email = sender_email
        self.password = password
        self.use_ssl = use_ssl
        self.max_workers = max_workers
        self.queue = Queue()
        self.workers = []

        # 启动工作线程
        self._start_workers()


    def _send_single_email(self, to_email: str, subject: str, body: str) -> bool:
        """
        发送单个邮件。

        参数:
            to_email (str): 收件人邮箱地址
            subject (str): 邮件主题
            body (str): 邮件正文

        返回:
            bool: 发送成功返回True，失败返回False
        """
        msg = self._create_message(to_email, subject, body)
        try:
            if self.use_ssl:
                with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
                    server.login(self.sender_email, self.password)
                    server.send_message(msg)
            else:
                with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                    server.starttls()
                    server.login(self.sender_email, self.password)
                    server.send_message(msg)
            print(f"成功发送邮件到 {to_email}")
            return True
        except Exception as e:
            print(f"发送邮件到 {to_email} 失败: {e}")
            return False

    def _start_workers(self):
        """
        启动工作线程来处理邮件队列。
        """
        for _ in range(self.max_workers):
            worker = Thread(target=self._worker_thread)
            worker.daemon = True
            worker.start()
            self.workers.append(worker)

    def _worker_thread(self):
        """
        工作线程的主函数，持续从队列中获取并发送邮件。
        """
        while True:
            task = self.queue.get()
            if task is None:
                break
            to_email, subject, body = task
            self._send_single_email(to_email, subject, body)
            self.queue.task_done()

    def _create_message(self, to_email: str, subject: str, body: str) -> MIMEText:
        """
        创建一个邮件消息对象。

        参数:
            to_email (str): 收件人邮箱地址
            subject (str): 邮件主题
            body (str): 邮件正文

        返回:
            MIMEText: 创建的邮件消息对象
        """
        msg = MIMEText(body, 'plain', 'utf-8')
        msg['Subject'] = Header(subject, 'utf-8')
        msg['From'] = self.sender_email
        msg['To'] = to_email
        return msg


    def add_to_queue(self, to_email: str, subject: str, body: str):
        """
        将邮件任务添加到发送队列。

        参数:
            to_email (str): 收件人邮箱地址
            subject (str): 邮件主题
            body (str): 邮件正文
        """
        self.queue.put((to_email, subject, body))

    def wait_for_completion(self):
        """
        等待所有队列中的邮件任务完成。
        """
        self.queue.join()

    def stop_workers(self):
        """
        停止所有工作线程。
        """
        for _ in range(self.max_workers):
            self.queue.put(None)
        for worker in self.workers:
            worker.join()