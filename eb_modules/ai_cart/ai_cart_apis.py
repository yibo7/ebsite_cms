
from flask import jsonify, request

from . import bp_ai_cart_apis


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

    # 完全提取不到（ok=false 且 partial=false）→ 先做原文兜底搜索
    # 注意：partial=true 表示有部分参数（如只有品牌），应继续搜索
    fallback_hit = False
    if not extract_result.get("ok") and not extract_result.get("partial"):
        # 用用户原始输入作为关键词做一次兜底搜索
        fallback_params = {"model": latest_msg.strip(), "brand": "", "oem": ""}
        t2 = time.time()
        fallback_products = handler.search(fallback_params)
        current_app.logger.warning(f"[⏱ 兜底搜索] {(time.time()-t2)*1000:.0f}ms → {len(fallback_products)} 个")

        if fallback_products:
            # 兜底搜到了 → 跳过引导，直接走销售文案流程
            matched_products = fallback_products
            extract_result = {"ok": True, "partial": True, "brand": "", "model": latest_msg.strip()}
            fallback_hit = True
            current_app.logger.warning(f"[🔍 兜底命中] 原文「{latest_msg}」搜索到 {len(matched_products)} 个商品")
        else:
            # 兜底也没搜到 → 引导客户
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
    if not fallback_hit:
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

    def _build_match(product, sku_code, product_id, doc_id, sku_image="", sku_price=0):
        """从商品和 SKU 构造一条匹配项"""
        return {
            "id": doc_id,
            "title": product.get("title", ""),
            "small_pic": sku_image or product.get("small_pic", ""),
            "unit_price": float(sku_price or product.get("unit_price", 0)),
            "market_price": float(sku_price or product.get("market_price", 0)),
            "class_name": product.get("class_name", ""),
            "content_id": product.get("sku", ""),
            "sku": sku_code or product.get("sku", ""),
            "product_id": product_id,
            "url": product.get("url", ""),
            "qty": 1,
        }

    matches = []
    for p in matched_products:
        # 解析 column_10 获取所有 SKU
        raw_skus = p.get("column_10", "[]")
        if isinstance(raw_skus, str):
            try: skus_list = json.loads(raw_skus)
            except: skus_list = []
        elif isinstance(raw_skus, list):
            skus_list = raw_skus
        else:
            skus_list = []

        # 如果商品没有 SKU，用商品本身作为一条匹配
        if not skus_list:
            matches.append(_build_match(p, p.get("sku", ""), p.get("sku", ""), str(p.get("_id", ""))))
        else:
            # 每个 SKU 生成一张独立卡片，使用 SKU 自己的价格
            for s in skus_list:
                sku_code = s.get("sku", "")
                product_id = s.get("productId", "")
                sku_image = s.get("image", "")
                sku_price = s.get("marketPrice", 0)
                matches.append(_build_match(p, sku_code, product_id, str(p.get("_id", "")), sku_image, sku_price))

    if not sales_result.get("reply"):
        sales_result["reply"] = (
            f"<p>为您找到以下产品：</p>"
            + "".join(f"<p>• {p['title']}</p>"
                     for p in matched_products[:3])
            + "<p>点击 <strong>[+]</strong> 加入购物车单，可在其中修改数量。</p>"
        )

    sales_result["matches"] = matches
    current_app.logger.warning(f"[⏱ 总耗时] {(time.time()-t0)*1000:.0f}ms")
    return jsonify(sales_result)

