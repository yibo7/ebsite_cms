from decimal import Decimal


class PayBackInfo:
    """
    支付回调的标准结果模型。

    支付平台异步通知到达后，由插件的 call_back() 填充此模型返回给系统。
    业务代码（监听 pay_saved_successful 信号的模块）依赖此模型处理订单状态。
    """
    def __init__(self):
        # ======== 核心字段 ========
        self.is_successful: bool = False   # 订单是否支付成功
        self.status_code: int = 0          # 付款状态码：1=支付成功，2=待支付，其他可自定义
        self.trade_no: str = ""            # 支付平台交易流水号
        self.order_no: str = ""            # 本系统订单号
        self.pay_amount: Decimal = 0       # 实付金额（Decimal 避免浮点精度丢失）
        self.currency: str = "CNY"         # 币种（CNY / USD / HKD 等）

        # ======== 扩展信息 ========
        self.buy_user_name: str = ""       # 买家账号（支付宝买家 email，微信 openid 等）
        self.payment_method: str = ""      # 支付方式标识（如 "wechat", "alipay", "paypal"）
        self.raw_data: dict = None         # 平台原始返回数据（用于对账/审计）
        self.info: str = ""                # 处理结果描述信息