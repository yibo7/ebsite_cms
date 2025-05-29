import ast
from abc import ABC, abstractmethod

import pymongo
from flask import render_template_string
from markupsafe import Markup

from entity.widgets_model import WidgetsModel


class WidgetTypeModel(ABC):
    _subclasses = []  # 类变量，用来存储所有子类的引用
    def __init__(self):
        self.id: int = 0 # 指定一个数字ID，注意不能重复
        self.name: str = '' # 部件类型名称
        self.temp: str = 'widget_list_save_where.html'     # 部件后台处理模板路径
        self.info: str = ''     # 可以用来保存一些数据

    def saving(self, model:WidgetsModel):
        """
        在部件保存前处理
        """
        pass

    def bll_hanndler(self):
        """
        如果需要调用业务类型
        :return: 业务对象
        """
        return None
    # 定义抽象方法
    @abstractmethod
    def temp_hanndler(self, model:WidgetsModel):
        """
        模板数据处理返回对象
        :return:
        """
        pass

    def where_hannder(self, model:WidgetsModel):
        """
        适合查询数据库的部件模板渲染
        :param model:
        :return:
        """
        s_where = {}
        if model.where_query:
            try:
                s_where = ast.literal_eval(model.where_query)
            except Exception:
                raise Exception(f"部件查询条件错误:{model.where_query}不是python下合法的mongodb语句,来自部件ID:{model._id}")
                # literal_eval 无法解析带有类型的字典，如 ObjectId "{'_id': ObjectId('64d2e7c93798563b080040c4')}"
            # 如要查询指定id的记录，可查询 自增加 id
            # s_where = eval(model.where_query, {'ObjectId': ObjectId}) # eval 比较危险，但功能强大

        order_by = model.order_by
        desc_asc = pymongo.DESCENDING if model.order_by_desc == 'DESC' else pymongo.ASCENDING
        int_limit = model.limit

        bll = self.bll_hanndler()  # get_type_by_id(model.temp_type).get('bll')

        data = bll.find_list_by_where(s_where, order_by, desc_asc, int_limit)

        return Markup(render_template_string(model.temp_code, data=data))