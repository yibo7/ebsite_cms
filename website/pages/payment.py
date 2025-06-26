
from flask import render_template, current_app, redirect, request

import eb_utils
from decorators import check_user_login
from eb_utils import http_helper
from entity.user_token import UserToken
from plugins.plugin_base import PaymentBase
from signals import pay_saved_successful
from website.pages import pages_blue

@pages_blue.route('/pay/return_url/<string:plugin_id>', methods=['GET', 'POST'])
def pay_return_url(plugin_id:str):
    """
    支付结束后，返回一个恭喜成功的页面，但这里不处理订单结束，订单结束只在pay_notify_url中处理
    """
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

    is_ok,err_info,payment_data = payment.call_back(request)
    if not is_ok:
        err = f"处理支付订单发生错误:{err_info}!"
        print(err)
        raise Exception(err)

    # 通知监听程序，在你的插件或模块中监听此事件并处理订单的状态(或参考shop中的init)
    pay_saved_successful.send(payment_data)
    # 返回插件要求的内容
    return payment.notify_success_response()


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

    v_pay_key = eb_utils.md5(f'{order_id}-{total_price}-{current_app.config['RandomKey']}')

    if v_pay_key != pay_key:
        raise Exception("支付数据验证出错!")

    payment:PaymentBase = current_app.pm.get_by_id(payment_plugin)

    if not payment:
        raise Exception(f"找不到支付插件:{payment_plugin}!")
    is_ok, pay_link = payment.create_pay_link(order_id,total_price)
    if not is_ok:
        raise Exception(f"构建支付连接出错:{pay_link}!")
    return redirect(pay_link)