import json
import time
import base64
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Tuple, Dict, Any
from urllib.parse import quote_plus, unquote_plus

import requests
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
from Crypto.Hash import SHA256

from entity.pay_back_model import PayBackInfo
from entity.pay_link_result import PayLinkResult
from plugins.plugin_base import PaymentBase, plugin_attribute


@plugin_attribute("支付宝", "1.1", "eb_site")
class AlipayPlugin(PaymentBase):
    def __init__(self, current_app):
        super().__init__(current_app)
        self.app_id = ""
        self.private_key = ""
        self.alipay_public_key = ""
        self.info = "基于支付宝的支付插件（v1.1 改进版）"
        self.gateway_url = "https://openapi.alipay.com/gateway.do"
        self.sandbox_gateway_url = "https://openapi.alipaydev.com/gateway.do"
        self.is_sandbox = False
        self.logger = logging.getLogger(__name__)

    # ==================== 配置校验 ====================

    def _validate_config(self) -> bool:
        if not self.app_id:
            self.logger.error("App ID 未配置")
            return False
        if not self.private_key:
            self.logger.error("商户私钥未配置")
            return False
        if not self.alipay_public_key:
            self.logger.error("支付宝公钥未配置")
            return False
        return True

    def _validate_order_params(self, order_id: str, amount: float) -> Tuple[bool, str]:
        if not order_id or not isinstance(order_id, str):
            return False, "订单号无效"
        if not isinstance(amount, (int, float)) or amount <= 0:
            return False, "金额必须大于0"
        if amount > 100000:
            return False, "单笔金额不能超过100000元"
        if round(amount, 2) != amount:
            return False, "金额精度不能超过2位小数"
        return True, ""

    # ==================== 签名工具 ====================

    def _format_private_key(self, private_key: str) -> str:
        key = private_key.strip()
        if not key.startswith('-----BEGIN'):
            key = f"-----BEGIN RSA PRIVATE KEY-----\n{key}\n-----END RSA PRIVATE KEY-----"
        return key

    def _format_public_key(self, public_key: str) -> str:
        key = public_key.strip()
        if not key.startswith('-----BEGIN'):
            key = f"-----BEGIN PUBLIC KEY-----\n{key}\n-----END PUBLIC KEY-----"
        return key

    def _rsa2_sign(self, unsigned_string: str) -> str:
        try:
            formatted_key = self._format_private_key(self.private_key)
            key = RSA.importKey(formatted_key)
            signer = PKCS1_v1_5.new(key)
            digest = SHA256.new(unsigned_string.encode('utf-8'))
            signature = signer.sign(digest)
            return base64.b64encode(signature).decode('utf-8')
        except Exception as e:
            self.logger.error(f"RSA2签名失败: {str(e)}")
            raise

    def _verify_signature(self, data: Dict[str, Any], signature: str) -> bool:
        try:
            items = []
            for key in sorted(data.keys()):
                # 剔除 sign / sign_type 以及 None / 空字符串
                if key not in ('sign', 'sign_type') and data[key] is not None and str(data[key]).strip():
                    value = unquote_plus(str(data[key]))
                    items.append(f"{key}={value}")
            unsigned_string = "&".join(items)

            formatted_key = self._format_public_key(self.alipay_public_key)
            key = RSA.importKey(formatted_key)
            verifier = PKCS1_v1_5.new(key)
            digest = SHA256.new(unsigned_string.encode('utf-8'))
            signature_bytes = base64.b64decode(signature)
            return verifier.verify(digest, signature_bytes)

        except Exception as e:
            self.logger.error(f"验签失败: {str(e)}")
            return False

    # ==================== HTTP 请求 ====================

    def _request(self, params: Dict[str, str]) -> Dict[str, Any]:
        """向支付宝网关发送请求并验签"""
        unsigned_items = [f"{k}={params[k]}" for k in sorted(params.keys())]
        unsigned_string = "&".join(unsigned_items)
        signature = self._rsa2_sign(unsigned_string)

        gateway_url = self.sandbox_gateway_url if self.is_sandbox else self.gateway_url
        query_items = [f"{k}={quote_plus(str(v), safe='')}" for k, v in params.items()]
        query_items.append(f"sign={quote_plus(signature, safe='')}")
        url = f"{gateway_url}?{'&'.join(query_items)}"

        self.logger.info(f"支付宝请求: method={params.get('method')}, out_trade_no={params.get('biz_content', '')[:80]}")
        resp = requests.get(url, timeout=15)
        resp.encoding = 'utf-8'

        try:
            body = resp.json()
        except ValueError:
            self.logger.error(f"支付宝响应非 JSON: {resp.text[:200]}")
            raise

        # 验签响应
        if 'sign' in body:
            resp_sign = body.pop('sign', '')
            if not self._verify_signature(body, resp_sign):
                self.logger.error("支付宝响应验签失败")
                raise Exception("支付宝响应签名验证失败")
            body['sign'] = resp_sign  # 还原

        return body

    # ==================== 业务参数构建 ====================

    def _build_request_params(self, order_id: str, amount: float,
                              subject: str = None, **kwargs) -> Dict[str, str]:
        biz_content = {
            "out_trade_no": order_id,
            "product_code": "FAST_INSTANT_TRADE_PAY",
            "total_amount": f"{amount:.2f}",
            "subject": subject or f"订单 {order_id}",
            # timeout_express 兼容旧版（相对分钟数）
            "timeout_express": "30m",
        }

        # 新版推荐使用 time_expire（绝对时间，rfc3339 格式）
        time_expire = kwargs.get('time_expire')
        if time_expire:
            biz_content["time_expire"] = time_expire
        else:
            # 默认 30 分钟后过期
            expire_time = datetime.now(timezone(timedelta(hours=8))) + timedelta(minutes=30)
            biz_content["time_expire"] = expire_time.strftime('%Y-%m-%d %H:%M:%S')

        # 可选参数：商品详情、附加信息等
        if kwargs.get('body'):
            biz_content['body'] = kwargs['body']
        if kwargs.get('goods_detail'):
            biz_content['goods_detail'] = kwargs['goods_detail']
        if kwargs.get('passback_params'):
            biz_content['passback_params'] = kwargs['passback_params']

        params = {
            "app_id": self.app_id,
            "method": "alipay.trade.page.pay",
            "format": "JSON",
            "charset": "utf-8",
            "sign_type": "RSA2",
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
            "version": "1.0",
            "biz_content": json.dumps(biz_content, separators=(',', ':'), ensure_ascii=False),
        }
        if self.notify_url:
            params["notify_url"] = self.notify_url
        if self.return_url:
            params["return_url"] = self.return_url
        return params

    # ==================== 必选接口 ====================

    def create_pay_link(self, order_id: str, amount: float, **kwargs) -> Tuple[bool, str, PayLinkResult]:
        """
        创建支付宝支付链接，返回 PayLinkResult.pay_url 用于前端跳转。
        """
        result = PayLinkResult()
        try:
            if not self._validate_config():
                return False, "支付宝配置不完整", result

            is_valid, error_msg = self._validate_order_params(order_id, amount)
            if not is_valid:
                return False, error_msg, result

            params = self._build_request_params(order_id, amount, kwargs.get('subject'), **kwargs)

            unsigned_items = [f"{k}={params[k]}" for k in sorted(params.keys())]
            unsigned_string = "&".join(unsigned_items)
            signature = self._rsa2_sign(unsigned_string)

            gateway_url = self.sandbox_gateway_url if self.is_sandbox else self.gateway_url
            query_items = [f"{k}={quote_plus(str(v), safe='')}" for k, v in params.items()]
            query_items.append(f"sign={quote_plus(signature, safe='')}")

            result.pay_url = f"{gateway_url}?{'&'.join(query_items)}"
            return True, '', result

        except Exception as e:
            return False, f"创建支付链接失败: {str(e)}", result

    def call_back(self, request) -> Tuple[bool, str, PayBackInfo]:
        """
        处理支付宝异步回调，返回标准化的 PayBackInfo。
        """
        pay_info = PayBackInfo()
        try:
            if request.method == 'POST':
                data = request.form.to_dict()
            else:
                data = request.args.to_dict()

            if not data:
                return False, "回调参数为空", pay_info

            self.logger.info(f"收到支付宝回调: out_trade_no={data.get('out_trade_no')}, "
                             f"trade_status={data.get('trade_status')}")

            required_params = ['sign', 'sign_type', 'out_trade_no', 'trade_status']
            for param in required_params:
                if param not in data:
                    return False, f"缺少必要参数: {param}", pay_info

            signature = data.pop('sign', '')
            if not self._verify_signature(data, signature):
                return False, "签名验证失败", pay_info

            trade_status = data.get('trade_status')
            pay_info.order_no = data.get('out_trade_no', '')
            pay_info.trade_no = data.get('trade_no', '')
            pay_info.pay_amount = Decimal(str(data.get('total_amount', '0')))
            pay_info.currency = "CNY"
            pay_info.payment_method = "alipay"
            pay_info.buy_user_name = data.get('buyer_logon_id', '')
            pay_info.raw_data = data

            if trade_status in ['TRADE_SUCCESS', 'TRADE_FINISHED']:
                pay_info.is_successful = True
                pay_info.status_code = 1
                pay_info.info = "支付成功"
                return True, "支付成功", pay_info
            elif trade_status == 'WAIT_BUYER_PAY':
                pay_info.status_code = 2
                pay_info.info = "等待买家付款"
                return False, "等待买家付款", pay_info
            elif trade_status == 'TRADE_CLOSED':
                pay_info.info = "交易已关闭"
                return False, "交易已关闭", pay_info
            else:
                pay_info.info = f"未知交易状态: {trade_status}"
                return False, pay_info.info, pay_info

        except Exception as e:
            return False, f"处理回调失败: {str(e)}", pay_info

    def notify_response(self, notify_data: PayBackInfo) -> str:
        """返回支付宝要求的确认响应"""
        return "success"

    # ==================== 可选接口 ====================

    def query_order(self, order_id: str) -> Tuple[bool, str, PayBackInfo]:
        """
        查询支付宝订单状态。
        文档：https://opendocs.alipay.com/open/02ekfj
        """
        pay_info = PayBackInfo()
        try:
            if not self._validate_config():
                return False, "支付宝配置不完整", pay_info

            biz_content = {"out_trade_no": order_id}
            params = {
                "app_id": self.app_id,
                "method": "alipay.trade.query",
                "format": "JSON",
                "charset": "utf-8",
                "sign_type": "RSA2",
                "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
                "version": "1.0",
                "biz_content": json.dumps(biz_content, separators=(',', ':')),
            }

            body = self._request(params)

            resp_data = body.get('alipay_trade_query_response', {})
            if resp_data.get('code') != '10000':
                return False, resp_data.get('sub_msg', resp_data.get('msg', '查询失败')), pay_info

            trade_status = resp_data.get('trade_status', '')
            pay_info.order_no = resp_data.get('out_trade_no', order_id)
            pay_info.trade_no = resp_data.get('trade_no', '')
            pay_info.pay_amount = Decimal(str(resp_data.get('total_amount', '0')))
            pay_info.is_successful = (trade_status == 'TRADE_SUCCESS')
            pay_info.status_code = 1 if trade_status == 'TRADE_SUCCESS' else 0
            pay_info.currency = "CNY"
            pay_info.raw_data = resp_data
            pay_info.info = resp_data.get('trade_status', 'UNKNOWN')

            return True, "查询成功", pay_info

        except Exception as e:
            return False, f"查询订单失败: {str(e)}", pay_info

    def refund_order(self, order_id: str, amount: float, reason: str = "") -> Tuple[bool, str, PayBackInfo]:
        """
        支付宝退款。文档：https://opendocs.alipay.com/open/02e7go
        注意：如果交易发生了退款，支付宝推荐使用 out_request_no 做幂等。
        """
        pay_info = PayBackInfo()
        try:
            if not self._validate_config():
                return False, "支付宝配置不完整", pay_info
            if amount <= 0:
                return False, "退款金额必须大于0", pay_info

            biz_content = {
                "out_trade_no": order_id,
                "refund_amount": f"{amount:.2f}",
                "refund_reason": reason or "用户申请退款",
                "out_request_no": f"R{order_id}{int(time.time())}",
            }
            params = {
                "app_id": self.app_id,
                "method": "alipay.trade.refund",
                "format": "JSON",
                "charset": "utf-8",
                "sign_type": "RSA2",
                "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
                "version": "1.0",
                "biz_content": json.dumps(biz_content, separators=(',', ':')),
            }

            body = self._request(params)

            resp_data = body.get('alipay_trade_refund_response', {})
            if resp_data.get('code') != '10000':
                return False, resp_data.get('sub_msg', resp_data.get('msg', '退款失败')), pay_info

            # code == 10000 且 fund_change 为 Y 或 refund_fee > 0
            pay_info.is_successful = True
            pay_info.order_no = resp_data.get('out_trade_no', order_id)
            pay_info.trade_no = resp_data.get('trade_no', '')
            pay_info.pay_amount = Decimal(str(resp_data.get('refund_fee', amount)))
            pay_info.raw_data = resp_data
            pay_info.info = "退款成功"

            return True, "退款成功", pay_info

        except Exception as e:
            return False, f"退款失败: {str(e)}", pay_info

    def close_order(self, order_id: str) -> Tuple[bool, str]:
        """
        关闭支付宝订单（仅限未支付订单）。
        文档：https://opendocs.alipay.com/open/02e7gn
        """
        try:
            if not self._validate_config():
                return False, "支付宝配置不完整"

            biz_content = {"out_trade_no": order_id}
            params = {
                "app_id": self.app_id,
                "method": "alipay.trade.close",
                "format": "JSON",
                "charset": "utf-8",
                "sign_type": "RSA2",
                "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
                "version": "1.0",
                "biz_content": json.dumps(biz_content, separators=(',', ':')),
            }

            body = self._request(params)

            resp_data = body.get('alipay_trade_close_response', {})
            if resp_data.get('code') != '10000':
                return False, resp_data.get('sub_msg', resp_data.get('msg', '关闭订单失败'))

            return True, "订单已关闭"

        except Exception as e:
            return False, f"关闭订单失败: {str(e)}"

    # ==================== 后台配置表单 ====================

    def params_temp(self) -> str:
        return '''
        <div class="form-group p-2">
            <label for="app_id">App ID <span style="color: red;">*</span></label>
            <input type="text" id="app_id" name="app_id"
                   value="{{model.app_id}}" class="form-control"
                   placeholder="请输入支付宝应用的App ID" required/>
            <small class="form-text text-muted">在支付宝开放平台创建应用后获得</small>
        </div>
        <div class="form-group p-2">
            <label for="alipay_public_key">支付宝公钥 <span style="color: red;">*</span></label>
            <textarea id="alipay_public_key" name="alipay_public_key"
                      class="form-control" rows="8"
                      placeholder="请输入支付宝公钥内容，可以包含或不包含BEGIN/END标识"
                      required>{{model.alipay_public_key}}</textarea>
            <small class="form-text text-muted">用于验证支付宝返回数据的签名</small>
        </div>
        <div class="form-group p-2">
            <label for="private_key">商户私钥 <span style="color: red;">*</span></label>
            <textarea id="private_key" name="private_key"
                      class="form-control" rows="8"
                      placeholder="请输入商户RSA私钥内容，可以包含或不包含BEGIN/END标识"
                      required>{{model.private_key}}</textarea>
            <small class="form-text text-muted">用于对请求参数进行签名，请妥善保管</small>
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
            <a href="https://open.alipay.com/" target="_blank">支付宝开放平台</a>
            创建 <strong>网页应用</strong>，获取 <strong>App ID</strong><br>
            2. 使用支付宝提供的密钥工具生成 <strong>RSA2 密钥对</strong><br>
            3. 在开放平台上传 <strong>应用公钥</strong>，获取 <strong>支付宝公钥</strong><br>
            4. 在开放平台 → 开发设置 中设置 <strong>异步通知地址</strong>为：<br>
            <code>/pay/notify_url/AlipayPlugin</code>
            <br>（需补全为完整的公网 HTTPS 地址）<br>
            5. 本插件使用 <strong>CNY（人民币）</strong>结算<br>
            6. 前端收到 <strong>pay_url</strong> 后，直接跳转即可打开支付宝支付页面<br>
            7. 沙箱环境使用
            <a href="https://open.alipay.com/develop/sandbox" target="_blank">支付宝沙箱</a>
            进行开发测试<br>
            8. v1.1 新增：支持 time_expire 绝对时间、query/refund/close 实际 API 调用
        </div>
        '''