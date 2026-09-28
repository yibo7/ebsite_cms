"""
eb_shop datas 模块入口
统一导出数据库连接，供 price_template.py 和 price_template_log.py 使用。
"""

from flask import current_app


def get_db():
    """获取当前 Flask 应用的 MongoDB 数据库实例"""
    return current_app.db