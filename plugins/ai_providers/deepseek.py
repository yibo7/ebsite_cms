"""
DeepSeek AI 提供者插件

API 文档：https://platform.deepseek.com/api-docs
"""
import json
from typing import Tuple

import requests

from plugins.plugin_base import AIProviderBase, plugin_attribute


@plugin_attribute("DeepSeek", "1.0", "ebsite")
class DeepSeekProvider(AIProviderBase):
    """DeepSeek 大模型调用（兼容 OpenAI 格式）"""

    BASE_URL = "https://api.deepseek.com/v1/chat/completions"

    def __init__(self, current_app):
        self.api_key: str = ""
        self.model: str = "deepseek-chat"
        self.info = "DeepSeek 大模型（兼容 OpenAI 格式）"
        super().__init__(current_app)

    def chat(self, messages: list, system_prompt: str = "", **kwargs) -> dict:
        temperature = kwargs.get("temperature", 0.7)
        max_tokens = kwargs.get("max_tokens", 2048)
        response_format = kwargs.get("response_format")

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                *messages,
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            payload["response_format"] = response_format

        resp = requests.post(
            self.BASE_URL,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=kwargs.get("timeout", 60),
        )
        resp.raise_for_status()
        data = resp.json()
        choice = data["choices"][0]

        return {
            "reply": choice["message"]["content"],
            "finish_reason": choice.get("finish_reason", "stop"),
            "usage": {
                "prompt_tokens": data.get("usage", {}).get("prompt_tokens", 0),
                "completion_tokens": data.get("usage", {}).get("completion_tokens", 0),
            },
        }

    def params_temp(self):
        return '''
        <div class="mb-3">
            <label>API Key <span style="color: red;">*</span></label>
            <input name="api_key" value="{{model.api_key}}" style="max-width:500px" class="form-control" required>
            <small class="form-text text-muted">
                在 <a href="https://platform.deepseek.com/api_keys" target="_blank">DeepSeek 平台</a> 创建 API Key
            </small>
        </div>
        <div class="mb-3">
            <label>模型名称</label>
            <input name="model" value="{{model.model}}" style="max-width:500px" class="form-control" placeholder="deepseek-chat">
            <small class="form-text text-muted">默认 deepseek-chat，可选 deepseek-reasoner 等</small>
        </div>
        <div class="alert alert-info mt-3">
            <strong>使用说明：</strong><br>
            1. 在 DeepSeek 平台注册并获取 API Key<br>
            2. DeepSeek 兼容 OpenAI 格式，参数设置与 OpenAI 类似<br>
            3. 模型建议使用 <strong>deepseek-chat</strong>（性价比最高）<br>
            4. 本插件支持 response_format 参数，可要求 AI 返回 JSON
        </div>
        '''