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
    #  用户组价格解析
    # ──────────────────────────────────────────────────────────────
    @staticmethod
    def _get_group_price(product_model: dict, user_id: ObjectId):
        """
        根据用户所在用户组，获取 SKU 对应的分组价格

        优先级：用户组价格 > marketPrice（未登录或未设置时返回 None）

        @param product_model: column_10 中的单个 SKU 字典
            {
                "name": "Original",
                "marketPrice": 20,
                "group_prices": [
                    {"group_id": "...", "group_name": "VIP", "price": 18}
                ]
            }
        @param user_id: 当前登录用户的 ObjectId

        @return: Decimal 价格，没有匹配时返回 None
        """
        from bll.user import User

        # 1. 未登录用户：无用户组，返回 None（使用 marketPrice）
        if not user_id:
            return None

        # 2. 获取用户的 group_id
        user_bll = User()
        user = user_bll.find_one_by_id(user_id)
        if not user or not user.group_id:
            return None

        user_group_id = str(user.group_id)

        # 3. 在 SKU 的 group_prices 中查找
        group_prices = product_model.get("group_prices") or []
        for gp in group_prices:
            if gp.get("group_id") == user_group_id:
                try:
                    return Decimal(str(gp.get("price", 0)))
                except Exception:
                    return None

        return None  # 无匹配 → 使用市场价

    def add_item(self,content_id:str, product_id: str, quantity: int = 1) -> str:

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

        product_oid = product_id
        existing = self.table.find_one({
            'user_id': self.user_id,
            'product_id': product_oid
        })
        if existing:
            self.table.update_one(
                {'_id': existing['_id']},
                {'$inc': {'quantity': quantity}}
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
            model.market_price = product_model["marketPrice"]
            # 用户组价格：如果设置了则使用，否则使用 marketPrice
            group_price = self._get_group_price(product_model, self.user_id)
            model.price = group_price if group_price is not None else model.market_price
            model.quantity  =quantity  # 订购的数量
            model.weight = product_model["weight"]
            cost_val = product_model.get("costPrice", 0)
            model.cost_price = Decimal128(str(Decimal(str(cost_val))))
            self.bll.add(model)
        return ""

    def get_items(self):

        cart = self.bll.find_list_by_where({'user_id': self.user_id})
        return cart
        # cart = list(self.table.find({'user_id': self.user_id}))
        # return cart
        # product_ids = [item['product_id'] for item in cart]
        # products = self.mongo.db.products.find({'_id': {'$in': product_ids}})
        # product_map = {p['_id']: p for p in products}
        #
        # result = []
        # for item in cart:
        #     p = product_map.get(item['product_id'])
        #     if p:
        #         result.append({
        #             'product_id': str(p['_id']),
        #             'name': p['name'],
        #             'price': p['price'],
        #             'quantity': item['quantity'],
        #             'subtotal': item['quantity'] * p['price']
        #         })
        # return result

    def update_quantity(self, content_id:str, product_id: str, quantity: int) -> str:
        if quantity <= 0:
            self.remove_item(product_id)
        else:
            self.table.update_one(
                {'user_id': self.user_id, 'product_id': product_id},
                {'$set': {'quantity': quantity}}
            )
        return ""

    def remove_item(self, product_id: str):
        self.table.delete_one({
            'user_id': self.user_id,
            'product_id': product_id
        })

    def clear_cart(self):
        self.table.delete_many({'user_id': self.user_id})

    def post_to_order(self,address_id:str)-> str:

        address_model = Address().find_one_by_id(address_id)
        if not address_model:
            return f"找不到地址：{address_id}"


        products = self.get_items()

        if not products:
            return "购物车中没有商品"

        bll_order =  ShopOrder()
        order_model = bll_order.new_instance()
        order_model.user_id = self.user_id
        order_model.order_status = 0
        order_model.user_account = self.user_account

        order_model.products = [product.__dict__ for product in products]
        order_model.address = address_model.__dict__

        total_market_price =Decimal('0.0')
        total_price = Decimal('0.0')
        total_weight = Decimal('0.0')
        total_cost_price = Decimal('0.0')
        for product in products:
            total_market_price += product.total_market_price
            total_price += product.total_price
            total_weight += product.total_weight
            total_cost_price += product.total_cost_price

        order_model.total_market_price = Decimal128(str(total_market_price))
        order_model.total_price = Decimal128(str(total_price))
        order_model.total_cost_price = Decimal128(str(total_cost_price))
        order_model.total_weight = Decimal128(str(total_weight))

        actual_price = Decimal(str(order_model.total_price))
        market_price = Decimal(str(order_model.total_market_price))

        # 计算折扣率
        if market_price != 0:  # 避免除以零的错误
            discount_rate = (actual_price / market_price) * 100
            # 如果需要保留两位小数
            discount_rate = round(discount_rate, 2)
        else:
            discount_rate = 0  # 或者根据业务需求处理市场价为0的情况

        order_model.discount = Decimal128(str(discount_rate)) # 折扣率
        order_model.discount_info = ""  # 折扣原因

        cost_price =  Decimal(str(order_model.total_cost_price))
        order_model.profit = Decimal128(str(actual_price - cost_price))  # 订单毛利


        bll_order.save(order_model)

        self.clear_cart()

        return ""
