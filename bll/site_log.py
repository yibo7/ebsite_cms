from bll.bll_base import BllBase
from eb_utils import http_helper
from entity.site_log_model import SiteLogModel


class SiteLog(BllBase[SiteLogModel]):
    def new_instance(self) -> SiteLogModel:
        return SiteLogModel()

    def add_log(self, user_name: str, ni_name: str, title: str, content: str, user_id=''):
        model = self.new_instance()
        model.title = title
        model.description = content
        model.user_id = user_id
        model.user_name = user_name
        model.ni_name = ni_name
        model.ip_addr = http_helper.get_ip()

        self.add(model)
