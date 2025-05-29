from flask import  jsonify

from bll.user import User
from decorators import check_token
from eb_cache import login_utils
from eb_modules.app_apis import bp_app_apis
from eb_utils import http_helper
from eb_utils.wei_xin_helper import wei_xin_bll
from entity import api_msg
from entity.user_token import UserToken

@bp_app_apis.route('wx_login', methods=['POST'])
def wx_login():
    """
    微信受权登录
    """
    wx_code = http_helper.get_prams('wxcode')  # 前端通过 wx.login()获取到的code

    if not wx_code:
        return jsonify(api_msg.api_err("wxcode不能为空"))

    # 前端调用wx.getUserInfo 可获取用户昵称，用户头像
    nickname = http_helper.get_prams('nickname')  # 获取用户昵称
    avatar = http_helper.get_prams('avatar')  # 用户头像

    mobile = http_helper.get_prams('mobile')  # 前端通过getPhoneNumber可获取用户的手机号

    # 1. 通过 code 换取openid

    wx_bll = wei_xin_bll()
    openid = wx_bll.get_openid(wx_code)

    if not openid:
        return jsonify(api_msg.api_err("openid无法获取，请确认wx_code是否正确传递"))

    # 2. 判断用户表中是否有绑定过此openid的用户
    user_bll = User()
    model = user_bll.get_by_openid(openid)
    if not model:  # 不存在用户，注册一个账号
        is_succesfull, msg_data = user_bll.reg_open_user(openid, mobile, nickname, avatar)
        if not is_succesfull:
            return jsonify(api_msg.api_err(msg_data))
        else:
            model = msg_data

    # 3. 生成TOKEN 返回给前端
    # utk = UserToken(model._id, model.username, model.ni_name, model.group_id, "", model.avatar, openid)
    # key = login_utils.set_app_token(utk)
    key = login_utils.update_app_token(model)
    return jsonify(api_msg.api_succesful(key))

@bp_app_apis.route('bind_wx', methods=['POST'])
@check_token()
def bind_wx(token: UserToken):
    """
    绑定微信
    """
    wx_code = http_helper.get_prams('wxcode')  # 前端通过 wx.login()获取到的code

    if not wx_code:
        return jsonify(api_msg.api_err("wxcode不能为空"))

    # 前端调用wx.getUserInfo 可获取用户昵称，用户头像
    nickname = http_helper.get_prams('nickname')  # 获取用户昵称
    avatar = http_helper.get_prams('avatar')  # 用户头像

    mobile = http_helper.get_prams('mobile')  # 前端通过getPhoneNumber可获取用户的手机号

    # 1. 通过 code 换取openid

    wx_bll = wei_xin_bll()
    openid = wx_bll.get_openid(wx_code)
    if not openid:
        return jsonify(api_msg.api_err("openid无法获取，请确认wx_code是否正确传递"))

    # 2. 判断用户表中是否有绑定过此openid的用户
    user_bll = User()
    # print(token.id)
    model = user_bll.find_one_by_id(token.id)
    if nickname:
        model.ni_name = nickname
    if mobile:
        model.mobile_number = mobile
    if avatar:
        model.avatar = avatar
    model.openid = openid
    user_bll.update(model)
    # 3. 生成TOKEN 返回给前端
    # utk = UserToken(model._id, model.username, model.ni_name, model.group_id, "", model.avatar, openid)
    # key = login_utils.set_app_token(utk)
    key = login_utils.update_app_token(model)
    return jsonify(api_msg.api_succesful(key))


@bp_app_apis.route('query_order', methods=['GET'])
def query_order():
    orderid = http_helper.get_prams('orderid') # 2233665598
    wx_bll = wei_xin_bll()
    order_info = wx_bll.query_by_id(orderid)

    # print(order_info.get('trade_state'))

    return jsonify(api_msg.api_succesful(order_info))