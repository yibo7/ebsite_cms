"""
阿里千问 AI 提供者插件

API 文档：https://help.aliyun.com/zh/model-studio/
千问兼容 OpenAI 格式，端点使用 dashscope.aliyuncs.com
"""
from typing import Tuple

import requests

from plugins.plugin_base import AIProviderBase, plugin_attribute


@plugin_attribute("阿里千问", "1.0", "ebsite")
class QwenProvider(AIProviderBase):
    """阿里千问大模型调用（兼容 OpenAI 格式）"""

    BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"

    def __init__(self, current_app):
        self.api_key: str = ""
        self.model: str = "qwen-plus"
        self.info = "阿里千问大模型"
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
                在 <a href="https://help.aliyun.com/zh/model-studio/getting-started/" target="_blank">阿里云模型服务灵积</a> 获取 API Key
            </small>
        </div>
        <div class="mb-3">
            <label>模型名称</label>
            <input name="model" value="{{model.model}}" style="max-width:500px" class="form-control" placeholder="qwen-plus">
            <small class="form-text text-muted">默认 qwen-plus，可选 qwen-max、qwen-turbo 等</small>
        </div>
        <div class="alert alert-info mt-3">
            <strong>使用说明：</strong><br>
            1. 在阿里云开通模型服务灵积（DashScope）并获取 API Key<br>
            2. 千问兼容 OpenAI 接口格式，可直接替换 OpenAI 使用<br>
            3. 模型建议：<strong>qwen-plus</strong> 性价比较好，<strong>qwen-max</strong> 效果最佳<br>
            4. 注意：阿里云 API Key 需要在控制台设置 IP 白名单才能调用
        </div>
        '''