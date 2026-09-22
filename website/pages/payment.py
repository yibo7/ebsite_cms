
from flask import render_template, current_app, redirect, request, jsonify

import eb_utils
from decorators import check_user_login
from eb_utils import http_helper
from entity.user_token import UserToken
from entity.pay_link_result import PayLinkResult
from plugins.plugin_base import PaymentBase
from signals import pay_saved_successful
from website.pages import pages_blue


@pages_blue.route('/pay/return_url/<string:plugin_id>', methods=['GET', 'POST'])
def pay_return_url(plugin_id:str):
    """
    支付结束后，返回一个恭喜成功的页面，但这里不处理订单结束，订单结束只在pay_notify_url中处理。

    特殊处理：PayPal 支付在用户审批后会重定向到此地址并携带 token 参数，
    此时调用插件 call_back 进行订单捕获。
    """
    # PayPal 等支付方式：用户从第三方审批页返回，携带 token 参数
    if request.args.get('token'):
        payment: PaymentBase = current_app.pm.get_by_id(plugin_id)
        if payment:
            is_ok, err_info, pay_info = payment.call_back(request)
            if is_ok:
                pay_saved_successful.send(pay_info)

    return render_template("pay_return_url.html")


@pages_blue.route('/pay/notify_url/<string:plugin_id>', methods=['GET', 'POST'])
def pay_notify_url(plugin_id:str):
    """
    处理支付订单的结束，这里将调用插件的call_back函数，获取相关数据，并发出通知，可在相应的模块中监听事件处理相应的订单结果
    """
    payment:PaymentBase = current_app.pm.get_by_id(plugin_id)
    if not payment:
        err = f"处理支付订单发生错误:找不到支付插件{plugin_id}!"
        print(err)
        raise Exception(err)

    is_ok, err_info, pay_info = payment.call_back(request)
    if not is_ok:
        err = f"处理支付订单发生错误:{err_info}!"
        print(err)
        raise Exception(err)

    # 通知监听程序（如 shop/quote 模块），处理订单状态
    pay_saved_successful.send(pay_info)
    # 返回插件要求的确认响应
    return payment.notify_response(pay_info)


@pages_blue.route('/pay/go_pay', methods=['POST'])
@check_user_login
def pay_go_pay(user_token:UserToken):
    """
    处理一个订单的支付，提交前端可参考shop中的sel_payment
    """
    payment_plugin = http_helper.get_prams("payment")
    order_name = http_helper.get_prams("order_name")
    order_id = http_helper.get_prams("order_id")
    total_price = http_helper.get_prams_float("total_price")
    pay_key = http_helper.get_prams("pay_key")

    if not any([payment_plugin, order_name, order_id, total_price]):
        raise Exception("传入的参数有问题!")

    v_pay_key = eb_utils.md5(f"{order_id}-{total_price}-{current_app.config['RandomKey']}")

    if v_pay_key != pay_key:
        raise Exception("支付数据验证出错!")

    payment:PaymentBase = current_app.pm.get_by_id(payment_plugin)

    if not payment:
        raise Exception(f"找不到支付插件:{payment_plugin}!")

    is_ok, err_msg, pay_result = payment.create_pay_link(
        order_id, total_price, subject=order_name,
    )
    if not is_ok:
        raise Exception(f"构建支付连接出错:{err_msg}!")

    # 根据不同的支付凭证类型，前端做不同处理
    if pay_result.pay_url:
        return redirect(pay_result.pay_url)
    if pay_result.qr_code_url:
        return redirect(pay_result.qr_code_url)
    if pay_result.trade_params:
        return jsonify(pay_result.trade_params)

    raise Exception("支付插件未返回有效的支付凭证")