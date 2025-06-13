from bll.bll_base import BllBase
from entity.list_item import ListItem
from entity.site_model_entity import SiteModelEntity, FieldModel
from model_controls.control_base import ControlBase


class SiteModel(BllBase[SiteModelEntity]):
    """
    模型设计
    """
    def new_instance(self) -> SiteModelEntity:
        model = SiteModelEntity()
        return model

    def _get_default_fields(self,model:SiteModelEntity):
        fields: list[dict] = []
        if model.type_id == 1:
            field = FieldModel(name='title', show_name='标题', control_id='1', control_name='单行文本输入框',
                               control_size='3')
            fields.append(field.__dict__)

            field = FieldModel(name='info', show_name='内容', control_id='2', control_name='多行文本输入框',
                               control_size='5')
            fields.append(field.__dict__)

        elif model.type_id == 2:
            field = FieldModel(name='info', show_name='分类简介', control_id='2', control_name='多行文本输入框',
                               control_size='5')
            fields.append(field.__dict__)

        return fields

    def save_default(self, model: SiteModelEntity):

        if not model._id:
            model.fields = self._get_default_fields(model)
        self.save(model)

    def get_by_type_id(self,type_id:int):
        s_where = {"type_id": type_id}
        return self.find_list_by_where(s_where)

    def save_fields(self, model: SiteModelEntity, field_model: FieldModel,field_name):
        if field_name:
            item = self.get_field_by_name(model,field_name)
            item["name"] = field_model.name
            item["show_name"] = field_model.show_name
            item["control_name"] = field_model.control_name
            item["control_id"] = field_model.control_id
            item["control_size"] = field_model.control_size

            self.save(model)
            return True
        else:
            exists = any(f_m.get('name') == field_model.name for f_m in model.fields)
            if not exists:
                model.fields.append(field_model.__dict__)
                self.save(model)
                return True

        return False

    def del_field(self, _id: str, field_name):
        model = self.find_one_by_id(_id)
        new_list = [item for item in model.fields if item.get('name') != field_name]
        model.fields = new_list
        self.save(model)

    def get_field_by_name(self, model, field_name) -> dict:

        first_match = next((item for item in model.fields if item.get('name') == field_name), None)
        return first_match

    def move_up(self, _id: str, field_name):
        model = self.find_one_by_id(_id)
        # 找到 name="info" 的项的索引
        current_index = next((index for index, field in enumerate(model.fields) if field["name"] == field_name), None)

        if current_index is not None and current_index > 0:
            current_item = model.fields.pop(current_index)
            model.fields.insert(current_index - 1, current_item)
            self.save(model)

    def move_down(self, _id: str, field_name):
        model = self.find_one_by_id(_id)
        # 找到 name="info" 的项的索引
        current_index = next((index for index, field in enumerate(model.fields) if field["name"] == field_name), None)

        if current_index is not None:
            # 将 name="info" 的项从原位置删除，并在索引-1的位置插入
            current_item = model.fields.pop(current_index)
            model.fields.insert(current_index + 1, current_item)
            self.save(model)

    # @staticmethod
    # def get_controls() -> list[ListItem]:
    #     lst = [
    #         ListItem(value=1, name='单行文本输入框'),
    #         ListItem(value=2, name='多行文本输入框'),
    #         ListItem(value=3, name='富文本编辑框'),
    #         ListItem(value=4, name='数字输入框'),
    #         ListItem(value=5, name='单图上传控件'),
    #         ListItem(value=6, name='单文件上传控件'),
    #         ListItem(value=7, name='多图上传控件'),
    #         ListItem(value=8, name='多文件上传控件'),
    #         ListItem(value=9, name='单图上传-显示路径')
    #     ]
    #     return lst

    @staticmethod
    def get_controls() -> list[ControlBase]:
        # 通过反射获取获取直接子类，应该采用缓存
        subclasses = ControlBase.__subclasses__()

        # 创建一个列表来存储所有子类的实例
        instances = []
        # 遍历所有子类，并为每个子类创建一个实例
        for subclass in subclasses:
            instance = subclass()
            instances.append(instance)
        return instances

    @staticmethod
    def get_control_by_id(ctr_id: int) -> ControlBase:
        ctrs = SiteModel.get_controls()
        # result = [item for item in ctrs if item.value == ctr_id]
        result = [item for item in ctrs if item.id == ctr_id]
        return result[0] if result else None

    @staticmethod
    def get_fields(type_id:int) -> list[str]:

        attributes = []
        if type_id==1: # content model
            from entity.news_content_model import NewsContentModel
            model = NewsContentModel()
            dic_f = model.__dict__
            dic_f.pop('_id')
            dic_f.pop('is_good')
            dic_f.pop('id')
            dic_f.pop('rand_num')
            dic_f.pop('user_id')
            dic_f.pop('user_name')
            dic_f.pop('user_ni_name')
            # dic_f.pop('favorable_num')
            # dic_f.pop('comment_num')
            # dic_f.pop('hits')
            # dic_f.pop('seo_description')
            # dic_f.pop('seo_keyword')
            # dic_f.pop('seo_title')
            dic_f.pop('class_id')
            dic_f.pop('class_name')
            dic_f.pop('class_n_id')
            dic_f.pop('add_time')

            # 获取当前类的属性
            for name, value in dic_f.items():
                attributes.append(name)
        elif type_id==2: # class model
            from entity.news_class_model import NewsClassModel
            model = NewsClassModel()
            dic_f = model.__dict__
            dic_f.pop('_id')
            dic_f.pop('order_id')
            dic_f.pop('id')
            dic_f.pop('parent_id')
            dic_f.pop('user_id')
            dic_f.pop('user_group_ids')
            dic_f.pop('class_temp_id')
            dic_f.pop('content_temp_id')
            dic_f.pop('content_model_id')
            dic_f.pop('add_time')
            dic_f.pop('class_name')

            # 获取当前类的属性
            for name, value in dic_f.items():
                attributes.append(name)
        return attributes

    def get_model_temp_by_id(self, model_id: str):
        model = self.find_one_by_id(model_id)
        if not model:
            return ""
        a_html = []
        for field in model.fields:
            control_id = int(field.get('control_id'))
            ctr_instance = SiteModel.get_control_by_id(control_id)
            a_html.append(ctr_instance.get_control_temp(field))

        s_html = ''.join(a_html)
        s_html = s_html.replace('[[', '{{').replace(']]', '}}')
        return s_html
