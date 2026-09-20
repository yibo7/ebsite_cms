import os
import re
import uuid
import hashlib
import base64
import json
import pymongo
from flask import jsonify, current_app, send_from_directory, request, url_for

from decorators import check_user_login
from . import bp_quote_apis

from entity.user_token import UserToken


# ─────────────────────────────────────────────────────────────────
#  智能报价系统 API
# ─────────────────────────────────────────────────────────────────


# ═════════════════════════════════════════════════════════════════
#  提示词加载 — 从 MongoDB 读取，回退到当前 Handler 的默认值
# ═════════════════════════════════════════════════════════════════

def _get_prompt(field: str) -> str:
    """
    从数据库加载提示词配置，DB 中无配置则回退到当前 Handler 的默认值

    @param field: 字段名 extract_prompt / sales_prompt_tpl / guide_prompt / shop_name / welcome_message
    @return: 提示词文本
    """
    from .datas.prompts_config import ShopQuotePrompts
    from .ai_handlers import get_ai_handler

    # 优先读取 DB
    value = ShopQuotePrompts().get_field(field)
    if value:
        return value

    # 回退到当前 Handler 的出厂默认值
    handler = get_ai_handler()
    default_attr = f"default_{field}"
    return getattr(handler, default_attr, "")


@bp_quote_apis.route('quote/welcome', methods=['GET'])
def quote_welcome():
    """返回可配置的欢迎语与店铺名称"""
    welcome = _get_prompt("welcome_message")
    shop_name = _get_prompt("shop_name") or "Green Rich"
    return jsonify({"welcome": welcome, "shop_name": shop_name})


@bp_quote_apis.route('quote/chat', methods=['POST'])
def quote_chat():
    """
    AI 智能报价对话（核心 API）— 提取 → 搜索 → 回复

    流程：
    1. AI 提取参数（极小提示词，已打印到日志）
       → 提取到至少部分信息 → 搜索
       → 完全提取不到 → 引导用户
    2. 后端搜索（有部分信息也模糊搜）
    3. AI 写文案：精确→销售；模糊→"你看是不是这些？"
    """
    import json
    import time
    from .ai_providers import get_provider

    data = request.get_json() or {}
    messages = data.get('messages', [])
    if not messages:
        return jsonify({"reply": "请问您需要什么商品？😊", "matches": []})

    user_msgs = [m["content"] for m in messages if m.get("role") == "user"]
    latest_msg = user_msgs[-1] if user_msgs else ""
    provider = get_provider()

    # ── Step 1: AI 提取产品参数 ──
    t0 = time.time()
    try:
        extract_result = provider.chat(
            [{"role": "user", "content": latest_msg}], _get_prompt("extract_prompt")
        )
    except Exception as e:
        current_app.logger.error(f"提取异常: {e}")
        extract_result = {"ok": False, "partial": False}
    if not isinstance(extract_result, dict):
        extract_result = {"ok": False, "partial": False}
    t1 = time.time()
    current_app.logger.warning(f"[⏱ 提取] {(t1-t0)*1000:.0f}ms | {json.dumps(extract_result, ensure_ascii=False)}")

    from .ai_handlers import get_ai_handler
    handler = get_ai_handler()

    # 调试：打印当前使用的提示词前 100 字符
    ep = _get_prompt("extract_prompt")
    current_app.logger.warning(f"[DEBUG extract_prompt 前100字] {ep[:100]}")
    gp = _get_prompt("guide_prompt")
    current_app.logger.warning(f"[DEBUG guide_prompt 前100字] {gp[:100]}")
    sp = _get_prompt("sales_prompt_tpl")
    current_app.logger.warning(f"[DEBUG sales_prompt_tpl 前100字] {sp[:100]}")

    # 完全提取不到（ok=false 且 partial=false）→ 引导客户
    # 注意：partial=true 表示有部分参数（如只有品牌），应继续搜索
    if not extract_result.get("ok") and not extract_result.get("partial"):
        try:
            t_guide_start = time.time()
            guide_result = provider.chat(
                [{"role": "user", "content": latest_msg}],
                _get_prompt("guide_prompt").format(user_msg=latest_msg[:300])
            )
            current_app.logger.warning(f"[⏱ 引导] {(time.time()-t_guide_start)*1000:.0f}ms")
            if isinstance(guide_result, dict) and guide_result.get("reply"):
                return jsonify({"reply": guide_result["reply"], "matches": []})
        except Exception as e:
            current_app.logger.error(f"引导异常: {e}")
        # 兜底
        return jsonify({"reply": handler.guide_fallback_reply(), "matches": []})

    # ── Step 2: 搜索商品（由品类 Handler 实现）──
    t2 = time.time()
    matched_products = handler.search(extract_result)
    current_app.logger.warning(f"[⏱ 搜索] {(time.time()-t2)*1000:.0f}ms → {len(matched_products)} 个")

    if not matched_products:
        current_app.logger.warning(f"[⏱ 总耗时] {(time.time()-t0)*1000:.0f}ms")
        return jsonify({"reply": handler.no_result_reply(extract_result), "matches": []})

    # ── Step 3: AI 写文案 ──
    found_lines = [f"- {p['title']} | ¥{p['unit_price']}" for p in matched_products]
    found_text = "\n".join(found_lines)

    ci = handler.build_custom_instruction(extract_result, bool(extract_result.get("ok")))

    sales_prompt = _get_prompt("sales_prompt_tpl").format(
        shop_name=_get_prompt("shop_name"),
        user_query=latest_msg[:200], found_products=found_text, custom_instruction=ci
    )

    try:
        t3 = time.time()
        sales_result = provider.chat(messages, sales_prompt)
        current_app.logger.warning(f"[⏱ 文案] {(time.time()-t3)*1000:.0f}ms")
        if not isinstance(sales_result, dict):
            sales_result = {"reply": str(sales_result)}
    except Exception as e:
        current_app.logger.error(f"文案异常: {e}")
        sales_result = {"reply": ""}

    matches = []
    for p in matched_products:
        matches.append({
            "title": p.get("title", ""),
            "small_pic": p.get("small_pic", ""),
            "unit_price": p.get("unit_price", 0),
            "market_price": p.get("market_price", 0),
            "class_name": p.get("class_name", ""),
            "sku": p.get("sku", ""),
            "url": p.get("url", ""),
            "remarks": p.get("remarks", ""),
            "qty": 1,
        })

    if not sales_result.get("reply"):
        sales_result["reply"] = (
            f"<p>为您找到以下产品：</p>"
            + "".join(f"<p>• {p['title']} <strong>¥{p['unit_price']}</strong></p>"
                     for p in matched_products[:3])
            + "<p>点击 <strong>[+]</strong> 加入询价单，可在其中修改数量。</p>"
        )

    sales_result["matches"] = matches
    current_app.logger.warning(f"[⏱ 总耗时] {(time.time()-t0)*1000:.0f}ms")
    return jsonify(sales_result)


@bp_quote_apis.route('quote/save_record', methods=['POST'])
def quote_save_record():
    """
    保存客户的询价记录（不保存完整对话，只保存最终询价单）

    请求体（JSON）：
    {
        "sessionId": "浏览器生成的UUID",
        "items": [
            {"content_id": "...", "product_id": "...", "qty": 10,
             "title": "佳能IR1730鼓芯", "price": 20.0}
        ],
        "summary": "佳能IR1730×10支, 东芝2505×15支",
        "total": 350.0
    }

    返回：{ "code": 0, "msg": "保存成功" }
    """
    from datetime import datetime

    data = request.get_json() or {}

    record = {
        "session_id": data.get("sessionId", ""),
        "items": data.get("items", []),
        "summary": data.get("summary", ""),
        "total": float(data.get("total", 0)),
        "user_agent": request.headers.get("User-Agent", "")[:256],
        "ip": request.remote_addr or "",
        "created_at": datetime.now(),
    }

    try:
        db = current_app.db
        db["ShopQuoteRecord"].insert_one(record)
        return jsonify({"code": 0, "msg": "保存成功"})
    except Exception as e:
        current_app.logger.error(f"保存询价记录失败: {e}")
        return jsonify({"code": -1, "msg": "保存失败"})


@bp_quote_apis.route('quote/submit_order', methods=['POST'])
@check_user_login
def quote_submit_order(user_token: UserToken):
    """
    将询价单转为正式订单（需要登录）

    请求体（JSON）：
    {
        "items": [
            {"content_id": "NewsContent的_id", "product_id": "规格的productId", "qty": 10}
        ]
    }

    返回：{ "code": 0, "msg": "已加入购物车" }
    """
    from eb_modules.eb_shop.datas.cart_manger import CartManager

    data = request.get_json() or {}
    items = data.get("items", [])

    if not items:
        return jsonify({"code": -1, "msg": "没有商品"})

    mgr = CartManager(user_token.id, user_token.name)
    errors = []

    for item in items:
        err = mgr.add_item(
            content_id=item["content_id"],
            product_id=item["product_id"],
            quantity=int(item.get("qty", 1))
        )
        if err:
            errors.append(err)

    if errors:
        return jsonify({"code": -1, "msg": "部分商品添加失败: " + "; ".join(errors)})

    return jsonify({"code": 0, "msg": "已加入购物车，请前往结算"})


@bp_quote_apis.route('quote/submit', methods=['POST'])
def quote_submit():
    """
    生成报价单（无需登录）

    请求体（JSON）：
    {
        "sessionId": "...",
        "items": [
            {"content_id": "...", "qty": 10, "title": "...", "price": 20.0, "spec": ""}
        ],
        "discount_rate": 0.10
    }

    返回：{"code": 0, "record_id": "QRxxxxxx", "url": "/shop/quote/QRxxxxxx"}
    """
    from .datas.quote_record import ShopQuoteRecord
    from eb_cache import login_utils

    data = request.get_json() or {}
    items_raw = data.get("items", [])
    if not items_raw:
        return jsonify({"code": -1, "msg": "询价单为空"})

    discount_rate = float(data.get("discount_rate", 0.10))
    session_id = data.get("sessionId", "")

    # 尝试获取登录用户信息
    user_token = login_utils.get_token()
    if user_token:
        user_id = str(user_token.id)
        user_account = user_token.name
    else:
        user_id = ""
        user_account = session_id

    # 构建产品明细（统一使用标准化数据结构）
    items = []
    total_original = 0.0
    for item in items_raw:
        unit_price = float(item.get("unit_price", item.get("price", 0)))
        qty = int(item.get("qty", 1))
        subtotal = round(unit_price * qty, 2)
        total_original += subtotal
        items.append({
            "title": item.get("title", ""),
            "small_pic": item.get("small_pic", ""),
            "unit_price": unit_price,
            "market_price": float(item.get("market_price", 0)),
            "class_name": item.get("class_name", ""),
            "sku": item.get("sku", ""),
            "url": item.get("url", ""),
            "remarks": item.get("remarks", ""),
            "qty": qty,
            "subtotal": subtotal,
        })

    total_discount = round(total_original * discount_rate, 2)
    total_final = round(total_original - total_discount, 2)

    # 保存到数据库
    bll = ShopQuoteRecord()
    model = bll.new_instance()
    model.session_id = session_id
    model.user_id = user_id
    model.user_account = user_account
    model.items = items
    model.item_count = len(items)
    model.total_qty = sum(i["qty"] for i in items)
    model.total_original = total_original
    model.total_discount = total_discount
    model.total_final = total_final
    model.discount_rate = discount_rate

    record_id = bll.save_record(model)

    quote_url = url_for('bp_quote_pages.quote_view', record_id=record_id) + f"?s={session_id}"

    return jsonify({"code": 0, "record_id": record_id, "url": quote_url})

