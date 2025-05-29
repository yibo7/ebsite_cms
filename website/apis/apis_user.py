
from flask import jsonify, g

from bll.apply_credites import ApplyCredites
from decorators import rate_limit_ip
from eb_utils import http_helper, flask_utils
from entity import api_msg
from entity.user_token import UserToken
from website.apis import api_blue_user


@api_blue_user.route('apply_credits', methods=['POST'])
@rate_limit_ip(3,60) # 一小时只允许调用3次
def add_credits():
    """
    申请积分-需要后台审核
    :return:
    """
    credits = http_helper.get_prams_int("credits")
    remark = http_helper.get_prams_int("remark")
    if credits and remark:
        bll = ApplyCredites()
        model = bll.new_instance()
        user_token: UserToken = g.u

        model.username = user_token.name
        model.ni_name = user_token.ni_name
        model.credits = credits
        model.remark = remark
        model.ip = flask_utils.get_client_ip()

        bll.add(model)
        return jsonify(api_msg.api_succesful("succesfull"))

    return jsonify(api_msg.api_err("请输入必要的参数!"))

@api_blue_user.route('login_info', methods=['POST','GET'])
def login_info():
    """
    获取登录后的用户信息
    :return:
    """
    user_token: UserToken = g.u
    if user_token:
        user_token.id = str(user_token.id)
        return jsonify(api_msg.api_succesful(user_token))
    return jsonify(api_msg.api_err("logout"))