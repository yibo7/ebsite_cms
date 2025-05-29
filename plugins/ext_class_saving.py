
from entity.news_class_model import NewsClassModel
from plugins.plugin_base import plugin_attribute, PluginBase
from signals import class_saving


@plugin_attribute("分类保存触发器", "1.0", "ebsite")
class ExtClassSaving(PluginBase):
    def __init__(self,current_app):
        self.info = "监听分类保存前后的处理"
        class_saving.connect(self.on_class_saving)
        super().__init__(current_app)

    def on_class_saving(self, model: NewsClassModel):
        # model.class_name = f"{model.class_name} 111111"
        print(f'保存分类前触发,标题:{model.class_name}，来自:{self.name}')
        return True,'succesfull'
