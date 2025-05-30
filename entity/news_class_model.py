from typing import Any

from eb_utils import url_links
from entity.entity_base import ModelBase, annotation


class NewsClassModel(ModelBase):
    def __init__(self):
        super().__init__()
        self.class_name: str = ""
        self.order_id: int = 0
        self.parent_id: str = ""
        self.info: str = ""
        self.seo_title: str = ""
        self.seo_keyword: str = ""
        self.seo_description: str = ""
        self.hits: int = 0
        self.user_id: str = ""
        self.user_group_ids: list[str] = []  # allow user group ids
        self.class_temp_id: str = ""
        self.content_temp_id: str = ""
        self.content_model_id: str = ""
        self.id: int = 0
        self.page_size = 30
        self.small_pic: str = ""  # 图片地址

        self.class_model_id: str = ""
        self.column_1: Any = None
        self.column_2: Any = None
        self.column_3: Any = None
        self.column_4: Any = None
        self.column_5: Any = None
        self.column_6: Any = None
        self.column_8: Any = None
        self.column_9: Any = None
        self.column_10: Any = None

    def get_url(self):
        return url_links.get_class_url(self.id)

    @annotation("分类名称")
    def a_class_name(self):
        return f'<a href="{url_links.get_class_url(self.id)}" target=_blank >{self.class_name}</a>'

    @annotation("自增ID")
    def b_id(self):
        return self.id

    @annotation("数据ID")
    def b_dataid(self):
        return self._id

    @annotation("分类数据")
    def c_id(self):
        return f'<a href="content_list?cid={self._id}">查看数据<a/>'

    @annotation("排序ID")
    def d_order_id(self):
        return self.order_id

    @annotation("添加时间|to_time_name")
    def e_add_time(self):
        return self.add_time

    def to_short_dic(self):
        """将实体对象转换为字典，只包含特定字段，并处理 ObjectId"""
        return {
            '_id': str(self._id),
            'id': self.id,
            'class_name': self.class_name
        }