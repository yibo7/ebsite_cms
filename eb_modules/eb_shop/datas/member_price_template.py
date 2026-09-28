"""
会员价模板 · 数据模型与业务逻辑

数据模型 MemberPriceTemplate（MongoDB 集合）：
    {
        _id: ObjectId,
        name: str,              # 模板名称
        category_id: str,       # 适用分类 ID
        pricing_base: str,      # 计价基准：market_price | cost_price
        group_rates: [          # 会员组系数数组
            { group_id: str, group_name: str, rate: float }
        ],
        created_at: float,
        updated_at: float,
        created_by: str
    }
"""

import time
from decimal import Decimal
from typing import Optional
from bson import ObjectId
from flask import current_app

from . import get_db

_COLLECTION = "MemberPriceTemplate"
VALID_PRICING_BASES = ("market_price", "cost_price")

# ──────────────────────────────────────────────
#  校验
# ──────────────────────────────────────────────

def validate_template(data: dict) -> list:
    """
    校验会员价模板数据的合法性。

    Args:
        data: 模板数据字典

    Returns:
        错误消息列表，为空表示校验通过
    """
    errors = []

    name = (data.get('name') or '').strip()
    if not name:
        errors.append("模板名称不能为空")

    category_id = (data.get('category_id') or '').strip()
    if not category_id:
        errors.append("请选择适用分类")

    pricing_base = data.get('pricing_base', '')
    if pricing_base not in VALID_PRICING_BASES:
        errors.append("计价基准不合法")

    # 会员组系数校验
    group_rates = data.get('group_rates', []) or []
    has_valid = False
    for gr in group_rates:
        rate = gr.get('rate')
        if rate is None or rate == '':
            continue
        try:
            rate = float(rate)
        except (ValueError, TypeError):
            errors.append(f"会员组「{gr.get('group_name', '')}」的系数格式不正确")
            continue

        if rate <= 0:
            errors.append(f"会员组「{gr.get('group_name', '')}」的系数必须为正数")
            continue

        if pricing_base == "market_price" and rate > 1:
            errors.append(f"会员组「{gr.get('group_name', '')}」：零售价折扣率不能大于 1（当前 {rate}）")

        if pricing_base == "cost_price" and rate < 1:
            errors.append(f"会员组「{gr.get('group_name', '')}」：成本价加价率不能小于 1（当前 {rate}）")

        has_valid = True

    if not has_valid:
        errors.append("至少需要一个会员组设置系数")

    return errors


def parse_group_rates_from_form(form: dict) -> list:
    """
    解析表单提交的会员组系数数据。

    表单中字段的命名约定：
        - group_rate_{group_id}

    Args:
        form: 表单数据

    Returns:
        解析后的会员组系数列表，每项含 group_id, group_name, rate
    """
    group_rates = []
    # 收集所有 group_rate_ 开头的字段
    for key in form:
        if key.startswith('group_rate_'):
            group_id = key[len('group_rate_'):]
            rate_val = form.get(key, '').strip()
            group_name = form.get(f'group_name_{group_id}', '').strip()

            gr = {
                'group_id': group_id,
                'group_name': group_name,
                'rate': None,
            }

            if rate_val:
                try:
                    gr['rate'] = float(rate_val)
                except (ValueError, TypeError):
                    gr['rate'] = None

            group_rates.append(gr)

    return group_rates


# ──────────────────────────────────────────────
#  CRUD
# ──────────────────────────────────────────────

def get_template_list() -> list:
    """
    获取模板列表，附带分类名称。

    Returns:
        模板列表
    """
    db = get_db()
    cursor = db[_COLLECTION].find().sort("updated_at", -1)
    templates = []
    for item in cursor:
        item['_id'] = str(item['_id'])

        # 分类名称
        cat_id = item.get('category_id', '')
        cat_name = ''
        if cat_id:
            try:
                cat = db["NewsClass"].find_one({"_id": ObjectId(cat_id)}, {"class_name": 1})
                if cat:
                    cat_name = cat.get('class_name', '')
            except Exception:
                pass
        item['category_name'] = cat_name

        # 有系数的会员组数
        group_rates = item.get('group_rates', []) or []
        item['group_count'] = sum(1 for g in group_rates if g.get('rate') is not None and g['rate'] != '')

        # 计价基准中文
        base_map = {
            'market_price': '零售价折扣率',
            'cost_price': '成本价加价率',
        }
        item['pricing_base_name'] = base_map.get(item.get('pricing_base', ''), item.get('pricing_base', ''))

        templates.append(item)
    return templates


def get_template(template_id: str) -> Optional[dict]:
    """获取单个模板"""
    try:
        db = get_db()
        item = db[_COLLECTION].find_one({"_id": ObjectId(template_id)})
        if item:
            item['_id'] = str(item['_id'])
        return item
    except Exception:
        return None


def create_template(data: dict, admin_user_id: str) -> str:
    """创建模板"""
    now = time.time()
    doc = {
        'name': (data.get('name') or '').strip(),
        'category_id': (data.get('category_id') or '').strip(),
        'pricing_base': data.get('pricing_base', 'market_price'),
        'group_rates': data.get('group_rates', []),
        'created_at': now,
        'updated_at': now,
        'created_by': admin_user_id,
    }
    db = get_db()
    result = db[_COLLECTION].insert_one(doc)
    return str(result.inserted_id)


def update_template(template_id: str, data: dict) -> bool:
    """更新模板"""
    try:
        update_data = {}
        if 'name' in data:
            update_data['name'] = (data['name'] or '').strip()
        if 'category_id' in data:
            update_data['category_id'] = (data['category_id'] or '').strip()
        if 'pricing_base' in data:
            update_data['pricing_base'] = data['pricing_base']
        if 'group_rates' in data:
            update_data['group_rates'] = data['group_rates']
        update_data['updated_at'] = time.time()

        db = get_db()
        result = db[_COLLECTION].update_one(
            {"_id": ObjectId(template_id)},
            {"$set": update_data}
        )
        return result.modified_count > 0
    except Exception:
        return False


def delete_template(template_id: str) -> bool:
    """删除模板"""
    try:
        db = get_db()
        result = db[_COLLECTION].delete_one({"_id": ObjectId(template_id)})
        return result.deleted_count > 0
    except Exception:
        return False


def copy_template(template_id: str, admin_user_id: str) -> Optional[str]:
    """复制模板"""
    original = get_template(template_id)
    if not original:
        return None

    now = time.time()
    doc = {
        'name': (original.get('name', '') or '') + ' - 副本',
        'category_id': original.get('category_id', ''),
        'pricing_base': original.get('pricing_base', 'market_price'),
        'group_rates': original.get('group_rates', []),
        'created_at': now,
        'updated_at': now,
        'created_by': admin_user_id,
    }
    db = get_db()
    result = db[_COLLECTION].insert_one(doc)
    return str(result.inserted_id)


# ──────────────────────────────────────────────
#  应用模板到分类
# ──────────────────────────────────────────────

def apply_template_to_category(
    template_id: str,
    apply_mode: str,
    below_cost_strategy: str,
    admin_user_id: str,
    admin_user_name: str,
) -> dict:
    """
    将会员价模板应用到其关联分类下的所有商品。

    Args:
        template_id: 模板 ID
        apply_mode: 'fill_empty' 或 'force_overwrite'
        below_cost_strategy: 低于成本价策略 - 'skip' | 'floor_to_cost' | 'reject_all'
        admin_user_id: 操作人 ID
        admin_user_name: 操作人姓名

    Returns:
        应用结果字典
    """
    template = get_template(template_id)
    if not template:
        return {'success': False, 'message': '模板不存在', 'log_id': None, 'result': None}

    db = get_db()
    nc_collection = db["NewsContent"]

    category_id = template['category_id']
    group_rates = template.get('group_rates', []) or []
    pricing_base = template.get('pricing_base', 'market_price')

    # 过滤出实际设置了系数的会员组
    active_rates = [g for g in group_rates if g.get('rate') is not None and g['rate'] != '']

    # 分类名称
    category_name = ''
    try:
        cat = db["NewsClass"].find_one({"_id": ObjectId(category_id)}, {"class_name": 1})
        if cat:
            category_name = cat.get('class_name', '')
    except Exception:
        pass

    # 统计变量
    total_products = 0
    success_count = 0
    skip_existing_count = 0
    skip_missing_price_count = 0
    error_count = 0
    floor_count = 0
    error_details = []

    cursor = nc_collection.find({"class_id": ObjectId(category_id)})

    for content in cursor:
        products = content.get('column_10', []) or []
        if isinstance(products, str):
            import json
            try:
                products = json.loads(products)
            except (json.JSONDecodeError, TypeError):
                products = []

        if not isinstance(products, list):
            products = []

        content_modified = False
        content_products = []

        for sku in products:
            if not isinstance(sku, dict):
                content_products.append(sku)
                continue

            total_products += 1

            # 检查是否已有会员价
            existing_group_prices = sku.get('group_prices', []) or []
            if existing_group_prices and apply_mode == 'fill_empty':
                content_products.append(sku)
                skip_existing_count += 1
                continue

            # 检查价格基准
            if pricing_base == 'market_price':
                base_price_val = sku.get('marketPrice')
            else:
                base_price_val = sku.get('costPrice')

            if not base_price_val or float(str(base_price_val)) <= 0:
                content_products.append(sku)
                skip_missing_price_count += 1
                continue

            base_price = Decimal(str(base_price_val))
            cost_price = Decimal(str(sku.get('costPrice', 0)))

            # 逐会员组计算价格
            new_group_prices = []
            has_error = False
            has_floor = False

            for gr in active_rates:
                rate = float(gr['rate'])
                unit_price = base_price * Decimal(str(rate))
                # 四舍五入保留2位小数
                import math
                unit_price = math.floor(float(unit_price) * 100) / 100
                unit_price = Decimal(str(unit_price))

                group_name = gr.get('group_name', '')

                # 保本校验
                if unit_price < cost_price:
                    if below_cost_strategy == 'skip':
                        error_details.append({
                            'product_id': str(content.get('_id', '')),
                            'sku': sku.get('sku', ''),
                            'group_name': group_name,
                            'reason': f"会员价 {unit_price} 低于成本价 {cost_price}，跳过"
                        })
                        error_count += 1
                        continue  # 跳过这个会员组
                    elif below_cost_strategy == 'floor_to_cost':
                        unit_price = cost_price
                        has_floor = True
                    elif below_cost_strategy == 'reject_all':
                        error_details.append({
                            'product_id': str(content.get('_id', '')),
                            'sku': sku.get('sku', ''),
                            'group_name': group_name,
                            'reason': f"会员价 {unit_price} 低于成本价 {cost_price}，整单拒绝"
                        })
                        error_count += 1
                        has_error = True
                        break

                new_group_prices.append({
                    'group_id': gr['group_id'],
                    'group_name': group_name,
                    'price': float(unit_price),
                })

            if has_error:
                content_products.append(sku)
                continue

            if has_floor:
                floor_count += 1

            # 更新 SKU 的会员价数据
            sku['group_prices'] = new_group_prices
            content_products.append(sku)
            content_modified = True
            success_count += 1

        if content_modified:
            nc_collection.update_one(
                {"_id": content['_id']},
                {"$set": {"column_10": content_products}}
            )

    # 写入日志
    from .member_price_template_log import write_log
    log_id = write_log({
        'template_id': template_id,
        'template_name': template.get('name', ''),
        'category_id': category_id,
        'category_name': category_name,
        'apply_mode': apply_mode,
        'below_cost_strategy': below_cost_strategy,
        'total_products': total_products,
        'group_count': len(active_rates),
        'success_count': success_count,
        'skip_existing_count': skip_existing_count,
        'skip_missing_price_count': skip_missing_price_count,
        'error_count': error_count,
        'floor_count': floor_count,
        'error_details': error_details,
        'created_by': admin_user_id,
        'created_by_name': admin_user_name,
        'snapshot': '',
    })

    msg_parts = [f"成功 {success_count}"]
    if skip_existing_count:
        msg_parts.append(f"跳过已有 {skip_existing_count}")
    if skip_missing_price_count:
        msg_parts.append(f"跳过缺价 {skip_missing_price_count}")
    if floor_count:
        msg_parts.append(f"兜底 {floor_count}")
    if error_count:
        msg_parts.append(f"异常 {error_count}")

    return {
        'success': True,
        'message': '应用完成：' + '，'.join(msg_parts),
        'log_id': log_id,
        'result': {
            'total_products': total_products,
            'success_count': success_count,
            'skip_existing_count': skip_existing_count,
            'skip_missing_price_count': skip_missing_price_count,
            'error_count': error_count,
            'floor_count': floor_count,
        }
    }


# ──────────────────────────────────────────────
#  辅助函数
# ──────────────────────────────────────────────

def count_products_in_category(category_id: str) -> int:
    """统计指定分类下的商品数量"""
    try:
        db = get_db()
        count = db["NewsContent"].count_documents({"class_id": ObjectId(category_id)})
        return count
    except Exception:
        return 0


def get_product_categories() -> list:
    """获取商品分类列表（用于模板表单的下拉选择）"""
    from eb_modules.eb_shop import bp_shop_pages
    config = getattr(bp_shop_pages, 'config', {}) or {}
    product_class_id = config.get('_product_class_id', '')

    db = get_db()
    try:
        root_oid = ObjectId(product_class_id) if product_class_id else None
    except Exception:
        root_oid = None

    result = []
    if root_oid:
        cats = list(db["NewsClass"].find({
            "$or": [
                {"_id": root_oid},
                {"parent_id": str(root_oid)}
            ]
        }).sort("order_id", 1))
        for c in cats:
            result.append({'_id': str(c['_id']), 'class_name': c.get('class_name', '')})

    if not result:
        cats = list(db["NewsClass"].find({}, {"_id": 1, "class_name": 1}).sort("order_id", 1))
        for c in cats:
            result.append({'_id': str(c['_id']), 'class_name': c.get('class_name', '')})

    return result


def get_sample_product(category_id: str) -> Optional[dict]:
    """
    获取指定分类下的示例商品，用于预览。
    选择规则与阶梯价模板一致。
    """
    try:
        db = get_db()
        cursor = db["NewsContent"].find(
            {"class_id": ObjectId(category_id)},
            {"_id": 1, "title": 1, "column_10": 1}
        ).sort("_id", -1)

        for content in cursor:
            products = content.get('column_10', []) or []
            if isinstance(products, str):
                import json
                try:
                    products = json.loads(products)
                except (json.JSONDecodeError, TypeError):
                    products = []

            if not isinstance(products, list):
                continue

            for sku in products:
                if not isinstance(sku, dict):
                    continue
                mp = sku.get('marketPrice')
                cp = sku.get('costPrice')
                if mp and cp:
                    try:
                        mp_val = float(str(mp))
                        cp_val = float(str(cp))
                        if mp_val > 0 and cp_val > 0:
                            return {
                                'product_id': str(content.get('_id', '')),
                                'product_name': content.get('title', ''),
                                'sku': sku.get('sku', ''),
                                'marketPrice': mp_val,
                                'costPrice': cp_val,
                            }
                    except (ValueError, TypeError):
                        continue

        return None
    except Exception:
        return None


def get_all_member_groups() -> list:
    """
    获取系统所有会员组（用于表单展示）。

    Returns:
        会员组列表，每项含 group_id, group_name
    """
    try:
        db = get_db()
        cursor = db["UserGroup"].find({}, {"_id": 1, "name": 1}).sort("order_id", 1)
        groups = []
        for item in cursor:
            groups.append({
                'group_id': str(item['_id']),
                'group_name': item.get('name', ''),
            })
        return groups
    except Exception:
        return []