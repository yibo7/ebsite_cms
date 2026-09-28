"""
应用日志数据模型与查询接口

日志集合 PriceTemplateLog 记录了每次应用模板的执行结果，包括：
- 执行摘要（总数、成功数、跳过数、异常数）
- 异常明细（商品 ID、SKU、原因）
- 操作人与操作时间

冗余字段（template_name, category_name, created_by_name）确保模板被删除后日志仍可读。
"""

import time
from typing import Optional
from bson import ObjectId
from flask import current_app

from . import get_db

# 集合名称
_COLLECTION = "PriceTemplateLog"


def write_log(data: dict) -> str:
    """
    写入一条应用日志。

    Args:
        data: 日志数据字典，包含以下字段：
            - template_id: 模板 ID
            - template_name: 模板名称
            - category_id: 分类 ID
            - category_name: 分类名称
            - apply_mode: 应用方式（fill_empty / force_overwrite）
            - total_products: 遍历商品总数
            - success_count: 成功应用数
            - skip_existing_count: 跳过（已有规则）数
            - skip_missing_price_count: 跳过（缺少价格基准）数
            - error_count: 异常数
            - error_details: 异常明细数组
            - created_by: 操作人 ID
            - created_by_name: 操作人姓名

    Returns:
        日志记录的 _id 字符串
    """
    data['created_at'] = time.time()
    db = get_db()
    result = db[_COLLECTION].insert_one(data)
    return str(result.inserted_id)


def get_log_list(limit: int = 50) -> list:
    """
    获取应用日志列表，按时间倒序排列。

    Args:
        limit: 返回条数上限，默认 50

    Returns:
        日志记录列表
    """
    db = get_db()
    cursor = db[_COLLECTION].find().sort("created_at", -1).limit(limit)
    logs = []
    for item in cursor:
        item['_id'] = str(item['_id'])
        logs.append(item)
    return logs


def get_log(log_id: str) -> Optional[dict]:
    """
    获取单条应用日志详情。

    Args:
        log_id: 日志 ID

    Returns:
        日志记录字典，或 None
    """
    try:
        db = get_db()
        item = db[_COLLECTION].find_one({"_id": ObjectId(log_id)})
        if item:
            item['_id'] = str(item['_id'])
        return item
    except Exception:
        return None