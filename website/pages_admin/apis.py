from flask import jsonify

from bll.data_bakup import DataBakup
from eb_utils import http_helper
from entity.api_msg import api_succesful, api_err
from website.pages_admin import admin_blue

"""
专供后台使用的API集
前端 POST 调用 : post_form("{{admin_path}}api/databack", {"t":1}, call_back);
"""

api_prex = "api/"

@admin_blue.route(f'{api_prex}databack', methods=['POST'])
def databack():
    backup_type = http_helper.get_prams_int('t')
    tip_info = ""
    bll = DataBakup()
    if backup_type==1: # 备份重要表
        bll.OutputDefaultData()
        tip_info = f"数据成功备份在：/{bll.back_path}"
    elif backup_type==2: # 备份所有表
        bll.OutputAllData()
        tip_info = f"数据成功备份在：/{bll.back_path}"
    elif backup_type == 3:  # 备份所有表
        bll.re_build_index()
        tip_info = "成功创建索引!"
    else:
        tip_info = "未知备份类型"

    if tip_info:
        return jsonify(api_err(tip_info))
    else:
        return jsonify(api_succesful("succesfull",tip_info))

