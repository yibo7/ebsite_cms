"""
品类处理器 — 插件式架构

标准化商品数据结构（search / matches / quote 存储统一使用此格式）：
  {
      "title": "商品名称",
      "small_pic": "商品封面图片 URL",
      "unit_price": 20.0,
      "market_price": 25.0,
      "class_name": "分类名称",
      "sku": "商品 SKU 或 ID",
      "url": "商品详情页链接",
      "remarks": "备注信息（规格、说明等）",
  }
"""
from abc import ABC, abstractmethod

_HANDLER_REGISTRY = {}


def register_ai_handler(name: str):
    def wrapper(cls):
        _HANDLER_REGISTRY[name] = cls
        return cls
    return wrapper


class AiHandlerBase(ABC):
    display_name: str = ""
    default_shop_name: str = ""
    default_welcome_message: str = ""
    default_extract_prompt: str = ""
    default_sales_prompt_tpl: str = ""
    default_guide_prompt: str = ""

    @abstractmethod
    def search(self, params: dict) -> list[dict]:
        ...

    def no_result_reply(self, params: dict) -> str:
        return "<p>抱歉，没有找到匹配的产品 😅</p>"

    def guide_fallback_reply(self) -> str:
        return "<p>请提供商品相关信息。</p>"

    @abstractmethod
    def build_custom_instruction(self, params: dict, exact: bool) -> str:
        ...


def get_ai_handler() -> AiHandlerBase:
    from .. import bp_quote_apis
    config = bp_quote_apis.config or {}
    name = config.get('product_type', 'printer_drum')
    cls = _HANDLER_REGISTRY.get(name)
    if not cls:
        raise ValueError(f"不支持的品类: {name}，可用: {list(_HANDLER_REGISTRY.keys())}")
    return cls()


from . import printer_drum
from . import clothing