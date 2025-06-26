class PayBackInfo:
    def __init__(self):
        self.status_code: int = 0  # 付款状态码，一般要求，1支付成功，2，提交但未支付，其他的状态可自定义,在事件监听中可以根据自身需求来处理
        self.is_successful: bool = False  # 订单是否支付成功
        self.trade_no: str = ""      # 支付平台的交易号
        self.order_no: str = ""      # 支付平台返回的订单号(本网站提供的订单号)
        self.pay_amount: str = ""    # 支付平台实际收到的金额
        self.buy_user_name: str = "" # 买家账号
        self.info: str = ""          # 处理结果信息