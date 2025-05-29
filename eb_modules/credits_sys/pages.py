import time

from flask import jsonify, current_app, render_template, redirect, request

from bll.apply_credites import ApplyCredites
from bll_orders.credit_logs import CreditLogs
from bll_orders.user_orders import CreditsOrder
from decorators import check_admin_login, check_user_login
from eb_modules.credits_sys import bp_credits_pages
from eb_modules.credits_sys.datas.credits_plan import CreditsPlanBll
from eb_utils import http_helper, flask_utils
from entity.user_token import UserToken
from temp_expand import get_table_html


# region 前台页面
@bp_credits_pages.route('/', methods=['GET', 'POST'])
def credits_index():
    return render_template("credits_index.html")

@bp_credits_pages.route('/apply_credits', methods=['GET', 'POST'])
@check_user_login
def apply_credits(user_token:UserToken):
    err = ''
    is_succesfull = False
    if request.method == 'POST':
        credits = http_helper.get_prams_int("credits")
        remark = http_helper.get_prams("remark")
        if credits and remark:
            bll = ApplyCredites()
            model = bll.new_instance()
            model.user_id = user_token.id
            model.username = user_token.name
            model.ni_name = user_token.ni_name
            model.credits = credits
            model.remark = remark
            model.ip = flask_utils.get_client_ip()
            bll.add(model)
            is_succesfull = True
        else:
            err = "请填写必要的参数!"
    return render_template("apply_credits.html",is_succesfull = is_succesfull, err=err)

# endregion

# region 管理后台页面
@bp_credits_pages.route('/credits_orders', methods=['GET'])
@check_admin_login
def credits_orders(admin_token:UserToken):


    keyword = http_helper.get_prams("k")
    page_num = http_helper.get_prams_int("p", 1)
    bll = CreditsOrder()
    datas, pager = bll.search(keyword, page_num, 'info')

    # del_btn = {"show_name": "删除", "url": "user_list_del?ids=#_id#", "confirm": True}
    # modify_btn = {"show_name": "修改", "url": "user_list_save?_id=#_id#", "confirm": False}

    table_html = get_table_html(datas)

    return render_template("credits_admin/credit_orders.html", table_html=table_html, pager=pager,
                           datas=datas)

@bp_credits_pages.route('credit_list', methods=['GET'])
@check_admin_login
def credit_list(admin_token:UserToken):
    keyword = http_helper.get_prams("k")
    page_num = http_helper.get_prams_int("p", 1)
    bll = CreditLogs()
    datas, pager = bll.search(keyword, page_num, 'info')

    table_html = get_table_html(datas)

    return render_template("credits_admin/credits_list.html", table_html=table_html, pager=pager,
                           datas=datas)

@bp_credits_pages.route('apply_credits_admin', methods=['GET'])
@check_admin_login
def apply_credits_admin(admin_token:UserToken):
    keyword = http_helper.get_prams("k")
    page_index = http_helper.get_prams_int("p", 1)
    type_id = http_helper.get_prams_int("tid",2)

    types = [
        {
            "id": 2,
            "name": "未处理"
        },
        {
            "id": 1,
            "name": "所有"
        },

        {
            "id": 3,
            "name": "已处理"
        }
    ]

    bll = ApplyCredites()
    datas, pager = bll.search_content(keyword, type_id, page_index)

    del_btn_allow = {"show_name": "通过", "url": "apply_credits_ap?t=1&ids=#_id#", "confirm": True}
    del_btn_not_allow = {"show_name": "不通过", "url": "apply_credits_ap?t=2&ids=#_id#", "confirm": True}
    table_html = get_table_html(datas, [del_btn_allow, del_btn_not_allow])

    return render_template("credits_admin/apply_credits.html",table_html=table_html,pager=pager, types=types)

@bp_credits_pages.route('apply_credits_ap', methods=['GET', 'POST'])
@check_admin_login
def apply_credits_ap(admin_token:UserToken):
    apply_type = http_helper.get_prams_int("t")
    if apply_type:
        data_id = http_helper.get_prams("ids")
        bll = ApplyCredites()
        model = bll.find_one_by_id(data_id)
        model.is_complate = True
        model.is_apply = True if apply_type==1 else False


        model.apply_ni_name =  admin_token.ni_name
        model.apply_username = admin_token.name
        model.apply_time = time.time()

        is_succesfull,err = bll.apply_opt(model)
        if err:
            print(err)

    return redirect("apply_credits_admin")



@bp_credits_pages.route('credit_plan_admin', methods=['GET'])
@check_admin_login
def credit_plan_admin(admin_token:UserToken):

    bll = CreditsPlanBll()
    datas = bll.find_all()

    del_btn = {"show_name": "删除", "url": "credit_plan_admin_del?ids=#_id#", "confirm": True}
    modify_btn = {"show_name": "修改", "url": "credit_plan_admin_save?_id=#_id#", "confirm": False}
    table_html = get_table_html(datas, [del_btn, modify_btn])

    return render_template("credits_admin/credits_plan.html",table_html=table_html)

@bp_credits_pages.route('credit_plan_admin_del', methods=['GET', 'POST'])
def credit_plan_admin_del():
    CreditsPlanBll().delete_from_page(http_helper.get_prams("ids"))
    return redirect("credit_plan_admin")

@bp_credits_pages.route('credit_plan_admin_save', methods=['GET','POST'])
@check_admin_login
def credit_plan_admin_save(admin_token:UserToken):
    data_id = http_helper.get_prams('_id')

    bll = CreditsPlanBll()
    model = bll.new_instance()
    if data_id:
        model = bll.find_one_by_id(data_id)

    err = ''
    if request.method == 'POST':
        dic_prams = http_helper.get_prams_dict()
        model.dict_to_model(dic_prams)
        if data_id:
            is_success = bll.update(model)
        else:
            is_success = bll.add(model)
        if is_success:
            return redirect('credit_plan_admin')

    return render_template("credits_admin/credits_plan_save.html",model=model, err=err)

# endregion
