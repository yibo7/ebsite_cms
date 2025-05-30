import time
from decimal import Decimal
from xml.sax import saxutils

import requests
import random
import string
import hashlib
import xml.etree.ElementTree as Et
from xml.dom import minidom

import xmltodict

from flask import request, Request


class WeiXinHelper:
    def __init__(self, wx_appid, wx_secret, wx_mch_id, wx_api_key):
        """
        微信工具类
        @param wx_appid:  你的小程序ID
        @param wx_secret: 你的小程序密钥
        @param wx_mch_id: 你的商户号
        @param wx_api_key: 你的API密钥
        """
        self.appid = wx_appid
        self.secret = wx_secret
        self.mch_id = wx_mch_id
        self.api_key = wx_api_key
        self.wx_pay_url = 'https://api.mch.weixin.qq.com/pay/unifiedorder'

    def get_openid(self, wx_code)->str:
        """
        通过code获取openid
        @param wx_code: 在uni-app上通过uni.login获取
        @return:
        """
        url = f"https://api.weixin.qq.com/sns/jscode2session"
        params = {
            'appid': self.appid,
            'secret': self.secret,
            'js_code': wx_code,
            'grant_type': 'authorization_code'
        }
        response = requests.get(url, params=params)
        data = response.json()
        # print(data)
        return data.get('openid')

    def create_payment_order(self,notify_url:str, openid:str, total_price:Decimal, out_trade_no:str, body:str, spbill_create_ip:str, notify_url_host=None,trade_type = "JSAPI") -> tuple[bool,str or dict]:
        """
        创建微信支付订单
        @param notify_url_host: 指定支付回调域名
        @param notify_url: 通知地址，相对的，不用填写域名
        @param trade_type: 支付类型，JSAPI：公众号支付(也适用小程序)  NATIVE：扫码支付  APP：App支付  MWEB：H5支付  MICROPAY：付款码支付
        @param openid: 如果使用JSAPI支付方式必须传入,trade_type=JSAPI，此参数必传
        @param total_price: 需要支付的金额，单位元
        @param out_trade_no: 自定义-订单ID
        @param body:    订单描述
        @param spbill_create_ip: 订单创建者IP
        @return: 客户端支付需要的参数
        """


        total_fee = int(total_price * 100) # 将元转换成分
        # domain = request.url_root.rstrip('/')
        # notify_url = f"{domain}{notify_url}"
        if notify_url_host:
            notify_url = f"{notify_url_host}{notify_url}"
        else:
            domain = request.url_root.rstrip('/')
            notify_url = f"{domain}{notify_url}"

        post_params = {
            'appid': self.appid,
            'mch_id': self.mch_id,
            'nonce_str': self._generate_nonce_str(),
            'body': body.encode('utf-8'),
            'out_trade_no': out_trade_no,
            'total_fee': str(total_fee),  # 确保金额为字符串格式
            'spbill_create_ip': spbill_create_ip,
            'notify_url': notify_url,
            'trade_type': trade_type,
            'fee_type': 'CNY',
            'openid': openid
        }
        post_params['sign'] = self._create_sign(post_params)
        xml_data = self._build_xml(post_params)

        # xml_data = f"""
        #     {xml_data}
        # """
        # print(xml_data)

        response = requests.post(self.wx_pay_url, data=xml_data, headers={'Content-Type': 'application/xml'})
        json_xml = self._parse_xml_to_json(response.content.decode('utf-8'))
        # print(json_xml)

        rz_data = json_xml["xml"]
        err_msg = '未知错误'
        if rz_data:
            if 'result_code' in rz_data and rz_data['result_code'] == 'SUCCESS':
                timestamp = int(time.time())
                pay_prams = {
                    "appId": self.appid,
                    "timeStamp": str(timestamp),
                    "nonceStr": rz_data['nonce_str'],
                    "package": f"prepay_id={rz_data['prepay_id']}",
                    "signType": "MD5"
                }
                pay_prams['paySign'] = self._create_sign(pay_prams)

                print(f'微信支付订单创建成功，支付完成通知地址:{notify_url}')

                return True,pay_prams
            elif 'return_code' in rz_data and rz_data['return_code'] == 'FAIL': #
                err_msg = f"创建订单失败:{rz_data['return_msg']}"
            else:
                err_msg = f"创建订单失败:{rz_data['err_code_des']}"
        else:
            err_msg = '请求不到数据'
        return False,err_msg

    def query_by_id(self,  out_trade_no=None):
        """查询支付订单状态"""
        if not out_trade_no:
            raise ValueError("需要提供transaction_id或out_trade_no中的至少一个")

        nonce_str = self._generate_nonce_str()
        sign = self._create_sign({
            'appid': self.appid,
            'mch_id': self.mch_id,
            'nonce_str': nonce_str,
            'out_trade_no': out_trade_no
        })

        # 构建XML请求数据
        xml_data = self._build_xml({
            'appid': self.appid,
            'mch_id': self.mch_id,
            'nonce_str': nonce_str,
            'sign': sign,
            'out_trade_no': out_trade_no
        })

        # 发送请求
        response = requests.post('https://api.mch.weixin.qq.com/pay/orderquery', data=xml_data,
                                 headers={'Content-Type': 'application/xml'})
        json_data = self._parse_xml_to_json(response.content.decode('utf-8'))
        return json_data['xml']

    def _parse_xml_to_json(self, xml_data):
        try:
            # 使用xmltodict解析XML
            dict_data = xmltodict.parse(xml_data)
            # 直接返回字典（JSON对象）
            return dict_data
        except Exception as e:
            print("解析XML时出错：", str(e))
            return None

    def _generate_nonce_str(self, length=32):
        """生成随机字符串"""
        letters = string.ascii_letters + string.digits
        return ''.join(random.choice(letters) for i in range(length))

    def _create_sign(self, data):
        """生成签名"""
        string_value = '&'.join(f"{k}={v}" for k, v in sorted(data.items()) if v)
        string_value += '&key=' + self.api_key
        return hashlib.md5(string_value.encode('utf-8')).hexdigest().upper()

    def _build_xml(self, data):
        """构建并格式化XML数据为字符串"""
        root = Et.Element('xml')
        for key, value in data.items():
            child = Et.SubElement(root, key)
            child.text = str(value)
        rough_string = Et.tostring(root, 'utf-8')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="    ")

    def check_pay_notify(self,req: Request) -> tuple[bool,str]:
        """
        支付通知处理
        @param req:
        @return: 是否成功，错误：信息|成功：订单ID
        """
        # 获取微信发送的 XML 请求数据
        xml_data = req.data
        if not xml_data:
            return False,'支付回通知XML为空'
        # print("支付回通知XML:", xml_data)
        # xml 返回的内容如下
        # b'<xml><appid><![CDATA[wx7261621a054cff30]]></appid>\n<bank_type><![CDATA[OTHERS]]></bank_type>\n<cash_fee><![CDATA[10]]></cash_fee>\n<fee_type><![CDATA[CNY]]></fee_type>\n<is_subscribe><![CDATA[N]]></is_subscribe>\n<mch_id><![CDATA[1684879749]]></mch_id>\n<nonce_str><![CDATA[vdKLrwPnOT9W1HayL9IkMOM2vFQa8MiW]]></nonce_str>\n<openid><![CDATA[oVK0l7RXcT9-d6Gi4Pg3Cx-LQzS4]]></openid>\n<out_trade_no><![CDATA[66e520856c4f173b5afb398e]]></out_trade_no>\n<result_code><![CDATA[SUCCESS]]></result_code>\n<return_code><![CDATA[SUCCESS]]></return_code>\n<sign><![CDATA[DF2290CA18AB46D960C46455D9F8D98E]]></sign>\n<time_end><![CDATA[20240914133521]]></time_end>\n<total_fee>10</total_fee>\n<trade_type><![CDATA[JSAPI]]></trade_type>\n<transaction_id><![CDATA[4200002372202409145497053898]]></transaction_id>\n</xml>'
        # 解析 XML 数据
        root = Et.fromstring(xml_data)
        return_code = root.find('return_code').text
        err_msg = ''
        if return_code == 'SUCCESS':  #
            # 支付成功
            out_trade_no = root.find('out_trade_no').text
            if out_trade_no:
                order_info = self.query_by_id(out_trade_no)
                if order_info and order_info.get('trade_state')=='SUCCESS':
                    return True,out_trade_no
                else:
                    err_msg = "无法获取订单或状态不成功"
        else:
            err_msg = root.find('return_msg').text
        return False,err_msg


def wei_xin_bll():
    wxzf_appid = 'wx72616fffffff30'
    wx_secret = 'test' # 基于web端的微信登录也使用到此key
    wxzf_mch_id = '1111111'
    api_key = 'testtesttest'

    return WeiXinHelper(wxzf_appid, wx_secret, wxzf_mch_id, api_key)