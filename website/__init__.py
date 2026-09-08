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
    default_theme = base_setting["ThemeName"]

    theme_name = os.environ.get('THEME', default_theme)

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

    app.config['SiteKey'] = base_setting['APP_KEY']  # 网站的密钥
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

    # 确保关键复合索引存在（后台非阻塞，仅 create_index 的 if_not_exists 语义）
    with app.app_context():
        try:
            news_collection = app.db['NewsContent']
            # 分类列表页排序索引：class_id + order_id + _id
            news_collection.create_index(
                [("class_id", 1), ("order_id", -1), ("_id", -1)],
                background=True
            )
            # 标签聚合索引：class_n_id + tags（加速 $unwind + $group 聚合）
            news_collection.create_index(
                [("class_n_id", 1), ("tags", 1)],
                background=True
            )
            # 用户内容列表索引：user_id + add_time（加速个人中心查询）
            news_collection.create_index(
                [("user_id", 1), ("add_time", -1)],
                background=True
            )
            # 热门排序索引：hits（加速 getHotDatas 按 hits 降序取 top N）
            news_collection.create_index(
                [("hits", -1)],
                background=True
            )
            # 推荐排序索引：is_good + hits（加速 getRecDatas 筛选推荐并按 hits 排序）
            news_collection.create_index(
                [("is_good", 1), ("hits", -1)],
                background=True
            )
            # 内容自增ID索引：id（加速专题页面按 id 查询内容）
            news_collection.create_index(
                [("id", 1)],
                background=True
            )
        except Exception:
            pass  # 索引创建失败不影响启动

    return app
