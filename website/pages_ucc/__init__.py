from flask import Blueprint, g, render_template, request, redirect, make_response, current_app

from bll.favorite import Favorite
from eb_cache import login_utils
from eb_utils import http_helper
from eb_utils.configs import WebPaths
from entity.user_token import UserToken

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
    return render_template(WebPaths.get_user_path("index.html"), user=g.u)


@user_blue.route('favorite', methods=['GET'])
def favorite():
    user_token: UserToken = g.u
    bll = Favorite()
    rewrite_rule = f'/user/favorite?p={{0}}'
    p = http_helper.get_prams_int("p",1)
    data_list, pager = bll.find_pager(p, 20, rewrite_rule, {'user_id': user_token.id})

    return render_template(WebPaths.get_user_path("favorite.html"), user=g.u,data_list=data_list, pager=pager)

@user_blue.route('log_out', methods=['GET'])
def user_log_out():
    resp = make_response(redirect(WebPaths.LOGIN_URL))
    login_utils.logout_user(resp)
    return resp
