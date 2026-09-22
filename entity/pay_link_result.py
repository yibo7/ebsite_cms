class PayLinkResult:
    """
    创建支付后返回的支付凭证结果。

    三种支付场景互斥，前端根据哪个字段非空来判断处理方式：

      pay_url       — URL 跳转类（支付宝、PayPal、微信 H5）
                      前端处理：window.location.href = result.pay_url

      qr_code_url   — 二维码扫码类（微信 NATIVE 扫码支付）
                      前端处理：将 qr_code_url 生成二维码供用户扫码

      trade_params  — JSAPI 参数类（微信 JSAPI / 小程序支付）
                      前端处理：调用 JSAPI 接口发起支付
    """
    def __init__(self):
        # URL 跳转（支付宝、PayPal、微信 H5）
        self.pay_url: str = ""

        # 二维码扫码（微信 NATIVE）
        self.qr_code_url: str = ""

        # JSAPI 支付参数（微信 JSAPI / 小程序）
        self.trade_params: dict = None