"""
服装品类处理器 — 按关键词模糊搜索
"""
import json, re
import pymongo
from bson import ObjectId
from flask import current_app
from bll.new_content import NewsContent
from . import AiHandlerBase, register_ai_handler

QUOTE_CLASS_ID = "6852498a0a8b42f2df14146e"

@register_ai_handler('clothing')
class ClothingHandler(AiHandlerBase):
    display_name = "服装"
    default_shop_name = "优选服饰"
    default_welcome_message = (
        '👋 <strong>欢迎选购</strong><br><br>'
        '我是 AI 服装导购助手，请告诉我您想找什么样的衣服？<br>'
        '例如：<br>• 红色连衣裙 M 码<br>• 白色纯棉T恤<br>• 黑色西装外套 XL'
    )
    default_extract_prompt = """你是一个服装销售助手。从用户消息中提取产品参数。

提取字段：
- category: 服装品类（如 连衣裙、T恤、衬衫、裤子、外套 等，没有则填空字符串）
- color: 颜色（如 红色、黑色、白色、蓝色 等，没有则填空字符串）
- size: 尺码（如 S、M、L、XL、XXL、均码 等，没有则填空字符串）
- material: 材质（如 棉、涤纶、丝绸、羊毛 等，如果有）
- keywords: 其他关键词（如 夏季、新款、修身 等，如果有）

## 规则
- 如果至少提取到 category，返回 {"category":"xx","ok":true}
- 如果只提取到颜色尺码但没有品类，也返回 {"color":"xx","size":"xx","ok":false,"partial":true}
- 如果完全无法提取，返回 {"ok":false,"partial":false}
只返回 JSON。"""
    default_sales_prompt_tpl = """你是一个服装的专业销售助手，代表"{shop_name}"店铺。

客户的选购需求：{user_query}

以下是店铺中匹配到的商品：
{found_products}

{custom_instruction}

## 格式要求
- 用 HTML 格式回复（可用 <p> <br> <strong> <ul><li> 标签）
- 用与客户输入相同的语言回复
- 输出 {{"reply":"HTML文案"}}
"""
    default_guide_prompt = """客户说：{user_msg}
客户没有提供具体的服装品类信息。
请用与客户输入相同的语言回复，友好地引导客户说出想找的服装品类、颜色和尺码。
输出 {{"reply":"HTML回复"}}
"""

    def search(self, params: dict) -> list[dict]:
        keywords = [params[k].strip() for k in ("category","color","size","material","keywords") if params.get(k,"").strip()]
        if not keywords: return []
        bll = NewsContent()
        class_oid = ObjectId(QUOTE_CLASS_ID)
        or_c = []
        for kw in keywords:
            pat = re.compile(re.escape(kw), re.IGNORECASE)
            for f in ("title","column_3","column_4","column_5","column_6"):
                or_c.append({f: pat})
        try:
            models = bll.find_list_by_where({"class_id": class_oid, "$or": or_c},
                                            sort_key="order_id", sort_direction=pymongo.DESCENDING, limit=20)
        except Exception as e:
            current_app.logger.error(f"服装搜索异常: {e}"); return []
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
            url = url_links.get_content_url(p.id) if p.id else (url_links.get_content_url(str(p._id)) if p._id else "")
            products.append({
                "title": p.title or "",
                "small_pic": p.small_pic or "",
                "unit_price": float(p.column_11 or 0),
                "market_price": mp,
                "class_name": "服装",
                "sku": str(p._id),
                "url": url,
                "remarks": p.column_7 or "",
            })
        return products

    def no_result_reply(self, params: dict) -> str:
        parts = [v for f in ("category","color","size") if (v := (params.get(f) or "").strip())]
        kw = " ".join(parts) if parts else "相关"
        return f"<p>抱歉，没有找到符合 <strong>{kw}</strong> 的服装 😅</p><p>请调整一下筛选条件试试。</p>"
    def guide_fallback_reply(self) -> str:
        return "<p>请告诉我您想找什么样的服装？比如：</p><p>• 红色连衣裙 M 码<br>• 白色纯棉T恤<br>• 黑色西装外套 XL</p>"
    def build_custom_instruction(self, params: dict, exact: bool) -> str:
        cat, col = (params.get("category") or "").strip(), (params.get("color") or "").strip()
        if exact: return "客户明确说了服装品类。热情介绍产品，引导点击 [+] 加入询价单。"
        if cat and not col: return f"客户只说了品类{cat}没提颜色。请客户看看这些是否合适。如果客户确认，引导点击 [+] 加入询价单。"
        if col and not cat: return f"客户只说了颜色{col}没提品类。请客户看看这些是否匹配。如果客户确认，引导点击 [+] 加入询价单。"
        return "信息不完整。请客户看看这些是否匹配。如果客户确认，引导点击 [+] 加入询价单。"