class EbTipError(Exception):
    """自定义错误"""
    def __init__(self, message="发生错误了"):
        self.message = message
        super().__init__(self.message)