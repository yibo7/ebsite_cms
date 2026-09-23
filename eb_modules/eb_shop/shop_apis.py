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
from .datas.cart_manger import CartManager


# ── 辅助函数：获取当前登录用户的 uid 和 user_name ──────────
def _current_user_info():
    """返回 (user_id_str, user_name) 或 (None, None)"""
    token = login_utils.get_token()
    if not token:
        return None, None
    return token.id, token.name or ""


def _product_to_dict(p):
    """将 NewsContentModel 序列化为前端需要的字典"""
    return {
        '_id': str(p._id),
        'id': p.id,
        'title': p.title,
        'small_pic': p.small_pic or '',
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
      - 无参数：返回品牌列表（parent_id 从模块配置中读取）
      - parent_id：返回该品牌 _id 下的型号列表
      - brand_name + 可选 model_name：
          返回 { brands, models, products }
          products 按 column_3(品牌名) / column_4(型号名) 筛选 NewsContent

    返回 JSON：
      { "code": 0, "brands": [...], "models": [...], "products": [...] }
    """
    try:
        parent_id = request.values.get('parent_id')
        brand_name = request.values.get('brand_name')
        model_name = request.values.get('model_name')

        # ── 1. 品牌列表（始终返回） ──────────────────────────────
        brand_parent_id = bp_shop_apis.config.get('brand_parent_id', '')
        if brand_parent_id:
            brand_parent_id = brand_parent_id.strip()
        if not brand_parent_id:
            # 配置尚未设置时，使用默认硬编码值
            brand_parent_id = "6852c97a9d0e112569a8cbf9"
        brands = NewsSpecial().get_by_pid(brand_parent_id) if brand_parent_id else []
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

    except Exception as e:
        print(f'product_filter 异常: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({"code": -1, "msg": str(e)}), 500


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


@bp_shop_apis.route('cart_count', methods=['GET'])
def cart_count():
    """
    获取当前登录用户的购物车商品总数量（所有商品 quantity 之和）
    返回 JSON：{ code: 0, data: { count: N } }
    """
    uid, account = _current_user_info()
    if not uid:
        return jsonify({"code": 0, "data": {"count": 0}})

    cart_mgr = CartManager(uid, account)
    count = cart_mgr.get_count()
    return jsonify({"code": 0, "data": {"count": count}})


@bp_shop_apis.route('product/<product_id>/prices', methods=['GET'])
def product_prices(product_id):
    """
    获取某个商品的当前用户可见价格规则。

    前端通过 /shop/api/product/{id}/prices 异步获取。
    服务端按用户身份过滤：
      - 零售用户：只返回 marketPrice
      - 批发会员：返回 marketPrice + member_price + qty_prices

    返回 JSON：
    {
      "code": 0,
      "data": {
        "product_id": "...",
        "skus": [
          {
            "sku": "GX-IR1435-002",
            "marketPrice": 20,
            "costPrice": 14,
            "member_price": 16,
            "member_group": "svip",
            "qty_prices": [
              {"min_qty": 10, "max_qty": 49, "price": 16},
              {"min_qty": 50, "max_qty": 99, "price": 12}
            ]
          }
        ]
      }
    }
    """
    try:
        # 1. 查找商品
        content = NewsContent().find_one_by_id(product_id)
        if not content:
            return jsonify({"code": -1, "msg": "商品不存在"}), 404

        # 2. 获取当前登录用户信息
        token = login_utils.get_token()
        user_group_id = None
        user_group_name = None

        if token and token.id:
            from bll.user import User
            user_bll = User()
            user = user_bll.find_one_by_id(token.id)
            if user and user.group_id:
                user_group_id = str(user.group_id)
                # 获取组名
                from bll.user_group import UserGroup
                group_bll = UserGroup()
                g = group_bll.find_one_by_id(ObjectId(user_group_id))
                if g:
                    user_group_name = g.name

        # 3. 解析 SKU 数据
        skus_data = content.column_10
        if isinstance(skus_data, str):
            skus_data = json.loads(skus_data)
        if not skus_data or not isinstance(skus_data, list):
            return jsonify({"code": -1, "msg": "商品无SKU数据"}), 404

        # 4. 按用户身份过滤每个 SKU 的价格规则
        result_skus = []
        for sku in skus_data:
            sku_info = {
                "sku": sku.get("sku", ""),
                "marketPrice": sku.get("marketPrice", 0),
                "costPrice": sku.get("costPrice", 0),
            }

            # 已登录且有用户组 → 返回会员价和阶梯价
            if user_group_id and sku.get("group_prices"):
                member = None
                for gp in sku["group_prices"]:
                    if gp.get("group_id") == user_group_id:
                        member = gp
                        break
                if member:
                    sku_info["member_price"] = member.get("price")
                    sku_info["member_group"] = member.get("group_name", user_group_name)

            # 阶梯价对所有用户可见（但前端按数量匹配）
            sku_info["qty_prices"] = sku.get("group_qty_prices", [])

            result_skus.append(sku_info)

        return jsonify({
            "code": 0,
            "data": {
                "product_id": product_id,
                "skus": result_skus
            }
        })

    except Exception as e:
        print(f'product_prices 异常: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({"code": -1, "msg": str(e)}), 500


# ── 关闭订单 ──────────────────────────────────────────
@bp_shop_apis.route('order_close', methods=['POST'])
@check_user_login
def order_close(user_token: UserToken):
    """关闭订单（取消）"""
    from eb_utils import http_helper
    order_id = http_helper.get_prams("order_id")
    reason = http_helper.get_prams("reason") or "用户取消"

    if not order_id:
        return jsonify({"code": -1, "msg": "参数错误"})

    bll = ShopOrder()
    model = bll.get_by_order_id(order_id)

    if not model:
        return jsonify({"code": -1, "msg": "订单不存在"})

    # 校验所有权：兼容 ObjectId 与字符串
    owner_id = str(model.user_id or '').strip()
    caller_id = str(user_token.id or '').strip()
    if owner_id != caller_id:
        return jsonify({"code": -1, "msg": "无权操作此订单"})

    if model.order_status != 0:
        return jsonify({"code": -1, "msg": "当前状态不允许关闭"})

    model.order_status = -1
    model.close_reason = reason
    bll.save(model)

    return jsonify({"code": 0, "msg": "订单已关闭"})


# ── 确认收货 ──────────────────────────────────────────
@bp_shop_apis.route('order_receipt', methods=['POST'])
@check_user_login
def order_receipt(user_token: UserToken):
    """确认收货"""
    from eb_utils import http_helper
    order_id = http_helper.get_prams("order_id")

    if not order_id:
        return jsonify({"code": -1, "msg": "参数错误"})

    bll = ShopOrder()
    model = bll.get_by_order_id(order_id)

    if not model:
        return jsonify({"code": -1, "msg": "订单不存在"})

    # 校验所有权：兼容 ObjectId 与字符串
    owner_id = str(model.user_id or '').strip()
    caller_id = str(user_token.id or '').strip()
    if owner_id != caller_id:
        return jsonify({"code": -1, "msg": "无权操作此订单"})

    if model.order_status != 2:
        return jsonify({"code": -1, "msg": "当前状态不允许确认收货"})

    model.order_status = 3
    model.finish_date = __import__('datetime').datetime.now()
    bll.save(model)

    return jsonify({"code": 0, "msg": "已确认收货"})

