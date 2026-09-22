import time
from decimal import Decimal

import pymongo
from flask import jsonify, current_app, render_template, redirect, request, url_for
from bll.temp_data_provider import TempDataProvider
from decorators import check_admin_login, check_user_login
from . import bp_ai_cart_pages
from .datas.quote_record import ShopQuoteRecord, QUOTE_STATUS, STATUS_CLASS
from eb_utils import http_helper
from entity.user_token import UserToken

# ═════════════════════════════════════════════════════════════════
#  报价单页面（无需登录，可分享）
# ═════════════════════════════════════════════════════════════════

@bp_ai_cart_pages.route('/', methods=['GET', 'POST'])
def credits_index():
    return redirect('ask/index.html')

@bp_ai_cart_pages.route('/quote/<record_id>', methods=['GET'])
def quote_view(record_id: str):
    """查看报价单"""
    bll = ShopQuoteRecord()
    model = bll.get_by_record_id(record_id)

    if not model:
        return render_template("quote_record.html", quote=None, record_id=record_id)

    # 转换为模板友好的格式
    items = []
    for p in (model.items or []):
        unit_price = float(p.get("unit_price", 0)) if not isinstance(p.get("unit_price"), str) else 0
        qty = int(p.get("qty", 1))
        items.append({
            "title": p.get("title", ""),
            "spec": p.get("spec", ""),
            "small_pic": p.get("small_pic", ""),
            "sku": p.get("sku", ""),
            "url": p.get("url", ""),
            "remarks": p.get("remarks", ""),
            "class_name": p.get("class_name", ""),
            "market_price": float(p.get("market_price", 0)),
            "qty": qty,
            "unit_price": unit_price,
            "subtotal": round(unit_price * qty, 2),
        })

    def _to_float(v):
        if v is None:
            return 0.0
        if isinstance(v, Decimal):
            return float(v)
        return float(str(v))

    quote_data = {
        "record_id": model.record_id,
        "products": items,
        "item_count": getattr(model, "item_count", len(items)),
        "total_qty": getattr(model, "total_qty", sum(i["qty"] for i in items)),
        "total_original": _to_float(getattr(model, "total_original", 0)),
        "total_discount": _to_float(getattr(model, "total_discount", 0)),
        "total_final": _to_float(getattr(model, "total_final", 0)),
        "discount_rate": float(getattr(model, "discount_rate", 0)),
        "add_time_str": _fmt_time(getattr(model, "add_time", None)),
        "contact": getattr(model, "contact", None) or {},
        "user_account": getattr(model, "user_account", ""),
        "status": getattr(model, "status", "pending_review"),
        "status_name": QUOTE_STATUS.get(getattr(model, "status", ""), "未知"),
    }

    # 判断当前访客是否是创建人（优先登录状态，其次 sessionId）
    from eb_cache import login_utils
    user_token = login_utils.get_token()
    model_user_id = getattr(model, "user_id", "")
    model_session_id = getattr(model, "session_id", "")

    if user_token and model_user_id and str(user_token.id) == model_user_id:
        is_owner = True
    else:
        caller_session = request.args.get("s", "")
        is_owner = bool(caller_session) and caller_session == model_session_id

    has_contact = bool(quote_data["contact"].get("name") or quote_data["contact"].get("phone"))

    return render_template(
        "quote_record.html", quote=quote_data, record_id=record_id,
        is_owner=is_owner, contact_submitted=has_contact
    )


@bp_ai_cart_pages.route('/quote/<record_id>/contact', methods=['POST'])
def quote_contact(record_id: str):
    """客户提交联系方式"""
    contact = {
        "name": request.form.get("name", "").strip(),
        "phone": request.form.get("phone", "").strip(),
        "email": request.form.get("email", "").strip(),
        "company": request.form.get("company", "").strip(),
        "address": request.form.get("address", "").strip(),
        "remark": request.form.get("remark", "").strip(),
    }

    bll = ShopQuoteRecord()
    bll.update_contact(record_id, contact)

    # 重新渲染页面，保持 session 参数
    s = request.args.get("s", "")
    sep = "&" if s else ""
    return redirect(url_for('bp_ai_cart_pages.quote_view', record_id=record_id) + f"?s={s}{sep}")


def _fmt_time(ts):
    """时间戳 → 可读字符串"""
    if not ts:
        return ""
    if isinstance(ts, (int, float)):
        from datetime import datetime
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
    return str(ts)[:16]


# region 管理后台页面

@bp_ai_cart_pages.route('/my_quotes', methods=['GET'])
@check_user_login
def my_quotes(user_token: UserToken):
    """我的报价单（个人中心）"""
    p = http_helper.get_prams_int("p", 1)
    page_size = 20

    bll = ShopQuoteRecord()
    user_id = str(user_token.id)
    data_list, pager = bll.find_by_user(user_id, p, page_size)

    items = []
    for item in data_list:
        ts = item.add_time
        if isinstance(ts, (int, float)):
            from datetime import datetime
            time_str = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
        else:
            time_str = str(ts)[:16] if ts else ""
        items.append({
            "record_id": item.record_id,
            "status": item.status,
            "status_name": QUOTE_STATUS.get(item.status, item.status),
            "total_final": float(item.total_final) if item.total_final else 0,
            "item_count": item.item_count,
            "total_qty": item.total_qty,
            "contact": getattr(item, "contact", {}) or {},
            "fail_reason": getattr(item, "fail_reason", ""),
            "add_time_str": time_str,
        })
    temp_data = TempDataProvider(user_id=user_token.id)
    return render_template("my_quotes.html", items=items, pager=pager,temp_data=temp_data)


@bp_ai_cart_pages.route('/shop_quotes', methods=['GET'])
@check_admin_login
def shop_quotes(admin_token: UserToken):
    """报价单管理（后台）"""
    p = http_helper.get_prams_int("p", 1)
    k = http_helper.get_prams("k") or ""
    k = k.strip()
    page_size = 20

    bll = ShopQuoteRecord()
    data_list, pager = bll.find_all_pager(p, page_size, k)

    items = []
    for item in data_list:
        ts = item.add_time
        if isinstance(ts, (int, float)):
            from datetime import datetime
            time_str = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
        else:
            time_str = str(ts)[:16] if ts else ""
        items.append({
            "record_id": item.record_id,
            "status": item.status,
            "status_name": QUOTE_STATUS.get(item.status, item.status),
            "status_class": STATUS_CLASS.get(item.status, "default"),
            "user_account": getattr(item, "user_account", ""),
            "contact": getattr(item, "contact", {}) or {},
            "product_list": [{
                "title": p.get("title", ""),
                "spec": p.get("spec", ""),
                "small_pic": p.get("small_pic", ""),
                "sku": p.get("sku", ""),
                "url": p.get("url", ""),
                "remarks": p.get("remarks", ""),
                "class_name": p.get("class_name", ""),
                "market_price": float(p.get("market_price", 0)),
                "qty": p.get("qty", 0),
                "unit_price": float(p.get("unit_price", 0)),
                "subtotal": float(p.get("subtotal", 0)),
            } for p in (item.items or [])],
            "total_original": float(item.total_original or 0),
            "total_discount": float(item.total_discount or 0),
            "total_final": float(item.total_final or 0),
            "discount_percent": int((item.discount_rate or 0) * 100),
            "fail_reason": getattr(item, "fail_reason", ""),
            "add_time_str": time_str,
        })

    return render_template("shop_admin/quote_admin.html", items=items, pager=pager)


@bp_ai_cart_pages.route('/shop_quote_update_status', methods=['GET'])
@check_admin_login
def shop_quote_update_status(admin_token: UserToken):
    """更新报价单状态（后台）"""
    record_id = http_helper.get_prams("record_id") or ""
    status = http_helper.get_prams("status") or ""
    reason = http_helper.get_prams("reason") or ""

    if record_id and status in QUOTE_STATUS:
        bll = ShopQuoteRecord()
        bll.update_status(record_id, status, reason)

    return redirect(url_for('bp_ai_cart_pages.shop_quotes'))


@bp_ai_cart_pages.route('/shop_quote_prompts', methods=['GET', 'POST'])
@check_admin_login
def shop_quote_prompts(admin_token: UserToken):
    """AI 提示词配置（后台）"""
    from .datas.prompts_config import ShopQuotePrompts

    bll = ShopQuotePrompts()
    config = bll.get_config()

    if request.method == 'POST':
        data = {
            "shop_name": request.form.get("shop_name", "").strip(),
            "welcome_message": request.form.get("welcome_message", "").strip(),
            "extract_prompt": request.form.get("extract_prompt", "").strip(),
            "sales_prompt_tpl": request.form.get("sales_prompt_tpl", "").strip(),
            "guide_prompt": request.form.get("guide_prompt", "").strip(),
        }
        bll.save_config(data)

        return redirect(url_for('bp_ai_cart_pages.shop_quote_prompts', saved=1))

    saved = bool(request.args.get("saved", False))

    # 从当前 Handler 加载品类默认值作为展示提示
    from .ai_handlers import get_ai_handler
    handler = get_ai_handler()

    return render_template(
        "shop_admin/prompts_config.html",
        config=config, saved=saved,
        defaults={
            "shop_name": getattr(handler, "default_shop_name", ""),
            "welcome_message": getattr(handler, "default_welcome_message", ""),
            "extract_prompt": getattr(handler, "default_extract_prompt", ""),
            "sales_prompt_tpl": getattr(handler, "default_sales_prompt_tpl", ""),
            "guide_prompt": getattr(handler, "default_guide_prompt", ""),
        }
    )
# endregion
