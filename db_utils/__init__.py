import os
from pymongo import MongoClient

from bll.site_settings import SiteSettings

def init_eb_db(app):
    """
    init mysql
    :param app:
    :return:
    """
    bs = app.config['base_settings']

    MONGODB_SERV = os.environ.get('MONGODB_SERV', bs.get('MONGODB_SERV'))
    MONGODB_NAME = os.environ.get('MONGODB_NAME', bs.get('MONGODB_NAME'))
    # 创建 MongoDB 客户端连接
    # global mongo_client

    mongo_client = MongoClient(MONGODB_SERV)

    # 选择或创建数据库
    # global mongo_db
    mongo_db = mongo_client[MONGODB_NAME]

    # 初始化 MongoDB 连接和其他配置
    app.db_client = mongo_client
    app.db = mongo_db

    bll = SiteSettings(mongo_db)

    model = bll.get_settings()

    # 确保数值型配置字段为 int｜DSML｜类型，防止数据库存储字符串导致比较异常
    for int_key in ('list_page_size', 'max_page_num', 'count_cache_ttl',
                    'max_search_total', 'search_cache_ttl',
                    'err_login_lock', 'reg_credits', 'upload_max_size',
                    'app_token_expired', 'index_cache_time'):
        if int_key in model:
            try:
                model[int_key] = int(model[int_key])
            except (ValueError, TypeError):
                pass

    app.config.update(model)


