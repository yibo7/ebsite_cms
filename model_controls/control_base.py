import ast
from abc import ABC, abstractmethod

import pymongo
from flask import render_template_string
from markupsafe import Markup

from entity.widgets_model import WidgetsModel


class ControlBase(ABC):
    def __init__(self):
        self.id: str = ''  # 控件唯一标识，格式：模块名_序号（如 sys_1、aitanqin_1）
        self.name: str = '' # 物件名称
        self.info: str = ''     # 可以用来保存一些数据

    # 定义抽象方法
    @abstractmethod
    def get_control_temp(self, field_model: dict):
        pass

