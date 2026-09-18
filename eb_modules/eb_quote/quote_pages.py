import time
from decimal import Decimal

import pymongo
from flask import jsonify, current_app, render_template, redirect, request, url_for
from bll.temp_data_provider import TempDataProvider
from decorators import check_admin_login, check_user_login
from . import bp_quote_pages
from .datas.quote_record import ShopQuoteRecord, QUOTE_STATUS, STATUS_CLASS
from eb_utils import http_helper
from entity.user_token import UserToken

# ═════════════════════════════════════════════════════════════════
#  报价单页面（无需登录，可分享）
# ═════════════════════════════════════════════════════════════════
@bp_quote_pages.route('/quote/<record_id>', methods=['GET'])
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
        "discount_rate": float(getattr(model, "discount_rate", 0.10)),
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


@bp_quote_pages.route('/quote/<record_id>/contact', methods=['POST'])
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
    return redirect(url_for('bp_quote_pages.quote_view', record_id=record_id) + f"?s={s}{sep}")


def _fmt_time(ts):
    """时间戳 → 可读字符串"""
    if not ts:
        return ""
    if isinstance(ts, (int, float)):
        from datetime import datetime
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
    return str(ts)[:16]


# region 管理后台页面

@bp_quote_pages.route('/my_quotes', methods=['GET'])
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


@bp_quote_pages.route('/shop_quotes', methods=['GET'])
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


@bp_quote_pages.route('/shop_quote_update_status', methods=['GET'])
@check_admin_login
def shop_quote_update_status(admin_token: UserToken):
    """更新报价单状态（后台）"""
    record_id = http_helper.get_prams("record_id") or ""
    status = http_helper.get_prams("status") or ""
    reason = http_helper.get_prams("reason") or ""

    if record_id and status in QUOTE_STATUS:
        bll = ShopQuoteRecord()
        bll.update_status(record_id, status, reason)

    return redirect(url_for('bp_quote_pages.shop_quotes'))
# endregion
