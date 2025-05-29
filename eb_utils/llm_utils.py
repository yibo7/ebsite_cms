import requests
import json


def qianwen_request(prompt, api_key):
    url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"

    headers = {
        "Content-Type": "application/json",
        "Authorization": api_key,
        "Connection": "keep-alive",
        "Accept": "*/*"
    }

    payload = {
        "model": "qwen-turbo",
        "input": {
            "prompt": prompt
        }
    }

    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()  # 抛出异常，如果请求不成功
        result = response.json()
        return result['output']['text']
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        return None
    except KeyError as e:
        print(f"Unexpected response format: {e}")
        return None

