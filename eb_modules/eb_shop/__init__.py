from flask import Flask, Blueprint

from entity.news_content_model import NewsContentModel
from signals import content_saving
from .. import module_attribute, ModuleInfo

module_url_prefix = "/shop"
# 模块扩展前台页面蓝图
bp_shop_pages = Blueprint('bp_shop_pages', __name__,
               template_folder='templates',
               static_folder='static',
               static_url_path='/',
               url_prefix=module_url_prefix)

# 模块扩展API蓝图
# bp_shop_apis = Blueprint('bp_shop_apis', __name__, url_prefix=f"{module_url_prefix}/api/")

settings_temp = None
@module_attribute('商城管理系统','简单的商城系统，比如，购物车，订单管理。',"/shop/shop_orders",settings_temp,'ebsite')
def module_init(app:Flask, model:ModuleInfo):
    """
    在模块加载成功后触发，此函数名称不能更改
    @param model: 当前模块实例
    @param app: 当前 flask app实例
    @return:
    """
    module_configs = model.get_configs()

    bp_shop_pages.config = module_configs

    app.register_blueprint(bp_shop_pages)

    content_saving.connect(on_content_saving)

def on_content_saving(model: NewsContentModel) -> (bool, str):
    print(f"商城模块-内容更新:{model.column_13}")
    return True, 'succesfull'

from . import pages
from .shop_controls import product_sku

