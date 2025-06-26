from typing import Any

from bson import ObjectId

from eb_utils import url_links
from entity.entity_base import ModelBase, annotation


class FavoriteModel(ModelBase):
    def __init__(self):
        super().__init__()
        self.content_title: str = ""
        self.content_id: int = 0
        self.small_pic: str = ""  # 图片地址
        self.class_name: str = ""
        self.class_n_id: int = 0
        self.user_id: ObjectId

    def get_url(self):
        return url_links.get_content_url(self.content_id)

    @annotation("标题")
    def a_title(self):
        return f'<a href="{url_links.get_content_url(self.content_id)}" target=_blank >{self.title}</a>'
