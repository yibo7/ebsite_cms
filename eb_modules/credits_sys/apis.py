import time

from bson import ObjectId
from flask import jsonify, request

from bll_orders.user_orders import CreditsOrder
from decorators import check_token, rate_limit_ip
from eb_modules.credits_sys import bp_credits_apis
from eb_modules.credits_sys.datas.credits_plan import CreditsPlanBll

from eb_utils import http_helper, flask_utils
from eb_utils.wei_xin_helper import wei_xin_bll
from entity import api_msg
from entity.user_token import UserToken
from entity_orders.credits_order_model import CreditsOrderModel


@bp_credits_apis.route('pay_notify/<payment_id>', methods=['GET','POST'])
def pay_notify(payment_id:int):
    """
    支付回调
    @param payment_id: 支付类型 1表示微信支付，2 表示支付宝
    @return: 微信不会处理返回的内容
    """
    # order_id = http_helper.get_prams('order_id')
    # bll = CreditsOrder()
    # bll.complete_order(order_id)
    # return jsonify(api_msg.api_err('test'))

    print(f"订单通知，来自：{payment_id}")
    wx_bll = wei_xin_bll()
    is_succesfull, err_msg = wx_bll.check_pay_notify(request)
    if is_succesfull:
        bll = CreditsOrder()
        # 完成订单
        bll.complete_order(err_msg) # err_msg 这里即是订单的ID

        return jsonify(api_msg.api_succesful("支付成功"))
    else:
        print(f'订单通知支付失败:{err_msg}')
        return jsonify(api_msg.api_err(err_msg))


@bp_credits_apis.route('buy_credits', methods=['POST'])
@check_token()
def buy_credits(token: UserToken):
    """
    购买积分
    """

    if not bp_credits_apis.config:
        return jsonify(api_msg.api_err('备份系统插件的配置没初始化!'))
    credit_price = bp_credits_apis.config["credits_price"] # 一块钱能购买多少个积分
    if credit_price:
        credit_price = int(credit_price)
        if credit_price <1:
            return jsonify(api_msg.api_err('积分定价不能小于1!'))
    else:
        return jsonify(api_msg.api_err('积分还没有定价，请到后台积分管理模块的设置定价!'))


    payment = http_helper.get_prams_int('payment')  # 支付方式，比如 1 微信，2 支付宝
    price = http_helper.get_prams_decimal('price')  #  价格
    order_name = http_helper.get_prams('order_name')  # 订单标题
    if order_name and payment > 0 and price > 0:

        credit_count = int(credit_price * price)  # 本交一共购买多少个积分

        if credit_count <1:
            return jsonify(api_msg.api_err('金额太少，至少要购买一个积分!'))

        model = CreditsOrderModel()
        model._id = ObjectId()
        model.user_id = token.id
        model.username = token.name
        model.user_niame = token.ni_name
        model.user_ip = flask_utils.get_client_ip()
        model.add_credits = credit_count
        model.type_id = 2  #  直接下单购买积分
        model.order_name = order_name
        model.info = f'购买积分【{order_name}】'
        model.pay_type = payment
        model.real_price = price
        model.price = price
        model.is_complete = False
        model.order_type_id = 0  # 后面可以定义购买套餐
        model.sign = model.sign_data()

        if payment==1: # 微信支付

            openid = token.open_id # http_helper.get_prams('openid')  # 如果是微信支付，需要传入这个
            if not openid:
                return jsonify(api_msg.api_err('微信支付需要传入openid'))

            wx_bll = wei_xin_bll()
            notify_url_host = None
            if bp_credits_apis.config and 'pay_back_url' in bp_credits_apis.config:
                notify_url_host = bp_credits_apis.config["pay_back_url"]  # 指定回调域名

            notify_url = "/credits/api/pay_notify/1"

            trade_type = http_helper.get_prams(
                'trade_type')  # 付类型，JSAPI：公众号支付(也适用小程序)  NATIVE：扫码支付  APP：App支付  MWEB：H5支付  MICROPAY：付款码支付
            if not trade_type:
                trade_type = "JSAPI"

            is_succesfull, data_msg = wx_bll.create_payment_order(notify_url,openid, model.real_price, model._id, model.order_name, model.user_ip,notify_url_host,trade_type)
            if is_succesfull:
                model.payment_prams = data_msg
            else: # 创建微信订单发生错误
                return jsonify(api_msg.api_err(data_msg))
        else:
            return jsonify(api_msg.api_err('目前只支持微信支付'))

        bll = CreditsOrder()
        model._id = bll.add(model)

        return jsonify(api_msg.api_succesful(model.to_dict(['add_time','complete_date','user_ip','type_id','user_niame','sign','username'])))
    return jsonify(api_msg.api_err('参数不完整'))



@bp_credits_apis.route('ad_credits', methods=['POST'])
# @rate_limit_ip(2,1440)  # 24小时只允许请求两次
# @check_sign(True)
@check_token()
def ad_credits(token: UserToken):
    """
    通过观看广告增加积分
    """
    return jsonify(api_msg.api_err('未完成'))

@bp_credits_apis.route('buy_credits_plan', methods=['POST'])
@check_token()
def buy_credits_plan(token: UserToken):
    """
    购买积分套餐
    """
    payment = http_helper.get_prams_int('payment')  # 支付方式，比如 1 微信，2 支付宝
    planid = http_helper.get_prams('planid')  # 积分套餐的订单ID


    if payment > 0 and planid:
        bll = CreditsPlanBll()
        model_plan = bll.find_one_by_id(planid)

        if not model_plan:
            return jsonify(api_msg.api_err(f'找不到套餐：{planid}!'))

        price = model_plan.real_price  # 实际价格
        order_name = model_plan.title  # 订单标题
        credit_count = model_plan.credits  # 本交一共购买多少个积分

        if credit_count < 1:
            return jsonify(api_msg.api_err('套餐积分至少要大于1!'))

        if price <= 0:
            return jsonify(api_msg.api_err('套餐价格至少要大于0!'))

        model = CreditsOrderModel()
        model._id = ObjectId()
        model.plan_id = str(model_plan._id)
        model.user_id = token.id
        model.username = token.name
        model.user_niame = token.ni_name
        model.user_ip = flask_utils.get_client_ip()
        model.add_credits = credit_count
        model.type_id = 2  # 直接下单购买积分
        model.order_name = order_name
        model.info = f'购买积分套餐【{order_name}】，套餐ID：{planid}'
        model.pay_type = payment
        model.real_price = price
        model.price = price
        model.is_complete = False
        model.order_type_id = 0  # 后面可以定义购买套餐
        model.sign = model.sign_data()

        if payment == 1:  # 微信支付

            openid = token.open_id  # http_helper.get_prams('openid')  # 如果是微信支付，需要传入这个
            if not openid:
                return jsonify(api_msg.api_err('微信支付需要传入openid'))

            wx_bll = wei_xin_bll()
            notify_url_host = None
            if bp_credits_apis.config and 'pay_back_url' in bp_credits_apis.config:
                notify_url_host = bp_credits_apis.config["pay_back_url"]  # 指定回调域名

            # print(f'notify_url_host:{notify_url_host}')

            notify_url = "/credits/api/pay_notify/1"


            trade_type = http_helper.get_prams('trade_type')  # 付类型，JSAPI：公众号支付(也适用小程序)  NATIVE：扫码支付  APP：App支付  MWEB：H5支付  MICROPAY：付款码支付
            if not trade_type:
                trade_type = "JSAPI"

            is_succesfull, data_msg = wx_bll.create_payment_order(notify_url, openid, model.real_price, model._id,
                                                                  model.order_name, model.user_ip,notify_url_host,trade_type)
            if is_succesfull:
                model.payment_prams = data_msg
            else:  # 创建微信订单发生错误
                return jsonify(api_msg.api_err(data_msg))
        else:
            return jsonify(api_msg.api_err('目前只支持微信支付'))

        bll = CreditsOrder()
        model._id = bll.add(model)

        return jsonify(api_msg.api_succesful(
            model.to_dict(['add_time', 'complete_date', 'user_ip', 'type_id', 'user_niame', 'sign', 'username'])))
    return jsonify(api_msg.api_err('参数不完整'))

@bp_credits_apis.route('buy_vip', methods=['POST'])
@check_token()
def buy_vip(token: UserToken):
    """
    购买VIP会员
    """
    return jsonify(api_msg.api_err('示完成'))



@bp_credits_apis.route('credits_plan', methods=['GET','POST'])
def credits_plan():
    """
    获取积分套餐
    @return: 积分套餐
    """
    bll = CreditsPlanBll()
    # 完成订单
    models = bll.find_all()
    models_dicts = [model.to_short_dic() for model in models]

    return jsonify(api_msg.api_succesful(models_dicts))