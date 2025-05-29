import re
from typing import Tuple

from bll.bll_base import BllBase
from bll.user import User
from eb_utils import flask_utils
from eb_utils.configs import SiteConstant
from eb_utils.mvc_pager import pager_html_admin
from entity.apply_credites_model import ApplyCreditesModel



class ApplyCredites(BllBase[ApplyCreditesModel]):

    def new_instance(self) -> ApplyCreditesModel:
        return ApplyCreditesModel()

    def search_content(self, keyword: str, t_id: int, page_index: int) -> Tuple[list[ApplyCreditesModel], str]:
        """
        模糊搜索
        :param keyword: 搜索的关键词, 不传入会搜索所有
        :param page_index: 页面码
        :param t_id: 类型
        :return:
        """
        datas, i_count = self.search_data(keyword, t_id, page_index)
        page_size = SiteConstant.PAGE_SIZE_AD
        pager = pager_html_admin(i_count, page_index, page_size, {'k': keyword})
        return datas, pager

    def search_data(self, keyword: str, t_id: int, page_number: int) -> Tuple[list[ApplyCreditesModel], int]:
        """
        模糊搜索
        :param keyword: 搜索的关键词, 不传入会搜索所有
        :param page_number: 页面码
        :param t_id:  类型
        :return:
        """
        page_size = SiteConstant.PAGE_SIZE_AD

        s_where = {}
        if keyword:
            regex_pattern = re.compile(f'.*{re.escape(keyword)}.*', re.IGNORECASE)  # IGNORE CASE 忽略大小写
            # s_where = {'title': {'$regex': regex_pattern}}
            # 构建查询条件
            s_where = {
                "$or": [
                    {"username": {"$regex": regex_pattern}},
                    {"ni_name": {"$regex": regex_pattern}},
                    {"ip": {"$regex": regex_pattern}},
                    {"remark": {"$regex": regex_pattern}},
                    {"pply_ni_name": {"$regex": regex_pattern}},
                    {"apply_username": {"$regex": regex_pattern}}

                ]
            }
        # print(f't_id:{t_id}')
        if t_id and t_id in [2,3]:
            # print('fffffffffffffff')
            s_where['is_complate'] = False if t_id==2 else True
        datas, i_count = self.find_pages(page_number, page_size, s_where)
        return datas, i_count

    def apply_opt(self,model:ApplyCreditesModel) -> Tuple[bool,str]:
        bll_user = User()
        model_user = bll_user.find_one_by_id(model.user_id)
        if not model_user:
            return False, '无法更新用户积分，无此用户'

        if model.is_apply: # 通过审核，修改用户的积分
            ip = flask_utils.get_client_ip()
            err_info = ""
            try:
                # 创建一个事物会话 默认causal_consistency=True 保持因果一致性
                with self.db_client.start_session(causal_consistency=True) as session:
                    # 开启事务会话
                    with session.start_transaction():
                        # 更新当前审核请求
                        self.update_trans(model, session)
                        # 更新修改用户积分
                        is_succesfull = bll_user.credits_change(session,model_user, model.credits, ip, 4,
                                                                     "在后台通过申请的积分")
                        if not is_succesfull:
                            err_info = "更改用户积分发生错误"
            except Exception as e:
                err_info = f"更改用户积分发生异常，事务已回滚：{e}"

        else:
            print('不通过审核')

        return False if err_info else True, err_info