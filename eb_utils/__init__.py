import hashlib
import inspect
import os
import random
import string
import uuid
from dataclasses import replace

from flask import render_template_string, current_app
from markupsafe import Markup

from eb_utils import string_check
from entity.news_class_model import NewsClassModel


def __convert_to_number(value):
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
    else:
        return value


def update_dic_to_class(dic_obj: {}, class_model):
    settings_dict = class_model.__dict__
    convert_dic = {key: __convert_to_number(value) for key, value in dic_obj.items()}
    settings_dict.update(convert_dic)
    settings_model_new = replace(class_model, **settings_dict)
    return settings_model_new


def random_string(length):
    """
    生成指定长度的随机字符串-支持大小写混合，可读性更高
    @param length: 指定长度
    @return:
    """
    # 定义可能的字符集合
    characters = string.ascii_letters + string.digits
    # 随机选择字符集合中的字符
    v_string = ''.join(random.choice(characters) for _ in range(length))
    return v_string

def random_string_hex(length):
    """
    生成指定长度的随机字符串-全小写，可读性不高，但更安全
    @param length: 指定长度
    @return:
    """
    return os.urandom(length).hex()

def random_int(min_value, max_value):
    """
    获取一个随机整数
    :param min_value: 最小数
    :param max_value: 最大数
    :return:
    """
    return random.randint(min_value, max_value)


def random_float(min_value, max_value):
    """
        获取一个随机小数
        :param min_value: 最小数
        :param max_value: 最大数
        :return:
        """
    return random.uniform(min_value, max_value)


def get_all_fields(model):
    attributes = []
    dic_f = model.__dict__
    if '_id' in dic_f:
        dic_f.pop('_id')
    # 获取当前类的属性
    for name, value in dic_f.items():
        attributes.append(name)

    fields_str = ", ".join(attributes)
    return fields_str


def md5(soure: str):
    """
    获取文件的MD5值
    :param soure: 原字符串
    :return:
    """
    return hashlib.md5(soure.encode('utf-8')).hexdigest()

def md5_file(file_path: str):
    """
    获取文件的MD5值
    :param file_path: 文件路径
    :return:
    """
    md5file = open(file_path,'rb')
    md5_str = hashlib.md5(md5file.read()).hexdigest()
    md5file.close()
    # print(md5_str)

def get_uuid():
    """
    获取一个唯一的字符串
    :return:
    """
    return str(uuid.uuid4())


def sha256(data):
    """
    Sha256加密算法

    :param data: 加密的内容
    :return: 加密后的数据
    """
    # 将输入数据编码为UTF-8字节
    bytes_data = data.encode('utf-8')

    # 创建SHA256哈希对象
    sha256_hash = hashlib.sha256()

    # 更新哈希对象with字节数据
    sha256_hash.update(bytes_data)

    # 获取十六进制表示的哈希值
    hashed_data = sha256_hash.hexdigest()

    return hashed_data.upper()


def cutstr(s, length):
    """截取字符串到指定长度。

    参数:
    s (str): 要截取的字符串。
    length (int): 指定的截取长度。

    返回:
    str: 截取后的字符串。
    """
    if length < 0:
        raise ValueError("长度不能为负数")
    if length > len(s):
        return s
    else:
        return s[:length]