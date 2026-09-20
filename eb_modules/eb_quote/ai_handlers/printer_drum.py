"""
打印复印耗材品类处理器 — 按品牌 + 型号精确搜索
"""
import json, re
import pymongo
from bson import ObjectId
from flask import current_app
from bll.new_content import NewsContent
from . import AiHandlerBase, register_ai_handler

QUOTE_CLASS_ID = "6852498a0a8b42f2df14146e"

@register_ai_handler('printer_drum')
class PrinterDrumHandler(AiHandlerBase):
    display_name = "打印复印耗材"
    default_shop_name = "Green Rich 金瑞治"
    default_welcome_message = (
        '👋 <strong>Welcome / 欢迎</strong><br><br>'
        '<strong>English:</strong> I\'m the AI quoting assistant for <strong>Green Rich</strong>. '
        'Tell me the <strong>brand and model</strong> of the copier drum you need — '
        'I\'ll check availability and price right away.<br><br>'
        '<strong>中文:</strong> 我是 <strong>Green Rich 金瑞治</strong> 的 AI 询价助手。'
        '请告诉我您需要的复印机鼓芯的<strong>品牌</strong>和<strong>型号</strong>，'
        '我会立即为您查询报价。'
    )
    default_extract_prompt = """你是一个复印机鼓芯销售助手。从用户消息中提取产品参数。

提取字段：
- brand: 复印机品牌（如 佳能/Canon、Ricoh、Sharp、Xerox、Kyocera、Toshiba、Samsung 等）
- model: 复印机型号（如 IR1730、MPC8003、MP9000 等）
- oem: OEM码/货号（如果有）

## 规则
- model 字段只放一个主要型号。如果用户提到多个型号，只选第一个。
- 如果有品牌也有型号，返回 {"brand":"xx","model":"xx","ok":true}
- 如果只有型号没有品牌，也返回 {"model":"xx","ok":false,"partial":true}
- 如果只有品牌没有型号，也返回 {"brand":"xx","ok":false,"partial":true}
- 如果完全无法提取，返回 {"ok":false,"partial":false}
只返回 JSON。"""
    default_sales_prompt_tpl = """你是一个复印机鼓芯的专业销售助手，代表"{shop_name}"公司。

客户的采购需求：{user_query}

以下是数据库中匹配到的产品：
{found_products}

{custom_instruction}

## 格式要求
- 用 HTML 格式回复（可用 <p> <br> <strong> <ul><li> 标签）
- 用与客户输入相同的语言回复
- 输出 {{"reply":"HTML文案"}}
"""
    default_guide_prompt = """客户说：{user_msg}
客户没有提供复印机鼓芯的品牌和型号信息。
请用与客户输入相同的语言回复，友好地引导客户提供品牌和型号信息。
输出 {{"reply":"HTML回复"}}
"""

    def search(self, params: dict) -> list[dict]:
        brand = (params.get("brand") or "").strip()
        model = (params.get("model") or "").strip()
        oem = (params.get("oem") or "").strip()
        bll = NewsContent()
        where = {"class_id": ObjectId(QUOTE_CLASS_ID)}
        if brand:
            where["column_3"] = re.compile(re.escape(brand), re.IGNORECASE)
        if model:
            parts = [p.strip() for p in re.split(r'[,，/、&]+|(?:\s+(?:and|与|和)\s+)', model) if len(p.strip()) >= 2]
            if not parts: parts = [model]
            or_c = []
            for p in parts:
                pat = re.compile(re.escape(p).replace(r"\ ", ".*"), re.IGNORECASE)
                for f in ("column_4","column_5","title"):
                    or_c.append({f: pat})
            where["$or"] = or_c
        if oem:
            where["column_6"] = re.compile(re.escape(oem), re.IGNORECASE)
        try:
            models = bll.find_list_by_where(where, sort_key="order_id",
                                            sort_direction=pymongo.DESCENDING, limit=10)
        except Exception as e:
            current_app.logger.error(f"打印耗材搜索异常: {e}"); return []
        products = []
        for p in models:
            skus = p.column_10
            if isinstance(skus, str):
                try: skus = json.loads(skus)
                except: skus = []
            mp = float(p.column_11 or 0)
            if skus and isinstance(skus, list):
                for s in skus:
                    if s.get("marketPrice"): mp = float(s["marketPrice"]); break
            from eb_utils import url_links
            try:
                url = url_links.get_content_url(p.id) if p.id else ""
            except Exception:
                url = ""
            current_app.logger.warning(f"[DEBUG url] id={p.id} _id={p._id} url={url}")
            products.append({
                "title": p.title or "",
                "small_pic": p.small_pic or "",
                "unit_price": float(p.column_11 or 0),
                "market_price": mp,
                "class_name": "打印耗材",
                "sku": str(p._id),
                "url": url,
                "remarks": p.column_7 or "",
            })
        return products

    def no_result_reply(self, params: dict) -> str:
        kw = f"{params.get('brand','')} {params.get('model','')}".strip()
        return f"<p>抱歉，没有找到 <strong>{kw}</strong> 的产品 😅</p><p>请确认品牌型号是否正确。</p>"
    def guide_fallback_reply(self) -> str:
        return ("<p>Please tell me the <strong>brand</strong> and <strong>model</strong>"
                " of the copier drum you need.</p><p>请提供复印机鼓芯的<strong>品牌</strong>和<strong>型号</strong>。</p>"
                "<p>例：<br>• Ricoh MPC8003<br>• 佳能 IR1730<br>• Sharp MX-2600N</p>")
    def build_custom_instruction(self, params: dict, exact: bool) -> str:
        b, m = (params.get("brand") or "").strip(), (params.get("model") or "").strip()
        if exact: return "客户明确说了品牌和型号。热情介绍产品，引导点击 [+] 加入询价单。"
        if m and not b: return f"客户只说了型号{m}没提品牌。请客户看看这些是否匹配。如果客户确认，引导点击 [+] 加入询价单。"
        if b and not m: return f"客户只说了品牌{b}没提型号。请客户看看这些是否匹配。如果客户确认，引导点击 [+] 加入询价单。"
        return "信息不完整。请客户看看这些是否匹配。如果客户确认，引导点击 [+] 加入询价单。"