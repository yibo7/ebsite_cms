
from entity.news_content_model import NewsContentModel
from plugins.plugin_base import plugin_attribute, PluginBase
from signals import content_saving


@plugin_attribute("内容保存触发器", "1.0", "ebsite")
class ExtContentSaving(PluginBase):
    def __init__(self, current_app):
        self.info = "监听内容保存前后的处理"
        content_saving.connect(self.on_content_saving)
        super().__init__(current_app)

    def on_content_saving(self, model: NewsContentModel):

        print(f'保存内容前触发fff,标题:{model.title}，来自:{self.name}')
        return True, 'succesfull'
