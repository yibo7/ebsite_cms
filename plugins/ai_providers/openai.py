"""
OpenAI AI 提供者插件

API 文档：https://platform.openai.com/docs/api-reference/chat
"""
from typing import Tuple

import requests

from plugins.plugin_base import AIProviderBase, plugin_attribute


@plugin_attribute("OpenAI", "1.0", "ebsite")
class OpenAIProvider(AIProviderBase):
    """OpenAI 大模型调用（标准 API）"""

    BASE_URL = "https://api.openai.com/v1/chat/completions"

    def __init__(self, current_app):
        self.api_key: str = ""
        self.model: str = "gpt-4o-mini"
        self.endpoint: str = ""  # 自定义端点（可选，兼容代理或国内镜像）
        self.info = "OpenAI 大模型"
        super().__init__(current_app)

    def _api_url(self) -> str:
        return self.endpoint.strip() or self.BASE_URL

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
            self._api_url(),
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
                在 <a href="https://platform.openai.com/api-keys" target="_blank">OpenAI 平台</a> 创建 API Key
            </small>
        </div>
        <div class="mb-3">
            <label>模型名称</label>
            <input name="model" value="{{model.model}}" style="max-width:500px" class="form-control" placeholder="gpt-4o-mini">
            <small class="form-text text-muted">默认 gpt-4o-mini，可选 gpt-4o、gpt-4-turbo 等</small>
        </div>
        <div class="mb-3">
            <label>自定义端点（可选）</label>
            <input name="endpoint" value="{{model.endpoint}}" style="max-width:500px" class="form-control" placeholder="https://api.openai.com/v1/chat/completions">
            <small class="form-text text-muted">留空使用官方端点，如需代理或国内镜像请填写完整 URL</small>
        </div>
        <div class="alert alert-info mt-3">
            <strong>使用说明：</strong><br>
            1. 在 OpenAI 平台注册并创建 API Key<br>
            2. 模型建议：<strong>gpt-4o-mini</strong>（性价比高），<strong>gpt-4o</strong>（效果最佳）<br>
            3. 如需使用国内代理或 Azure OpenAI，请在「自定义端点」中填写对应 URL<br>
            4. 本插件支持 response_format 参数，可要求 AI 返回 JSON 对象
        </div>
        '''