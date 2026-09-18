"""
AI 供应商抽象层

职责：
  1. 定义 AiProviderBase 抽象基类，所有供应商必须继承
  2. 提供 get_provider() 工厂方法，根据模块配置反射实例化
  3. 维护 _PROVIDER_REGISTRY 注册表，供应商通过 @register_provider 注册

使用方式：
  provider = get_provider()
  result = provider.chat(messages, system_prompt)
  # result = {"reply": "...", "matches": [...]}
"""
from abc import ABC, abstractmethod
from flask import current_app

# ── 供应商注册表 ──
_PROVIDER_REGISTRY = {}


def register_provider(name: str):
    """装饰器：将供应商类注册到全局注册表"""
    def wrapper(cls):
        _PROVIDER_REGISTRY[name] = cls
        return cls
    return wrapper


class AiProviderBase(ABC):
    """所有 AI 供应商必须继承此类"""

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    @abstractmethod
    def chat(self, messages: list, system_prompt: str) -> dict:
        """
        调用 AI 聊天

        @param messages: 对话历史
            [{"role": "user", "content": "..."},
             {"role": "assistant", "content": "..."}]
        @param system_prompt: 系统提示词（包含完整产品目录）

        @return: dict，必须包含以下结构：
            {
                "reply": "AI 回复文本（可含 HTML）",
                "matches": [
                    {"productId": "MongoDB _id 字符串",
                     "skuIndex": 0,   # column_10 数组中的索引
                     "qty": 10}       # 客户想要的数量
                ]
            }
            无匹配时 matches 返回空数组 []
        """
        ...


def get_provider() -> AiProviderBase:
    """
    根据模块后台配置，反射获取 AI 供应商实例

    从 bp_shop_apis.config 中读取：
      - ai_provider: 供应商名称（deepseek / joyagent / qwen）
      - ai_key:      API 密钥
      - ai_model:    模型名称

    返回：AiProviderBase 子类实例
    抛出：ValueError（不支持的供应商）
    """
    # 避免循环导入：在函数内延迟引用
    from eb_modules.eb_shop import bp_shop_apis
    config = bp_shop_apis.config

    provider_name = config.get('ai_provider', 'deepseek')
    api_key = config.get('ai_key', '')
    model = config.get('ai_model', '')

    cls = _PROVIDER_REGISTRY.get(provider_name)
    if not cls:
        raise ValueError(
            f"不支持的 AI 供应商: {provider_name}，"
            f"可用选项: {list(_PROVIDER_REGISTRY.keys())}"
        )

    return cls(api_key=api_key, model=model)


# ── 导入具体供应商实现，触发 @register_provider 装饰器 ──
from . import deepseek
from . import joyagent
from . import qwen