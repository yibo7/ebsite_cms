
from flask import jsonify, current_app, send_from_directory, request, url_for

from decorators import check_user_login
from . import bp_ai_cart_apis

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


def _parse_json_reply(raw: dict) -> dict:
    """
    解析新插件 AIProviderBase.chat() 的返回值。

    新插件返回 {reply: "JSON字符串", finish_reason: "stop", usage: {...}}
    需要把 reply 里的 JSON 字符串解析出来，合并回顶层。

    :param raw: chat() 返回的原始 dict
    :return: 解析后的 dict；解析失败时返回 {"ok": False, "partial": False}
    """
    import json

    if not isinstance(raw, dict):
        return {"ok": False, "partial": False}

    reply = raw.get("reply", "")
    if not isinstance(reply, str) or not reply.strip():
        return raw

    # 尝试解析 reply 为 JSON
    try:
        parsed = json.loads(reply.strip())
        if isinstance(parsed, dict):
            # 合并：parsed 覆盖到 raw 顶层，保留 finish_reason / usage 等字段
            merged = dict(raw)
            merged.update(parsed)
            merged.pop("reply", None)  # 原始 reply 字符串不再需要
            return merged
    except (json.JSONDecodeError, TypeError):
        pass

    # 不是 JSON 就原样返回
    return raw


@bp_ai_cart_apis.route('quote/welcome', methods=['GET'])
def quote_welcome():
    """返回可配置的欢迎语与店铺名称"""
    welcome = _get_prompt("welcome_message")
    shop_name = _get_prompt("shop_name") or "Green Rich"
    return jsonify({"welcome": welcome, "shop_name": shop_name})


@bp_ai_cart_apis.route('quote/chat', methods=['POST'])
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
    from flask import current_app

    # 使用系统插件管理器获取默认 AI 提供者
    provider = current_app.pm.get_default_ai()
    if not provider:
        return jsonify({"reply": "AI 服务未配置，请在系统设置中配置默认 AI 提供者。😊", "matches": []})

    data = request.get_json() or {}
    messages = data.get('messages', [])
    if not messages:
        return jsonify({"reply": "请问您需要什么商品？😊", "matches": []})

    user_msgs = [m["content"] for m in messages if m.get("role") == "user"]
    latest_msg = user_msgs[-1] if user_msgs else ""

    # ── Step 1: AI 提取产品参数 ──
    t0 = time.time()
    try:
        raw = provider.chat(
            [{"role": "user", "content": latest_msg}], _get_prompt("extract_prompt")
        )
        # 新插件 chat() 返回 {reply: "JSON字符串", ...}，需要二次解析
        extract_result = _parse_json_reply(raw)
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
            raw = provider.chat(
                [{"role": "user", "content": latest_msg}],
                _get_prompt("guide_prompt").format(user_msg=latest_msg[:300])
            )
            guide_result = _parse_json_reply(raw)
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

    # ── Step 3: AI 写文案（不透露具体价格）──
    found_lines = [f"- {p['title']}" for p in matched_products]
    found_text = "\n".join(found_lines)

    ci = handler.build_custom_instruction(extract_result, bool(extract_result.get("ok")))

    sales_prompt = _get_prompt("sales_prompt_tpl").format(
        shop_name=_get_prompt("shop_name"),
        user_query=latest_msg[:200], found_products=found_text, custom_instruction=ci
    )

    try:
        t3 = time.time()
        raw_sales = provider.chat(messages, sales_prompt)
        sales_result = _parse_json_reply(raw_sales)
        current_app.logger.warning(f"[⏱ 文案] {(time.time()-t3)*1000:.0f}ms")
        if not isinstance(sales_result, dict):
            sales_result = {"reply": str(raw_sales.get("reply", ""))}
    except Exception as e:
        current_app.logger.error(f"文案异常: {e}")
        sales_result = {"reply": ""}

    matches = []
    for p in matched_products:
        # 从 column_10 提取第一个真实 SKU 码（用于前端显示）
        raw_skus = p.get("column_10", "[]")
        if isinstance(raw_skus, str):
            try: skus_list = json.loads(raw_skus)
            except: skus_list = []
        elif isinstance(raw_skus, list):
            skus_list = raw_skus
        else:
            skus_list = []
        first_sku = skus_list[0].get("sku", "") if skus_list else ""

        matches.append({
            "title": p.get("title", ""),
            "small_pic": p.get("small_pic", ""),
            "unit_price": float(p.get("unit_price", 0)),
            "market_price": float(p.get("market_price", 0)),
            "class_name": p.get("class_name", ""),
            "content_id": p.get("sku", ""),        # MongoDB ObjectId，供后端定价查找
            "sku": first_sku or p.get("sku", ""),  # 真实 SKU 码，无则回退 ObjectId
            "url": p.get("url", ""),
            "qty": 1,
        })

    if not sales_result.get("reply"):
        sales_result["reply"] = (
            f"<p>为您找到以下产品：</p>"
            + "".join(f"<p>• {p['title']}</p>"
                     for p in matched_products[:3])
            + "<p>点击 <strong>[+]</strong> 加入询价单，可在其中修改数量。</p>"
        )

    sales_result["matches"] = matches
    current_app.logger.warning(f"[⏱ 总耗时] {(time.time()-t0)*1000:.0f}ms")
    return jsonify(sales_result)


@bp_ai_cart_apis.route('quote/save_record', methods=['POST'])
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


@bp_ai_cart_apis.route('quote/submit_order', methods=['POST'])
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


# ═════════════════════════════════════════════════════════════════
#  按用户组定价 — 从 SKU group_prices 获取对应用户组的价格
# ═════════════════════════════════════════════════════════════════

def _resolve_user_group() -> tuple:
    """
    获取当前用户的 group_id 与 group_name。
    未登录用户返回 ("", "vip")，即默认 VIP 价。
    """
    from eb_cache import login_utils
    token = login_utils.get_token()
    if token and token.group_id:
        return token.group_id, token.group_name or "vip"
    return "", "vip"


def _lookup_group_price(skus: list, target_group_id: str) -> float | None:
    """
    在 SKU 的 group_prices 数组中查找对应用户组的价格。
    1) 优先匹配 group_id；2) 回退匹配 group_name=='vip'；3) 取第一个 group_price。
    """
    if not skus or not isinstance(skus, list):
        return None
    for s in skus:
        gps = s.get("group_prices") or []
        if not isinstance(gps, list):
            continue
        # 精确匹配 group_id
        if target_group_id:
            for gp in gps:
                if gp.get("group_id") == target_group_id:
                    return float(gp.get("price", 0))
        # 未登录/无匹配 → 找 VIP
        for gp in gps:
            if gp.get("group_name", "").lower() == "vip":
                return float(gp.get("price", 0))
        # 兜底：取第一个
        for gp in gps:
            return float(gp.get("price", 0))
    return None


def _resolve_item_price(item: dict, user_group_id: str) -> float:
    """
    根据提交的 item 信息，从数据库查询并返回对应用户组的价格。
    item 中必须包含 id（MongoDB _id 字符串）和可选的 sku 字段。
    """
    from bll.new_content import NewsContent
    from entity.news_content_model import NewsContentModel
    import json

    content_id = item.get("id") or item.get("content_id", "")
    if not content_id:
        current_app.logger.warning(f"[定价] item 缺少 id，使用提交的 unit_price")
        return float(item.get("unit_price", item.get("price", 0)))

    try:
        bll = NewsContent()
        product = bll.find_one_by_id(content_id)
        if not product:
            current_app.logger.warning(f"[定价] 未找到产品 {content_id}")
            return float(item.get("unit_price", item.get("price", 0)))

        raw_skus = product.column_10 or "[]"
        if isinstance(raw_skus, str):
            try:
                skus = json.loads(raw_skus)
            except json.JSONDecodeError:
                skus = []
        elif isinstance(raw_skus, list):
            skus = raw_skus
        else:
            skus = []

        # 优先匹配当前选中 SKU
        sku_code = item.get("sku", "")
        if sku_code:
            matched = [s for s in skus if s.get("sku") == sku_code]
            if matched:
                price = _lookup_group_price(matched, user_group_id)
                if price is not None:
                    return price

        # 无 SKU 匹配 → 在所有 SKU 中查找
        price = _lookup_group_price(skus, user_group_id)
        if price is not None:
            return price

        # 最终兜底：marketPrice → column_11
        mp = float(item.get("market_price", 0))
        if mp:
            return mp
        return float(product.column_11 or 0)

    except Exception as e:
        current_app.logger.error(f"[定价] 异常: {e}")
        return float(item.get("unit_price", item.get("price", 0)))


@bp_ai_cart_apis.route('quote/submit', methods=['POST'])
def quote_submit():
    """
    生成报价单（无需登录）

    请求体（JSON）：
    {
        "sessionId": "...",
        "items": [
            {"id": "...", "qty": 10, "title": "...", "sku": "..."}
        ],
        "contact": {},
        "discount_rate": 0.10
    }

    返回：{"code": 0, "record_id": "QRxxxxxx", "url": ".../quote/QRxxxxxx"}
    """
    from .datas.quote_record import ShopQuoteRecord
    from eb_cache import login_utils

    data = request.get_json() or {}
    items_raw = data.get("items", [])
    if not items_raw:
        return jsonify({"code": -1, "msg": "询价单为空"})

    discount_rate = float(data.get("discount_rate", 0))
    session_id = data.get("sessionId", "")

    # 获取用户组信息（用于定价）
    user_group_id, user_group_name = _resolve_user_group()
    current_app.logger.warning(f"[定价] 用户组: {user_group_name} ({user_group_id})")

    # 尝试获取登录用户信息
    user_token = login_utils.get_token()
    if user_token:
        user_id = str(user_token.id)
        user_account = user_token.name
    else:
        user_id = ""
        user_account = session_id

    # 构建产品明细 —— 根据用户组自动定价
    items = []
    total_original = 0.0
    for item in items_raw:
        unit_price = _resolve_item_price(item, user_group_id)
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
    model.user_group_name = user_group_name

    record_id = bll.save_record(model)

    quote_url = url_for('bp_ai_cart_pages.quote_view', record_id=record_id) + f"?s={session_id}"

    return jsonify({"code": 0, "record_id": record_id, "url": quote_url})

