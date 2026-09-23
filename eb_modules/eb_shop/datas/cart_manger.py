from decimal import Decimal

from bson import Decimal128
from bson.objectid import ObjectId
from datetime import datetime

from bll.address import Address
from bll.new_content import NewsContent

from eb_modules.eb_shop.datas.shop_orders import ShopOrder
from eb_modules.eb_shop.datas.shopping_cart import ShoppingCartBll


class CartManager:
    def __init__(self,  user_id: str,  user_account: str):

        self.user_id = ObjectId(user_id)
        self.user_account = user_account
        self.bll = ShoppingCartBll()
        self.table = self.bll.table

    # ──────────────────────────────────────────────────────────────
    #  价格计算（全维度）
    # ──────────────────────────────────────────────────────────────
    @staticmethod
    def _get_user_group_id(user_id: ObjectId):
        """获取用户所在的用户组 ID"""
        if not user_id:
            return None
        from bll.user import User
        user = User().find_one_by_id(user_id)
        if user and user.group_id:
            return str(user.group_id)
        return None

    @staticmethod
    def _calculate_final_price(product_model: dict, quantity: int, user_group_id: str) -> dict:
        """
        全维度价格计算，返回 {price, source}

        规则：
          1. 收集候选价格：会员价、阶梯价、基础零售价
          2. 取最低价
          3. 底价校验（不低于成本价）

        @param product_model: SKU 数据字典
        @param quantity: 购买数量
        @param user_group_id: 用户组 ID（None 表示零售）
        @return: {"price": Decimal, "source": str}
        """
        candidates = []

        market_price = Decimal(str(product_model.get("marketPrice", 0)))

        # 候选 A：会员组价格
        if user_group_id:
            group_prices = product_model.get("group_prices") or []
            for gp in group_prices:
                if gp.get("group_id") == user_group_id:
                    try:
                        candidates.append({
                            "price": Decimal(str(gp["price"])),
                            "source": "会员价"
                        })
                    except Exception:
                        pass
                    break

        # 候选 B：批量阶梯价
        qty_prices = product_model.get("group_qty_prices") or []
        for tier in qty_prices:
            min_qty = tier.get("min_qty", 0)
            max_qty = tier.get("max_qty")
            try:
                min_ok = quantity >= int(min_qty)
                max_ok = (max_qty is None or max_qty == '' or max_qty == 0) or quantity <= int(max_qty)
                if min_ok and max_ok:
                    candidates.append({
                        "price": Decimal(str(tier["price"])),
                        "source": f"阶梯价 {min_qty}-{max_qty or '∞'} 件档"
                    })
                    break
            except (ValueError, TypeError):
                continue

        # 候选 C：基础零售价
        candidates.append({"price": market_price, "source": "零售价"})

        # 取最低价
        best = candidates[0]
        for c in candidates[1:]:
            if c["price"] < best["price"]:
                best = c

        final_price = best["price"]
        final_source = best["source"]

        # 底价校验
        cost_price = Decimal(str(product_model.get("costPrice", 0)))
        if final_price < cost_price:
            final_price = cost_price
            final_source = "成本价"

        return {"price": final_price, "source": final_source}

    # ──────────────────────────────────────────────────────────────
    #  购物车操作
    # ──────────────────────────────────────────────────────────────
    def add_item(self, content_id: str, product_id: str, quantity: int = 1) -> str:
        content_model = NewsContent().find_one_by_id(content_id)
        if not content_model:
            return f"找不到商品：{content_id}"
        # 查找第一个匹配的对象
        product_model = next((item for item in content_model.column_10 if item.get("productId") == product_id), None)
        if not product_model:
            return f"商品：{content_id}还没有添加规格。"

        stock = product_model["stock"]
        if stock < quantity:
            return f"库存量不足：{quantity}"

        # 计算价格
        user_group_id = self._get_user_group_id(self.user_id)
        price_result = self._calculate_final_price(product_model, quantity, user_group_id)

        product_oid = product_id
        existing = self.table.find_one({
            'user_id': self.user_id,
            'product_id': product_oid
        })
        if existing:
            # 更新数量时重新计算价格
            new_qty = existing['quantity'] + quantity
            new_price_result = self._calculate_final_price(product_model, new_qty, user_group_id)
            self.table.update_one(
                {'_id': existing['_id']},
                {
                    '$inc': {'quantity': quantity},
                    '$set': {
                        'price': Decimal128(str(new_price_result['price'])),
                        'price_source': new_price_result['source']
                    }
                }
            )
        else:
            model = self.bll.new_instance()

            model.user_id = self.user_id
            model.content_title = content_model.title
            model.content_id = content_model._id
            model.content_n_id = content_model.id
            model.small_pic = content_model.small_pic
            model.class_name = content_model.class_name
            model.class_n_id = content_model.class_n_id

            model.product_name = product_model["name"]
            model.product_sku = product_model["sku"]
            model.product_id = product_model["productId"]
            model.market_price = Decimal128(str(Decimal(str(product_model["marketPrice"]))))
            model.price = Decimal128(str(price_result["price"]))
            model.price_source = price_result["source"]
            model.quantity = quantity
            model.weight = Decimal128(str(Decimal(str(product_model.get("weight", 0)))))
            cost_val = product_model.get("costPrice", 0)
            model.cost_price = Decimal128(str(Decimal(str(cost_val))))

            # 存储原始定价规则（用于购物车数量变更时重新计算）
            model.group_prices = product_model.get("group_prices", [])
            model.group_qty_prices = product_model.get("group_qty_prices", [])

            self.bll.add(model)
        return ""

    def get_count(self) -> int:
        """获取当前用户的购物车商品总数量（所有商品 quantity 之和）"""
        pipeline = [
            {'$match': {'user_id': self.user_id}},
            {'$group': {'_id': None, 'total': {'$sum': '$quantity'}}}
        ]
        result = list(self.table.aggregate(pipeline))
        return result[0]['total'] if result else 0

    def get_items(self):
        cart = self.bll.find_list_by_where({'user_id': self.user_id})
        # 重新计算每个商品的价格
        user_group_id = self._get_user_group_id(self.user_id)
        for item in cart:
            product_model = {
                "marketPrice": float(str(item.market_price)) if item.market_price else 0,
                "costPrice": float(str(item.cost_price)) if item.cost_price else 0,
                "group_prices": getattr(item, 'group_prices', []) or [],
                "group_qty_prices": getattr(item, 'group_qty_prices', []) or [],
            }
            price_result = self._calculate_final_price(product_model, item.quantity, user_group_id)
            item.price = Decimal128(str(price_result["price"]))
            # 持久化更新
            self.table.update_one(
                {'_id': item._id},
                {'$set': {
                    'price': Decimal128(str(price_result["price"])),
                    'price_source': price_result["source"]
                }}
            )
        return cart

    def update_quantity(self, content_id: str, product_id: str, quantity: int) -> str:
        if quantity <= 0:
            self.remove_item(product_id)
        else:
            # 重新获取原始定价规则并计算价格
            item = self.table.find_one({
                'user_id': self.user_id,
                'product_id': product_id
            })
            if item:
                user_group_id = self._get_user_group_id(self.user_id)
                product_model = {
                    "marketPrice": float(str(item.get('market_price', 0))),
                    "costPrice": float(str(item.get('cost_price', 0))),
                    "group_prices": item.get('group_prices', []) or [],
                    "group_qty_prices": item.get('group_qty_prices', []) or [],
                }
                price_result = self._calculate_final_price(product_model, quantity, user_group_id)
                self.table.update_one(
                    {'user_id': self.user_id, 'product_id': product_id},
                    {
                        '$set': {
                            'quantity': quantity,
                            'price': Decimal128(str(price_result["price"])),
                            'price_source': price_result["source"]
                        }
                    }
                )
        return ""

    def remove_item(self, product_id: str):
        self.table.delete_one({
            'user_id': self.user_id,
            'product_id': product_id
        })

    def clear_cart(self):
        self.table.delete_many({'user_id': self.user_id})

    def post_to_order(self, address_id: str, remark: str = "") -> str:
        address_model = Address().find_one_by_id(address_id)
        if not address_model:
            return f"找不到地址：{address_id}"

        products = self.get_items()

        if not products:
            return "购物车中没有商品"

        # 重新计算最终价格（锁定价格）
        user_group_id = self._get_user_group_id(self.user_id)
        total_price = Decimal('0.0')
        total_market_price = Decimal('0.0')
        total_weight = Decimal('0.0')
        total_cost_price = Decimal('0.0')

        product_snapshots = []
        for product in products:
            product_model = {
                "marketPrice": float(str(product.market_price)) if product.market_price else 0,
                "costPrice": float(str(product.cost_price)) if product.cost_price else 0,
                "group_prices": getattr(product, 'group_prices', []) or [],
                "group_qty_prices": getattr(product, 'group_qty_prices', []) or [],
            }
            price_result = self._calculate_final_price(
                product_model, product.quantity, user_group_id
            )

            unit_price = price_result["price"]
            subtotal = unit_price * product.quantity
            total_price += subtotal
            total_market_price += product.total_market_price
            total_weight += product.total_weight
            total_cost_price += product.total_cost_price

            product_snapshots.append({
                "content_title": product.content_title,
                "content_id": str(product.content_id),
                "product_name": product.product_name,
                "product_sku": product.product_sku,
                "product_id": product.product_id,
                "quantity": product.quantity,
                "price": float(str(unit_price)),
                "price_source": price_result["source"],
                "market_price": float(str(product.market_price)) if product.market_price else 0,
                "cost_price": float(str(product.cost_price)) if product.cost_price else 0,
                "weight": float(str(product.weight)) if product.weight else 0,
                "subtotal": float(str(subtotal)),
            })

        # 计算运费
        from eb_modules.eb_shop import bp_shop_pages
        config = getattr(bp_shop_pages, 'config', {}) or {}
        free_shipping_threshold = Decimal(str(config.get('free_shipping_threshold', 500)))
        flat_shipping_fee = Decimal(str(config.get('flat_shipping_fee', 20)))

        if free_shipping_threshold > 0 and total_price >= free_shipping_threshold:
            freight = Decimal('0.0')
        elif free_shipping_threshold == 0:
            freight = Decimal('0.0')
        else:
            freight = flat_shipping_fee

        bll_order = ShopOrder()
        order_model = bll_order.new_instance()
        order_model.user_id = self.user_id
        order_model.order_status = 0
        order_model.user_account = self.user_account

        order_model.products = product_snapshots
        order_model.address = address_model.__dict__

        order_model.total_market_price = Decimal128(str(total_market_price))
        order_model.total_price = Decimal128(str(total_price))
        order_model.freight = Decimal128(str(freight))
        order_model.total_amount = Decimal128(str(total_price + freight))  # 应付总额含运费
        order_model.total_cost_price = Decimal128(str(total_cost_price))
        order_model.total_weight = Decimal128(str(total_weight))
        order_model.remark = remark  # 保存订单备注

        actual_price = total_price
        market_price_val = total_market_price

        # 计算折扣率
        if market_price_val != 0:
            discount_rate = (actual_price / market_price_val) * 100
            discount_rate = round(discount_rate, 2)
        else:
            discount_rate = 0

        order_model.discount = Decimal128(str(discount_rate))
        order_model.discount_info = ""

        order_model.profit = Decimal128(str(actual_price - total_cost_price))

        bll_order.save(order_model)

        self.clear_cart()

        return ""