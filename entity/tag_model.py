import eb_utils
from entity.entity_base import ModelBase, annotation

def get_tag_page_link(tag_name:str):
    return f'/tgv{eb_utils.md5(tag_name)}ps1.html'

class TagModel(ModelBase):
    def __init__(self):
        super().__init__()
        self.name = ""
        # self.md5 = ''
        self.article_count:int=0


    def get_url(self):
        return get_tag_page_link(self.name)