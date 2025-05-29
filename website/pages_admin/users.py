import time

from flask import render_template, request, redirect, g

from bll.apply_credites import ApplyCredites
from bll.user import User
from bll.user_group import UserGroup
from bll_orders.credit_logs import CreditLogs
from bll_orders.user_orders import CreditsOrder
from entity.user_group_model import UserGroupModel
from entity.user_model import UserModel
from entity.user_token import UserToken
from temp_expand import get_table_html
from website.pages_admin import admin_blue
from eb_utils import http_helper, flask_utils
from eb_utils.configs import WebPaths


# region user-group

@admin_blue.route('user_group', methods=['GET'])
def user_group():
    ug = UserGroup()
    datas = ug.find_all()
    return render_template(WebPaths.get_admin_path("user/user_group.html"), datas=datas)


@admin_blue.route('user_group/save', methods=['GET', 'POST'])
def user_group_add():
    g_id = http_helper.get_prams('_id')
    model = UserGroupModel()
    bll = UserGroup()
    err = ''
    if g_id:
        model = bll.find_one_by_id(g_id)

    if request.method == 'POST':
        name = http_helper.get_prams('name')
        price = http_helper.get_prams_decimal('price')
        credit = http_helper.get_prams_int('credits')
        model.name = name
        model.price = price
        model.credits = credit
        if not g_id and bll.exist_name(name):
            err = '已经存在相同名称的用户组'
        else:
            bll.save(model)
            return redirect('../user_group')

    return render_template(WebPaths.get_admin_path("user/user_group_save.html"), model=model, err=err)


@admin_blue.route('user_group/del', methods=['GET', 'POST'])
def user_group_del():
    UserGroup().delete_from_page(http_helper.get_prams("ids"))
    return redirect("../user_group")


# endregion

# region users


@admin_blue.route('user_list', methods=['GET'])
def user_list():
    keyword = http_helper.get_prams("k")
    page_num = http_helper.get_prams_int("p", 1)
    bll = User()
    datas, pager = bll.search(keyword, page_num, 'username')

    del_btn = {"show_name": "删除", "url": "user_list_del?ids=#_id#", "confirm": True}
    modify_btn = {"show_name": "修改", "url": "user_list_save?_id=#_id#", "confirm": False}

    table_html = get_table_html(datas, [del_btn, modify_btn])

    return render_template(WebPaths.get_admin_path("user/user_list.html"), table_html=table_html, pager=pager,
                           datas=datas)


@admin_blue.route('user_list_save', methods=['GET', 'POST'])
def user_list_save():
    data_id = http_helper.get_prams('_id')
    model = UserModel()
    bll = User()
    if data_id:
        model = User().find_one_by_id(data_id)

    err = ''
    if request.method == 'POST':
        dic_prams = http_helper.get_prams_dict()
        model.dict_to_model(dic_prams)
        # _id = bll.save(model)
        if data_id:
            is_success = bll.update(model)
        else:
            is_success, err = bll.reg_user(model)
        if is_success:
            return redirect('user_list')

    group = UserGroup().find_all()
    return render_template(WebPaths.get_admin_path("user/user_list_save.html"), model=model, group=group, err=err)


@admin_blue.route('user_list_del', methods=['GET', 'POST'])
def user_list_del():
    User().delete_from_page(http_helper.get_prams("ids"))
    return redirect("user_list")

# endregion 以下功能已经由模块集成

#
# @admin_blue.route('pay_orders', methods=['GET'])
# def pay_orders():
#     keyword = http_helper.get_prams("k")
#     page_num = http_helper.get_prams_int("p", 1)
#     bll = CreditsOrder()
#     datas, pager = bll.search(keyword, page_num, 'info')
#
#     # del_btn = {"show_name": "删除", "url": "user_list_del?ids=#_id#", "confirm": True}
#     # modify_btn = {"show_name": "修改", "url": "user_list_save?_id=#_id#", "confirm": False}
#
#     table_html = get_table_html(datas)
#
#     return render_template(WebPaths.get_admin_path("user/pay_orders.html"), table_html=table_html, pager=pager,
#                            datas=datas)
#
#
#
# @admin_blue.route('credit_list', methods=['GET'])
# def credit_list():
#     keyword = http_helper.get_prams("k")
#     page_num = http_helper.get_prams_int("p", 1)
#     bll = CreditLogs()
#     datas, pager = bll.search(keyword, page_num, 'info')
#
#     table_html = get_table_html(datas)
#
#     return render_template(WebPaths.get_admin_path("user/pay_orders.html"), table_html=table_html, pager=pager,
#                            datas=datas)
#
#
# @admin_blue.route('apply_credits', methods=['GET'])
# def apply_credits():
#     keyword = http_helper.get_prams("k")
#     page_index = http_helper.get_prams_int("p", 1)
#     type_id = http_helper.get_prams_int("tid",2)
#
#     types = [
#         {
#             "id": 2,
#             "name": "未处理"
#         },
#         {
#             "id": 1,
#             "name": "所有"
#         },
#
#         {
#             "id": 3,
#             "name": "已处理"
#         }
#     ]
#
#     bll = ApplyCredites()
#     datas, pager = bll.search_content(keyword, type_id, page_index)
#
#     del_btn_allow = {"show_name": "通过", "url": "apply_credits_ap?t=1&ids=#_id#", "confirm": True}
#     del_btn_not_allow = {"show_name": "不通过", "url": "apply_credits_ap?t=2&ids=#_id#", "confirm": True}
#     table_html = get_table_html(datas, [del_btn_allow, del_btn_not_allow])
#
#     return render_template(WebPaths.get_admin_path("user/apply_credits.html"),table_html=table_html,pager=pager, types=types)
#
# @admin_blue.route('apply_credits_ap', methods=['GET', 'POST'])
# def apply_credits_ap():
#     apply_type = http_helper.get_prams_int("t")
#     if apply_type:
#         data_id = http_helper.get_prams("ids")
#         bll = ApplyCredites()
#         model = bll.find_one_by_id(data_id)
#         model.is_complate = True
#         model.is_apply = True if apply_type==1 else False
#
#         user_token: UserToken = g.u
#
#         model.apply_ni_name =  user_token.ni_name
#         model.apply_username = user_token.name
#         model.apply_time = time.time()
#
#         is_succesfull,err = bll.apply_opt(model)
#         if err:
#             print(err)
#
#     return redirect("apply_credits")