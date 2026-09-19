import json
import re
from collections import Counter

from bson import ObjectId
from flask import Flask, Blueprint, current_app

import eb_utils
from bll.new_content import NewsContent
from eb_utils import http_helper
from entity.news_content_model import NewsContentModel
from entity.pay_back_model import PayBackInfo
from signals import content_saving, pay_saved_successful, search_prepare
from .datas.shop_orders import ShopOrder
from .. import module_attribute, ModuleInfo

module_url_prefix = "/shop"
# 模块扩展前台页面蓝图
bp_shop_pages = Blueprint('bp_shop_pages', __name__,
               template_folder='templates',
               static_folder='static',
               static_url_path='/',
               url_prefix=module_url_prefix)

# 模块扩展API蓝图
bp_shop_apis = Blueprint('bp_shop_apis', __name__, url_prefix=f"{module_url_prefix}/api/")


@bp_shop_pages.context_processor
def inject_site_name():
    """
    使用context_processor上下文件处理器，注入pages_blue下所有模板的公共变量
    """

    return {'SiteName': current_app.config['site_name'] or 'ebsite'}


settings_temp = '''
<div class="mb-3">
    <label>商品分类 ID <small class="text-muted">（NewsContent 中商品所属的分类 _id）</small></label>
    <input name="product_class_id" value="{{model.product_class_id}}"
           style="max-width:400px" class="form-control" required>
</div>
<div class="mb-3">
    <label>文章分类 ID <small class="text-muted">（NewsContent 中商城文章的分类 _id）</small></label>
    <input name="article_class_id" value="{{model.article_class_id}}"
           style="max-width:400px" class="form-control" required>
</div>
<div class="mb-3">
    <label>品牌专题父级 ID <small class="text-muted">（NewsSpecial 中品牌分组的父级 _id）</small></label>
    <input name="brand_parent_id" value="{{model.brand_parent_id}}"
           style="max-width:400px" class="form-control" required>
</div>
<div class="alert alert-info">修改配置后需重启服务才能生效。</div>
'''

# ── 运行时配置（module_init 中从 DB 读取后填充） ─────────────
product_class_id: ObjectId = None
article_class_id: ObjectId = None


@module_attribute(
    '商城管理系统',
    '简单的商城系统，比如，购物车，订单管理。',
    "/shop/shop_orders",
    settings_temp,
    'ebsite',
    config_fields={
        'product_class_id': 'str',
        'article_class_id': 'str',
        'brand_parent_id': 'str',
    }
)
def module_init(app:Flask, model:ModuleInfo):
    """
    在模块加载成功后触发，此函数名称不能更改
    @param model: 当前模块实例
    @param app: 当前 flask app实例
    @return:
    """
    module_configs = model.get_configs() or {}

    # 将分类 ID 转换为 ObjectId 并注入模块级变量和蓝图配置
    global product_class_id, article_class_id

    product_class_id = _to_objid(module_configs.get('product_class_id'))
    article_class_id = _to_objid(module_configs.get('article_class_id'))
    module_configs['_product_class_id'] = str(product_class_id) if product_class_id else ''
    module_configs['_article_class_id'] = str(article_class_id) if article_class_id else ''

    bp_shop_pages.config = module_configs
    bp_shop_apis.config = module_configs  # API 蓝图同样需要配置

    # 注册配置热更新
    def refresh_config(saved_config):
        global product_class_id, article_class_id
        product_class_id = _to_objid(saved_config.get('product_class_id'))
        article_class_id = _to_objid(saved_config.get('article_class_id'))
        saved_config['_product_class_id'] = str(product_class_id) if product_class_id else ''
        saved_config['_article_class_id'] = str(article_class_id) if article_class_id else ''
        bp_shop_pages.config = saved_config
        bp_shop_apis.config = saved_config
    model.on_config_changed(refresh_config)

    app.register_blueprint(bp_shop_pages)
    app.register_blueprint(bp_shop_apis)

    content_saving.connect(on_content_saving)
    pay_saved_successful.connect(on_pay_saved_successful)
    search_prepare.connect(on_search_prepare)

    ShopOrder(app).create_index_order_id()


def _to_objid(val):
    """安全地将字符串转为 ObjectId，无效时返回 None"""
    if val:
        val = val.strip()
        if ObjectId.is_valid(val):
            return ObjectId(val)
    return None


def is_have_sku(model: NewsContentModel)->bool:
    """
       检查 column_10 中是否有重复 sku，或数据库中已存在的 sku
       """
    try:

        specs = model.column_10
        if isinstance(specs, str):
            specs = json.loads(specs)

        # 1. 检查自身是否有重复的 sku
        sku_list = [item.get('sku') for item in specs if item.get('sku')]
        sku_counter = Counter(sku_list)
        local_duplicates = [sku for sku, count in sku_counter.items() if count > 1]
        if local_duplicates:
            print("当前数据中存在重复 sku：", local_duplicates)
            return True

        # 2. 检查数据库中是否已存在这些 sku（限定在商品分类内）
        collection = NewsContent().table
        existing = collection.find_one({
            "class_id": product_class_id,
            "column_10.sku": {"$in": sku_list},
            "_id": {"$ne": model._id}  # 排除当前记录
        })
        if existing:
            print("数据库中已存在相同 sku")
            return True

        return False
    except Exception as e:
        print(f"SKU 检查失败: {e}")
        return True  # 为安全起见，如果异常也不允许提交

def on_content_saving(model: NewsContentModel) -> (bool, str):

    if model.column_10 and 'costPrice' in model.column_10: # costPrice 只处理保存了产品规格的数据
        if is_have_sku(model):
            return False, '存在相同的商品货号'

        model.column_10 = json.loads(model.column_10)
        for product in model.column_10:
            product["productId"] = eb_utils.md5(product["sku"])
        model.small_pic = model.column_10[0]["image"]
        model.column_11 = model.column_10[0]["marketPrice"]
        print(f"商城模块-内容更新:{model.column_10}")

    return True, 'succesfull'

def on_pay_saved_successful(model: PayBackInfo) -> (bool, str):
    print(f'订单{model.order_no}支付成功，开始处理订单状态')
    # todo
    return True, 'succesfull'


# ---------------------------- 商品/文章分类ID（从数据库配置读取）────
# 实际值在 module_init 中从模块配置加载，赋值给 product_class_id / article_class_id


def _build_word_conditions(keyword: str, fields: list) -> dict:
    """
    拆词搜索（AND 逻辑）。
    将关键词按空白拆为单词，每个单词必须在至少一个字段中匹配。
    例如 "RICOH MPC8003" → 必须同时有字段含 "RICOH" 和字段含 "MPC8003"，
    避免任意一词匹配导致的搜索结果太宽泛。
    """
    words = [w for w in keyword.split() if w]
    if not words:
        return {}

    if len(words) == 1:
        # 单个单词：跨字段 $or
        word = words[0]
        return {
            "$or": [
                {field: {"$regex": re.escape(word), "$options": "i"}}
                for field in fields
            ]
        }

    # 多个单词：每个单词至少匹配一个字段（$and）
    return {
        "$and": [
            {
                "$or": [
                    {field: {"$regex": re.escape(word), "$options": "i"}}
                    for field in fields
                ]
            }
            for word in words
        ]
    }


def on_search_prepare(ctx: dict):
    """
    商城模块自定义搜索。
    当搜索参数中有 t=1 时为商品搜索（默认），t=2 时为文章搜索。
    """
    t = http_helper.get_prams("t")
    if t is None:
        return  # 不是商城触发的搜索

    keyword = ctx.get("keyword", "")
    if not keyword:
        return

    if t == "2":
        # 文章搜索
        ctx["template"] = "search_article.html"
        query = {"class_id": article_class_id}
        query.update(_build_word_conditions(keyword, ["title", "info"]))
        ctx["query"] = query
    else:
        # 商品搜索（默认）
        ctx["template"] = "search_product.html"
        query = {"class_id": product_class_id}
        query.update(_build_word_conditions(keyword, [
            "column_3", "column_4", "column_5", "column_6"
        ]))
        ctx["query"] = query



from . import shop_pages
from . import shop_apis
from .shop_controls import product_sku

