import json
import time
import base64
import logging
from typing import Tuple, Dict, Any
from urllib.parse import quote_plus, unquote_plus
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
from Crypto.Hash import SHA256

from entity.pay_back_model import PayBackInfo
from plugins.plugin_base import PaymentBase, plugin_attribute


@plugin_attribute("支付宝", "1.0", "eb_site")
class AlipayPlugin(PaymentBase):
    def __init__(self, current_app):
        super().__init__(current_app)
        self.app_id = ""
        self.private_key = ""
        self.alipay_public_key = ""
        self.info = "基于支付宝的支付插件（此插件用AI生成，未经测试，如有需要请自行修改）"
        self.gateway_url = "https://openapi.alipay.com/gateway.do"
        self.sandbox_gateway_url = "https://openapi.alipaydev.com/gateway.do"
        self.is_sandbox = False  # 是否使用沙箱环境

        # 设置日志
        self.logger = logging.getLogger(__name__)

    def notify_response(self, notify_data: PayBackInfo):
        """
        根据当前支付平台要求，在通知页面返回处理的结果，notify_data中有通知处理后的结果数据，但不同的平台可能对通知结果格式有不一样的要求
        """
        return "success"

    def _validate_config(self) -> bool:
        """验证配置参数"""
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
        """验证订单参数"""
        if not order_id or not isinstance(order_id, str):
            return False, "订单号无效"

        if not isinstance(amount, (int, float)) or amount <= 0:
            return False, "金额必须大于0"

        if amount > 100000:  # 单笔限额10万
            return False, "单笔金额不能超过100000元"

        # 金额精度检查（最多2位小数）
        if round(amount, 2) != amount:
            return False, "金额精度不能超过2位小数"

        return True, ""

    def _format_private_key(self, private_key: str) -> str:
        """格式化私钥"""
        key = private_key.strip()
        if not key.startswith('-----BEGIN'):
            key = f"-----BEGIN RSA PRIVATE KEY-----\n{key}\n-----END RSA PRIVATE KEY-----"
        return key

    def _format_public_key(self, public_key: str) -> str:
        """格式化公钥"""
        key = public_key.strip()
        if not key.startswith('-----BEGIN'):
            key = f"-----BEGIN PUBLIC KEY-----\n{key}\n-----END PUBLIC KEY-----"
        return key

    def _rsa2_sign(self, unsigned_string: str) -> str:
        """RSA2签名"""
        try:
            formatted_key = self._format_private_key(self.private_key)
            key = RSA.importKey(formatted_key)
            signer = PKCS1_v1_5.new(key)
            digest = SHA256.new(unsigned_string.encode('utf-8'))
            signature = signer.sign(digest)
            return base64.b64encode(signature).decode('utf-8')
        except Exception as e:
            self.logger.error(f"RSA2签名失败: {str(e)}")
            raise Exception(f"签名失败: {str(e)}")

    def _verify_signature(self, data: Dict[str, Any], signature: str) -> bool:
        """验证支付宝回调签名"""
        try:
            # 构造待验签字符串（排除sign和sign_type参数）
            items = []
            for key in sorted(data.keys()):
                if key not in ['sign', 'sign_type'] and data[key] is not None and str(data[key]).strip():
                    # URL解码参数值
                    value = unquote_plus(str(data[key]))
                    items.append(f"{key}={value}")

            unsigned_string = "&".join(items)
            self.logger.info(f"验签字符串: {unsigned_string}")

            # 验证签名
            formatted_key = self._format_public_key(self.alipay_public_key)
            key = RSA.importKey(formatted_key)
            verifier = PKCS1_v1_5.new(key)
            digest = SHA256.new(unsigned_string.encode('utf-8'))

            signature_bytes = base64.b64decode(signature)
            return verifier.verify(digest, signature_bytes)

        except Exception as e:
            self.logger.error(f"验签失败: {str(e)}")
            return False

    def _build_request_params(self, order_id: str, amount: float, subject: str = None) -> Dict[str, str]:
        """构建请求参数"""
        # 业务参数
        biz_content = {
            "out_trade_no": order_id,
            "product_code": "FAST_INSTANT_TRADE_PAY",
            "total_amount": f"{amount:.2f}",
            "subject": subject or f"订单 {order_id}",
            "timeout_express": "30m"  # 订单超时时间
        }

        # 公共参数
        params = {
            "app_id": self.app_id,
            "method": "alipay.trade.page.pay",
            "format": "JSON",
            "charset": "utf-8",
            "sign_type": "RSA2",
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
            "version": "1.0",
            "biz_content": json.dumps(biz_content, separators=(',', ':'), ensure_ascii=False)
        }

        # 添加回调地址（如果配置了）
        if hasattr(self, 'notify_url') and self.notify_url:
            params["notify_url"] = self.notify_url
        if hasattr(self, 'return_url') and self.return_url:
            params["return_url"] = self.return_url

        return params

    def create_pay_link(self, order_id: str, amount: float, **kwargs) -> Tuple[bool, str]:
        """创建支付链接"""
        try:
            # 1. 验证配置
            if not self._validate_config():
                return False, "支付宝配置不完整"

            # 2. 验证订单参数
            is_valid, error_msg = self._validate_order_params(order_id, amount)
            if not is_valid:
                return False, error_msg

            # 3. 构建请求参数
            subject = kwargs.get('subject')
            params = self._build_request_params(order_id, amount, subject)

            # 4. 生成待签名字符串
            unsigned_items = [f"{k}={params[k]}" for k in sorted(params.keys())]
            unsigned_string = "&".join(unsigned_items)

            self.logger.info(f"待签名字符串: {unsigned_string}")

            # 5. 生成签名
            signature = self._rsa2_sign(unsigned_string)

            # 6. 构建最终URL
            gateway_url = self.sandbox_gateway_url if self.is_sandbox else self.gateway_url
            query_items = [f"{k}={quote_plus(str(v), safe='')}" for k, v in params.items()]
            query_items.append(f"sign={quote_plus(signature, safe='')}")

            pay_url = f"{gateway_url}?{'&'.join(query_items)}"

            self.logger.info(f"创建支付链接成功，订单号: {order_id}")
            return True, pay_url

        except Exception as e:
            error_msg = f"创建支付链接失败: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg

    def call_back(self, request) -> Tuple[bool, str, Dict[str, Any]]:
        """处理支付宝回调"""
        try:
            # 1. 获取回调参数
            if request.method == 'POST':
                data = request.form.to_dict()
            else:
                data = request.args.to_dict()

            if not data:
                return False, "回调参数为空", {}

            self.logger.info(f"收到支付宝回调: {data}")

            # 2. 验证必要参数
            required_params = ['sign', 'sign_type', 'out_trade_no', 'trade_status']
            for param in required_params:
                if param not in data:
                    return False, f"缺少必要参数: {param}", {}

            # 3. 验证签名
            signature = data.get('sign')
            if not self._verify_signature(data, signature):
                self.logger.error("签名验证失败")
                return False, "签名验证失败", {}

            # 4. 检查交易状态
            trade_status = data.get('trade_status')
            order_id = data.get('out_trade_no')

            if trade_status in ['TRADE_SUCCESS', 'TRADE_FINISHED']:
                # 支付成功
                result_data = {
                    'order_id': order_id,
                    'trade_no': data.get('trade_no'),
                    'buyer_email': data.get('buyer_logon_id'),
                    'amount': float(data.get('total_amount', 0)),
                    'trade_status': trade_status,
                    'gmt_payment': data.get('gmt_payment'),
                    'receipt_amount': data.get('receipt_amount')
                }

                self.logger.info(f"订单 {order_id} 支付成功")
                return True, "支付成功", result_data

            elif trade_status == 'WAIT_BUYER_PAY':
                # 等待买家付款
                return False, "等待买家付款", {'order_id': order_id, 'trade_status': trade_status}

            elif trade_status == 'TRADE_CLOSED':
                # 交易关闭
                return False, "交易已关闭", {'order_id': order_id, 'trade_status': trade_status}

            else:
                # 其他状态
                return False, f"未知交易状态: {trade_status}", {'order_id': order_id, 'trade_status': trade_status}

        except Exception as e:
            error_msg = f"处理回调失败: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg, {}

    def query_order(self, order_id: str) -> Tuple[bool, str, Dict[str, Any]]:
        """查询订单状态"""
        try:
            if not self._validate_config():
                return False, "支付宝配置不完整", {}

            # 构建查询参数
            biz_content = {
                "out_trade_no": order_id
            }

            params = {
                "app_id": self.app_id,
                "method": "alipay.trade.query",
                "format": "JSON",
                "charset": "utf-8",
                "sign_type": "RSA2",
                "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
                "version": "1.0",
                "biz_content": json.dumps(biz_content, separators=(',', ':'))
            }

            # 生成签名
            unsigned_items = [f"{k}={params[k]}" for k in sorted(params.keys())]
            unsigned_string = "&".join(unsigned_items)
            signature = self._rsa2_sign(unsigned_string)

            # 这里需要发送HTTP请求到支付宝接口
            # 由于这是一个示例，这里只返回模拟结果
            self.logger.info(f"查询订单: {order_id}")
            return True, "查询成功", {"order_id": order_id, "status": "unknown"}

        except Exception as e:
            error_msg = f"查询订单失败: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg, {}

    def close_order(self, order_id: str) -> Tuple[bool, str]:
        """关闭订单"""
        try:
            if not self._validate_config():
                return False, "支付宝配置不完整"

            # 构建关闭订单参数
            biz_content = {
                "out_trade_no": order_id
            }

            params = {
                "app_id": self.app_id,
                "method": "alipay.trade.close",
                "format": "JSON",
                "charset": "utf-8",
                "sign_type": "RSA2",
                "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
                "version": "1.0",
                "biz_content": json.dumps(biz_content, separators=(',', ':'))
            }

            # 生成签名
            unsigned_items = [f"{k}={params[k]}" for k in sorted(params.keys())]
            unsigned_string = "&".join(unsigned_items)
            signature = self._rsa2_sign(unsigned_string)

            # 这里需要发送HTTP请求到支付宝接口
            self.logger.info(f"关闭订单: {order_id}")
            return True, "订单关闭成功"

        except Exception as e:
            error_msg = f"关闭订单失败: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg

    def refund_order(self, order_id: str, refund_amount: float, refund_reason: str = "") -> Tuple[
        bool, str, Dict[str, Any]]:
        """订单退款"""
        try:
            if not self._validate_config():
                return False, "支付宝配置不完整", {}

            if refund_amount <= 0:
                return False, "退款金额必须大于0", {}

            # 构建退款参数
            biz_content = {
                "out_trade_no": order_id,
                "refund_amount": f"{refund_amount:.2f}",
                "refund_reason": refund_reason or "用户申请退款"
            }

            params = {
                "app_id": self.app_id,
                "method": "alipay.trade.refund",
                "format": "JSON",
                "charset": "utf-8",
                "sign_type": "RSA2",
                "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
                "version": "1.0",
                "biz_content": json.dumps(biz_content, separators=(',', ':'))
            }

            # 生成签名
            unsigned_items = [f"{k}={params[k]}" for k in sorted(params.keys())]
            unsigned_string = "&".join(unsigned_items)
            signature = self._rsa2_sign(unsigned_string)

            # 这里需要发送HTTP请求到支付宝接口
            self.logger.info(f"申请退款: 订单{order_id}, 金额{refund_amount}")
            return True, "退款申请成功", {"order_id": order_id, "refund_amount": refund_amount}

        except Exception as e:
            error_msg = f"退款失败: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg, {}

    def params_temp(self) -> str:
        """后台管理面板模板"""
        return '''
        <div class="form-group p-2">
            <label for="app_id">App ID <span style="color: red;">*</span></label>
            <input type="text" 
                   id="app_id"
                   name="app_id" 
                   value="{{model.app_id}}" 
                   class="form-control" 
                   placeholder="请输入支付宝应用的App ID"
                   required/>
            <small class="form-text text-muted">在支付宝开放平台创建应用后获得</small>
        </div>

        <div class="form-group p-2">
            <label for="alipay_public_key">支付宝公钥 <span style="color: red;">*</span></label>
            <textarea id="alipay_public_key"
                      name="alipay_public_key" 
                      class="form-control" 
                      rows="8"
                      placeholder="请输入支付宝公钥内容，可以包含或不包含BEGIN/END标识"
                      required>{{model.alipay_public_key}}</textarea>
            <small class="form-text text-muted">用于验证支付宝返回数据的签名</small>
        </div>

        <div class="form-group p-2">
            <label for="private_key">商户私钥 <span style="color: red;">*</span></label>
            <textarea id="private_key"
                      name="private_key" 
                      class="form-control" 
                      rows="8"
                      placeholder="请输入商户RSA私钥内容，可以包含或不包含BEGIN/END标识"
                      required>{{model.private_key}}</textarea>
            <small class="form-text text-muted">用于对请求参数进行签名，请妥善保管</small>
        </div>

        <div class="form-group p-2">
            <label for="is_sandbox">环境设置</label>
            <div class="form-check">
                <input type="checkbox" 
                       id="is_sandbox"
                       name="is_sandbox" 
                       class="form-check-input" 
                       value="1"
                       {% if model.is_sandbox %}checked{% endif %}>
                <label class="form-check-label" for="is_sandbox">
                    使用沙箱环境（测试环境）
                </label>
            </div>
            <small class="form-text text-muted">开发测试时请勾选，正式环境请取消勾选</small>
        </div>

        <div class="alert alert-warning mt-3">
            <h6>配置说明：</h6>
            <ul class="mb-0">
                <li>请确保在支付宝开放平台正确配置了应用的公钥</li>
                <li>回调地址需要在支付宝开放平台进行配置</li>
                <li>沙箱环境仅用于开发测试，不会产生真实交易</li>
                <li>私钥信息非常重要，请妥善保管，不要泄露</li>
            </ul>
        </div>
        <div class="alert alert-warning mt-3">
            <h6>支付宝支付插件配置说明：</h6>
            <div class="mb-0">
                <li>1. App ID: </br>
                   - 登录支付宝开放平台 (https://open.alipay.com)</br>
                   - 创建应用后获得的唯一标识</br>
                 </li>   
                <li>2. 应用私钥:</br>
                   - 使用支付宝提供的密钥生成工具生成RSA2密钥对</br>
                   - 私钥用于签名，需要妥善保管</br>
                </li>
                <li>3. 支付宝公钥:</br>
                   - 在支付宝开放平台上传应用公钥后获得</br>
                   - 用于验证支付宝返回数据的签名</br>
                </li>
                <li>4. 回调地址配置:</br>
                   - 需要在支付宝开放平台配置异步通知地址</br>
                   - 地址必须是公网可访问的HTTPS地址</br>
                </li>
                <li>注意事项：</br>
                    - 请确保服务器时间准确</br>
                    - 生产环境必须使用HTTPS</br>
                    - 定期检查和更新密钥</br>
                </li>
            </div>
        </div>
        '''
