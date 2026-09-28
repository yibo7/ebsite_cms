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
def cart():
    """
    购物车页面。
    根据配置支持两种模式：
      - cart_force_login=True:  必须登录才能访问（原行为）
      - cart_force_login=False: 未登录用户可作为游客访问
    """
    from eb_modules.eb_shop import bp_shop_pages as _bp
    config = getattr(_bp, 'config', {}) or {}
    cart_force_login = config.get('cart_force_login', True)

    from eb_cache.login_utils import get_token
    user_token = get_token()

    if cart_force_login:
        if not user_token:
            return redirect(url_for('pages_blue.login'))
        return _cart_logged_in(user_token)

    # ── 非强制登录（游客模式） ──
    import uuid
    from flask import make_response

    cart_token = request.cookies.get('cart_token')
    if not cart_token:
        cart_token = str(uuid.uuid4())
    need_set_cookie = not request.cookies.get('cart_token')

    if user_token:
        bll = CartManager(user_id=user_token.id, user_account=user_token.name)
    else:
        bll = CartManager(session_id=cart_token)

    err = ''
    action = http_helper.get_prams_int("action", 0)
    content_id = http_helper.get_prams("cid")
    product_id = http_helper.get_prams("pid")
    quantity = http_helper.get_prams_int("num", 1)

    if action == 2 and content_id and product_id:
        err = bll.update_quantity(content_id, product_id, quantity)
        if not err:
            resp = redirect(url_for('bp_shop_pages.cart'))
            if need_set_cookie:
                resp.set_cookie('cart_token', cart_token, max_age=30*24*3600, path='/')
            return resp
    elif action == 3 and product_id:
        bll.remove_item(product_id)
        resp = redirect(url_for('bp_shop_pages.cart'))
        if need_set_cookie:
            resp.set_cookie('cart_token', cart_token, max_age=30*24*3600, path='/')
        return resp
    elif action == 4:
        bll.clear_cart()
        resp = redirect(url_for('bp_shop_pages.cart'))
        if need_set_cookie:
            resp.set_cookie('cart_token', cart_token, max_age=30*24*3600, path='/')
        return resp

    shopping_cart = bll.get_items()

    total_count = sum(item.quantity for item in shopping_cart)
    total_price = sum(Decimal(str(item.price)) * item.quantity for item in shopping_cart)
    total_price = round(total_price, 2)

    resp = make_response(render_template("shopping_cart.html",
        shopping_cart=shopping_cart, total_count=total_count, total_price=total_price, err=err))
    if need_set_cookie:
        resp.set_cookie('cart_token', cart_token, max_age=30*24*3600, path='/')
    return resp


def _cart_logged_in(user_token):
    """已登录用户的购物车处理（原逻辑）"""
    err = ''
    bll = CartManager(user_id=user_token.id, user_account=user_token.name)
    content_id = http_helper.get_prams("cid")
    product_id = http_helper.get_prams("pid")
    quantity = http_helper.get_prams_int("num", 1)
    action = http_helper.get_prams_int("action", 0)

    if action == 2 and content_id and product_id:
        err = bll.update_quantity(content_id, product_id, quantity)
        if not err:
            return redirect(url_for('bp_shop_pages.cart'))
    elif action == 3 and product_id:
        bll.remove_item(product_id)
        return redirect(url_for('bp_shop_pages.cart'))
    elif action == 4:
        bll.clear_cart()
        return redirect(url_for('bp_shop_pages.cart'))

    shopping_cart = bll.get_items()
    total_count = sum(item.quantity for item in shopping_cart)
    total_price = sum(Decimal(str(item.price)) * item.quantity for item in shopping_cart)
    total_price = round(total_price, 2)
    return render_template("shopping_cart.html",
        shopping_cart=shopping_cart, total_count=total_count, total_price=total_price, err=err)


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




# region 阶梯价模板管理

@bp_shop_pages.route('/price_template_list', methods=['GET'])
@check_admin_login
def price_template_list(admin_token: UserToken):
    """模板列表"""
    from eb_modules.eb_shop.datas.price_template import get_template_list
    templates = get_template_list()
    # 读取 URL 中传递的消息
    msg = request.args.get('_msg', '')
    msg_type = request.args.get('_msg_type', 'success')
    return render_template("shop_admin/price_template_list.html", templates=templates,
                           _msg=msg, _msg_type=msg_type)


@bp_shop_pages.route('/price_template_form', methods=['GET', 'POST'])
@bp_shop_pages.route('/price_template_form/<template_id>', methods=['GET', 'POST'])
@check_admin_login
def price_template_form(admin_token: UserToken, template_id=None):
    """新建 / 编辑模板"""
    from eb_modules.eb_shop.datas.price_template import (
        get_template, create_template, update_template,
        validate_template, parse_tiers_from_form,
        get_product_categories, get_sample_product
    )

    template = None
    if template_id:
        template = get_template(template_id)

    categories = get_product_categories()

    # 当前选中的分类 ID
    selected_category_id = None
    if template:
        selected_category_id = template.get('category_id', '')

    errors = []

    if request.method == 'POST':
        # 获取表单数据
        name = request.form.get('name', '').strip()
        category_id = request.form.get('category_id', '').strip()
        pricing_base = request.form.get('pricing_base', 'market_price')
        tiers = parse_tiers_from_form(request.form)

        data = {
            'name': name,
            'category_id': category_id,
            'pricing_base': pricing_base,
            'tiers': tiers,
        }

        # 校验
        errors = validate_template(data)
        if errors:
            sample_product = None
            if category_id:
                sample_product = get_sample_product(category_id)
            return render_template(
                "shop_admin/price_template_form.html",
                template=data,
                template_id=template_id,
                categories=categories,
                selected_category_id=category_id,
                sample_product=sample_product,
                _errors=errors,
            )

        if template_id:
            # 更新
            update_template(template_id, data)
            return redirect(url_for('bp_shop_pages.price_template_list',
                                    _msg='模板已更新', _msg_type='success'))
        else:
            # 创建
            new_id = create_template(data, str(admin_token.id))
            return redirect(url_for('bp_shop_pages.price_template_form', template_id=new_id,
                                    _msg='模板已创建', _msg_type='success'))

    # GET
    selected_category_id = selected_category_id or request.args.get('category_id', '')
    sample_product = None
    if selected_category_id:
        sample_product = get_sample_product(selected_category_id)

    return render_template(
        "shop_admin/price_template_form.html",
        template=template,
        categories=categories,
        selected_category_id=selected_category_id,
        sample_product=sample_product,
        _errors=errors,
    )


@bp_shop_pages.route('/price_template_delete/<template_id>', methods=['POST'])
@check_admin_login
def price_template_delete(admin_token: UserToken, template_id):
    """删除模板"""
    from eb_modules.eb_shop.datas.price_template import delete_template
    if delete_template(template_id):
        return redirect(url_for('bp_shop_pages.price_template_list',
                                _msg='模板已删除', _msg_type='success'))
    else:
        return redirect(url_for('bp_shop_pages.price_template_list',
                                _msg='模板删除失败', _msg_type='danger'))


@bp_shop_pages.route('/price_template_copy/<template_id>', methods=['POST'])
@check_admin_login
def price_template_copy(admin_token: UserToken, template_id):
    """复制模板"""
    from eb_modules.eb_shop.datas.price_template import copy_template
    new_id = copy_template(template_id, str(admin_token.id))
    if new_id:
        return redirect(url_for('bp_shop_pages.price_template_form', template_id=new_id,
                                _msg='模板已复制，请修改名称和系数', _msg_type='success'))
    else:
        return redirect(url_for('bp_shop_pages.price_template_list',
                                _msg='模板复制失败', _msg_type='danger'))


@bp_shop_pages.route('/price_template_apply/<template_id>', methods=['GET', 'POST'])
@check_admin_login
def price_template_apply(admin_token: UserToken, template_id):
    """应用模板确认与执行"""
    from eb_modules.eb_shop.datas.price_template import (
        get_template, apply_template_to_category,
        count_products_in_category
    )

    template = get_template(template_id)
    if not template:
        return redirect(url_for('bp_shop_pages.price_template_list',
                                _msg='模板不存在', _msg_type='danger'))

    # 获取分类名称
    category_name = ''
    from bson import ObjectId
    cat_id = template.get('category_id', '')
    if cat_id:
        try:
            from bll.new_class import NewsClass
            cat = NewsClass().find_one_by_id(cat_id)
            if cat:
                category_name = cat.class_name
        except Exception:
            pass

    product_count = count_products_in_category(cat_id) if cat_id else 0

    if request.method == 'POST':
        apply_mode = request.form.get('apply_mode', 'fill_empty')
        if apply_mode not in ('fill_empty', 'force_overwrite'):
            return redirect(url_for('bp_shop_pages.price_template_apply', template_id=template_id,
                                    _msg='应用方式不合法', _msg_type='danger'))

        admin_name = getattr(admin_token, 'name', '') or ''

        result = apply_template_to_category(
            template_id, apply_mode,
            str(admin_token.id), admin_name
        )

        if result['success']:
            log_id = result.get('log_id')
            if log_id:
                return redirect(url_for('bp_shop_pages.price_template_log_detail', log_id=log_id,
                                        _msg=result['message'], _msg_type='success'))
            return redirect(url_for('bp_shop_pages.price_template_log',
                                    _msg=result['message'], _msg_type='success'))
        else:
            return redirect(url_for('bp_shop_pages.price_template_apply', template_id=template_id,
                                    _msg=result['message'], _msg_type='danger'))

    _msg = request.args.get('_msg', '')
    _msg_type = request.args.get('_msg_type', 'danger')
    return render_template(
        "shop_admin/price_template_apply.html",
        template=template,
        category_name=category_name,
        product_count=product_count,
        _msg=_msg, _msg_type=_msg_type,
    )


@bp_shop_pages.route('/price_template_log', methods=['GET'])
@check_admin_login
def price_template_log(admin_token: UserToken):
    """应用日志列表"""
    from eb_modules.eb_shop.datas.price_template_log import get_log_list
    logs = get_log_list()
    msg = request.args.get('_msg', '')
    msg_type = request.args.get('_msg_type', 'success')
    return render_template("shop_admin/price_template_log.html", logs=logs,
                           _msg=msg, _msg_type=msg_type)


@bp_shop_pages.route('/price_template_log_detail/<log_id>', methods=['GET'])
@check_admin_login
def price_template_log_detail(admin_token: UserToken, log_id):
    """日志详情"""
    from eb_modules.eb_shop.datas.price_template_log import get_log
    log = get_log(log_id)
    msg = request.args.get('_msg', '')
    msg_type = request.args.get('_msg_type', 'success')
    return render_template("shop_admin/price_template_log_detail.html", log=log,
                           _msg=msg, _msg_type=msg_type)

# endregion

# region 会员价模板管理

@bp_shop_pages.route('/member_price_template_list', methods=['GET'])
@check_admin_login
def member_price_template_list(admin_token: UserToken):
    """会员价模板列表"""
    from eb_modules.eb_shop.datas.member_price_template import get_template_list
    templates = get_template_list()
    msg = request.args.get('_msg', '')
    msg_type = request.args.get('_msg_type', 'success')
    return render_template("shop_admin/member_price_template/list.html", templates=templates,
                           _msg=msg, _msg_type=msg_type)


@bp_shop_pages.route('/member_price_template_form', methods=['GET', 'POST'])
@bp_shop_pages.route('/member_price_template_form/<template_id>', methods=['GET', 'POST'])
@check_admin_login
def member_price_template_form(admin_token: UserToken, template_id=None):
    """新建 / 编辑会员价模板"""
    from eb_modules.eb_shop.datas.member_price_template import (
        get_template, create_template, update_template,
        validate_template, parse_group_rates_from_form,
        get_product_categories, get_sample_product,
        get_all_member_groups,
    )

    template = None
    if template_id:
        template = get_template(template_id)

    categories = get_product_categories()
    member_groups = get_all_member_groups()

    # 当前选中的分类 ID
    selected_category_id = None
    if template:
        selected_category_id = template.get('category_id', '')

    errors = []

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        category_id = request.form.get('category_id', '').strip()
        pricing_base = request.form.get('pricing_base', 'market_price')

        # 构建 group_rates：合并表单提交的系数与已有会员组信息
        raw_rates = parse_group_rates_from_form(request.form)
        # 用所有会员组补齐 group_name
        group_map = {g['group_id']: g['group_name'] for g in member_groups}
        group_rates = []
        for r in raw_rates:
            gid = r['group_id']
            if gid in group_map:
                r['group_name'] = group_map[gid]
            group_rates.append(r)

        data = {
            'name': name,
            'category_id': category_id,
            'pricing_base': pricing_base,
            'group_rates': group_rates,
        }

        errors = validate_template(data)
        if errors:
            sample_product = None
            if category_id:
                sample_product = get_sample_product(category_id)
            # 把用户输入的系数合并回 member_groups
            rate_map = {r['group_id']: r['rate'] for r in group_rates}
            for g in member_groups:
                g['rate'] = rate_map.get(g['group_id'])
            return render_template(
                "shop_admin/member_price_template/form.html",
                template=data,
                template_id=template_id,
                categories=categories,
                member_groups=member_groups,
                selected_category_id=category_id,
                sample_product=sample_product,
                _errors=errors,
            )

        if template_id:
            update_template(template_id, data)
            return redirect(url_for('bp_shop_pages.member_price_template_list',
                                    _msg='会员价模板已更新', _msg_type='success'))
        else:
            new_id = create_template(data, str(admin_token.id))
            return redirect(url_for('bp_shop_pages.member_price_template_form', template_id=new_id,
                                    _msg='会员价模板已创建', _msg_type='success'))

    # GET
    selected_category_id = selected_category_id or request.args.get('category_id', '')
    sample_product = None
    if selected_category_id:
        sample_product = get_sample_product(selected_category_id)

    # 把模板中已有的系数合并到 member_groups
    if template:
        template_rates = template.get('group_rates', []) or []
        rate_map = {r['group_id']: r['rate'] for r in template_rates}
        for g in member_groups:
            g['rate'] = rate_map.get(g['group_id'])

    return render_template(
        "shop_admin/member_price_template/form.html",
        template=template,
        categories=categories,
        member_groups=member_groups,
        selected_category_id=selected_category_id,
        sample_product=sample_product,
        _errors=errors,
    )


@bp_shop_pages.route('/member_price_template_delete/<template_id>', methods=['POST'])
@check_admin_login
def member_price_template_delete(admin_token: UserToken, template_id):
    """删除会员价模板"""
    from eb_modules.eb_shop.datas.member_price_template import delete_template
    if delete_template(template_id):
        return redirect(url_for('bp_shop_pages.member_price_template_list',
                                _msg='会员价模板已删除', _msg_type='success'))
    else:
        return redirect(url_for('bp_shop_pages.member_price_template_list',
                                _msg='会员价模板删除失败', _msg_type='danger'))


@bp_shop_pages.route('/member_price_template_copy/<template_id>', methods=['POST'])
@check_admin_login
def member_price_template_copy(admin_token: UserToken, template_id):
    """复制会员价模板"""
    from eb_modules.eb_shop.datas.member_price_template import copy_template
    new_id = copy_template(template_id, str(admin_token.id))
    if new_id:
        return redirect(url_for('bp_shop_pages.member_price_template_form', template_id=new_id,
                                _msg='会员价模板已复制，请修改名称和系数', _msg_type='success'))
    else:
        return redirect(url_for('bp_shop_pages.member_price_template_list',
                                _msg='会员价模板复制失败', _msg_type='danger'))


@bp_shop_pages.route('/member_price_template_apply/<template_id>', methods=['GET', 'POST'])
@check_admin_login
def member_price_template_apply(admin_token: UserToken, template_id):
    """应用会员价模板确认与执行"""
    from eb_modules.eb_shop.datas.member_price_template import (
        get_template, apply_template_to_category,
        count_products_in_category
    )

    template = get_template(template_id)
    if not template:
        return redirect(url_for('bp_shop_pages.member_price_template_list',
                                _msg='模板不存在', _msg_type='danger'))

    # 分类名称
    category_name = ''
    cat_id = template.get('category_id', '')
    if cat_id:
        try:
            from bll.new_class import NewsClass
            cat = NewsClass().find_one_by_id(cat_id)
            if cat:
                category_name = cat.class_name
        except Exception:
            pass

    product_count = count_products_in_category(cat_id) if cat_id else 0

    # 有系数的会员组数
    group_rates = template.get('group_rates', []) or []
    group_count = sum(1 for g in group_rates if g.get('rate') is not None and g['rate'] != '')

    if request.method == 'POST':
        apply_mode = request.form.get('apply_mode', 'fill_empty')
        below_cost_strategy = request.form.get('below_cost_strategy', 'skip')

        if apply_mode not in ('fill_empty', 'force_overwrite'):
            return redirect(url_for('bp_shop_pages.member_price_template_apply', template_id=template_id,
                                    _msg='应用方式不合法', _msg_type='danger'))
        if below_cost_strategy not in ('skip', 'floor_to_cost', 'reject_all'):
            return redirect(url_for('bp_shop_pages.member_price_template_apply', template_id=template_id,
                                    _msg='低于成本价策略不合法', _msg_type='danger'))

        admin_name = getattr(admin_token, 'name', '') or ''

        result = apply_template_to_category(
            template_id, apply_mode, below_cost_strategy,
            str(admin_token.id), admin_name
        )

        if result['success']:
            log_id = result.get('log_id')
            if log_id:
                return redirect(url_for('bp_shop_pages.member_price_template_log_detail', log_id=log_id,
                                        _msg=result['message'], _msg_type='success'))
            return redirect(url_for('bp_shop_pages.member_price_template_log',
                                    _msg=result['message'], _msg_type='success'))
        else:
            return redirect(url_for('bp_shop_pages.member_price_template_apply', template_id=template_id,
                                    _msg=result['message'], _msg_type='danger'))

    _msg = request.args.get('_msg', '')
    _msg_type = request.args.get('_msg_type', 'danger')
    return render_template(
        "shop_admin/member_price_template/apply.html",
        template=template,
        category_name=category_name,
        product_count=product_count,
        group_count=group_count,
        _msg=_msg, _msg_type=_msg_type,
    )


@bp_shop_pages.route('/member_price_template_log', methods=['GET'])
@check_admin_login
def member_price_template_log(admin_token: UserToken):
    """会员价应用日志列表"""
    from eb_modules.eb_shop.datas.member_price_template_log import get_log_list
    logs = get_log_list()
    msg = request.args.get('_msg', '')
    msg_type = request.args.get('_msg_type', 'success')
    return render_template("shop_admin/member_price_template/log.html", logs=logs,
                           _msg=msg, _msg_type=msg_type)


@bp_shop_pages.route('/member_price_template_log_detail/<log_id>', methods=['GET'])
@check_admin_login
def member_price_template_log_detail(admin_token: UserToken, log_id):
    """会员价日志详情"""
    from eb_modules.eb_shop.datas.member_price_template_log import get_log
    log = get_log(log_id)
    msg = request.args.get('_msg', '')
    msg_type = request.args.get('_msg_type', 'success')
    return render_template("shop_admin/member_price_template/log_detail.html", log=log,
                           _msg=msg, _msg_type=msg_type)

# endregion
