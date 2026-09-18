"""
阿里千问 AI 供应商实现
API 文档：https://help.aliyun.com/zh/model-studio/
千问兼容 OpenAI 格式，端点使用 dashscope.aliyuncs.com
"""
import json
import requests
from . import AiProviderBase, register_provider


@register_provider('qwen')
class QwenProvider(AiProviderBase):
    """阿里千问大模型调用（兼容 OpenAI 格式）"""

    BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"

    def chat(self, messages: list, system_prompt: str) -> dict:
        resp = requests.post(
            self.BASE_URL,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": self.model or "qwen-plus",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    *messages
                ],
                "temperature": 0.3,
                "response_format": {"type": "json_object"}
            },
            timeout=60
        )
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        return json.loads(content)