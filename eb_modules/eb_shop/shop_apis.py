import os
import re
import uuid
import hashlib
import base64
import json
import pymongo
from flask import jsonify, current_app, send_from_directory, request

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


# ─────────────────────────────────────────────────────────────────
#  智能报价系统 API
# ─────────────────────────────────────────────────────────────────

QUOTE_CLASS_ID = "6852498a0a8b42f2df14146e"  # 产品所在分类 ID


def _load_quote_products(max_count: int = 500) -> list[dict]:
    """
    加载报价系统的产品列表（从 NewsContent 指定分类）
    结果会被缓存到 current_app.config，避免每次请求都查库

    返回格式：
    [
        {
            "_id": "MongoDB ObjectId 字符串",
            "title": "佳能 IR1730 鼓芯",
            "small_pic": "/uploads/xxx.jpg",
            "brand": "佳能",
            "model_name": "IR1730",
            "compatible": "兼容机型",
            "oem_code": "OEM码",
            "price": 20.0,
            "skus": [{"name": "Original", "marketPrice": 20, ...}]
        },
        ...
    ]
    """
    cache_key = "_quote_products_cache"
    cached = current_app.config.get(cache_key)
    if cached:
        return cached

    bll = NewsContent()
    # 注意：class_id 在 MongoDB 中是 ObjectId 类型
    # 不能用 get_new_datas（它传字符串查不到），直接查
    class_oid = ObjectId(QUOTE_CLASS_ID)
    import pymongo
    models = bll.find_list_by_where(
        {"class_id": class_oid},
        sort_key="_id",
        sort_direction=pymongo.DESCENDING,
        limit=max_count
    )

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
            "oem_code": p.column_6 or "",
            "price": float(p.column_11 or 0),
            "skus": skus or [],
        })

    # 缓存1分钟（后台新增商品后最多1分钟可见）
    current_app.config[cache_key] = products
    return products


@bp_shop_apis.route('quote/products', methods=['GET'])
def quote_products():
    """
    获取报价系统中的所有产品列表

    返回 JSON：
    {
        "code": 0,
        "data": [ {_id, title, brand, model_name, price, skus, ...} ]
    }
    """
    products = _load_quote_products()
    return jsonify({"code": 0, "data": products})


def _build_product_catalog_text(products: list[dict]) -> str:
    """将产品列表转为极简的 AI 目录文本（最小 token 数）"""
    lines = []
    for i, p in enumerate(products, 1):
        # 只保留产品 ID、名称和价格，极度精简
        title_short = p["title"][:60]  # 标题截断
        lines.append(
            f'{i}. [{p["_id"]}] {title_short} ¥{p["price"]}'
        )
    return "\n".join(lines)


_SYSTEM_PROMPT_TPL = """你是一个复印机感光鼓芯（OPC鼓）的专业智能销售助手，代表"Green Rich 金瑞治"公司。

## 可用产品目录（JSON格式）
以下是数据库中所有可售产品的完整数据，每个产品包含以下字段：
- productId: MongoDB _id（唯一标识）
- title: 商品名称
- brand: 适用品牌
- model_name: 适用品牌型号
- compatible: 兼容机型
- price: 市场价（¥）
- small_pic: 商品缩略图URL
- skus: 规格数组（每个规格有 name, marketPrice, stock 等）

{product_catalog}

## 你的任务
1. 根据客户问题，从以上产品目录中匹配合适的产品
2. 用热情专业的中文回复客户
3. 在 matches 中返回匹配的产品ID

## 回复格式
{{
    "reply": "HTML格式的回复文本（禁止Markdown，只能用<br><strong><p><ul><li>标签）",
    "matches": [
        {{"productId": "产品的_id字符串", "qty": 客户需要的数量}}
    ]
}}

## 规则
- 每次推荐产品时，必须在 matches 中列出其 productId
- 如果客户说了数量，在 qty 中体现
- 如果不确定数量，默认 qty=1
- 完全不匹配时 matches 返回 []
- 禁止添加目录中不存在的产品
"""


def _enrich_matches_from_reply(reply: str, products: list[dict]) -> list[dict]:
    """
    从 AI 回复文本中精确提取匹配的产品

    策略：双层匹配
    第一层（精确）：检查归一化的产品标题是否出现在回复中
    第二层（兜底）：检查 "品牌+型号" 组合是否出现在回复中

    @param reply: AI 回复文本
    @param products: 产品列表
    @return: [{"productId": "...", "skuIndex": 0, "qty": 1}, ...]
    """
    import re

    if not reply or not products:
        return []

    # 归一化 AI 回复：去空格、分隔符、特殊字符
    reply_flat = re.sub(r'[\s\-_/\\,，、()（）\[\]【】:：]+', '', reply.lower())

    results = []

    for p in products:
        # --- 第一层：标题精确匹配 ---
        title = p.get("title") or ""
        title_flat = re.sub(r'[\s\-_/\\,，、()（）\[\]【】:：]+', '', title.lower())

        matched = False
        if len(title_flat) >= 10 and title_flat in reply_flat:
            matched = True

        # --- 第二层：品牌+型号组合匹配 ---
        if not matched:
            brand = (p.get("brand") or "").lower().strip()
            model = (p.get("model_name") or "").lower().strip()
            if brand and model:
                # 组合方式1: "ricohmp9000"
                combo1 = re.sub(r'[\s\-_]+', '', f"{brand}{model}")
                # 组合方式2: "mp9000" (部分型号)
                combo2 = re.sub(r'[\s\-_]+', '', model)

                if combo1 in reply_flat or (len(combo2) >= 4 and combo2 in reply_flat):
                    matched = True

        if matched:
            results.append({
                "productId": p["_id"],
                "skuIndex": 0,
                "qty": 1
            })

    # 最多返回 2 个（通常只有 1 个精确匹配）
    return results[:2]


def _search_products(products: list[dict], query: str) -> list[dict]:
    """
    从用户查询文本中搜索匹配的产品（检索优先）

    策略：
    1. 精确匹配：品牌名、型号名、标题完全匹配（最高分）
    2. 模糊匹配：将查询词拆分为 token，与产品关键词模糊匹配
    3. 按匹配分数排序，返回 Top-5

    @param products: 所有产品列表
    @param query: 用户查询文本
    @return: 按匹配度排序的产品列表
    """
    import re
    if not query or not products:
        return []

    query_lower = query.lower().strip()

    # 从查询中提取有意义的 token
    # 先尝试提取品牌+型号的组合（如 "佳能 IR1730"）
    query_tokens = set()
    for token in re.split(r'[\s,，、/]+', query_lower):
        token = token.strip()
        if len(token) >= 2:
            query_tokens.add(token)

    current_app.logger.warning(
        f"[_search_products] 查询='{query_lower[:80]}', "
        f"提取关键词={query_tokens}"
    )

    # 对每个产品评分
    scored = []
    for p in products:
        score = 0
        # 构建可搜索文本
        search_text = (
            f"{p.get('title','')} {p.get('brand','')} "
            f"{p.get('model_name','')} {p.get('compatible','')} "
            f"{p.get('oem_code','')}"
        ).lower()

        # --- 精确匹配（高分）---
        # 查询词完全出现在标题/品牌/型号中
        for qt in query_tokens:
            if qt in search_text:
                score += len(qt) * 3  # 长关键词权重大

        # 查询整体出现在标题中（最高分）
        if query_lower in search_text:
            score += 50

        # 查询中的每个字符片段匹配
        # 例如 "IR1730" 匹配 "IR1730"
        for qt in query_tokens:
            # 数字型号精确匹配
            for field in ['model_name', 'title']:
                field_val = (p.get(field) or '').lower()
                if qt == field_val or qt in field_val.split():
                    score += 30

            # 品牌精确匹配
            brand = (p.get('brand') or '').lower()
            if qt == brand:
                score += 25

        # --- 辅助加分 ---
        # sku 名称匹配
        for sku in (p.get('skus') or []):
            sku_name = (sku.get('name') or '').lower()
            if sku_name and any(qt in sku_name for qt in query_tokens):
                score += 5

        if score > 0:
            scored.append((p, score))
            current_app.logger.warning(
                f"  [评分] {p['title'][:50]} → {score}分"
            )

    # 按分数降序排列
    scored.sort(key=lambda x: x[1], reverse=True)

    # 返回 Top-5
    return [p for p, s in scored[:5]]


@bp_shop_apis.route('quote/chat', methods=['POST'])
def quote_chat():
    """
    AI 智能报价对话（核心 API）

    流程：
    1. 加载所有产品数据，构建完整目录
    2. 将整个目录作为上下文喂给 AI
    3. AI 自主匹配合适产品，返回 reply + matches(productId)
    4. 前端根据 productId 从缓存中查取产品详情渲染卡片

    请求体（JSON）：
    {"sessionId": "...", "messages": [{"role": "user", "content": "..."}]}

    返回（JSON）：
    {
        "reply": "HTML回复",
        "matches": [{"productId": "...", "qty": 1}]
    }
    """
    from eb_modules.eb_shop.ai_providers import get_provider

    data = request.get_json() or {}
    messages = data.get('messages', [])

    if not messages:
        return jsonify({"reply": "请告诉我您需要什么品牌和型号的鼓芯？😊", "matches": []})

    # 1. 加载所有产品（已修复 ObjectId 问题）
    products = _load_quote_products()
    catalog_text = _build_product_catalog_text(products)
    current_app.logger.warning(
        f"[quote/chat] 产品总数={len(products)}, 最新消息数={len(messages)}"
    )

    # 2. 构建 system prompt，把全部产品喂给 AI
    system_prompt = _SYSTEM_PROMPT_TPL.format(product_catalog=catalog_text)

    # 【调试】打印提交给 AI 的完整数据
    current_app.logger.warning("=" * 60)
    current_app.logger.warning("【提交给 AI 的 System Prompt】")
    for line in system_prompt.split("\n"):
        current_app.logger.warning(f"  | {line}")
    current_app.logger.warning("=" * 60)
    current_app.logger.warning(f"【提交给 AI 的 Messages（共 {len(messages)} 条）】")
    for i, msg in enumerate(messages):
        current_app.logger.warning(f"  msg[{i}] role={msg['role']}, content={msg['content'][:200]}")
    current_app.logger.warning("=" * 60)

    # 3. 调用 AI — 让它自己匹配并返回结构化数据
    try:
        provider = get_provider()
        result = provider.chat(messages, system_prompt)

        # 校验
        if not isinstance(result, dict):
            result = {"reply": str(result), "matches": []}
        if "reply" not in result or not result["reply"]:
            result["reply"] = "<p>已为您查询到相关信息。</p>"
        if "matches" not in result or not isinstance(result["matches"], list):
            result["matches"] = []

        # 验真：只保留 productId 在数据库中的 matches
        valid_ids = {p["_id"] for p in products}
        ai_matches = [
            m for m in result["matches"]
            if m.get("productId") in valid_ids
        ]

        # 后处理：如果 AI 没返回 matches，从回复文本中自动提取
        if len(ai_matches) == 0:
            backend_matches = _enrich_matches_from_reply(
                result["reply"], products
            )
            current_app.logger.warning(
                f"[quote/chat] AI 未返回匹配，后端自动提取到 "
                f"{len(backend_matches)} 个"
            )
            result["matches"] = backend_matches
        else:
            result["matches"] = ai_matches

        current_app.logger.warning(
            f"[quote/chat] 最终 matches={len(result['matches'])} 个"
        )
        return jsonify(result)

    except Exception as e:
        current_app.logger.error(f"AI报价对话异常: {e}", exc_info=True)
        return jsonify({
            "reply": f"抱歉，AI 服务暂时不可用 🙏<br>错误: {str(e)[:100]}<br>请直接告诉我们需要什么品牌和型号。",
            "matches": []
        })


@bp_shop_apis.route('quote/save_record', methods=['POST'])
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
        db["QuoteRecord"].insert_one(record)
        return jsonify({"code": 0, "msg": "保存成功"})
    except Exception as e:
        current_app.logger.error(f"保存询价记录失败: {e}")
        return jsonify({"code": -1, "msg": "保存失败"})


@bp_shop_apis.route('quote/submit_order', methods=['POST'])
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

