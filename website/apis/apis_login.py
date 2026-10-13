
"""
网站第三方登录（OAuth）接口。

本模块属于网站自身的 API 体系（website/apis），不依赖 eb_modules/app_apis 模块：
无论后台是否启用「APP-APIS」模块，网站前台的三方登录都应可用。

涉及两个接口：
  - openlogin       : 获取第三方授权页 URL（前端拿到后跳转）
  - open_login_back : 第三方平台授权后的回调，完成后设 cookie 并重定向回首页

对应插件：plugins/open_login_*.py（基类 OpenLoginBase）
"""

import time
from urllib.parse import quote

from flask import jsonify, current_app, redirect, request

from bll.user import User
from eb_cache import login_utils
from eb_utils import http_helper, flask_utils
from entity import api_msg
from website.apis import api_blue


@api_blue.route('openlogin', methods=['GET', 'POST'])
def openlogin():
    """
    获取三方登录连接
    """
    plugin_id = http_helper.get_prams('pid')
    pm = current_app.pm
    pl = pm.get_by_id(plugin_id)
    is_succesful, msg = pl.login()
    if is_succesful:
        return jsonify(api_msg.api_succesful(msg))
    else:
        return jsonify(api_msg.api_err(msg))


@api_blue.route('open_login_back', methods=['GET'])
def open_login_back():
    """
    三方登录回调处理（OAuth 第二步）。

    第三方平台授权后重定向到此地址，完成：
    1. 调用插件 call_back 获取标准化的用户信息
    2. 按 email → openid 分层查找用户，自动关联或注册
    3. 生成会话 token 并设置 cookie
    4. 重定向回首页
    """
    plugin_id = http_helper.get_prams('plugin')
    if not plugin_id:
        return redirect('/?login_error=' + quote('缺少 plugin 参数'))

    pm = current_app.pm
    plugin = pm.get_by_id(plugin_id)
    if not plugin:
        return redirect('/?login_error=' + quote('未找到登录插件'))

    # 1. 调用插件的回调处理方法
    is_ok, msg, user_info = plugin.call_back(request)
    if not is_ok:
        return redirect('/?login_error=' + quote(msg or '第三方登录失败'))

    bll = User()
    need_update = False
    user = None

    # ---------------------------------------------------------------
    # 2. 按 email 优先查找（Google/Apple 等有邮箱的平台）
    #    这是主流做法：用户能通过第三方登录，证明他已拥有该邮箱，
    #    系统应自动关联到此邮箱的已有账号，而非创建新账号。
    # ---------------------------------------------------------------
    if user_info.email:
        user = bll.find_by_email(user_info.email)
        if user:
            # 关联第三方账号到已有用户
            if not user.openid:
                user.openid = user_info.user_open_id
                need_update = True
            if user_info.avatar_url and user.avatar != user_info.avatar_url:
                user.avatar = user_info.avatar_url
                need_update = True
            if user_info.user_ni_name and user.ni_name != user_info.user_ni_name:
                user.ni_name = user_info.user_ni_name
                need_update = True

    # 3. 按 openid 查找（微信等无邮箱的平台 / email 未匹配到）
    if not user:
        user = bll.get_by_openid(user_info.user_open_id)
        if user:
            # 已有用户，更新资料
            if user_info.avatar_url and user.avatar != user_info.avatar_url:
                user.avatar = user_info.avatar_url
                need_update = True
            if user_info.user_ni_name and user.ni_name != user_info.user_ni_name:
                user.ni_name = user_info.user_ni_name
                need_update = True
            if user_info.email and not user.email_address:
                user.email_address = user_info.email
                need_update = True

    # 4. 完全没找到 → 注册新用户
    if not user:
        is_reg_ok, result = bll.reg_open_user(
            openid=user_info.user_open_id,
            mobile='',
            nickname=user_info.user_ni_name,
            avatar=user_info.avatar_url,
            email=user_info.email,
        )
        if not is_reg_ok:
            return redirect('/?login_error=' + quote(str(result)))
        user = result
    elif need_update:
        user.last_login_ip = flask_utils.get_client_ip()
        user.last_login_date = time.time()
        user.login_count += 1
        bll.update(user)

    # 5. 生成 token 并设置 cookie
    login_utils.update_app_token(user)
    resp = redirect('/')
    login_utils.set_cookie_token(user, resp)
    return resp
