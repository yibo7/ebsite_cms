"""
京东 JoyAgent AI 供应商实现

说明：
  JoyAgent 使用兼容 OpenAI 的 chat/completions 接口，
  但返回内容为纯文本（不支持 response_format: json_object），
  因此需要额外做一次 JSON 解析，解析失败时返回兜底结构。

API 端点：{BASE_URL}/chat/completions
"""
import json
import re
import requests
from . import AiProviderBase, register_provider


@register_provider('joyagent')
class JoyAgentProvider(AiProviderBase):
    """京东 JoyAgent 大模型调用"""

    BASE_URL = "https://agentrs.jd.com/api/saas/openai-u/v1"

    def chat(self, messages: list, system_prompt: str) -> dict:
        resp = requests.post(
            f"{self.BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": self.model or "DeepSeek-V4-Flash",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    *messages
                ],
            },
            # 超时：120 秒（产品目录较大，处理需要时间）
            timeout=120
        )
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]

        # JoyAgent 不支持 response_format，尝试从返回文本中提取 JSON
        return self._parse_reply(content)

    def _parse_reply(self, content: str) -> dict:
        """从 AI 回复文本中提取 JSON 结构"""
        # 尝试直接解析
        content = content.strip()
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # 尝试提取 ```json ... ``` 代码块
        json_match = re.search(
            r'```(?:json)?\s*\n?(.*?)\n?```', content, re.DOTALL
        )
        if json_match:
            try:
                return json.loads(json_match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # 尝试提取最外层的 { ... }
        brace_match = re.search(r'(\{.*\})', content, re.DOTALL)
        if brace_match:
            try:
                return json.loads(brace_match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # 全失败：将整个回复作为 reply，matches 为空
        return {"reply": content, "matches": []}