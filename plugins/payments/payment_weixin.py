import json
import time
import hashlib
import logging
from typing import Tuple, Dict, Any
from xml.etree import ElementTree
import requests
from plugins.plugin_base import PaymentBase, plugin_attribute


@plugin_attribute("微信支付", "1.0", "eb_site")
class WechatPayPlugin(PaymentBase):
    def __init__(self, current_app):
        super().__init__(current_app)
        self.app_id = ""  # 微信公众号或小程序appid
        self.mch_id = ""  # 微信支付商户号
        self.api_key = ""  # API密钥
        self.cert_path = ""  # 证书路径(退款需要)
        self.key_path = ""  # 密钥路径(退款需要)
        self.info = "基于微信支付的支付插件（此插件用AI生成，未经测试，如有需要请自行修改）"
        self.gateway_url = "https://api.mch.weixin.qq.com"
        self.sandbox_gateway_url = "https://api.mch.weixin.qq.com/sandboxnew"
        self.is_sandbox = False  # 是否使用沙箱环境
        self.logger = logging.getLogger(__name__)

    def _validate_config(self) -> bool:
        """验证配置参数"""
        if not all([self.app_id, self.mch_id, self.api_key]):
            self.logger.error("微信支付配置不完整")
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

        # 微信支付金额单位为分，必须为整数
        if int(amount * 100) != amount * 100:
            return False, "金额必须保留到分"

        return True, ""

    def _generate_nonce_str(self, length=32) -> str:
        """生成随机字符串"""
        import random
        import string
        chars = string.ascii_letters + string.digits
        return ''.join(random.choice(chars) for _ in range(length))

    def _generate_sign(self, params: Dict[str, Any]) -> str:
        """生成微信支付签名"""
        # 参数按key排序
        sorted_params = sorted(params.items(), key=lambda x: x[0])
        # 拼接成URL参数形式
        string_sign = '&'.join([f"{k}={v}" for k, v in sorted_params if k != 'sign' and v is not None])
        # 拼接API密钥
        string_sign += f"&key={self.api_key}"
        # MD5加密并转为大写
        return hashlib.md5(string_sign.encode('utf-8')).hexdigest().upper()

    def _verify_sign(self, params: Dict[str, Any]) -> bool:
        """验证微信支付签名"""
        if 'sign' not in params:
            return False

        sign = params.pop('sign')
        calculated_sign = self._generate_sign(params)
        return sign == calculated_sign

    def _build_request_params(self, order_id: str, amount: float, description: str = None, **kwargs) -> Dict[str, Any]:
        """构建请求参数"""
        params = {
            "appid": self.app_id,
            "mch_id": self.mch_id,
            "nonce_str": self._generate_nonce_str(),
            "body": description or f"订单 {order_id}",
            "out_trade_no": order_id,
            "total_fee": int(amount * 100),  # 微信支付单位为分
            "spbill_create_ip": kwargs.get('client_ip', '127.0.0.1'),
            "notify_url": getattr(self, 'notify_url', ''),
            "trade_type": kwargs.get('trade_type', 'NATIVE'),  # JSAPI, NATIVE, APP等
            "time_start": time.strftime('%Y%m%d%H%M%S'),
            "time_expire": time.strftime('%Y%m%d%H%M%S', time.localtime(time.time() + 1800))  # 30分钟过期
        }

        # 附加参数处理
        if kwargs.get('openid') and params['trade_type'] == 'JSAPI':
            params['openid'] = kwargs['openid']
        if kwargs.get('product_id') and params['trade_type'] == 'NATIVE':
            params['product_id'] = kwargs['product_id']

        # 生成签名
        params['sign'] = self._generate_sign(params)
        return params

    def _dict_to_xml(self, params: Dict[str, Any]) -> str:
        """字典转XML"""
        xml = ["<xml>"]
        for k, v in params.items():
            xml.append(f"<{k}>{v}</{k}>")
        xml.append("</xml>")
        return "".join(xml)

    def _xml_to_dict(self, xml_str: str) -> Dict[str, Any]:
        """XML转字典"""
        try:
            xml = ElementTree.fromstring(xml_str)
            return {child.tag: child.text for child in xml}
        except Exception as e:
            self.logger.error(f"XML解析失败: {str(e)}")
            return {}

    def create_pay_link(self, order_id: str, amount: float, **kwargs) -> Tuple[bool, str]:
        """创建支付链接/二维码"""
        try:
            # 1. 验证配置
            if not self._validate_config():
                return False, "微信支付配置不完整"

            # 2. 验证订单参数
            is_valid, error_msg = self._validate_order_params(order_id, amount)
            if not is_valid:
                return False, error_msg

            # 3. 构建请求参数
            params = self._build_request_params(order_id, amount, kwargs.get('description'), **kwargs)

            # 4. 发送请求
            base_url = self.sandbox_gateway_url if self.is_sandbox else self.gateway_url
            url = f"{base_url}/pay/unifiedorder"
            headers = {'Content-Type': 'application/xml'}
            response = requests.post(url, data=self._dict_to_xml(params).encode('utf-8'), headers=headers)

            # 5. 处理响应
            result = self._xml_to_dict(response.text)
            if result.get('return_code') != 'SUCCESS':
                return False, result.get('return_msg', '微信支付请求失败')

            if not self._verify_sign(result):
                return False, "签名验证失败"

            # 根据交易类型返回不同结果
            trade_type = params.get('trade_type', 'NATIVE')
            if trade_type == 'NATIVE':
                return True, result.get('code_url', '')  # 二维码链接
            elif trade_type == 'JSAPI':
                # 生成JSAPI支付参数
                jsapi_params = {
                    "appId": self.app_id,
                    "timeStamp": str(int(time.time())),
                    "nonceStr": self._generate_nonce_str(),
                    "package": f"prepay_id={result['prepay_id']}",
                    "signType": "MD5"
                }
                jsapi_params['paySign'] = self._generate_sign(jsapi_params)
                return True, json.dumps(jsapi_params)
            else:
                return True, json.dumps(result)

        except Exception as e:
            error_msg = f"创建支付链接失败: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg

    def call_back(self, request) -> Tuple[bool, str, Dict[str, Any]]:
        """处理微信支付回调"""
        try:
            # 1. 获取回调数据
            xml_data = request.data
            if not xml_data:
                return False, "回调数据为空", {}

            # 2. 解析XML
            callback_data = self._xml_to_dict(xml_data)
            self.logger.info(f"收到微信支付回调: {callback_data}")

            # 3. 验证签名
            if not self._verify_sign(callback_data):
                return False, "签名验证失败", {}

            # 4. 检查支付结果
            if callback_data.get('return_code') != 'SUCCESS':
                return False, f"支付失败: {callback_data.get('return_msg')}", {}

            if callback_data.get('result_code') != 'SUCCESS':
                return False, f"支付失败: {callback_data.get('err_code_des')}", {}

            # 5. 返回成功数据
            order_id = callback_data.get('out_trade_no')
            result_data = {
                'order_id': order_id,
                'transaction_id': callback_data.get('transaction_id'),
                'amount': float(callback_data.get('total_fee', 0)) / 100,  # 转换为元
                'payment_time': callback_data.get('time_end'),
                'trade_state': callback_data.get('result_code'),
                'payer_openid': callback_data.get('openid')
            }

            self.logger.info(f"订单 {order_id} 支付成功")
            return True, "支付成功", result_data

        except Exception as e:
            error_msg = f"处理回调失败: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg, {}

    def notify_success_response(self):
        """
        根据当前支付平台要求，在通知页面返回成功的结果
        """
        return "success"

    def query_order(self, order_id: str) -> Tuple[bool, str, Dict[str, Any]]:
        """查询订单状态"""
        try:
            if not self._validate_config():
                return False, "微信支付配置不完整", {}

            params = {
                "appid": self.app_id,
                "mch_id": self.mch_id,
                "out_trade_no": order_id,
                "nonce_str": self._generate_nonce_str()
            }
            params['sign'] = self._generate_sign(params)

            base_url = self.sandbox_gateway_url if self.is_sandbox else self.gateway_url
            url = f"{base_url}/pay/orderquery"
            headers = {'Content-Type': 'application/xml'}
            response = requests.post(url, data=self._dict_to_xml(params).encode('utf-8'), headers=headers)

            result = self._xml_to_dict(response.text)
            if result.get('return_code') != 'SUCCESS':
                return False, result.get('return_msg', '查询失败'), {}

            if not self._verify_sign(result):
                return False, "签名验证失败", {}

            # 处理查询结果
            status_map = {
                'SUCCESS': '支付成功',
                'REFUND': '转入退款',
                'NOTPAY': '未支付',
                'CLOSED': '已关闭',
                'REVOKED': '已撤销',
                'USERPAYING': '用户支付中',
                'PAYERROR': '支付失败'
            }

            order_data = {
                'order_id': order_id,
                'transaction_id': result.get('transaction_id'),
                'status': status_map.get(result.get('trade_state', 'UNKNOWN')),
                'amount': float(result.get('total_fee', 0)) / 100,
                'payment_time': result.get('time_end'),
                'trade_state_desc': result.get('trade_state_desc')
            }

            return True, "查询成功", order_data

        except Exception as e:
            error_msg = f"查询订单失败: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg, {}

    def close_order(self, order_id: str) -> Tuple[bool, str]:
        """关闭订单"""
        try:
            if not self._validate_config():
                return False, "微信支付配置不完整"

            params = {
                "appid": self.app_id,
                "mch_id": self.mch_id,
                "out_trade_no": order_id,
                "nonce_str": self._generate_nonce_str()
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
            error_msg = f"关闭订单失败: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg

    def refund_order(self, order_id: str, refund_amount: float, refund_reason: str = "") -> Tuple[
        bool, str, Dict[str, Any]]:
        """订单退款"""
        try:
            if not self._validate_config():
                return False, "微信支付配置不完整", {}

            if not all([self.cert_path, self.key_path]):
                return False, "退款需要配置证书路径", {}

            if refund_amount <= 0:
                return False, "退款金额必须大于0", {}

            params = {
                "appid": self.app_id,
                "mch_id": self.mch_id,
                "nonce_str": self._generate_nonce_str(),
                "out_trade_no": order_id,
                "out_refund_no": f"R{order_id}{int(time.time())}",
                "total_fee": int(self.query_order(order_id)[2].get('amount', 0) * 100),
                "refund_fee": int(refund_amount * 100),
                "refund_desc": refund_reason or "用户申请退款",
                "notify_url": getattr(self, 'refund_notify_url', '')
            }
            params['sign'] = self._generate_sign(params)

            base_url = self.sandbox_gateway_url if self.is_sandbox else self.gateway_url
            url = f"{base_url}/secapi/pay/refund"
            headers = {'Content-Type': 'application/xml'}

            # 需要证书的请求
            cert = (self.cert_path, self.key_path)
            response = requests.post(url, data=self._dict_to_xml(params).encode('utf-8'),
                                     headers=headers, cert=cert)

            result = self._xml_to_dict(response.text)
            if result.get('return_code') != 'SUCCESS':
                return False, result.get('return_msg', '退款失败'), {}

            if not self._verify_sign(result):
                return False, "签名验证失败", {}

            refund_data = {
                'order_id': order_id,
                'refund_id': result.get('refund_id'),
                'refund_amount': float(result.get('refund_fee', 0)) / 100,
                'refund_status': result.get('result_code'),
                'refund_msg': result.get('err_code_des')
            }

            return True, "退款申请成功", refund_data

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
                   placeholder="请输入微信公众号或小程序的AppID"
                   required/>
            <small class="form-text text-muted">在微信公众平台获取</small>
        </div>

        <div class="form-group p-2">
            <label for="mch_id">商户号 <span style="color: red;">*</span></label>
            <input type="text" 
                   id="mch_id"
                   name="mch_id" 
                   value="{{model.mch_id}}" 
                   class="form-control" 
                   placeholder="请输入微信支付商户号"
                   required/>
            <small class="form-text text-muted">在微信支付商户平台获取</small>
        </div>

        <div class="form-group p-2">
            <label for="api_key">API密钥 <span style="color: red;">*</span></label>
            <input type="text" 
                   id="api_key"
                   name="api_key" 
                   value="{{model.api_key}}" 
                   class="form-control" 
                   placeholder="请输入微信支付API密钥"
                   required/>
            <small class="form-text text-muted">在微信支付商户平台设置API密钥</small>
        </div>

        <div class="form-group p-2">
            <label for="cert_path">证书路径</label>
            <input type="text" 
                   id="cert_path"
                   name="cert_path" 
                   value="{{model.cert_path}}" 
                   class="form-control" 
                   placeholder="请输入微信支付证书路径"/>
            <small class="form-text text-muted">退款操作需要配置证书路径</small>
        </div>

        <div class="form-group p-2">
            <label for="key_path">密钥路径</label>
            <input type="text" 
                   id="key_path"
                   name="key_path" 
                   value="{{model.key_path}}" 
                   class="form-control" 
                   placeholder="请输入微信支付密钥路径"/>
            <small class="form-text text-muted">退款操作需要配置密钥路径</small>
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
                <li>请确保在微信支付商户平台正确配置了API密钥</li>
                <li>回调地址需要在微信支付商户平台进行配置</li>
                <li>退款功能需要配置支付证书</li>
                <li>沙箱环境仅用于开发测试，不会产生真实交易</li>
                <li>API密钥非常重要，请妥善保管，不要泄露</li>
            </ul>
        </div>
        <div class="alert alert-warning mt-3">
            <h6>微信支付插件配置说明：</h6>
            <div class="mb-0">
                <li>1. App ID: </br>
                   - 登录微信公众平台 (https://mp.weixin.qq.com)</br>
                   - 获取公众号或小程序的AppID</br>
                 </li>   
                <li>2. 商户号:</br>
                   - 登录微信支付商户平台 (https://pay.weixin.qq.com)</br>
                   - 获取商户号(MCHID)</br>
                </li>
                <li>3. API密钥:</br>
                   - 在微信支付商户平台设置API密钥</br>
                   - 用于签名验证，需要32位随机字符串</br>
                </li>
                <li>4. 支付证书:</br>
                   - 在商户平台下载API证书</br>
                   - 退款等安全级别较高的接口需要证书</br>
                </li>
                <li>5. 回调地址配置:</br>
                   - 需要在微信支付商户平台配置支付通知地址</br>
                   - 地址必须是公网可访问的HTTPS地址</br>
                </li>
                <li>注意事项：</br>
                    - 金额单位为分，必须为整数</br>
                    - 生产环境必须使用HTTPS</br>
                    - 定期检查和更新API密钥</br>
                    - 服务器时间必须准确</br>
                </li>
            </div>
        </div>
        '''