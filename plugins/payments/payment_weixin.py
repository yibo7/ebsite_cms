import json
import time
import base64
import logging
from decimal import Decimal
from typing import Tuple, Dict, Any, Optional
from urllib.parse import quote

import requests
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
from Crypto.Hash import SHA256
from Crypto.Cipher import AES as AES_CBC

from entity.pay_back_model import PayBackInfo
from entity.pay_link_result import PayLinkResult
from plugins.plugin_base import PaymentBase, plugin_attribute


@plugin_attribute("微信支付V3", "3.0", "eb_site")
class WechatPayPlugin(PaymentBase):
    """
    微信支付 V3 API 插件。

    基于 2025 年最新版微信支付 V3 JSON API 实现，
    支持 JSAPI（公众号/小程序）、NATIVE（扫码）、H5（手机网页）三种支付场景。
    """

    def __init__(self, current_app):
        super().__init__(current_app)
        # ======== 配置项 ========
        self.app_id = ""               # 公众号/小程序 AppID
        self.mch_id = ""               # 微信支付商户号（V3 中参数名为 mchid）
        self.api_v3_key = ""           # APIv3 密钥（32 字节，用于回调数据解密）
        self.mch_private_key = ""      # 商户私钥（PEM 格式，用于请求签名）
        self.mch_serial_no = ""        # 商户证书序列号
        self.auth_type = "NATIVE"      # 支付场景: NATIVE / JSAPI / H5
        self.platform_serial_cache = {}  # {serial_no: cert_pem} 平台证书缓存

        self.info = "基于微信支付 V3 API 的支付插件"
        self.base_url = "https://api.mch.weixin.qq.com"
        self.logger = logging.getLogger(__name__)

    # ==================== 配置校验 ====================

    def _validate_config(self) -> bool:
        if not self.app_id:
            self.logger.error("AppID 未配置")
            return False
        if not self.mch_id:
            self.logger.error("商户号未配置")
            return False
        if not self.api_v3_key:
            self.logger.error("APIv3 密钥未配置")
            return False
        if not self.mch_private_key:
            self.logger.error("商户私钥未配置")
            return False
        if not self.mch_serial_no:
            self.logger.error("商户证书序列号未配置")
            return False
        if not self.notify_url:
            self.logger.error("回调地址未配置")
            return False
        return True

    def _validate_order_params(self, order_id: str, amount: float) -> Tuple[bool, str]:
        if not order_id or not isinstance(order_id, str):
            return False, "订单号无效"
        if not isinstance(amount, (int, float)) or amount <= 0:
            return False, "金额必须大于0"
        if amount > 100000:
            return False, "单笔金额不能超过100000元"
        # 金额只能到分
        if int(amount * 100) != round(amount * 100):
            return False, "金额精度不能超过2位小数"
        return True, ""

    # ==================== 签名工具 ====================

    def _format_private_key(self, key_str: str) -> str:
        """统一私钥格式，兼容带/不带 BEGIN 标记"""
        key_str = key_str.strip()
        if not key_str.startswith('-----BEGIN'):
            key_str = f"-----BEGIN RSA PRIVATE KEY-----\n{key_str}\n-----END RSA PRIVATE KEY-----"
        return key_str

    def _load_private_key(self):
        """加载商户 RSA 私钥"""
        formatted_key = self._format_private_key(self.mch_private_key)
        return RSA.importKey(formatted_key)

    def _rsa_sign(self, message: str) -> str:
        """使用商户私钥对消息做 SHA256-RSA 签名（PKCS1v15）"""
        key = self._load_private_key()
        signer = PKCS1_v1_5.new(key)
        digest = SHA256.new(message.encode('utf-8'))
        signature = signer.sign(digest)
        return base64.b64encode(signature).decode('utf-8')

    def _rsa_verify(self, message: str, signature_b64: str, cert_pem: str) -> bool:
        """使用平台证书公钥验证签名"""
        try:
            key_str = cert_pem.strip()
            if not key_str.startswith('-----BEGIN'):
                key_str = f"-----BEGIN PUBLIC KEY-----\n{key_str}\n-----END PUBLIC KEY-----"
            public_key = RSA.importKey(key_str)
            verifier = PKCS1_v1_5.new(public_key)
            digest = SHA256.new(message.encode('utf-8'))
            return verifier.verify(digest, base64.b64decode(signature_b64))
        except Exception:
            return False

    def _generate_nonce_str(self, length=32) -> str:
        import random
        import string
        chars = string.ascii_letters + string.digits
        return ''.join(random.choice(chars) for _ in range(length))

    def _build_auth_header(self, method: str, url_path: str, body: str = "") -> str:
        """
        构造 V3 API 请求的 Authorization 头。

        WECHATPAY2-SHA256-RSA2048
        mchid="...",nonce_str="...",timestamp="...",serial_no="...",signature="..."
        """
        timestamp = str(int(time.time()))
        nonce = self._generate_nonce_str()
        message = f"{method}\n{url_path}\n{timestamp}\n{nonce}\n{body}\n"
        signature = self._rsa_sign(message)
        return (
            f'WECHATPAY2-SHA256-RSA2048 '
            f'mchid="{self.mch_id}",'
            f'nonce_str="{nonce}",'
            f'timestamp="{timestamp}",'
            f'serial_no="{self.mch_serial_no}",'
            f'signature="{signature}"'
        )

    def _decrypt_aes_256_gcm(self, ciphertext_b64: str, nonce: str, associated_data: str) -> str:
        """
        使用 APIv3 密钥解密 AEAD_AES_256_GCM 密文。

        pycryptodome 的 AES GCM 模式要求解密时 manually 拼接
        ciphertext + tag（最后 16 字节），因为 decrypt_and_verify
        期望输入是 (密文+tag) 的合并体。
        """
        key = self.api_v3_key.encode('utf-8')
        if len(key) != 32:
            raise ValueError(f"APIv3 密钥长度必须为 32 字节，当前为 {len(key)} 字节")

        raw = base64.b64decode(ciphertext_b64)
        # GCM 密文的最后 16 字节是认证标签 (tag)
        ct = raw[:-16]
        tag = raw[-16:]

        nonce_bytes = nonce.encode('utf-8')
        aad = associated_data.encode('utf-8') if associated_data else None

        cipher = AES_CBC.new(key, AES_CBC.MODE_GCM, nonce=nonce_bytes, mac_len=16)
        cipher.update(aad or b'')
        plaintext = cipher.decrypt_and_verify(ct, tag)
        return plaintext.decode('utf-8')

    # ==================== 平台证书管理 ====================

    def _fetch_platform_certificates(self) -> Dict[str, str]:
        """
        获取微信支付平台证书列表。

        接口: GET /v3/certificates
        证书内容使用 APIv3 密钥解密。
        """
        url_path = "/v3/certificates"
        headers = {
            "Authorization": self._build_auth_header("GET", url_path),
            "Accept": "application/json",
            "User-Agent": "ebsite-cms/1.0",
        }
        url = f"{self.base_url}{url_path}"
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        body = resp.json()

        certs = {}
        for item in body.get('data', []):
            serial_no = item.get('serial_no', '')
            encrypt_cert = item.get('encrypt_certificate', {})
            nonce = encrypt_cert.get('nonce', '')
            ciphertext = encrypt_cert.get('ciphertext', '')
            associated_data = encrypt_cert.get('associated_data', '')

            cert_pem = self._decrypt_aes_256_gcm(ciphertext, nonce, associated_data)
            certs[serial_no] = cert_pem

        return certs

    def _get_platform_cert(self, serial_no: str) -> Optional[str]:
        """按序列号获取平台证书（带内存缓存）"""
        if serial_no not in self.platform_serial_cache:
            try:
                self.platform_serial_cache = self._fetch_platform_certificates()
            except Exception as e:
                self.logger.error(f"获取平台证书失败: {str(e)}")
                return None
        return self.platform_serial_cache.get(serial_no)

    # ==================== HTTP 请求（V3 签名版） ====================

    def _v3_request(self, method: str, url_path: str, body: dict = None) -> Dict[str, Any]:
        """发送带 V3 签名的 HTTP 请求"""
        body_str = json.dumps(body, separators=(',', ':'), ensure_ascii=False) if body else ""
        headers = {
            "Authorization": self._build_auth_header(method, url_path, body_str),
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "ebsite-cms/1.0",
        }
        url = f"{self.base_url}{url_path}"
        self.logger.info(f"微信V3请求: {method} {url_path}")

        if method == "GET":
            resp = requests.get(url, headers=headers, timeout=15)
        else:
            resp = requests.post(url, headers=headers, data=body_str.encode('utf-8'), timeout=15)

        if resp.status_code != 200:
            raise requests.exceptions.HTTPError(
                f"HTTP {resp.status_code}: {resp.text[:300]}",
                response=resp,
            )
        return resp.json()

    # ==================== 下单参数构建 ====================

    def _build_order_body(self, order_id: str, amount: float,
                          description: str = None, **kwargs) -> dict:
        """构建下单接口的通用请求体"""
        time_expire = kwargs.get('time_expire')
        if not time_expire:
            # 默认 30 分钟后过期，rfc3339 格式
            from datetime import datetime, timezone, timedelta
            expire_dt = datetime.now(timezone(timedelta(hours=8))) + timedelta(minutes=30)
            time_expire = expire_dt.strftime('%Y-%m-%dT%H:%M:%S+08:00')

        body = {
            "appid": self.app_id,
            "mchid": self.mch_id,
            "description": description or f"订单 {order_id}",
            "out_trade_no": order_id,
            "time_expire": time_expire,
            "notify_url": self.notify_url,
            "amount": {
                "total": int(round(amount * 100)),
                "currency": "CNY",
            },
        }

        # 商户附加数据（回调时会原样返回）
        if kwargs.get('attach'):
            body['attach'] = kwargs['attach']

        # 场景信息（必填用户 IP）
        client_ip = kwargs.get('client_ip', '127.0.0.1')
        body['scene_info'] = {"payer_client_ip": client_ip}

        return body

    # ==================== 必选接口 ====================

    def create_pay_link(self, order_id: str, amount: float, **kwargs) -> Tuple[bool, str, PayLinkResult]:
        """
        创建微信支付凭证。

        auth_type = NATIVE → 返回 qr_code_url（二维码扫码）
        auth_type = JSAPI  → 返回 trade_params（JSAPI 调起支付参数）
        auth_type = H5     → 返回 pay_url（H5 跳转链接）
        """
        result = PayLinkResult()
        try:
            if not self._validate_config():
                return False, "微信支付配置不完整", result

            is_valid, error_msg = self._validate_order_params(order_id, amount)
            if not is_valid:
                return False, error_msg, result

            auth_type = kwargs.get('auth_type', self.auth_type)
            description = kwargs.get('description')
            order_body = self._build_order_body(order_id, amount, description, **kwargs)

            # JSAPI 需要 openid
            if auth_type == 'JSAPI':
                openid = kwargs.get('openid')
                if not openid:
                    return False, "JSAPI 支付需要传入 openid", result
                order_body['payer'] = {"openid": openid}
                url_path = "/v3/pay/transactions/jsapi"
            elif auth_type == 'NATIVE':
                url_path = "/v3/pay/transactions/native"
            elif auth_type == 'H5':
                url_path = "/v3/pay/transactions/h5"
                order_body['scene_info']['h5_info'] = {
                    "type": "Wap",
                    "app_name": kwargs.get('app_name', '在线商城'),
                    "app_url": kwargs.get('app_url', ''),
                }
            else:
                return False, f"不支持的支付场景: {auth_type}", result

            resp = self._v3_request("POST", url_path, order_body)

            if auth_type == 'NATIVE':
                result.qr_code_url = resp.get('code_url', '')
                if not result.qr_code_url:
                    return False, "未获取到二维码链接", result
            elif auth_type == 'JSAPI':
                prepay_id = resp.get('prepay_id', '')
                if not prepay_id:
                    return False, "未获取到 prepay_id", result
                result.trade_params = self._build_jsapi_params(prepay_id)
            elif auth_type == 'H5':
                result.pay_url = resp.get('h5_url', '')
                if not result.pay_url:
                    return False, "未获取到 H5 支付链接", result

            return True, '', result

        except requests.exceptions.HTTPError as e:
            self.logger.error(f"微信V3下单HTTP错误: {e}")
            return False, f"下单请求失败: HTTP {e.response.status_code}", result
        except Exception as e:
            self.logger.error(f"创建支付失败: {str(e)}")
            return False, f"创建支付失败: {str(e)}", result

    def _build_jsapi_params(self, prepay_id: str) -> Dict[str, str]:
        """
        构建 JSAPI 调起支付所需的参数。

        V3 要求 signType = RSA，签名使用商户私钥。
        """
        params = {
            "appId": self.app_id,
            "timeStamp": str(int(time.time())),
            "nonceStr": self._generate_nonce_str(),
            "package": f"prepay_id={prepay_id}",
            "signType": "RSA",
        }
        # 签名串: appId\ntimeStamp\nnonceStr\npackage\n
        sign_message = f"{params['appId']}\n{params['timeStamp']}\n{params['nonceStr']}\n{params['package']}\n"
        params['paySign'] = self._rsa_sign(sign_message)
        return params

    def call_back(self, request) -> Tuple[bool, str, PayBackInfo]:
        """
        处理微信支付 V3 异步回调。

        V3 回调说明：
          - 请求体为 JSON，resource 字段经过 AEAD_AES_256_GCM 加密
          - 需使用 APIv3 密钥解密后才能获取交易数据
          - 可选验证 Wechatpay-Signature 请求头
        """
        pay_info = PayBackInfo()
        try:
            body_json = request.get_data(as_text=True)
            if not body_json:
                return False, "回调数据为空", pay_info

            body = json.loads(body_json)
            self.logger.info(f"收到微信V3回调: event_type={body.get('event_type')}")

            # === 第一步：验签（可选但建议） ===
            wechatpay_serial = request.headers.get('Wechatpay-Serial', '')
            wechatpay_signature = request.headers.get('Wechatpay-Signature', '')
            wechatpay_timestamp = request.headers.get('Wechatpay-Timestamp', '')
            wechatpay_nonce = request.headers.get('Wechatpay-Nonce', '')

            if wechatpay_serial and wechatpay_signature:
                cert_pem = self._get_platform_cert(wechatpay_serial)
                if cert_pem:
                    sign_message = f"{wechatpay_timestamp}\n{wechatpay_nonce}\n{body_json}\n"
                    if not self._rsa_verify(sign_message, wechatpay_signature, cert_pem):
                        self.logger.warning("微信V3回调签名验证失败，将仅依赖解密验证")
                else:
                    self.logger.warning(f"未找到序列号 {wechatpay_serial} 对应的平台证书，跳过验签")

            # === 第二步：解密 resource ===
            resource = body.get('resource', {})
            if not resource:
                return False, "回调中缺少 resource 字段", pay_info

            ciphertext = resource.get('ciphertext', '')
            nonce = resource.get('nonce', '')
            associated_data = resource.get('associated_data', '')

            if not ciphertext or not nonce:
                return False, "回调 resource 缺少 ciphertext 或 nonce", pay_info

            plaintext = self._decrypt_aes_256_gcm(ciphertext, nonce, associated_data)
            self.logger.info(f"微信V3回调解密成功")
            trade_data = json.loads(plaintext)

            # === 第三步：解析交易数据 ===
            trade_state = trade_data.get('trade_state', '')
            pay_info.order_no = trade_data.get('out_trade_no', '')
            pay_info.trade_no = trade_data.get('transaction_id', '')
            pay_info.pay_amount = Decimal(str(trade_data.get('amount', {}).get('total', 0))) / 100
            pay_info.currency = "CNY"
            pay_info.payment_method = "wechat"
            pay_info.buy_user_name = trade_data.get('payer', {}).get('openid', '')
            pay_info.raw_data = trade_data

            if trade_state == 'SUCCESS':
                pay_info.is_successful = True
                pay_info.status_code = 1
                pay_info.info = "支付成功"
                return True, "支付成功", pay_info
            else:
                pay_info.info = f"交易状态: {trade_state}"
                return False, pay_info.info, pay_info

        except json.JSONDecodeError as e:
            return False, f"回调数据 JSON 解析失败: {str(e)}", pay_info
        except Exception as e:
            return False, f"处理回调失败: {str(e)}", pay_info

    def notify_response(self, notify_data: PayBackInfo) -> str:
        """
        返回微信支付 V3 要求的回调确认响应。

        处理成功返回空字符串（HTTP 200），失败返回 JSON 告知微信需要重试。
        """
        if notify_data.is_successful:
            return ""
        return json.dumps({"code": "FAIL", "message": notify_data.info})

    # ==================== 可选接口 ====================

    def query_order(self, order_id: str) -> Tuple[bool, str, PayBackInfo]:
        """
        查询微信支付订单状态（通过商户订单号）。
        文档：https://pay.weixin.qq.com/doc/v3/merchant/4012791859
        """
        pay_info = PayBackInfo()
        try:
            if not self._validate_config():
                return False, "微信支付配置不完整", pay_info

            url_path = f"/v3/pay/transactions/out-trade-no/{quote(order_id, safe='')}?mchid={self.mch_id}"
            resp = self._v3_request("GET", url_path)

            trade_state = resp.get('trade_state', 'UNKNOWN')
            pay_info.order_no = resp.get('out_trade_no', order_id)
            pay_info.trade_no = resp.get('transaction_id', '')
            pay_info.pay_amount = Decimal(str(resp.get('amount', {}).get('total', 0))) / 100
            pay_info.is_successful = (trade_state == 'SUCCESS')
            pay_info.status_code = 1 if trade_state == 'SUCCESS' else 0
            pay_info.currency = "CNY"
            pay_info.raw_data = resp
            pay_info.info = resp.get('trade_state_desc', trade_state)

            return True, "查询成功", pay_info

        except requests.exceptions.HTTPError as e:
            code = e.response.status_code
            if code == 404:
                return False, "订单不存在", pay_info
            return False, f"查询请求失败: HTTP {code}", pay_info
        except Exception as e:
            return False, f"查询订单失败: {str(e)}", pay_info

    def refund_order(self, order_id: str, amount: float, reason: str = "") -> Tuple[bool, str, PayBackInfo]:
        """
        微信支付 V3 退款。
        文档：https://pay.weixin.qq.com/doc/v3/merchant/4012791862

        注意：V3 退款无需双向证书，但仍需正确配置 APIv3 密钥和商户私钥。
        """
        pay_info = PayBackInfo()
        try:
            if not self._validate_config():
                return False, "微信支付配置不完整", pay_info
            if amount <= 0:
                return False, "退款金额必须大于0", pay_info

            # 先查询订单获取原始总金额
            query_ok, query_msg, query_info = self.query_order(order_id)
            if not query_ok:
                return False, f"无法获取订单信息: {query_msg}", pay_info
            original_total_fen = int(query_info.pay_amount * 100) if query_info.pay_amount > 0 else int(round(amount * 100))

            refund_body = {
                "out_trade_no": order_id,
                "out_refund_no": f"R{order_id}{int(time.time())}",
                "amount": {
                    "refund": int(round(amount * 100)),
                    "total": original_total_fen,
                    "currency": "CNY",
                },
                "notify_url": self.notify_url,
            }
            if reason:
                refund_body['reason'] = reason

            resp = self._v3_request("POST", "/v3/refund/domestic/refunds", refund_body)

            refund_status = resp.get('status', '')
            pay_info.order_no = resp.get('out_trade_no', order_id)
            pay_info.trade_no = resp.get('refund_id', '')
            pay_info.pay_amount = Decimal(str(resp.get('amount', {}).get('refund', 0))) / 100
            pay_info.raw_data = resp

            if refund_status in ['SUCCESS', 'PROCESSING']:
                pay_info.is_successful = True
                pay_info.info = f"退款{'处理中' if refund_status == 'PROCESSING' else '成功'}"
                return True, pay_info.info, pay_info
            else:
                pay_info.info = f"退款失败: {refund_status}"
                return False, pay_info.info, pay_info

        except requests.exceptions.HTTPError as e:
            detail = ""
            try:
                detail = e.response.text[:300]
            except Exception:
                pass
            return False, f"退款请求失败: HTTP {e.response.status_code} {detail}", pay_info
        except Exception as e:
            return False, f"退款失败: {str(e)}", pay_info

    def close_order(self, order_id: str) -> Tuple[bool, str]:
        """
        关闭微信支付订单（仅限未支付订单）。
        文档：https://pay.weixin.qq.com/doc/v3/merchant/4012791860
        """
        try:
            if not self._validate_config():
                return False, "微信支付配置不完整"

            body = {"mchid": self.mch_id}
            url_path = f"/v3/pay/transactions/out-trade-no/{quote(order_id, safe='')}/close"
            self._v3_request("POST", url_path, body)

            return True, "订单已关闭"

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return False, "订单不存在"
            return False, f"关闭订单失败: HTTP {e.response.status_code}"
        except Exception as e:
            return False, f"关闭订单失败: {str(e)}"

    # ==================== 后台配置表单 ====================

    def params_temp(self) -> str:
        return '''
        <div class="form-group p-2">
            <label for="app_id">AppID <span style="color: red;">*</span></label>
            <input type="text" id="app_id" name="app_id"
                   value="{{model.app_id}}" class="form-control"
                   placeholder="请输入公众号/小程序的 AppID" required/>
            <small class="form-text text-muted">在微信公众平台（mp.weixin.qq.com）获取</small>
        </div>
        <div class="form-group p-2">
            <label for="mch_id">商户号 <span style="color: red;">*</span></label>
            <input type="text" id="mch_id" name="mch_id"
                   value="{{model.mch_id}}" class="form-control"
                   placeholder="请输入微信支付商户号" required/>
            <small class="form-text text-muted">在微信支付商户平台（pay.weixin.qq.com）获取</small>
        </div>
        <div class="form-group p-2">
            <label for="mch_serial_no">商户证书序列号 <span style="color: red;">*</span></label>
            <input type="text" id="mch_serial_no" name="mch_serial_no"
                   value="{{model.mch_serial_no}}" class="form-control"
                   placeholder="请查看商户证书详情中的序列号" required/>
            <small class="form-text text-muted">
                在商户平台 → 账户中心 → API安全 → 管理API证书中查看证书序列号
            </small>
        </div>
        <div class="form-group p-2">
            <label for="api_v3_key">APIv3 密钥 <span style="color: red;">*</span></label>
            <input type="text" id="api_v3_key" name="api_v3_key"
                   value="{{model.api_v3_key}}" class="form-control"
                   placeholder="32位字符，含数字和字母" required/>
            <small class="form-text text-muted">
                在商户平台 → 账户中心 → API安全 → 设置APIv3密钥（32字节）
            </small>
        </div>
        <div class="form-group p-2">
            <label for="mch_private_key">商户私钥 <span style="color: red;">*</span></label>
            <textarea id="mch_private_key" name="mch_private_key"
                      class="form-control" rows="8"
                      placeholder="-----BEGIN RSA PRIVATE KEY-----&#10;...&#10;-----END RSA PRIVATE KEY-----"
                      required>{{model.mch_private_key}}</textarea>
            <small class="form-text text-muted">
                生成 API 证书时同时生成的商户私钥文件（apiclient_key.pem），请妥善保管
            </small>
        </div>
        <div class="form-group p-2">
            <label for="auth_type">支付场景</label>
            <select id="auth_type" name="auth_type" class="form-control">
                <option value="NATIVE" {% if model.auth_type == 'NATIVE' %}selected{% endif %}>NATIVE - 扫码支付</option>
                <option value="JSAPI" {% if model.auth_type == 'JSAPI' %}selected{% endif %}>JSAPI - 公众号/小程序内支付</option>
                <option value="H5" {% if model.auth_type == 'H5' %}selected{% endif %}>H5 - 手机网页支付</option>
            </select>
            <small class="form-text text-muted">选择默认的支付调起方式</small>
        </div>
        <div class="form-group p-2">
            <label for="notify_url">回调通知地址</label>
            <input type="text" id="notify_url" name="notify_url"
                   value="{{model.notify_url}}" class="form-control"
                   placeholder="/pay/notify_url/WechatPayPlugin" disabled/>
            <small class="form-text text-muted">
                系统自动使用 <code>/pay/notify_url/WechatPayPlugin</code>，
                请在商户平台 → 产品中心 → 开发配置中设置完整的公网可访问 HTTPS 地址
            </small>
        </div>
        <div class="alert alert-warning mt-3">
            <strong>⚠️ 微信支付 V3 迁移说明：</strong><br>
            本插件基于微信支付 <strong>V3 API</strong> 实现，与旧版 V2（XML/MD5）不兼容。<br><br>
            <strong>配置步骤：</strong><br>
            1. 登录
            <a href="https://pay.weixin.qq.com/" target="_blank">微信支付商户平台</a><br>
            2. 账户中心 → API安全 → 申请/管理 <strong>API证书</strong>（V3 用）<br>
            3. 下载证书后，用文本编辑器打开 <code>apiclient_key.pem</code>，将完整内容填入上方的"商户私钥"字段<br>
            4. 在 API安全 页面查看证书详情，复制 <strong>证书序列号</strong><br>
            5. 在 API安全 页面设置 <strong>APIv3 密钥</strong>（需要是 32 字节的随机字符串）<br>
            6. 在产品中心 → 开发配置 中设置 <strong>支付回调通知地址</strong> 为完整的 HTTPS URL<br><br>
            <strong>前端对接：</strong><br>
            • NATIVE 扫码支付：使用返回的 <strong>qr_code_url</strong> 生成二维码<br>
            • JSAPI 公众号支付：使用返回的 <strong>trade_params</strong> 调用 WeixinJSBridge.invoke()<br>
            • H5 支付：直接跳转返回的 <strong>pay_url</strong><br><br>
            <strong>退款说明：</strong><br>
            V3 退款无需双向证书（V2 需要），但仍需配置好 APIv3 密钥和商户私钥。
        </div>
        '''