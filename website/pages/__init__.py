import threading
import time

from flask import Blueprint, g, render_template, request, redirect, make_response, current_app, send_from_directory

import eb_cache
from bll.temp_data_provider import TempDataProvider
from bll.user import User
from eb_cache import login_utils
from eb_cache.cache_keys import CacheKeys
from eb_utils.configs import WebPaths
from eb_utils.image_code import ImageCode
from eb_utils.string_check import is_email, is_mobile
from entity.user_model import UserModel

pages_blue = Blueprint('pages_blue', __name__)
from . import cms_page
from . import payment

@pages_blue.context_processor
def inject_site_name():
    """
    使用context_processor上下文件处理器，注入pages_blue下所有模板的公共变量
    """

    return {'SiteName': current_app.config['site_name'] or 'ebsite'}

from flask import Request
from werkzeug.test import EnvironBuilder


def render_and_cache_index(lang='zh'):
    with current_app.app_context():
        default = current_app.config.get('DEFAULT_LANG', 'zh')
        # 首页缓存用真实根路径，request.path 不会被污染
        builder = EnvironBuilder(path='/')
        env = builder.get_environ()
        env['ORIG_PATH_INFO'] = f'/{lang}' if lang != default else '/'
        req = Request(env)
        with current_app.request_context(env):
            # 后台线程中没有 set_lang() 执行，手动设置语言标记
            from flask import g
            g.lang = lang
            g.lang_dict = _load_lang_dict_for_cache(lang)
            temp_path = current_app.config.get('index_temp_path',"index.html")
            rendered = render_template(temp_path, index_data=TempDataProvider())
            cache_key = f"{CacheKeys.INDEX_HTML}_{lang}_v2"
            time_key = f"{CacheKeys.INDEX_TIME}_{lang}_v2"
            eb_cache.set_data(rendered, ex_second=0, key=cache_key)
            eb_cache.set_data(time.time(), ex_second=0, key=time_key)
            print(f"index cache updated ({lang})")
            return rendered

def _load_lang_dict_for_cache(lang):
    """后台缓存线程专用：加载语言字典"""
    import json
    import os
    try:
        theme_name = current_app.config.get('base_settings', {}).get('ThemeName', 'aitanqin')
        default = current_app.config.get('DEFAULT_LANG', 'zh')
        def _load(code):
            p = os.path.join(current_app.root_path, 'themes', theme_name, 'i18n', f'{code}.json')
            try:
                with open(p, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return {}
        result = _load(lang)
        if lang != default:
            defaults = _load(default)
            for k, v in defaults.items():
                result.setdefault(k, v)
        return result
    except Exception:
        return {}

def run_in_app_context(app, func, *args, **kwargs):
    def wrapped():
        with app.app_context():
            func(*args, **kwargs)
    threading.Thread(target=wrapped).start()

@pages_blue.route('/', methods=['GET'])
def index():
    current_lang = getattr(g, 'lang', 'zh')
    temp_path = current_app.config.get('index_temp_path',"index.html")
    cache_time = current_app.config.get('index_cache_time', 0)
    cache_time = int(cache_time)
    if cache_time > 0:
        cache_key = f"{CacheKeys.INDEX_HTML}_{current_lang}"
        cached_html = eb_cache.get(cache_key)
        if cached_html:
            time_key = f"{CacheKeys.INDEX_TIME}_{current_lang}"
            last_update = eb_cache.get(time_key) or 0
            if time.time() - last_update > cache_time:
                use_app = current_app._get_current_object()
                run_in_app_context(use_app, render_and_cache_index, current_lang)
            return make_response(cached_html)

        rendered = render_and_cache_index(current_lang)
        return make_response(rendered)

    return render_template(temp_path, index_data=TempDataProvider())


@pages_blue.errorhandler(404)
def page_not_found(error):
    return render_template('404.html'), 404


@pages_blue.route('/login', methods=['GET', 'POST'])
def login():
    err_msg = ""
    err_count = login_utils.get_count('user_login_err_count')
    login_force_verify = current_app.config.get('login_force_verify', True)
    if request.method == 'POST':
        username = request.form.get("username", None)
        password = request.form.get("pass", None)
        image_code = request.form.get("code", None)
        if not login_force_verify or is_email(username) or is_mobile(username):
            is_safe = True
            if err_count > 0:
                is_safe, err_msg = ImageCode().check_code(image_code)
            if is_safe:
                _prefix = ''
                cur_lang = getattr(g, 'lang', '')
                default = current_app.config.get('DEFAULT_LANG', 'zh')
                if cur_lang and cur_lang != default:
                    _prefix = f'/{cur_lang}'
                resp = make_response(redirect(_prefix + WebPaths.USER_INDEX))
                is_safe, err_msg = User().login(username, password, resp)
                if is_safe:
                    return resp
                else:
                    err_count = login_utils.add_count_hour('user_login_err_count')
        else:
            err_msg = "请输入有效的EMAIL或手机号"

    return render_template("login.html", is_safe_code=err_count > 0, err=err_msg)


@pages_blue.route('/reg', methods=['GET', 'POST'])
def reg():
    err_msg = None
    if request.method == 'POST':
        username = request.form.get("username", None)
        password = request.form.get("password", None)
        passwordr = request.form.get("repassword", None)
        image_code = request.form.get("code", None)

        if image_code:
            is_safe, err_msg = ImageCode().check_code(image_code)
            if not is_safe:
                err_msg = "验证码错误!"
        else:
            err_msg = "验证码无效!"

        is_username_email = False
        if username:
            if is_email(username):
                is_username_email = True
                # send email code
                pass
            elif is_mobile(username):
                # send mobile code
                pass
            else:
                err_msg = '请输入正确的手机号或EMAIL'
        else:
            err_msg = "用户名不能为空!"

        if not all([password, passwordr]) or password != passwordr:
            err_msg = "密码格式不对或两次密码不一至!"

        if len(password) < 6:
            err_msg = "密码长度要大于6!"

        if not err_msg:
            user = UserModel()
            user.username = username
            user.ni_name = username
            user.password = password
            if is_username_email:
                user.email_address = username
            else:
                user.mobile_number = username
            [is_ok, msg] = User().reg_user(user)
            if is_ok:
                _prefix = ''
                cur_lang = getattr(g, 'lang', '')
                default = current_app.config.get('DEFAULT_LANG', 'zh')
                if cur_lang and cur_lang != default:
                    _prefix = f'/{cur_lang}'
                resp = make_response(redirect(_prefix + WebPaths.USER_INDEX))
                login_utils.set_cookie_token(user, resp)

                return resp
            else:
                err_msg = msg
    return render_template("reg.html", err=err_msg)


@pages_blue.route('/reg_info.html', methods=['GET', 'POST'])
def reg_info():
    return render_template("reg_info.html")


@pages_blue.route('/imgcode')
def img_code():
    return ImageCode().getImgCode()
