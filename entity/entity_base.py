import re
import time
from typing import Optional, List

from bson import ObjectId, Decimal128
from flask import current_app

from eb_utils import string_check


def convert_to_type(value):
    if isinstance(value, str):
        if string_check.is_int(value):
            return int(value)
        elif string_check.is_decimal(value):
            return float(value)
        elif value == 'on':
            return True
        elif value == 'checkbox_unchecked':
            return False
        else:
            return value
    return value


def annotation(value):
    def decorator(func):
        setattr(func, 'annotation', value)
        return func

    return decorator


class ModelBase:
    def __init__(self):
        self._id = ''
        self.add_time = time.time()  # int(time.time())  # 只精确到秒

    def dict_to_model(self, dic_data: dict, is_object_id=True):
        for key, value in dic_data.items():
            if not hasattr(self, key):
                continue  # 如果属性不存在，跳过这个键值对
            col_v = getattr(self, key)
            tem_v = value
            if  key == '_id' and value and is_object_id:  # 在修改数据时，接收到的_id为字符串类型
                tem_v = ObjectId(value)
                # tem_v = value
            elif key == 'id' and value:
                tem_v = int(value)
            elif isinstance(col_v, int) and isinstance(value, str) and value:
                tem_v = int(value)
            elif isinstance(col_v, float) and isinstance(value, str) and value:
                tem_v = float(value)

            setattr(self, key, tem_v)
        return self

    # def add_atr_setting(self, func, setting: str):
    #     func = self._add_annotation(setting)(func)

    def add_annotation(self, value):
        def decorator(func):
            setattr(func, 'annotation', value)
            return func

        return decorator

    def get_title(self, attribute_name: str):
        attribute = getattr(self, attribute_name)
        return getattr(attribute, 'annotation', None)

    def has_title(self, col):
        return hasattr(col, 'annotation')

    def get_titles(self):
        annotated_attributes = []

        for attribute_name in dir(self):
            attribute = getattr(self, attribute_name)
            if hasattr(attribute, 'annotation'):
                annotation_value = getattr(attribute, 'annotation')
                attribute_value = attribute.__get__(self)()

                filter_name = ''
                title = annotation_value
                if '|' in title:
                    a_title = title.split('|')
                    title = a_title[0]
                    filter_name = a_title[1]

                if filter_name:
                    attribute_value = current_app.jinja_env.filters[filter_name](str(attribute_value))

                annotated_attributes.append({
                    'title': title,
                    # 'col_name': attribute_name,
                    'value': attribute_value
                })

        return annotated_attributes

    def to_dict(self, exclude_fields: Optional[List[str]] = None) -> dict:
        """
        将模型转换为可序列化的字典-解决MongoDb中ObjectId，Decimal128无法序列化的问题

        :param exclude_fields: 需要排除的字段列表
        :return: 可序列化的字典
        """

        def serialize_value(value):
            if isinstance(value, ObjectId):
                return str(value)
            elif isinstance(value, Decimal128):
                return float(value.to_decimal())
            return value

        exclude_fields = set(exclude_fields or [])
        return {
            key: serialize_value(value)
            for key, value in self.__dict__.items()
            if key not in exclude_fields
        }