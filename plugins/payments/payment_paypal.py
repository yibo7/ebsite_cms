import json
import logging
from decimal import Decimal
from typing import Tuple

import requests
from flask import Request

from entity.pay_back_model import PayBackInfo
from entity.pay_link_result import PayLinkResult
from plugins.plugin_base import PaymentBase, plugin_attribute


@plugin_attribute("PayPal", "1.0", "ebsite")
class PaypalPlugin(PaymentBase):
    """
    PayPal 支付插件。

    使用 PayPal REST API (Orders v2) 实现服务器端支付流程：
      1. create_pay_link() → 创建订单，返回 PayPal 审批页 URL
      2. 用户跳转到 PayPal 完成审批
      3. PayPal 重定向到本系统 return_url，携带 token=ORDER_ID
      4. call_back() 捕获订单，完成扣款
      5. PayPal 异步发送 webhook 通知到 notify_url
    """

    def __init__(self, current_app):
        super().__init__(current_app)
        self.client_id: str = ""
        self.client_secret: str = ""
        self.is_sandbox: bool = True
        self.info = "基于 PayPal REST API 的支付插件"

        self.logger = logging.getLogger(__name__)

    # ==================== 环境与认证 ====================

    def _api_base(self) -> str:
        return "https://api-m.sandbox.paypal.com" if self.is_sandbox else "https://api-m.paypal.com"

    def _get_oauth_token(self) -> str:
        """
        获取 PayPal OAuth 2.0 access_token。
        :return: access_token 字符串
        :raises Exception: 获取失败时抛出
        """
        url = f"{self._api_base()}/v1/oauth2/token"
        resp = requests.post(
            url,
            auth=(self.client_id, self.client_secret),
            headers={"Accept": "application/json"},
            data={"grant_type": "client_credentials"},
        )
        if resp.status_code != 200:
            raise Exception(f"获取 PayPal Token 失败（HTTP {resp.status_code}）: {resp.text}")
        return resp.json()["access_token"]

    def _auth_header(self, token: str) -> dict:
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    # ==================== 必选接口 ====================

    def create_pay_link(
        self,
        order_id: str,
        amount: float,
        **kwargs,
    ) -> Tuple[bool, str, PayLinkResult]:
        """
        创建 PayPal 订单，返回审批页面 URL（pay_url）。
        """
        result = PayLinkResult()
        try:
            if not self.client_id or not self.client_secret:
                return False, "PayPal 配置不完整（client_id / client_secret）", result
            if amount <= 0:
                return False, "金额必须大于 0", result

            token = self._get_oauth_token()
            headers = self._auth_header(token)

            # 获取完整域名用于 return_url / cancel_url
            from flask import request as flask_req
            host_url = flask_req.host_url.rstrip("/")

            subject = kwargs.get("subject") or f"Order {order_id}"
            order_data = {
                "intent": "CAPTURE",
                "purchase_units": [
                    {
                        "reference_id": order_id,
                        "description": subject,
                        "amount": {
                            "currency_code": "USD",
                            "value": f"{amount:.2f}",
                        },
                    }
                ],
                "payment_source": {
                    "paypal": {
                        "experience_context": {
                            "payment_method_preference": "IMMEDIATE_PAYMENT_REQUIRED",
                            "landing_page": "LOGIN",
                            "user_action": "PAY_NOW",
                            "return_url": f"{host_url}/pay/return_url/{self.id}",
                            "cancel_url": f"{host_url}/pay/cancel",
                        }
                    }
                },
            }

            url = f"{self._api_base()}/v2/checkout/orders"
            resp = requests.post(url, json=order_data, headers=headers)

            if resp.status_code not in (200, 201):
                error_detail = resp.json().get("message", resp.text)
                return False, f"创建 PayPal 订单失败: {error_detail}", result

            order = resp.json()

            # 从返回的 links 中找出 "payer-action" 即审批页 URL
            for link in order.get("links", []):
                if link.get("rel") == "payer-action":
                    result.pay_url = link["href"]
                    return True, "", result

            return False, "PayPal 未返回审批链接", result

        except Exception as e:
            return False, f"创建 PayPal 支付失败: {str(e)}", result

    def call_back(self, request: Request) -> Tuple[bool, str, PayBackInfo]:
        """
        处理 PayPal 支付结果。

        两种场景：
          - GET  + token → 用户从 PayPal 审批页返回，执行订单捕获
          - POST          → PayPal webhook 异步通知（暂为基础支持）
        """
        pay_info = PayBackInfo()

        # -- 场景1：用户从 PayPal 审批页返回 --
        if request.method == "GET" and request.args.get("token"):
            return self._capture_order(request.args["token"], pay_info)

        # -- 场景2：PayPal webhook 通知 --
        if request.method == "POST":
            # 基础处理：记录日志，返回确认
            try:
                webhook_data = request.get_json(silent=True) or {}
                self.logger.info(f"收到 PayPal webhook: {webhook_data.get('event_type')}")
                pay_info.info = f"Webhook received: {webhook_data.get('event_type', 'unknown')}"
                return True, pay_info.info, pay_info
            except Exception as e:
                return False, f"处理 webhook 失败: {str(e)}", pay_info

        return False, "不支持的请求方式", pay_info

    # ==================== 订单捕获 ====================

    def _capture_order(
        self, order_id: str, pay_info: PayBackInfo
    ) -> Tuple[bool, str, PayBackInfo]:
        """
        捕获（扣款）一个已审批的 PayPal 订单。
        """
        try:
            token = self._get_oauth_token()
            headers = self._auth_header(token)

            url = f"{self._api_base()}/v2/checkout/orders/{order_id}/capture"
            resp = requests.post(url, headers=headers, json={})

            if resp.status_code not in (200, 201):
                error_msg = resp.json().get("message", resp.text)
                return False, f"捕获 PayPal 订单失败: {error_msg}", pay_info

            result = resp.json()
            status = result.get("status")

            if status == "COMPLETED":
                purchase_unit = result["purchase_units"][0]
                capture = purchase_unit["payments"]["captures"][0]

                pay_info.is_successful = True
                pay_info.status_code = 1
                pay_info.trade_no = capture["id"]
                pay_info.order_no = purchase_unit.get("reference_id", order_id)
                pay_info.pay_amount = Decimal(str(capture["amount"]["value"]))
                pay_info.currency = capture["amount"]["currency_code"]
                pay_info.payment_method = "paypal"
                pay_info.buy_user_name = result.get("payer", {}).get("email_address", "")
                pay_info.raw_data = result
                pay_info.info = "支付成功"

                self.logger.info(
                    f"PayPal 订单 {pay_info.order_no} 支付成功，"
                    f"交易号 {pay_info.trade_no}，金额 {pay_info.pay_amount} {pay_info.currency}"
                )
                return True, "支付成功", pay_info

            else:
                pay_info.info = f"PayPal 订单状态: {status}"
                return False, pay_info.info, pay_info

        except Exception as e:
            return False, f"捕获订单异常: {str(e)}", pay_info

    def notify_response(self, notify_data: PayBackInfo) -> str:
        """
        返回 PayPal webhook 确认响应。
        """
        return json.dumps({"status": "OK"})

    # ==================== 可选接口 ====================

    def query_order(self, order_id: str) -> Tuple[bool, str, PayBackInfo]:
        """
        查询 PayPal 订单状态。
        注意：order_id 在这里是 PayPal 返回的交易号（capture ID），
        而非本系统订单号。如需通过系统订单号查询，需额外维护映射关系。
        """
        pay_info = PayBackInfo()
        try:
            token = self._get_oauth_token()
            headers = self._auth_header(token)

            url = f"{self._api_base()}/v2/checkout/orders/{order_id}"
            resp = requests.get(url, headers=headers)

            if resp.status_code != 200:
                return False, f"查询失败（HTTP {resp.status_code}）", pay_info

            result = resp.json()
            pay_info.order_no = result.get("id", "")
            pay_info.trade_no = result.get("id", "")
            pay_info.is_successful = result.get("status") == "COMPLETED"
            pay_info.raw_data = result
            pay_info.info = f"状态: {result.get('status', 'unknown')}"

            if result.get("purchase_units"):
                unit = result["purchase_units"][0]
                pay_info.pay_amount = Decimal(str(unit["amount"]["value"]))
                pay_info.currency = unit["amount"]["currency_code"]

            return True, "查询成功", pay_info

        except Exception as e:
            return False, f"查询异常: {str(e)}", pay_info

    # ==================== 后台配置表单 ====================

    def params_temp(self) -> str:
        return '''
        <div class="form-group p-2">
            <label for="client_id">Client ID <span style="color: red;">*</span></label>
            <input type="text" id="client_id" name="client_id"
                   value="{{model.client_id}}" class="form-control"
                   placeholder="请输入 PayPal REST API 客户端 ID" required/>
            <small class="form-text text-muted">
                在 <a href="https://developer.paypal.com/dashboard/" target="_blank">PayPal Developer Dashboard</a>
                → Apps & Credentials 中获取
            </small>
        </div>
        <div class="form-group p-2">
            <label for="client_secret">Client Secret <span style="color: red;">*</span></label>
            <input type="text" id="client_secret" name="client_secret"
                   value="{{model.client_secret}}" class="form-control"
                   placeholder="请输入 PayPal REST API 客户端密钥" required/>
            <small class="form-text text-muted">与 Client ID 对应的客户端密钥</small>
        </div>
        <div class="form-group p-2">
            <label>环境设置</label>
            <div class="form-check">
                <input type="checkbox" id="is_sandbox" name="is_sandbox"
                       class="form-check-input" value="1"
                       {% if model.is_sandbox %}checked{% endif %}>
                <label class="form-check-label" for="is_sandbox">使用沙箱环境（Sandbox）</label>
            </div>
            <small class="form-text text-muted">
                开发测试时勾选，使用 PayPal Sandbox 模拟支付。正式上线前取消勾选。
            </small>
        </div>
        <div class="alert alert-info mt-3">
            <strong>使用说明：</strong><br>
            1. 在
            <a href="https://developer.paypal.com/dashboard/" target="_blank">PayPal Developer Dashboard</a>
            创建 REST API 应用获取凭据<br>
            2. 在 Sandbox 中创建测试买家账号用于开发测试<br>
            3. 本插件使用 <strong>USD</strong> 结算，请确保您的业务支持美元交易<br>
            4. 用户完成支付后会自动跳回网站，无需手动配置回调地址
        </div>
        '''