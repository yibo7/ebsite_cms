from flask import Blueprint, g, render_template, request, redirect, make_response, current_app

from eb_cache import login_utils
from eb_utils.configs import WebPaths

user_blue = Blueprint('user', __name__, url_prefix=WebPaths.USER_PATH)


@user_blue.context_processor
def inject_site_name():
    """
    使用context_processor上下文件处理器，注入pages_blue下所有模板的公共变量
    """
    return {'SiteName': current_app.config['site_name']}


# region 后台请求前的处理

@user_blue.before_request
def before_req():
    """
    在后台页面请求前进行一些权限处理
    :return:
    """
    g.u = None
    user_token = login_utils.get_token()
    if user_token:
        g.u = user_token
        g.uid = user_token.id
    else:
        return redirect("/login")


# endregion


@user_blue.route('index', methods=['GET'])
def user_index():
    # order_bll = UserOrders()
    # order_model = order_bll.new_instance()
    # order_model.user_id = g.uid
    #
    # order_model.user_id = g.u.id
    # order_model.user_niame = g.u.ni_name
    # order_model.username = g.u.name
    # order_model.user_ip = flask_utils.get_client_ip()
    # order_model.type_id = 1
    # order_model.add_credits = 1000
    # order_model.price = 198.0
    # order_model.real_price = 150.6689
    # order_model.order_type_id = "2356fsdwf3"
    # order_model.pay_type = 2
    # order_model.info = f"{order_model.username}通过支付宝购买了包月VIP"
    #
    # is_ok = order_bll.add_order(order_model)
    # if is_ok:
    #     print('下单成功')
    # else:
    #     print('下单失败')

    return render_template(WebPaths.get_user_path("index.html"), user=g.u)


@user_blue.route('log_out', methods=['GET'])
def user_log_out():
    resp = make_response(redirect(WebPaths.LOGIN_URL))
    login_utils.logout_user(resp)
    return resp
