"""
会员价应用日志 · 写入与查询

集合 MemberPriceTemplateLog 记录了每次应用会员价模板的执行结果。
"""

import time
from typing import Optional
from bson import ObjectId
from . import get_db

_COLLECTION = "MemberPriceTemplateLog"


def write_log(data: dict) -> str:
    """
    写入一条应用日志。

    Args:
        data: 日志数据字典

    Returns:
        日志记录的 _id 字符串
    """
    data['created_at'] = time.time()
    db = get_db()
    result = db[_COLLECTION].insert_one(data)
    return str(result.inserted_id)


def get_log_list(limit: int = 50) -> list:
    """获取应用日志列表，按时间倒序排列"""
    db = get_db()
    cursor = db[_COLLECTION].find().sort("created_at", -1).limit(limit)
    logs = []
    for item in cursor:
        item['_id'] = str(item['_id'])
        logs.append(item)
    return logs


def get_log(log_id: str) -> Optional[dict]:
    """获取单条应用日志详情"""
    try:
        db = get_db()
        item = db[_COLLECTION].find_one({"_id": ObjectId(log_id)})
        if item:
            item['_id'] = str(item['_id'])
        return item
    except Exception:
        return None