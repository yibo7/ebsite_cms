import time
from decimal import Decimal

from bson import ObjectId
import pymongo
from flask import jsonify, current_app, render_template, redirect, request, url_for
from pydantic.v1 import DecimalError

import eb_utils

from bll.address import Address
from bll.new_content import NewsContent
from bll.temp_data_provider import TempDataProvider
from decorators import check_admin_login, check_user_login
from eb_modules.eb_shop import bp_shop_pages
from eb_modules.eb_shop.datas.cart_manger import CartManager
from eb_modules.eb_shop.datas.shop_orders import ShopOrder, ORDER_STATUS_MAP
from eb_utils import http_helper
from entity.user_token import UserToken
from plugins.plugin_base import PaymentBase


@bp_shop_pages.route('/cart', methods=['GET', 'POST'])
@check_user_login
def cart(user_token:UserToken):
    err = ''
    bll = CartManager(user_token.id,user_token.name)
    content_id = http_helper.get_prams("cid")
    product_id = http_helper.get_prams("pid")
    quantity = http_helper.get_prams_int("num",1)
    action = http_helper.get_prams_int("action",1)

    if action==1 and content_id and product_id:
        err = bll.add_item(content_id, product_id,quantity)
        if not err:
            # 当需要刷新页面并去掉所有参数时
            return redirect(url_for('bp_shop_pages.cart'))
    elif action==2 and content_id and product_id:
        err =bll.update_quantity(content_id, product_id, quantity)
        if not err:
            return redirect(url_for('bp_shop_pages.cart'))

    elif action==3 and  product_id:
        bll.remove_item(product_id)
        return redirect(url_for('bp_shop_pages.cart'))

    elif action==4:
        bll.clear_cart()
        return redirect(url_for('bp_shop_pages.cart'))

    shopping_cart = bll.get_items()

    total_count = sum(item.quantity for item in shopping_cart)
    total_price = sum(Decimal(str(item.price)) * item.quantity for item in shopping_cart)
    total_price = round(total_price, 2)  # 保留 2 位小数
    return render_template("shopping_cart.html", shopping_cart=shopping_cart,total_count=total_count,total_price=total_price, err=err)


@bp_shop_pages.route('/post_order', methods=['GET', 'POST'])
@check_user_login
def post_order(user_token:UserToken):
    err = ''
    bll = CartManager(user_token.id,user_token.name)
    address_id = http_helper.get_prams("address")
    if address_id:
        remark = http_helper.get_prams("remark") or ""
        err = bll.post_to_order(address_id, remark)
        if err:
            print(err)
            return render_template("post_order.html", err=err)
        # 提交后跳转到支付页面，order_id 由 post_to_order 内部生成后返回
        # 重新查询最新订单
        from eb_modules.eb_shop.datas.shop_orders import ShopOrder
        orders = ShopOrder().find_list_by_where(
            {'user_id': ObjectId(user_token.id)},
            sort_key="add_time",
            sort_direction=pymongo.DESCENDING,
            limit=1
        )
        if orders:
            return redirect(url_for('bp_shop_pages.sel_payment', orderid=orders[0].order_id))
        return redirect(url_for('bp_shop_pages.my_orders'))

    shopping_cart = bll.get_items()
    total_count = sum(item.quantity for item in shopping_cart)
    total_price = sum(Decimal(str(item.price)) * item.quantity for item in shopping_cart)
    total_price = round(total_price, 2)  # 保留 2 位小数

    addr_datas = Address().get_by_user_id(user_token.id)

    # 获取运费配置
    config = getattr(bp_shop_pages, 'config', {}) or {}
    free_shipping_threshold = int(config.get('free_shipping_threshold', 500))
    flat_shipping_fee = int(config.get('flat_shipping_fee', 20))

    # 计算运费
    if free_shipping_threshold == 0:
        shipping_fee = 0
    elif total_price >= free_shipping_threshold:
        shipping_fee = 0
    else:
        shipping_fee = flat_shipping_fee

    total_amount = round(total_price + shipping_fee, 2)

    # 判断是否有阶梯价促进提示
    tier_hints = []
    for item in shopping_cart:
        group_qty_prices = getattr(item, 'group_qty_prices', []) or []
        current_price = Decimal(str(item.price))
        for tier in group_qty_prices:
            min_qty = tier.get('min_qty', 0)
            tier_price = Decimal(str(tier.get('price', 0)))
            if item.quantity < min_qty and tier_price < current_price:
                diff = min_qty - item.quantity
                tier_hints.append({
                    'name': item.product_name,
                    'diff': diff,
                    'tier_price': float(tier_price)
                })
                break

    return render_template("post_order.html",
        addr_datas=addr_datas,
        shopping_cart=shopping_cart,
        total_count=total_count,
        total_price=total_price,
        shipping_fee=shipping_fee,
        total_amount=total_amount,
        free_shipping_threshold=free_shipping_threshold,
        flat_shipping_fee=flat_shipping_fee,
        tier_hints=tier_hints,
        err=err
    )


@bp_shop_pages.route('/my_orders', methods=['GET', 'POST'])
@check_user_login
def my_orders(user_token:UserToken):
    err = ''
    bll = ShopOrder()
    p_number = http_helper.get_prams_int("p",1)
    data_list, pager = bll.get_by_user_id(p_number, user_token.id)
    temp_data = TempDataProvider(user_id=user_token.id)
    return render_template("my_orders.html", data_list=data_list,pager=pager,err=err,user=user_token,temp_data=temp_data)


@bp_shop_pages.route('/sel_payment', methods=['GET', 'POST'])
@check_user_login
def sel_payment(user_token:UserToken):
    
    order_id = http_helper.get_prams("orderid")
    if not order_id:
        raise Exception("输入的参数不正确!")

    bll = ShopOrder()
    model_order = bll.get_by_order_id(order_id)
    total_price = 0
    freight = 0
    total_amount = 0
    if model_order:
        total_price = Decimal(str(model_order.total_price))
        if total_price <= 0:
            raise Exception("支付金额不能小于等于0!")
        # 读取运费
        if model_order.freight:
            freight = Decimal(str(model_order.freight))
        # 应付总额（含运费）
        if model_order.total_amount:
            total_amount = Decimal(str(model_order.total_amount))
        else:
            total_amount = total_price + freight
    else:
        raise Exception(f"找不到订单：{order_id}")

    payments:[PaymentBase] = current_app.pm.get_by_payment_plugins()

    order_name = f"订单号:{order_id} 时间:{model_order.add_time} 下单人:{model_order.address.get('user_name')}"
    pay_key = eb_utils.md5(f"{order_id}-{total_amount}-{current_app.config['RandomKey']}'")

    return render_template("sel_payment.html",
        pay_key=pay_key,
        order_name=order_name,
        total_price=total_price,
        total_amount=total_amount,
        order_id=order_id,
        payments=payments,
        freight=freight,
        order_model=model_order
    )


# region 管理后台页面
@bp_shop_pages.route('/shop_orders', methods=['GET'])
@check_admin_login
def shop_orders(admin_token:UserToken):

    from bson import ObjectId
    p = http_helper.get_prams_int("p", 1)
    k = http_helper.get_prams("k")
    k = k.strip() if k else ""
    page_size = 20
    rewrite_rule = '/shop/shop_orders?p={{0}}'

    bll = ShopOrder()

    # 构建查询条件：支持多字段模糊搜索
    where = {}
    if k:
        import re
        pattern = {"$regex": re.escape(k), "$options": "i"}
        where["$or"] = [
            {"order_id": pattern},
            {"address.user_name": pattern},
            {"address.phone": pattern},
            {"address.email": pattern},
        ]

    data_list, pager = bll.find_pager(p, page_size, rewrite_rule, where, sort_key="add_time", sort_direction=pymongo.DESCENDING)

    # 预处理数据为模板友好格式
    from datetime import datetime
    items = []
    for item in data_list:
        addr = item.address or {}
        if not isinstance(addr, dict):
            addr = addr.__dict__ if hasattr(addr, '__dict__') else {}
        ts = item.add_time
        if isinstance(ts, (int, float)):
            time_str = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
        elif ts:
            time_str = ts.strftime("%Y-%m-%d %H:%M")
        else:
            time_str = ""
        total_price = float(str(item.total_price)) if item.total_price else 0
        freight = float(str(item.freight)) if item.freight else 0
        products = []
        for p in (item.products or []):
            if isinstance(p, dict):
                products.append({
                    "name": p.get("content_title", ""),
                    "spec": p.get("product_name", ""),
                    "qty": p.get("quantity", 0),
                    "price": float(str(p.get("price", 0))),
                })
        # 时间戳格式化工具函数
        def fmt_time(v):
            if isinstance(v, (int, float)):
                return datetime.fromtimestamp(v).strftime("%Y-%m-%d %H:%M")
            return (v.strftime("%Y-%m-%d %H:%M") if v else "")
        items.append({
            "_id": str(item._id),
            "order_id": item.order_id,
            "user_account": item.user_account,
            "user_name": addr.get("user_name", ""),
            "phone": addr.get("phone", ""),
            "address_info": addr.get("address_info", ""),
            "email": addr.get("email", ""),
            "post_code": addr.get("post_code", ""),
            "products": products,
            "total_price": total_price,
            "freight": freight,
            "payment_name": item.payment_name or "",
            "delivery_name": item.delivery_name or "",
            "delivery_number": item.delivery_number or "",
            "remark": item.remark or "",
            "add_time": time_str,
            "status_name": item.order_statu_name if hasattr(item, 'order_statu_name') else ORDER_STATUS_MAP.get(item.order_status, '未知'),
        })

    return render_template("shop_admin/shop_orders.html", items=items, pager=pager)


@bp_shop_pages.route('/del_order', methods=['GET'])
@check_admin_login
def del_order(admin_token:UserToken):
    """删除订单（物理删除）"""
    oid = http_helper.get_prams("id")
    if oid:
        ShopOrder().delete_by_id(oid)
    return redirect(url_for('bp_shop_pages.shop_orders'))


@bp_shop_pages.route('/level_price', methods=['GET'])
@check_admin_login
def level_price(admin_token:UserToken):

    return render_template("shop_admin/level_price.html")



# endregion
