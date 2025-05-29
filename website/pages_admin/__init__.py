import os
import platform
import sys
from datetime import datetime
from pathlib import Path

from flask import Blueprint, g, render_template, request, redirect, make_response, current_app, jsonify

from bll.admin_login_log import AdminLoginLog
from bll.admin_user import AdminUser
from bll.data_bakup import DataBakup
from bll.file_upload import FileUpload
from bll.send_msg_data import SendMsgData
from bll.site_log import SiteLog
from bll.site_settings import SiteSettings
from bll.user_group import UserGroup
from decorators import rate_limit_ip
from eb_cache import login_utils
from eb_utils import http_helper
from eb_utils.configs import WebPaths
from bll.admin_menus import AdminMenus
from eb_utils.image_code import ImageCode
from eb_utils.xs_json import XsJson
from entity import api_msg
from temp_expand import get_table_html

theme_name = "default"
theme_template_path = os.path.join('themes', theme_name, 'templates')
theme_static_path = os.path.join('themes', theme_name, 'static')
admin_blue = Blueprint('admin', __name__,
                       url_prefix=WebPaths.ADMIN_PATH,
                       template_folder=theme_template_path,
                       static_folder=theme_static_path,static_url_path='/')

from . import menus
from . import users
from . import adminer
from . import logs

from . import custom_form
from . import news_class
from . import news_content
from . import news_special
from . import widgets
from . import templates
from . import plugins
from . import modules
from . import site_model

from . import apis

# region 后台请求前的处理

@admin_blue.before_request
def before_req():
    """
    在后台页面请求前进行一些权限处理
    :return:
    """
    # 跳过静态资源的访问
    if request.endpoint and request.endpoint == f"{admin_blue.name}.static":
        return  None # 返回 None，继续正常处理请求
    # 如果请求的是登录页，就不拦截
    if request.path in [f'{WebPaths.ADMIN_PATH}login_ad',f'{WebPaths.ADMIN_PATH}setup_data']:
        return None

    g.u = None
    admin_token = login_utils.get_token_admin()
    if admin_token:
        g.u = admin_token
        g.uid = admin_token.id
        return None
    else:
        return redirect(f"{WebPaths.ADMIN_PATH}login_ad")


# endregion
@admin_blue.context_processor
def inject_admin_path():
    """
    将admin_path注入模板，在模板中可以这样调用 {{ admin_path }}
    :return:
    """
    return dict(admin_path=WebPaths.ADMIN_PATH)

@admin_blue.route('/login_ad', methods=['GET', 'POST'])
@rate_limit_ip(10,60) # 一小时只允许调用10次
def login_ad():
    err_msg = ""
    is_exist_all_table = DataBakup().is_exist_all_table()
    if not is_exist_all_table:  # 如果默认表不存在，可以说明是第一次安装项目
        RandomKey = current_app.config['RandomKey']
        return redirect(f'{WebPaths.ADMIN_PATH}setup_data?key={RandomKey}')

    err_count = login_utils.get_count('adminer_login_err_count')

    if request.method == 'POST':
        # session.pop(SessionIds.User, None)
        username = request.form.get("username", None)
        password = request.form.get("pass", None)
        image_code = request.form.get("code", None)
        is_safe = True
        if err_count > 0:
            is_safe, err_msg = ImageCode().check_code(image_code)
        if is_safe:
            resp = make_response(redirect(WebPaths.ADMIN_INDEX))
            is_safe, err_msg = AdminUser().login(username, password, resp)
            if is_safe:
                # expires = datetime.datetime.now() + datetime.timedelta(hours=24)
                # resp.set_cookie(SiteConstant.COOKIE_AD_TOKEN_KEY, err_msg, expires=expires)
                return resp
            else:
                err_count = login_utils.add_count_hour('adminer_login_err_count')

        AdminLoginLog().add_log(username, username, '后台登录失败', err_msg)

    # settings_model = get_settings()
    return render_template("admin_login.html", is_safe_code=err_count > 0, err=err_msg)


@admin_blue.route('/setup_data', methods=['GET', 'POST'])
def setup_data():
    err_msg = ""

    site_key_md5 = request.args.get("key", None)
    is_allow = False
    RandomKey = current_app.config['RandomKey']

    if site_key_md5 == RandomKey:
        is_allow = True

    is_exist_all_table = DataBakup().is_exist_all_table()

    if is_exist_all_table: # 如果已经存在所有表不允许再配置数据
        is_allow = False
        print('已经存在表，不允许再初始化')

    if request.method == 'POST' and is_allow:
        DataBakup().InitDefaultData()  # 第一次安装时导入默认数据
        SiteLog().add_log("", "", '初始化数据', err_msg)
        return redirect(WebPaths.ADMIN_LOGIN)

    return render_template("setup.html", is_allow=is_allow)

@admin_blue.route('index', methods=['GET'])
def admin_index():
    menu = AdminMenus().get_by_pid("")
    return render_template("admin_index.html", menu_data=menu)


@admin_blue.route('wellcome', methods=['GET'])
def admin_wellcome():
    admin_token = g.u
    python_version_info = f"{platform.system()} {platform.release()}  Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    db_version_info = current_app.db.command({'buildInfo': 1})
    # print(db_version_info)
    db_version = "0.0"
    if db_version_info and 'version' in db_version_info:
        db_version = db_version_info['version']
        db_version = f"MongoDb {db_version}"

    return render_template("wellcome.html",db_version=db_version, admin_token=admin_token, version_info=python_version_info)


@admin_blue.route('log_out', methods=['GET'])
def admin_log_out():
    resp = make_response(redirect(WebPaths.ADMIN_LOGIN))
    login_utils.logout_admin(resp)
    return resp

def get_theme_folders():
    theme_dir = Path(__file__).parent.parent / 'themes'
    return [folder.name for folder in theme_dir.iterdir() if folder.is_dir()]


@admin_blue.route('settings', methods=['GET', 'POST'])
def admin_settings():
    settings_model = current_app.config
    sms_senders = current_app.pm.get_by_sms_plugins()
    email_senders = current_app.pm.get_by_email_plugins()
    uploaders = current_app.pm.get_by_uploader_plugins()
    theme_names = get_theme_folders()
    print(theme_names)
    baseSettings = current_app.config['base_settings']
    currentTheme = baseSettings["ThemeName"]

    if request.method == 'POST':
        prams_dict = http_helper.get_prams_dict()
        bll = SiteSettings(current_app.db)
        bll.save_setting(prams_dict)
        current_app.config.update(prams_dict)

        bs = current_app.config['base_settings']
        olg_theme = bs["ThemeName"]
        new_theme = prams_dict["theme_name"]
        if olg_theme != new_theme:
            try:
                CF = XsJson("conf/setting.json")
                bs["ThemeName"] = new_theme
                CF.save(bs)
            except Exception as e:
                print(
                    '保存系统设置时发生错误，无法将主题保存到setting.json，你可能正在使用无状态服务平台，请手动修改setting.json的主题')
                print(f'错误信息：{e}')

    return render_template("configs/settings.html",theme_names=theme_names,theme_selected=currentTheme, uploaders=uploaders,sms_senders=sms_senders,email_senders=email_senders, model=settings_model,
                           group=UserGroup().find_all())

@admin_blue.route('test_email', methods=['POST'])
def test_email():
    emails:str = current_app.config['report_emails']

    if emails:
        email = emails.split(',')[0]
        current_app.pm.send_email(email, '来自EbSite的测试邮件',f'来自EbSite的测试邮件:{datetime.now()}')
    return jsonify(api_msg.api_succesful(email))

@admin_blue.route('files', methods=['GET'])
def files():
    keyword = http_helper.get_prams("k")
    page_index = http_helper.get_prams_int("p", 1)
    plugin_id = http_helper.get_prams("pid")
    uploaders = current_app.pm.get_by_uploader_plugins()

    bll = FileUpload()
    datas, pager = bll.search_content(keyword, plugin_id, page_index)

    del_btn = {"show_name": "删除", "url": "files_del?ids=#_id#", "confirm": True}
    table_html = get_table_html(datas, [del_btn])

    return render_template(WebPaths.get_admin_path("configs/files.html"),table_html=table_html,pager=pager, uploaders=uploaders)

@admin_blue.route('files_del', methods=['GET', 'POST'])
def files_del():
    FileUpload().delete_from_page(http_helper.get_prams("ids"))
    return redirect("files")

@admin_blue.route('send_list', methods=['GET'])
def send_list():
    keyword = http_helper.get_prams("k")
    page_index = http_helper.get_prams_int("p", 1)
    type_id = http_helper.get_prams("tid")

    types = [
        {
            "id": 1,
            "name": "手机短信发送记录"
        },
        {
            "id": 2,
            "name": "EMAIL发送记录"
        }
    ]

    bll = SendMsgData()
    datas, pager = bll.search_content(keyword, type_id, page_index)

    del_btn = {"show_name": "删除", "url": "send_list_del?ids=#_id#", "confirm": True}
    table_html = get_table_html(datas, [del_btn])

    return render_template(WebPaths.get_admin_path("configs/send_list.html"),table_html=table_html,pager=pager, types=types)

@admin_blue.route('send_list_del', methods=['GET', 'POST'])
def send_list_del():
    SendMsgData().delete_from_page(http_helper.get_prams("ids"))
    return redirect("send_list")