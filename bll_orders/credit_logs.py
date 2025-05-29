from typing import Optional

from flask import Flask
from pymongo.client_session import ClientSession
from werkzeug.security import generate_password_hash, check_password_hash

from bll.bll_base import BllBase
from entity_orders.credit_logs_model import CreditLogsModel


class CreditLogs(BllBase[CreditLogsModel]):
    def __init__(self, app: Optional[Flask] = None):
        super().__init__(app)

    def new_instance(self) -> CreditLogsModel:
        return CreditLogsModel()

    def add_log(self, model: CreditLogsModel, session: Optional[ClientSession]):

        self.add_trans(model, session)

