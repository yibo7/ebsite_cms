import time

from bll.bll_base import BllBase
from bll.user import User
from entity_orders.credits_order_model import CreditsOrderModel


class CreditsOrder(BllBase[CreditsOrderModel]):

    def new_instance(self) -> CreditsOrderModel:
        return CreditsOrderModel()

    def complete_order(self, order_id:str) -> bool:
        """
        接收到支付完成通知，更改订单状态，调整用户积分
        @param order_id: 订单ID
        @return:
        """
        # print(f'订单通知支付成功，订单ID：{order_id}')
        bll = CreditsOrder()
        model = bll.find_one_by_id(order_id)
        if not model:
            print(f'支付通知，不存在订单ID：{order_id}')
            return False

        if model.is_complete or model.is_payed:
            print(f'失败，因为订单{order_id}已经支付并处理!')
            return False

        is_ok = False
        try:
            # 创建一个事物会话 默认causal_consistency=True 保持因果一致性
            with self.db_client.start_session(causal_consistency=True) as session:
                # 开启事务会话
                with session.start_transaction():

                    model.is_complete = True
                    model.is_payed = True
                    model.complete_date = time.time()  # 完成支付的时间
                    bll.update_trans(model,session)

                    bll_user = User()
                    model_user = bll_user.find_one_by_id(model.user_id)
                    # 减少用户积分，并减少冻结积分
                    log_demo_info = f"成功购买积分,积分订单ID：{model._id}"
                    bll_user.credits_change(session, model_user, model.add_credits, model.user_ip, 2, log_demo_info)
                    print(f'{model.username} 成功购买积分，积分增持成功')

                    is_ok = True
        except Exception as e:
            # 输出异常内容
            print(f'调用事务下单发生异常，已经回滚：{e}')
        return is_ok
