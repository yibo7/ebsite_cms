import os
import re
import pymongo
from flask import jsonify, current_app, send_from_directory, request, url_for

from decorators import check_user_login
from eb_modules.eb_shop import bp_shop_apis
from bll.new_special import NewsSpecial
from bll.new_content import NewsContent
from eb_utils import url_links
from eb_cache import login_utils
from bson import ObjectId

from entity.user_token import UserToken
from .datas.shop_orders import ShopOrder


def _product_to_dict(p):
    """将 NewsContentModel 序列化为前端需要的字典"""
    return {
        '_id': str(p._id),
        'id': p.id,
        'title': p.title,
        'small_pic': p.small_pic or '',
        'info': p.info or '',
        'class_name': p.class_name or '',
        'class_id': str(p.class_id) if p.class_id else '',
        'column_3': p.column_3 or '',
        'column_4': p.column_4 or '',
        'column_6': p.column_6 or '',
        'column_11': p.column_11 or '',
        'url': url_links.get_content_url(p.id),
    }


@bp_shop_apis.route('product_filter', methods=['POST', 'GET'])
def product_filter():
    """
    品牌/型号级联筛选 API

    请求参数（GET 或 POST）：
      - 无参数：返回品牌列表（parent_id = 6852c97a9d0e112569a8cbf9）
      - parent_id：返回该品牌 _id 下的型号列表
      - brand_name + 可选 model_name：
          返回 { brands, models, products }
          products 按 column_3(品牌名) / column_4(型号名) 筛选 NewsContent

    返回 JSON：
      { "code": 0, "brands": [...], "models": [...], "products": [...] }
    """
    parent_id = request.values.get('parent_id')
    brand_name = request.values.get('brand_name')
    model_name = request.values.get('model_name')

    # ── 1. 品牌列表（始终返回） ──────────────────────────────
    brands = NewsSpecial().get_by_pid("6852c97a9d0e112569a8cbf9")
    brand_list = [s.to_short_dic() for s in brands]

    # ── 2. 型号 / 商品查询条件 ─────────────────────────────
    models = []
    products = []

    if parent_id:
        # 只查型号（兼容旧逻辑）
        models = [s.to_short_dic() for s in NewsSpecial().get_by_pid(parent_id)]

    elif brand_name:
        # 根据品牌名称查找品牌对象 → 获取其 _id 查型号
        matched_brand = None
        for b in brands:
            if b.name == brand_name:
                matched_brand = b
                break
        if matched_brand:
            models = [s.to_short_dic() for s in NewsSpecial().get_by_pid(str(matched_brand._id))]

        # 查询商品
        where = {"column_3": brand_name}
        if model_name:
            where["column_4"] = model_name

        content_list = NewsContent().find_list_by_where(
            where=where,
            sort_key="order_id",
            sort_direction=pymongo.DESCENDING,
        )
        products = [_product_to_dict(p) for p in content_list]

    return jsonify({
        "code": 0,
        "brands": brand_list,
        "models": models,
        "products": products,
    })


@bp_shop_apis.route('order_count', methods=['GET'])
def order_count():
    """
    获取当前登录用户的订单统计数据（异步供个人中心首页使用）
    返回 JSON：{ code: 0, data: { total, pending, paid, shipped, done } }
    """
    user_token = login_utils.get_token()
    if not user_token:
        return jsonify({"code": -1, "data": {"total": 0, "pending": 0, "paid": 0, "shipped": 0, "done": 0}})

    uid = ObjectId(user_token.id)
    order_bll = ShopOrder()

    total = order_bll.count({"user_id": uid})
    pending = order_bll.count({"user_id": uid, "order_status": 0})
    paid = order_bll.count({"user_id": uid, "order_status": 1})
    shipped = order_bll.count({"user_id": uid, "order_status": 2})
    done = order_bll.count({"user_id": uid, "order_status": 3})

    return jsonify({
        "code": 0,
        "data": {
            "total": total,
            "pending": pending,
            "paid": paid,
            "shipped": shipped,
            "done": done,
        }
    })

