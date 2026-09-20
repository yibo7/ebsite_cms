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
from bll.new_content import NewsContent
from bson import ObjectId

from entity.user_token import UserToken


# ─────────────────────────────────────────────────────────────────
#  智能报价系统 API
# ─────────────────────────────────────────────────────────────────

QUOTE_CLASS_ID = "6852498a0a8b42f2df14146e"  # 产品所在分类 ID


# ═════════════════════════════════════════════════════════════════
#  AI 提取提示词 — 从客户消息中提取产品参数
# ═════════════════════════════════════════════════════════════════
_EXTRACT_PROMPT = """你是一个复印机鼓芯销售助手。从用户消息中提取产品参数。

提取字段：
- brand: 复印机品牌（如 佳能/Canon、Ricoh、Sharp、Xerox、Kyocera、Toshiba、Samsung 等）
- model: 复印机型号（如 IR1730、MPC8003、MP9000 等）
- oem: OEM码/货号（如果有）

## 规则
- 提取到多少返回多少，不要遗漏
- model 字段只放一个主要型号。如果用户提到多个型号，只选第一个。**绝对不要用逗号/和/and 拼接多个型号为一个字符串 **
- 如果有品牌也有型号，返回 {"brand":"xx","model":"xx","ok":true}
- 如果只有型号没有品牌，也返回 {"model":"xx","ok":false,"partial":true}
- 如果只有品牌没有型号，也返回 {"brand":"xx","ok":false,"partial":true}
- 如果完全无法提取，返回 {"ok":false,"partial":false}

只返回 JSON。"""


# ═════════════════════════════════════════════════════════════════
#  销售文案提示词 — 根据搜索结果写销售文案
# ═════════════════════════════════════════════════════════════════
_SALES_PROMPT_TPL = """你是一个复印机鼓芯的专业销售助手，代表"Green Rich 金瑞治"公司。

客户的采购需求：{user_query}

以下是数据库中匹配到的产品：
{found_products}

{custom_instruction}

## 格式要求
- 用 HTML 格式回复（可用 <p> <br> <strong> <ul><li> 标签）
- 用与客户输入相同的语言回复（客户说英语→英语，日语→日语，中文→中文）
- 输出 {{"reply":"HTML文案"}}
"""


# ═════════════════════════════════════════════════════════════════
#  引导提示词 — 提取失败时 AI 同语言引导客户
# ═════════════════════════════════════════════════════════════════
_GUIDE_PROMPT = """客户说：{user_msg}

客户没有提供复印机鼓芯的品牌和型号信息。
请用与客户输入相同的语言回复，友好地引导客户提供品牌和型号信息。
输出 {{"reply":"HTML回复"}}
"""


def _search_products_by_params(
    brand: str, model: str, oem: str = ""
) -> list[dict]:
    """
    根据品牌、型号搜索数据库中的产品（不用查完全部产品缓存）

    搜索策略（参考网站原有 search 接口）：
    1. 从 NewsContent 指定分类中查询
    2. 先用 brand 精确匹配 column_3（适用品牌）
    3. 再用 model 模糊匹配 column_4（适用品牌型号）或 title
    4. 按 order_id 排序，返回 Top-10

    @param brand: 品牌名（如 Ricoh、佳能）
    @param model: 型号（如 MPC8003、IR1730）
    @param oem:   OEM码（可选）
    @return: 产品列表（dict 格式: _id, title, small_pic, brand, model_name, compatible, oem_code, price, skus）
    """
    import re
    from bson import ObjectId
    import pymongo

    bll = NewsContent()
    class_oid = ObjectId(QUOTE_CLASS_ID)

    # 构建查询条件
    where = {"class_id": class_oid}

    if brand:
        # 品牌匹配 column_3（不区分大小写）
        where["column_3"] = re.compile(re.escape(brand), re.IGNORECASE)

    if model:
        # 型号匹配：column_4、column_5 或 title 中包含型号关键词
        # column_5（适用型号）包含完整的兼容型号列表，如 "Canon iR1435/iR1435i/iR1435iF/IR1435P"
        # 不加 column_5 会导致搜索具体子型号（如 IR1435P）时遗漏
        #
        # 支持多型号拆分：用户/AI 可能传入 "MP 9000 1100 1350, Aficio Pro 1106EX 1356"
        # 按逗号/斜杠/和/and 拆分后分别搜索每个型号
        model_parts = re.split(r'[,，/、&]+|(?:\s+(?:and|与|和)\s+)', model)
        model_parts = [p.strip() for p in model_parts if len(p.strip()) >= 2]

        if not model_parts:
            model_parts = [model]

        or_conditions = []
        for part in model_parts:
            # ① 完整部分的正则（如 "MP 9000 1100 1350"）
            part_pattern = re.compile(
                re.escape(part).replace(r"\ ", ".*"), re.IGNORECASE
            )
            or_conditions.append({"column_4": part_pattern})
            or_conditions.append({"column_5": part_pattern})
            or_conditions.append({"title": part_pattern})

            # ② 进一步拆分：长串中提取单个型号组合
            # 如 "MP 9000 1100 1350" → 分别搜 "MP 9000"、"MP 1100"、"MP 1350"
            # 这样即使 column_4 只存了 "MP 9000" 也能搜到
            tokens = part.split()
            if len(tokens) >= 3:
                prefix = tokens[0]  # 型号前缀（如 MP、IR、iR、Pro 等）
                for token in tokens[1:]:
                    combined = f"{prefix} {token}"
                    if len(combined) >= 3:
                        comb_pattern = re.compile(
                            re.escape(combined).replace(r"\ ", ".*"),
                            re.IGNORECASE,
                        )
                        or_conditions.append({"column_4": comb_pattern})
                        or_conditions.append({"column_5": comb_pattern})
                        or_conditions.append({"title": comb_pattern})

        where["$or"] = or_conditions

    if oem:
        where["column_6"] = re.compile(re.escape(oem), re.IGNORECASE)

    try:
        models = bll.find_list_by_where(
            where,
            sort_key="order_id",
            sort_direction=pymongo.DESCENDING,
            limit=10
        )
    except Exception as e:
        current_app.logger.error(f"搜索产品异常: {e}")
        return []

    # 转为前端需要的 dict 格式
    products = []
    for p in models:
        skus = p.column_10
        if isinstance(skus, str):
            try:
                skus = json.loads(skus)
            except (json.JSONDecodeError, TypeError):
                skus = []

        products.append({
            "_id": str(p._id),
            "title": p.title or "",
            "small_pic": p.small_pic or "",
            "brand": p.column_3 or "",
            "model_name": p.column_4 or "",
            "compatible": p.column_5 or "",
            "price": float(p.column_11 or 0),
            "skus": skus or [],
        })

    return products


@bp_quote_apis.route('quote/welcome', methods=['GET'])
def quote_welcome():
    """返回可配置的欢迎语"""
    default = (
        '👋 <strong>Welcome / 欢迎</strong><br><br>'
        '<strong>English:</strong> I\'m the AI quoting assistant for <strong>Green Rich</strong>. '
        'Tell me the <strong>brand and model</strong> of the copier drum you need — '
        'I\'ll check availability and price right away.<br><br>'
        '<strong>中文:</strong> 我是 <strong>Green Rich 金瑞治</strong> 的 AI 询价助手。'
        '请告诉我您需要的复印机鼓芯的<strong>品牌</strong>和<strong>型号</strong>，'
        '我会立即为您查询报价。'
    )
    welcome = (bp_quote_apis.config or {}).get('welcome_message', '') or ''
    return jsonify({"welcome": welcome if welcome.strip() else default})


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
        return jsonify({"reply": "请告诉我您需要什么品牌和型号的鼓芯？😊", "matches": []})

    user_msgs = [m["content"] for m in messages if m.get("role") == "user"]
    latest_msg = user_msgs[-1] if user_msgs else ""
    provider = get_provider()

    # ── Step 1: AI 提取产品参数 ──
    t0 = time.time()
    try:
        extract_result = provider.chat(
            [{"role": "user", "content": latest_msg}], _EXTRACT_PROMPT
        )
    except Exception as e:
        current_app.logger.error(f"提取异常: {e}")
        extract_result = {"ok": False, "partial": False}
    if not isinstance(extract_result, dict):
        extract_result = {"ok": False, "partial": False}
    t1 = time.time()
    current_app.logger.warning(f"[⏱ 提取] {(t1-t0)*1000:.0f}ms | {json.dumps(extract_result, ensure_ascii=False)}")

    brand = (extract_result.get("brand") or "").strip()
    model = (extract_result.get("model") or "").strip()
    oem = (extract_result.get("oem") or "").strip()

    # 完全提取不到 → 让 AI 用同语言引导客户
    if not brand and not model and not oem:
        try:
            t_guide_start = time.time()
            guide_result = provider.chat(
                [{"role": "user", "content": latest_msg}],
                _GUIDE_PROMPT.format(user_msg=latest_msg[:300])
            )
            current_app.logger.warning(f"[⏱ 引导] {(time.time()-t_guide_start)*1000:.0f}ms")
            if isinstance(guide_result, dict) and guide_result.get("reply"):
                return jsonify({"reply": guide_result["reply"], "matches": []})
        except Exception as e:
            current_app.logger.error(f"引导异常: {e}")
        # 兜底
        return jsonify({
            "reply": "<p>Please tell me the <strong>brand</strong> and <strong>model</strong> of the copier drum you need.</p>"
                     "<p>请提供复印机鼓芯的<strong>品牌</strong>和<strong>型号</strong>。</p>"
                     "<p>例：<br>• Toshiba E168<br>• 佳能 iRC5030<br>• Samsung MLT-R706</p>",
            "matches": []
        })

    # ── Step 2: 搜索数据库 ──
    t2 = time.time()
    matched_products = _search_products_by_params(brand, model, oem)
    current_app.logger.warning(f"[⏱ 搜索] {(time.time()-t2)*1000:.0f}ms | brand={brand} model={model} → {len(matched_products)} 个")

    if not matched_products:
        kw = f"{brand} {model}".strip()
        current_app.logger.warning(f"[⏱ 总耗时] {(time.time()-t0)*1000:.0f}ms")
        return jsonify({
            "reply": f"<p>抱歉，没有找到 <strong>{kw}</strong> 的产品 😅</p>"
                     f"<p>请确认品牌型号是否正确。</p>",
            "matches": []
        })

    # ── Step 3: AI 写文案 ──
    found_lines = [f"- {p['title']} | ¥{p['price']}" for p in matched_products]
    found_text = "\n".join(found_lines)

    is_exact = extract_result.get("ok", False)
    if is_exact:
        ci = "客户明确说了品牌和型号。热情介绍产品，引导点击 [+] 加入询价单。"
    else:
        if model and not brand:
            ci = f"客户只说了型号{model}没提品牌。不确定对不对，请客户看看这些是否匹配。"
        elif brand and not model:
            ci = f"客户只说了品牌{brand}没提型号。请客户看看这些是否匹配。"
        else:
            ci = "信息不完整。请客户看看这些是否匹配。"
        ci += "如果客户确认，引导点击 [+] 加入询价单。"

    sales_prompt = _SALES_PROMPT_TPL.format(
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
            "productId": p["_id"],
            "title": p["title"],
            "price": p["price"],
            "small_pic": p.get("small_pic", ""),
            "brand": p.get("brand", ""),
            "qty": 1
        })

    if not sales_result.get("reply"):
        sales_result["reply"] = (
            f"<p>为您找到以下产品：</p>"
            + "".join(f"<p>• {p['title']} <strong>¥{p['price']}</strong></p>"
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

    # 构建产品明细（全部用 float，MongoDB 原生支持）
    items = []
    total_original = 0.0
    for item in items_raw:
        price = float(item.get("price", 0))
        qty = int(item.get("qty", 1))
        subtotal = round(price * qty, 2)
        total_original += subtotal
        items.append({
            "title": item.get("title", ""),
            "small_pic": item.get("small_pic", ""),
            "spec": item.get("spec", ""),
            "qty": qty,
            "unit_price": price,
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

