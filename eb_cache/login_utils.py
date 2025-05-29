import datetime

from flask import request, current_app

import eb_cache
from bll.user_group import UserGroup
from eb_utils.configs import SiteConstant
from eb_utils.flask_utils import get_client_ip
from entity.admin_user_model import AdminUserModel
from entity.user_model import UserModel
from entity.user_token import UserToken


def get_safe_coe_key():
    sid = request.session_id
    if sid:
        return f'safe_code_{sid}'
    return None


def get_token() -> UserToken or None:
    token_key = request.cookies.get(SiteConstant.COOKIE_TOKEN_KEY)
    if token_key:
        user_token = eb_cache.get_obj(token_key)  # type:UserToken
        return user_token
    return None


def get_token_admin() -> UserToken or None:
    token_key = request.cookies.get(SiteConstant.COOKIE_AD_TOKEN_KEY)
    if token_key:
        admin_token = eb_cache.get_obj(token_key)  # type:UserToken
        return admin_token
    return None


def logout_user(resp):
    token_key = request.cookies.get(SiteConstant.COOKIE_TOKEN_KEY)
    if token_key:
        eb_cache.delete(token_key)
        resp.delete_cookie(token_key)
    return token_key


def logout_admin(resp):
    token_key = request.cookies.get(SiteConstant.COOKIE_AD_TOKEN_KEY)
    if token_key:
        eb_cache.delete(token_key)
        resp.delete_cookie(token_key)
    return token_key


def get_count_key(key: str):
    return f"{get_client_ip()}_{key}"


def add_count_second(key, timeout=60):
    """
    生成某个键下的自增值，并过期会自动清理
    :param key:
    :param timeout:
    :return:
    """
    new_key = get_count_key(key)
    new_value = eb_cache.next_id(new_key, timeout)

    return new_value


def add_count_minute(key, ex_minutes=60):
    expiration_seconds = ex_minutes * 60
    return add_count_second(key, expiration_seconds)


def add_count_hour(key, ex_hours=24):
    expiration_seconds = ex_hours * 60 * 60
    return add_count_second(key, expiration_seconds)


def get_count(key):
    new_key = get_count_key(key)
    i_count = eb_cache.get(new_key)
    if i_count:
        return int(i_count)
    return 0

# def set_app_token(token: UserToken) -> str:
#     if not token.group_name:
#         group_model = UserGroup().find_one_by_id(token.group_id)
#         token.group_name = group_model.name
#     app_token_expired = current_app.config['app_token_expired'] or 24
#     token_key = eb_cache.set_ex_hours(token, int(app_token_expired))
#     return token_key

def update_app_token(model: UserModel) -> str:
    group_model = UserGroup().find_one_by_id(model.group_id)
    token = UserToken(model._id, model.username, model.ni_name, model.group_id, group_model.name, model.avatar,model.openid)
    # if not token.group_name:
    #     group_model = UserGroup().find_one_by_id(token.group_id)
    #     token.group_name = group_model.name
    app_token_expired = current_app.config['app_token_expired'] or 24
    token_key = eb_cache.set_ex_hours(token, int(app_token_expired))
    return token_key


def set_cookie_token(model: UserModel, resp):

    group_model = UserGroup().find_one_by_id(model.group_id)
    token = UserToken(model._id, model.username, model.ni_name, model.group_id, group_model.name, model.avatar,
                      model.openid)
    app_token_expired = current_app.config['app_token_expired'] or 24
    user_key = eb_cache.set_ex_hours(token, int(app_token_expired))
    expires = datetime.datetime.now() + datetime.timedelta(hours=24)
    resp.set_cookie(SiteConstant.COOKIE_TOKEN_KEY, user_key, expires=expires)
    # return session_id

def set_cookie_token_admin(user: AdminUserModel, resp):
    """
    设置管理员登录的Token，其实也就是COOKIE_AD_TOKEN_KEY不一样
    """
    token = UserToken(user._id, user.user_name, user.real_name, user.role_id, user.role_name, "")
    admin_key = eb_cache.set_ex_hours(token, 24)
    expires = datetime.datetime.now() + datetime.timedelta(hours=24)
    resp.set_cookie(SiteConstant.COOKIE_AD_TOKEN_KEY, admin_key, expires=expires)

# def set_token_admin(token: UserToken, resp):
#     """
#     设置管理员登录的Token，其实也就是COOKIE_AD_TOKEN_KEY不一样
#     """
#     admin_key = eb_cache.set_ex_hours(token, 24)
#     expires = datetime.datetime.now() + datetime.timedelta(hours=24)
#     resp.set_cookie(SiteConstant.COOKIE_AD_TOKEN_KEY, admin_key, expires=expires)
