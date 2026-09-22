import json
import time
import hashlib
import logging
from decimal import Decimal
from typing import Tuple, Dict, Any
from xml.etree import ElementTree
import requests

from entity.pay_back_model import PayBackInfo
from entity.pay_link_result import PayLinkResult
from plugins.plugin_base import PaymentBase, plugin_attribute


@plugin_attribute("微信支付", "1.0", "eb_site")
class WechatPayPlugin(PaymentBase):
    def __init__(self, current_app):
        super().__init__(current_app)
        self.app_id = ""          # 微信公众号或小程序 appid
        self.mch_id = ""          # 微信支付商户号
        self.api_key = ""         # API 密钥
        self.cert_path = ""       # 证书路径（退款需要）
        self.key_path = ""        # 密钥路径（退款需要）
        self.info = "基于微信支付的支付插件"
        self.gateway_url = "https://api.mch.weixin.qq.com"
        self.sandbox_gateway_url = "https://api.mch.weixin.qq.com/sandboxnew"
        self.is_sandbox = False
        self.logger = logging.getLogger(__name__)

    # ==================== 配置校验 ====================

    def _validate_config(self) -> bool:
        if not all([self.app_id, self.mch_id, self.api_key]):
            self.logger.error("微信支付配置不完整")
            return False
        return True

    def _validate_order_params(self, order_id: str, amount: float) -> Tuple[bool, str]:
        if not order_id or not isinstance(order_id, str):
            return False, "订单号无效"
        if not isinstance(amount, (int, float)) or amount <= 0:
            return False, "金额必须大于0"
        if amount > 100000:
            return False, "单笔金额不能超过100000元"
        if int(amount * 100) != amount * 100:
            return False, "金额必须保留到分"
        return True, ""

    # ==================== 签名工具 ====================

    def _generate_nonce_str(self, length=32) -> str:
        import random
        import string
        chars = string.ascii_letters + string.digits
        return ''.join(random.choice(chars) for _ in range(length))

    def _generate_sign(self, params: Dict[str, Any]) -> str:
        sorted_params = sorted(params.items(), key=lambda x: x[0])
        string_sign = '&'.join([f"{k}={v}" for k, v in sorted_params if k != 'sign' and v is not None])
        string_sign += f"&key={self.api_key}"
        return hashlib.md5(string_sign.encode('utf-8')).hexdigest().upper()

    def _verify_sign(self, params: Dict[str, Any]) -> bool:
        if 'sign' not in params:
            return False
        sign = params.pop('sign')
        calculated_sign = self._generate_sign(params)
        return sign == calculated_sign

    # ==================== XML 工具 ====================

    def _dict_to_xml(self, params: Dict[str, Any]) -> str:
        xml = ["<xml>"]
        for k, v in params.items():
            xml.append(f"<{k}>{v}</{k}>")
        xml.append("</xml>")
        return "".join(xml)

    def _xml_to_dict(self, xml_str: str) -> Dict[str, Any]:
        try:
            xml = ElementTree.fromstring(xml_str)
            return {child.tag: child.text for child in xml}
        except Exception as e:
            self.logger.error(f"XML解析失败: {str(e)}")
            return {}

    # ==================== 业务参数构建 ====================

    def _build_request_params(self, order_id: str, amount: float, description: str = None, **kwargs) -> Dict[str, Any]:
        params = {
            "appid": self.app_id,
            "mch_id": self.mch_id,
            "nonce_str": self._generate_nonce_str(),
            "body": description or f"订单 {order_id}",
            "out_trade_no": order_id,
            "total_fee": int(amount * 100),
            "spbill_create_ip": kwargs.get('client_ip', '127.0.0.1'),
            "notify_url": self.notify_url,
            "trade_type": kwargs.get('trade_type', 'NATIVE'),
            "time_start": time.strftime('%Y%m%d%H%M%S'),
            "time_expire": time.strftime('%Y%m%d%H%M%S', time.localtime(time.time() + 1800)),
        }
        if kwargs.get('openid') and params['trade_type'] == 'JSAPI':
            params['openid'] = kwargs['openid']
        if kwargs.get('product_id') and params['trade_type'] == 'NATIVE':
            params['product_id'] = kwargs['product_id']
        params['sign'] = self._generate_sign(params)
        return params

    # ==================== 必选接口 ====================

    def create_pay_link(self, order_id: str, amount: float, **kwargs) -> Tuple[bool, str, PayLinkResult]:
        """
        创建微信支付凭证。

        根据 trade_type 返回不同凭证：
          - NATIVE → qr_code_url（扫码支付）
          - JSAPI  → trade_params（公众号/小程序内支付）
        """
        result = PayLinkResult()
        try:
            if not self._validate_config():
                return False, "微信支付配置不完整", result

            is_valid, error_msg = self._validate_order_params(order_id, amount)
            if not is_valid:
                return False, error_msg, result

            params = self._build_request_params(order_id, amount, kwargs.get('description'), **kwargs)
            base_url = self.sandbox_gateway_url if self.is_sandbox else self.gateway_url
            url = f"{base_url}/pay/unifiedorder"
            headers = {'Content-Type': 'application/xml'}
            response = requests.post(url, data=self._dict_to_xml(params).encode('utf-8'), headers=headers)

            resp_data = self._xml_to_dict(response.text)
            if resp_data.get('return_code') != 'SUCCESS':
                return False, resp_data.get('return_msg', '微信支付请求失败'), result
            if not self._verify_sign(resp_data):
                return False, "签名验证失败", result

            trade_type = params.get('trade_type', 'NATIVE')
            if trade_type == 'NATIVE':
                result.qr_code_url = resp_data.get('code_url', '')
            elif trade_type == 'JSAPI':
                jsapi_params = {
                    "appId": self.app_id,
                    "timeStamp": str(int(time.time())),
                    "nonceStr": self._generate_nonce_str(),
                    "package": f"prepay_id={resp_data['prepay_id']}",
                    "signType": "MD5",
                }
                jsapi_params['paySign'] = self._generate_sign(jsapi_params)
                result.trade_params = jsapi_params
            else:
                result.trade_params = resp_data

            return True, '', result

        except Exception as e:
            return False, f"创建支付失败: {str(e)}", result

    def call_back(self, request) -> Tuple[bool, str, PayBackInfo]:
        """
        处理微信支付异步回调，返回标准化的 PayBackInfo。
        """
        pay_info = PayBackInfo()
        try:
            xml_data = request.data
            if not xml_data:
                return False, "回调数据为空", pay_info

            callback_data = self._xml_to_dict(xml_data)
            self.logger.info(f"收到微信支付回调: {callback_data}")

            if not self._verify_sign(callback_data):
                return False, "签名验证失败", pay_info
            if callback_data.get('return_code') != 'SUCCESS':
                return False, f"支付失败: {callback_data.get('return_msg')}", pay_info
            if callback_data.get('result_code') != 'SUCCESS':
                return False, f"支付失败: {callback_data.get('err_code_des')}", pay_info

            pay_info.is_successful = True
            pay_info.status_code = 1
            pay_info.trade_no = callback_data.get('transaction_id', '')
            pay_info.order_no = callback_data.get('out_trade_no', '')
            pay_info.pay_amount = Decimal(callback_data.get('total_fee', '0')) / 100
            pay_info.currency = "CNY"
            pay_info.payment_method = "wechat"
            pay_info.buy_user_name = callback_data.get('openid', '')
            pay_info.raw_data = callback_data
            pay_info.info = "支付成功"

            return True, "支付成功", pay_info

        except Exception as e:
            return False, f"处理回调失败: {str(e)}", pay_info

    def notify_response(self, notify_data: PayBackInfo) -> str:
        """返回微信支付要求的确认响应"""
        return "success"

    # ==================== 可选接口 ====================

    def query_order(self, order_id: str) -> Tuple[bool, str, PayBackInfo]:
        pay_info = PayBackInfo()
        try:
            if not self._validate_config():
                return False, "微信支付配置不完整", pay_info

            params = {
                "appid": self.app_id,
                "mch_id": self.mch_id,
                "out_trade_no": order_id,
                "nonce_str": self._generate_nonce_str(),
            }
            params['sign'] = self._generate_sign(params)

            base_url = self.sandbox_gateway_url if self.is_sandbox else self.gateway_url
            url = f"{base_url}/pay/orderquery"
            headers = {'Content-Type': 'application/xml'}
            response = requests.post(url, data=self._dict_to_xml(params).encode('utf-8'), headers=headers)

            result = self._xml_to_dict(response.text)
            if result.get('return_code') != 'SUCCESS':
                return False, result.get('return_msg', '查询失败'), pay_info
            if not self._verify_sign(result):
                return False, "签名验证失败", pay_info

            trade_state = result.get('trade_state', 'UNKNOWN')
            pay_info.order_no = order_id
            pay_info.trade_no = result.get('transaction_id', '')
            pay_info.pay_amount = Decimal(result.get('total_fee', '0')) / 100
            pay_info.is_successful = (trade_state == 'SUCCESS')
            pay_info.status_code = 1 if trade_state == 'SUCCESS' else 0
            pay_info.raw_data = result
            pay_info.info = result.get('trade_state_desc', '')

            return True, "查询成功", pay_info

        except Exception as e:
            return False, f"查询订单失败: {str(e)}", pay_info

    def refund_order(self, order_id: str, amount: float, reason: str = "") -> Tuple[bool, str, PayBackInfo]:
        pay_info = PayBackInfo()
        try:
            if not self._validate_config():
                return False, "微信支付配置不完整", pay_info
            if not all([self.cert_path, self.key_path]):
                return False, "退款需要配置证书路径", pay_info
            if amount <= 0:
                return False, "退款金额必须大于0", pay_info

            params = {
                "appid": self.app_id,
                "mch_id": self.mch_id,
                "nonce_str": self._generate_nonce_str(),
                "out_trade_no": order_id,
                "out_refund_no": f"R{order_id}{int(time.time())}",
                "total_fee": int(amount * 100),
                "refund_fee": int(amount * 100),
                "refund_desc": reason or "用户申请退款",
                "notify_url": self.notify_url,
            }
            params['sign'] = self._generate_sign(params)

            base_url = self.sandbox_gateway_url if self.is_sandbox else self.gateway_url
            url = f"{base_url}/secapi/pay/refund"
            headers = {'Content-Type': 'application/xml'}
            cert = (self.cert_path, self.key_path)
            response = requests.post(url, data=self._dict_to_xml(params).encode('utf-8'),
                                     headers=headers, cert=cert)

            result = self._xml_to_dict(response.text)
            if result.get('return_code') != 'SUCCESS':
                return False, result.get('return_msg', '退款失败'), pay_info
            if not self._verify_sign(result):
                return False, "签名验证失败", pay_info

            pay_info.is_successful = True
            pay_info.order_no = order_id
            pay_info.trade_no = result.get('refund_id', '')
            pay_info.pay_amount = Decimal(result.get('refund_fee', '0')) / 100
            pay_info.raw_data = result
            pay_info.info = "退款成功"

            return True, "退款成功", pay_info

        except Exception as e:
            return False, f"退款失败: {str(e)}", pay_info

    def close_order(self, order_id: str) -> Tuple[bool, str]:
        try:
            if not self._validate_config():
                return False, "微信支付配置不完整"

            params = {
                "appid": self.app_id,
                "mch_id": self.mch_id,
                "out_trade_no": order_id,
                "nonce_str": self._generate_nonce_str(),
            }
            params['sign'] = self._generate_sign(params)

            base_url = self.sandbox_gateway_url if self.is_sandbox else self.gateway_url
            url = f"{base_url}/pay/closeorder"
            headers = {'Content-Type': 'application/xml'}
            response = requests.post(url, data=self._dict_to_xml(params).encode('utf-8'), headers=headers)

            result = self._xml_to_dict(response.text)
            if result.get('return_code') != 'SUCCESS':
                return False, result.get('return_msg', '关闭订单失败')
            if not self._verify_sign(result):
                return False, "签名验证失败"

            return True, "订单关闭成功"

        except Exception as e:
            return False, f"关闭订单失败: {str(e)}"

    # ==================== 后台配置表单 ====================

    def params_temp(self) -> str:
        return '''
        <div class="form-group p-2">
            <label for="app_id">App ID <span style="color: red;">*</span></label>
            <input type="text" id="app_id" name="app_id"
                   value="{{model.app_id}}" class="form-control"
                   placeholder="请输入微信公众号或小程序的AppID" required/>
            <small class="form-text text-muted">在微信公众平台获取</small>
        </div>
        <div class="form-group p-2">
            <label for="mch_id">商户号 <span style="color: red;">*</span></label>
            <input type="text" id="mch_id" name="mch_id"
                   value="{{model.mch_id}}" class="form-control"
                   placeholder="请输入微信支付商户号" required/>
            <small class="form-text text-muted">在微信支付商户平台获取</small>
        </div>
        <div class="form-group p-2">
            <label for="api_key">API密钥 <span style="color: red;">*</span></label>
            <input type="text" id="api_key" name="api_key"
                   value="{{model.api_key}}" class="form-control"
                   placeholder="请输入微信支付API密钥" required/>
            <small class="form-text text-muted">在微信支付商户平台设置API密钥</small>
        </div>
        <div class="form-group p-2">
            <label for="cert_path">证书路径</label>
            <input type="text" id="cert_path" name="cert_path"
                   value="{{model.cert_path}}" class="form-control"
                   placeholder="请输入微信支付证书路径"/>
            <small class="form-text text-muted">退款操作需要配置证书路径</small>
        </div>
        <div class="form-group p-2">
            <label for="key_path">密钥路径</label>
            <input type="text" id="key_path" name="key_path"
                   value="{{model.key_path}}" class="form-control"
                   placeholder="请输入微信支付密钥路径"/>
            <small class="form-text text-muted">退款操作需要配置密钥路径</small>
        </div>
        <div class="form-group p-2">
            <label>环境设置</label>
            <div class="form-check">
                <input type="checkbox" id="is_sandbox" name="is_sandbox"
                       class="form-check-input" value="1"
                       {% if model.is_sandbox %}checked{% endif %}>
                <label class="form-check-label" for="is_sandbox">使用沙箱环境（测试环境）</label>
            </div>
        </div>
        <div class="alert alert-info mt-3">
            <strong>使用说明：</strong><br>
            1. 在
            <a href="https://mp.weixin.qq.com/" target="_blank">微信公众平台</a>
            获取公众号/小程序的 <strong>AppID</strong><br>
            2. 在
            <a href="https://pay.weixin.qq.com/" target="_blank">微信支付商户平台</a>
            获取 <strong>商户号（MCHID）</strong>，并设置 <strong>API 密钥</strong><br>
            3. 在商户平台下载 <strong>API 证书</strong>（退款等安全接口需要）<br>
            4. 在商户平台 → 产品中心 → 开发配置 中设置支付回调地址为：<br>
            <code>/pay/notify_url/WechatPayPlugin</code>
            <br>（需补全为完整的公网 HTTPS 地址）<br>
            5. 本插件使用 <strong>CNY（人民币）</strong>结算，金额单位为元，自动转为分发送给微信<br>
            6. 前端根据返回的凭证类型处理：
               <br>　• <strong>pay_url</strong> → 跳转支付（H5）
               <br>　• <strong>qr_code_url</strong> → 生成二维码供用户扫码（NATIVE）
               <br>　• <strong>trade_params</strong> → 调用 WeixinJSBridge.invoke() 发起支付（JSAPI）
        </div>
        '''