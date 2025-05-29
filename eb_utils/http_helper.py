import decimal
import re
from decimal import Decimal

from flask import request


def get_prams(key: str):
    s_value = None
    if request.method == 'POST':
        s_value = request.form.get(key, None)
    else:
        s_value = request.args.get(key, None)

    if s_value == 'None':  # 隐藏的Id控件默认是字符串的None
        s_value = None

    return s_value


def get_prams_dict():
    dict_prams = {}
    if request.method == 'POST':
        dict_prams = request.form.to_dict()
    else:
        dict_prams = request.args.to_dict()
    for key, value in dict_prams.items():
        if value == 'on':
            dict_prams[key] = True
        elif value == 'checkbox_unchecked':
            dict_prams[key] = False
    return dict_prams

def clean_dict(data: dict) -> dict:
    cleaned_data = {}
    for key, value in data.items():
        # 限制键值为字符串，避免嵌套字段注入
        if isinstance(key, str) and isinstance(value, str):
            safe_key = clean_keywords(key.strip())       # 清除空白并转义特殊字符
            safe_value = clean_keywords(value.strip(),False,1000)   # XSS 防护
            cleaned_data[safe_key] = safe_value
    return cleaned_data

def clean_keywords(key_words: str,is_clear_re_dos = True,cut_len:int = 100) -> str:
    # 1. 去除首尾空格
    cleaned = key_words.strip()

    # 2. 限制长度，防止构造攻击或浪费资源
    cleaned = cleaned[:cut_len]

    # 3. 移除 MongoDB 查询关键字符（避免被识别为操作符）
    cleaned = cleaned.replace('$', '').replace('{', '').replace('}', '')

    # 4. 清除危险的正则控制字符（防止 ReDoS）,但会去掉.号*号等待，比如abc@163.com并会变成abc@163com
    if is_clear_re_dos:
        cleaned = re.sub(r'[\[\]\(\)\.\*\+\?\^\|\\]', '', cleaned)

    # 5. 替换连续空白为单空格
    cleaned = re.sub(r'\s+', ' ', cleaned)

    # 6. （可选）禁止纯特殊字符输入
    if re.fullmatch(r'[\W_]+', cleaned):
        cleaned = ''

    return cleaned

def get_prams_int(key: str, default: int = 0) -> int:
    s_value = get_prams(key)
    if s_value:
        return int(s_value)
    return default


def get_prams_float(key: str, default: float = 0.0) -> float:
    s_value = get_prams(key)
    if s_value:
        return float(s_value)
    return default


def get_prams_decimal(key: str, default: decimal = 0.0) -> decimal:
    s_value = get_prams(key)
    if s_value:
        return Decimal(s_value)
    return default


def get_prams_bool(key: str, default: bool = False) -> bool:
    s_value = get_prams(key)
    if s_value:
        return bool(s_value)
    return default


def get_ip():
    ip = request.remote_addr
    return ip


def get_url_full():
    url = request.url
    return url
