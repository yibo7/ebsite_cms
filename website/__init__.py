import os

from flask import Flask
from jinja2 import ChoiceLoader, FileSystemLoader
from werkzeug.routing import BaseConverter

import eb_utils
from db_utils import init_eb_db
from eb_cache import init_eb_cache
from eb_modules import load_modules
from eb_utils.xs_json import XsJson
from plugins import load_plugins
from signals import app_created
from temp_expand import reg_temp_expand

# 自定义转换器：匹配32位十六进制字符串（MD5）
class MD5Converter(BaseConverter):
    regex = r'[a-fA-F0-9]{32}'

def create_app():  # run_mode
    """
    创建app
    :return: FlaskApp
    """

    base_setting = XsJson("conf/setting.json").load()
    # db_conn = os.environ.get('MONGODB_SERV', None)
    # if db_conn:
    #     base_setting["MONGODB_SERV"] = db_conn
    theme_name = base_setting["ThemeName"]
    theme_template_path = os.path.join('themes', theme_name, 'templates')
    theme_static_path = os.path.join('themes', theme_name, 'static')
    app = Flask(__name__,template_folder=theme_template_path, static_folder=theme_static_path,static_url_path='/')
    app.url_map.converters['md5'] = MD5Converter  # 注册路由转换器，目前主要应用于标签页面URl强制md5规则

    # 加入多个模板目录
    # app.jinja_loader = ChoiceLoader([
    #     FileSystemLoader(theme_template_path),
    #     FileSystemLoader(default_template_path),
    # ])

    app.config['RandomKey'] = eb_utils.random_string_hex(32)  # 每次启动都会生成一个随机字符

    app.config['TEMPLATES_AUTO_RELOAD'] = True  # 模板热更新

    # region 加载基础设置

    app.config.update({'base_settings': base_setting})

    # endregion

    init_eb_db(app)
    init_eb_cache(app)
    reg_temp_expand(app)

    load_plugins(app)

    # 将蓝图注册到app中

    from website.pages import pages_blue
    app.register_blueprint(pages_blue)
    from website.pages_admin import admin_blue
    app.register_blueprint(admin_blue)
    from website.apis import api_blue
    app.register_blueprint(api_blue)
    from website.pages_ucc import user_blue
    app.register_blueprint(user_blue)
    from website.apis import api_blue_user
    app.register_blueprint(api_blue_user)

    app_created.send(app)  # 发送应用创建信号
    load_modules(app)

    return app
