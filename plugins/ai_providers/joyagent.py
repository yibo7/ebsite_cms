"""
京东 JoyAgent AI 提供者插件

API 端点：{BASE_URL}/chat/completions

说明：
  JoyAgent 使用兼容 OpenAI 的 chat/completions 接口，
  但不支持 response_format: json_object。
"""
import json
import re
from typing import Tuple

import requests

from plugins.plugin_base import AIProviderBase, plugin_attribute


@plugin_attribute("京东 JoyAgent", "1.0", "ebsite")
class JoyAgentProvider(AIProviderBase):
    """京东 JoyAgent 大模型调用"""

    BASE_URL = "https://agentrs.jd.com/api/saas/openai-u/v1"

    def __init__(self, current_app):
        self.api_key: str = ""
        self.model: str = "DeepSeek-V4-Flash"
        self.info = "京东 JoyAgent 大模型"
        super().__init__(current_app)

    def chat(self, messages: list, system_prompt: str = "", **kwargs) -> dict:
        temperature = kwargs.get("temperature", 0.7)
        max_tokens = kwargs.get("max_tokens", 4096)

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                *messages,
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        resp = requests.post(
            f"{self.BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=kwargs.get("timeout", 120),
        )
        resp.raise_for_status()
        data = resp.json()
        choice = data["choices"][0]
        content = choice["message"]["content"]

        return {
            "reply": content,
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
            <small class="form-text text-muted">京东 JoyAgent 平台提供的 API Key</small>
        </div>
        <div class="mb-3">
            <label>模型名称</label>
            <input name="model" value="{{model.model}}" style="max-width:500px" class="form-control" placeholder="DeepSeek-V4-Flash">
            <small class="form-text text-muted">默认 DeepSeek-V4-Flash</small>
        </div>
        <div class="alert alert-info mt-3">
            <strong>使用说明：</strong><br>
            1. 在京东 JoyAgent 平台获取 API Key<br>
            2. 注意：JoyAgent <strong>不支持</strong> response_format 参数<br>
            3. 如需 AI 返回结构化 JSON，请在 system_prompt 中明确要求<br>
            4. JoyAgent 底层使用 DeepSeek 模型，效果与 DeepSeek 官方接近
        </div>
        '''