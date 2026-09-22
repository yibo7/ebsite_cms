"""
提示词配置 - 数据模型与业务层

将 AI 提示词从代码硬编码迁移到 MongoDB 存储，
支持在后台管理页面直接编辑，无需重启生效。

集合名：ShopQuotePrompts（由类名 BllBase 自动派生）
"""
from datetime import datetime
from typing import Optional

from flask import Flask
from bll.bll_base import BllBase
from entity.entity_base import ModelBase


class ShopQuotePromptsModel(ModelBase):
    """提示词配置（单例文档：profile_key="default"）"""
    def __init__(self):
        super().__init__()
        self.profile_key: str = "default"
        self.shop_name: str = ""
        self.welcome_message: str = ""     # 欢迎语（支持 HTML）
        self.extract_prompt: str = ""      # AI 提取参数提示词
        self.sales_prompt_tpl: str = ""    # 销售文案模板（含 {} 占位符）
        self.guide_prompt: str = ""        # 引导客户提示词
        self.updated_at: Optional[datetime] = None


# ═════════════════════════════════════════════════════════════════
#  初始提示词 —— 由各品类 Handler 自带的默认值写入
#  此处不再定义硬编码默认值，运行时回退由 _get_prompt() 委托到 Handler
# ═════════════════════════════════════════════════════════════════


class ShopQuotePrompts(BllBase[ShopQuotePromptsModel]):
    """
    提示词配置业务层

    集合名 ShopQuotePrompts，存储单例文档 (profile_key="default")。
    """

    def __init__(self, app: Optional[Flask] = None):
        super().__init__(app)

    def new_instance(self) -> ShopQuotePromptsModel:
        return ShopQuotePromptsModel()

    # ── 读取 ──

    def get_config(self) -> Optional[ShopQuotePromptsModel]:
        """获取单例配置文档，不存在返回 None"""
        return self.find_one_by_where({"profile_key": "default"})

    def get_field(self, field: str) -> str:
        """
        从 DB 读取指定字段值

        @param field: extract_prompt / sales_prompt_tpl / guide_prompt / shop_name / welcome_message
        @return: 字段值字符串，不存在返回 ""
        """
        config = self.get_config()
        if config:
            return getattr(config, field, "") or ""
        return ""

    # ── 写入 ──

    def save_config(self, data: dict):
        """保存或更新配置（upsert）"""
        data["updated_at"] = datetime.now()
        self.table.update_one(
            {"profile_key": "default"},
            {"$set": data},
            upsert=True,
        )

    # ── 初始化 ──

    def ensure_seeded(self):
        """
        如果数据库中没有配置文档，用当前品类 Handler 的默认值创建一份。
        切换品类后不会覆盖已有配置（管理员可手动在后台编辑）。
        """
        existing = self.get_config()
        if existing:
            return

        # 获取当前 Handler 的出厂默认值
        from ..ai_handlers import get_ai_handler
        handler = get_ai_handler()

        self.save_config({
            "shop_name": handler.default_shop_name,
            "welcome_message": handler.default_welcome_message,
            "extract_prompt": handler.default_extract_prompt,
            "sales_prompt_tpl": handler.default_sales_prompt_tpl,
            "guide_prompt": handler.default_guide_prompt,
        })