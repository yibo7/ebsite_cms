"""
阶梯价模板 · 数据模型与业务逻辑

职责：
    - 模板数据的增删改查
    - 模板校验逻辑
    - 表单档位解析
    - 应用模板到分类的核心逻辑
    - 统计分类下商品数
    - 复制模板
    - 获取示例商品（用于预览）

数据模型 PriceTemplate（MongoDB 集合）：
    {
        _id: ObjectId,
        name: str,              # 模板名称
        category_id: str,       # 适用分类 ID（NewsClass 的 _id）
        pricing_base: str,      # 计价基准：market_price | cost_price
        tiers: [                # 阶梯规则数组
            { min_qty: int, max_qty: int | None, rate: float }
        ],
        created_at: float,      # 创建时间戳
        updated_at: float,      # 更新时间戳
        created_by: str         # 创建人 ID
    }
"""

import time
import math
from decimal import Decimal
from typing import Optional
from bson import ObjectId
from flask import current_app

from . import get_db

# 集合名称
_COLLECTION = "PriceTemplate"

# ──────────────────────────────────────────────
#  常量
# ──────────────────────────────────────────────

VALID_PRICING_BASES = ("market_price", "cost_price")

# ──────────────────────────────────────────────
#  校验
# ──────────────────────────────────────────────

def validate_template(data: dict) -> list:
    """
    校验模板数据的合法性。

    Args:
        data: 模板数据字典

    Returns:
        错误消息列表，为空表示校验通过
    """
    errors = []

    # 1. 模板名称不能为空
    name = (data.get('name') or '').strip()
    if not name:
        errors.append("模板名称不能为空")

    # 2. 必须选择适用分类
    category_id = (data.get('category_id') or '').strip()
    if not category_id:
        errors.append("请选择适用分类")

    # 3. 计价基准必须合法
    pricing_base = data.get('pricing_base', '')
    if pricing_base not in VALID_PRICING_BASES:
        errors.append("计价基准不合法")

    # 4. 档位校验
    tiers = data.get('tiers', [])
    if not tiers or not isinstance(tiers, list):
        errors.append("至少需要一个档位")
        return errors

    # 过滤无效行
    valid_tiers = [t for t in tiers if t.get('min_qty') is not None and t.get('min_qty') != '']
    if len(valid_tiers) < 1:
        errors.append("至少需要一个档位")
        return errors

    # 排序检查（按 min_qty 升序）
    sorted_tiers = sorted(valid_tiers, key=lambda t: int(t['min_qty']))

    for i, tier in enumerate(sorted_tiers):
        min_qty = int(tier['min_qty'])
        max_qty = tier.get('max_qty')
        rate = tier.get('rate')

        # 检查系数是否有效
        if rate is None or rate == '':
            errors.append(f"档位 {min_qty}+ 的系数不能为空")
            continue
        try:
            rate = float(rate)
        except (ValueError, TypeError):
            errors.append(f"档位 {min_qty}+ 的系数格式不正确")
            continue

        # 区间连续性检查（从第二档开始）
        if i > 0:
            prev_max = sorted_tiers[i - 1].get('max_qty')
            if prev_max is not None and prev_max != '' and prev_max != 0:
                if int(prev_max) + 1 != min_qty:
                    errors.append(f"档位区间不连续：第 {i} 档上限为 {prev_max}，第 {i + 1} 档下限为 {min_qty}")
            elif prev_max is None or prev_max == '' or prev_max == 0:
                errors.append(f"只有最后一档的上限可以为空/0")

        # 最后一档上限必须为空或0
        if i == len(sorted_tiers) - 1:
            if max_qty is not None and max_qty != '' and max_qty != 0:
                errors.append("最后一档的上限必须为空或0")
        else:
            if max_qty is None or max_qty == '' or max_qty == 0:
                errors.append(f"第 {i + 1} 档不是最后一档，上限不能为空或0")

        # 基于零售价折扣率时，系数 ≤ 1
        if pricing_base == "market_price" and rate > 1:
            errors.append(f"档位 {min_qty}+：零售价折扣率不能大于 1（当前 {rate}）")

        # 基于成本价加价率时，系数 ≥ 1
        if pricing_base == "cost_price" and rate < 1:
            errors.append(f"档位 {min_qty}+：成本价加价率不能小于 1（当前 {rate}）")

    # 系数随数量递增而递减
    for i in range(len(sorted_tiers) - 1):
        r1 = float(sorted_tiers[i]['rate'])
        r2 = float(sorted_tiers[i + 1]['rate'])
        if r2 >= r1:
            errors.append(
                f"系数必须随数量递增而递减：档 {sorted_tiers[i]['min_qty']}+ 系数为 {r1}，"
                f"档 {sorted_tiers[i + 1]['min_qty']}+ 系数为 {r2}"
            )

    return errors


def parse_tiers_from_form(form: dict) -> list:
    """
    解析表单提交的档位数据。

    表单中档位字段的命名约定：
        - tier_min_qty_0, tier_min_qty_1, ...
        - tier_max_qty_0, tier_max_qty_1, ...
        - tier_rate_0, tier_rate_1, ...

    Args:
        form: 表单数据（request.form 或 request.args）

    Returns:
        解析后的档位列表，每项含 min_qty, max_qty, rate
    """
    tiers = []
    # 收集所有档位索引
    indices = set()
    for key in form:
        if key.startswith('tier_min_qty_'):
            try:
                idx = int(key.split('_')[-1])
                indices.add(idx)
            except (ValueError, IndexError):
                pass

    for idx in sorted(indices):
        min_qty = form.get(f'tier_min_qty_{idx}')
        max_qty = form.get(f'tier_max_qty_{idx}')
        rate = form.get(f'tier_rate_{idx}')

        # 跳过空行
        if not min_qty and not rate:
            continue

        tier = {}
        try:
            tier['min_qty'] = int(min_qty) if min_qty else None
        except (ValueError, TypeError):
            tier['min_qty'] = None

        if max_qty is not None and max_qty != '':
            try:
                tier['max_qty'] = int(max_qty)
            except (ValueError, TypeError):
                tier['max_qty'] = None
        else:
            tier['max_qty'] = None

        if rate is not None and rate != '':
            try:
                tier['rate'] = float(rate)
            except (ValueError, TypeError):
                tier['rate'] = None
        else:
            tier['rate'] = None

        # 行数据无效时跳过
        if tier['min_qty'] is None and tier['rate'] is None:
            continue

        tiers.append(tier)

    return tiers


# ──────────────────────────────────────────────
#  CRUD
# ──────────────────────────────────────────────

def get_template_list() -> list:
    """
    获取模板列表，附带分类名称。

    Returns:
        模板列表（已添加 category_name 字段）
    """
    db = get_db()
    cursor = db[_COLLECTION].find().sort("updated_at", -1)
    templates = []
    for item in cursor:
        item['_id'] = str(item['_id'])

        # 查询分类名称
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

        # 档位数
        tiers = item.get('tiers', []) or []
        item['tier_count'] = len(tiers)

        # 计价基准中文
        base_map = {
            'market_price': '零售价折扣率',
            'cost_price': '成本价加价率',
        }
        item['pricing_base_name'] = base_map.get(item.get('pricing_base', ''), item.get('pricing_base', ''))

        templates.append(item)
    return templates


def get_template(template_id: str) -> Optional[dict]:
    """
    获取单个模板。

    Args:
        template_id: 模板 ID

    Returns:
        模板字典，或 None
    """
    try:
        db = get_db()
        item = db[_COLLECTION].find_one({"_id": ObjectId(template_id)})
        if item:
            item['_id'] = str(item['_id'])
        return item
    except Exception:
        return None


def create_template(data: dict, admin_user_id: str) -> str:
    """
    创建模板。

    Args:
        data: 模板数据字典
        admin_user_id: 创建人 ID

    Returns:
        新模板的 _id 字符串
    """
    now = time.time()
    doc = {
        'name': (data.get('name') or '').strip(),
        'category_id': (data.get('category_id') or '').strip(),
        'pricing_base': data.get('pricing_base', 'market_price'),
        'tiers': data.get('tiers', []),
        'created_at': now,
        'updated_at': now,
        'created_by': admin_user_id,
    }
    db = get_db()
    result = db[_COLLECTION].insert_one(doc)
    return str(result.inserted_id)


def update_template(template_id: str, data: dict) -> bool:
    """
    更新模板。

    Args:
        template_id: 模板 ID
        data: 要更新的字段

    Returns:
        是否更新成功
    """
    try:
        update_data = {}
        if 'name' in data:
            update_data['name'] = (data['name'] or '').strip()
        if 'category_id' in data:
            update_data['category_id'] = (data['category_id'] or '').strip()
        if 'pricing_base' in data:
            update_data['pricing_base'] = data['pricing_base']
        if 'tiers' in data:
            update_data['tiers'] = data['tiers']
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
    """
    删除模板。

    Args:
        template_id: 模板 ID

    Returns:
        是否删除成功
    """
    try:
        db = get_db()
        result = db[_COLLECTION].delete_one({"_id": ObjectId(template_id)})
        return result.deleted_count > 0
    except Exception:
        return False


def copy_template(template_id: str, admin_user_id: str) -> Optional[str]:
    """
    复制模板。

    复制计价基准、阶梯规则，新模板名称自动加后缀" - 副本"。

    Args:
        template_id: 原模板 ID
        admin_user_id: 当前操作人 ID

    Returns:
        新模板的 _id 字符串，失败返回 None
    """
    original = get_template(template_id)
    if not original:
        return None

    now = time.time()
    doc = {
        'name': (original.get('name', '') or '') + ' - 副本',
        'category_id': original.get('category_id', ''),
        'pricing_base': original.get('pricing_base', 'market_price'),
        'tiers': original.get('tiers', []),
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
    admin_user_id: str,
    admin_user_name: str,
) -> dict:
    """
    将模板应用到其关联分类下的所有商品。

    执行流程：
        1. 获取模板
        2. 查询该分类下所有商品（NewsContent）
        3. 遍历每个商品的每个 SKU，按模板规则计算阶梯价
        4. 保本校验（单价不得低于成本价）
        5. 更新 SKU 的 group_qty_prices 字段
        6. 写入应用日志

    Args:
        template_id: 模板 ID
        apply_mode: 应用方式 - 'fill_empty' 仅补充空白 / 'force_overwrite' 强制覆盖
        admin_user_id: 操作人 ID
        admin_user_name: 操作人姓名

    Returns:
        应用结果字典，包含以下字段：
            - success: bool
            - message: str
            - log_id: str | None
            - result: dict（统计数字）
    """
    template = get_template(template_id)
    if not template:
        return {'success': False, 'message': '模板不存在', 'log_id': None, 'result': None}

    db = get_db()
    nc_collection = db["NewsContent"]

    category_id = template['category_id']
    tiers = template.get('tiers', []) or []
    pricing_base = template.get('pricing_base', 'market_price')

    # 获取分类名称
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
    error_details = []

    # 查询该分类下的所有商品
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

            # 检查是否已有阶梯规则
            existing_qty_prices = sku.get('group_qty_prices', []) or []
            if existing_qty_prices and apply_mode == 'fill_empty':
                content_products.append(sku)
                skip_existing_count += 1
                continue

            # 检查价格基准是否存在
            if pricing_base == 'market_price':
                base_price = sku.get('marketPrice')
            else:
                base_price = sku.get('costPrice')

            if not base_price or float(str(base_price)) <= 0:
                content_products.append(sku)
                skip_missing_price_count += 1
                continue

            base_price = Decimal(str(base_price))

            # 逐档计算阶梯价
            new_qty_prices = []
            tier_has_error = False

            for tier in tiers:
                min_qty = int(tier['min_qty'])
                max_qty = tier.get('max_qty')
                rate = float(tier['rate'])

                # 计算单价
                unit_price = base_price * Decimal(str(rate))
                # 四舍五入保留2位小数
                unit_price = math.floor(unit_price * 100) / 100

                # 保本校验
                cost_price = Decimal(str(sku.get('costPrice', 0)))
                if unit_price < cost_price:
                    error_details.append({
                        'product_id': str(content.get('_id', '')),
                        'sku': sku.get('sku', ''),
                        'reason': f"计算单价 {unit_price} 低于成本价 {cost_price}，跳过"
                    })
                    error_count += 1
                    tier_has_error = True
                    break

                new_qty_prices.append({
                    'min_qty': min_qty,
                    'max_qty': max_qty if max_qty else None,
                    'price': float(unit_price),
                })

            if tier_has_error:
                content_products.append(sku)
                continue

            # 更新 SKU 的阶梯价数据
            sku['group_qty_prices'] = new_qty_prices
            content_products.append(sku)
            content_modified = True
            success_count += 1

        # 保存修改后的商品
        if content_modified:
            nc_collection.update_one(
                {"_id": content['_id']},
                {"$set": {"column_10": content_products}}
            )

    # 写入日志
    from .price_template_log import write_log
    log_id = write_log({
        'template_id': template_id,
        'template_name': template.get('name', ''),
        'category_id': category_id,
        'category_name': category_name,
        'apply_mode': apply_mode,
        'total_products': total_products,
        'success_count': success_count,
        'skip_existing_count': skip_existing_count,
        'skip_missing_price_count': skip_missing_price_count,
        'error_count': error_count,
        'error_details': error_details,
        'created_by': admin_user_id,
        'created_by_name': admin_user_name,
    })

    return {
        'success': True,
        'message': f"应用完成：成功 {success_count}，跳过已有 {skip_existing_count}，"
                   f"跳过缺价 {skip_missing_price_count}，异常 {error_count}",
        'log_id': log_id,
        'result': {
            'total_products': total_products,
            'success_count': success_count,
            'skip_existing_count': skip_existing_count,
            'skip_missing_price_count': skip_missing_price_count,
            'error_count': error_count,
        }
    }


# ──────────────────────────────────────────────
#  辅助函数
# ──────────────────────────────────────────────

def count_products_in_category(category_id: str) -> int:
    """
    统计指定分类下的商品数量。

    Args:
        category_id: 分类 ID（NewsClass 的 _id）

    Returns:
        商品总数
    """
    try:
        db = get_db()
        count = db["NewsContent"].count_documents({"class_id": ObjectId(category_id)})
        return count
    except Exception:
        return 0


def get_product_categories() -> list:
    """
    获取商品分类列表（用于模板表单的下拉选择）。

    从 shop 模块的配置中获取商品分类根 ID，然后查找其下的所有子分类。

    Returns:
        分类列表，每项含 _id, class_name
    """
    from eb_modules.eb_shop import bp_shop_pages
    config = getattr(bp_shop_pages, 'config', {}) or {}
    product_class_id = config.get('_product_class_id', '')

    db = get_db()
    if product_class_id:
        try:
            root_oid = ObjectId(product_class_id)
        except Exception:
            root_oid = None
    else:
        root_oid = None

    # 如果没有配置根分类，返回所有分类
    query = {}
    if root_oid:
        query = {"_id": root_oid}

    result = []
    # 获取根分类
    if root_oid:
        root = db["NewsClass"].find_one({"_id": root_oid}, {"_id": 1, "class_name": 1})
        if root:
            # 获取所有子分类（包括根）
            cats = list(db["NewsClass"].find({
                "$or": [
                    {"_id": root_oid},
                    {"parent_id": str(root_oid)}
                ]
            }).sort("order_id", 1))
            for c in cats:
                result.append({'_id': str(c['_id']), 'class_name': c.get('class_name', '')})

    # 如果根分类不存在或没找到子分类，返回所有
    if not result:
        cats = list(db["NewsClass"].find({}, {"_id": 1, "class_name": 1}).sort("order_id", 1))
        for c in cats:
            result.append({'_id': str(c['_id']), 'class_name': c.get('class_name', '')})

    return result


def get_sample_product(category_id: str) -> Optional[dict]:
    """
    获取指定分类下的示例商品，用于预览。

    选择规则：
        - 按创建时间倒序，取该分类下最新一个商品
        - 该商品必须有完整的 marketPrice 和 costPrice
        - 如果最新商品价格数据不完整，继续往后找
        - 如果该分类下没有任何价格数据完整的商品，返回 None

    Returns:
        示例商品字典：
        {
            'product_id': str,
            'product_name': str,
            'sku': str,
            'marketPrice': float,
            'costPrice': float,
        }
        或 None
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