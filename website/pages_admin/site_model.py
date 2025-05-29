from flask import render_template, request, redirect, url_for
from bll.site_model import SiteModel
from entity.site_model_entity import FieldModel
from temp_expand import get_table_html
from website.pages_admin import admin_blue
from eb_utils import http_helper, flask_utils
from eb_utils.configs import WebPaths



@admin_blue.route('model_list', methods=['GET'])
def model_list():
    bll = SiteModel()

    type_id = http_helper.get_prams_int("tid")

    if not type_id:
        return flask_utils.show_err("没有type_id")

    datas = bll.get_by_type_id(type_id)

    del_btn = {"show_name": "删除", "url": f"model_list_del?ids=#_id#", "confirm": True}
    modify_btn = {"show_name": "修改", "url": f"model_list_save?_id=#_id#&tid={type_id}", "confirm": False}
    fields_btn = {"show_name": "管理字段", "url": f"model_fields?_id=#_id#", "confirm": False}

    table_html = get_table_html(datas, [del_btn, modify_btn, fields_btn], False)

    return render_template(WebPaths.get_admin_path("site_model/model_list.html"),type_id=type_id, table_html=table_html)


@admin_blue.route('model_list_save', methods=['GET', 'POST'])
def model_list_save():
    g_id = http_helper.get_prams('_id')
    type_id = http_helper.get_prams_int("tid")

    if not type_id:
        return flask_utils.show_err("没有type_id")

    bll = SiteModel()
    model = bll.new_instance()
    if g_id:
        model = bll.find_one_by_id(g_id)
    err = ''
    if request.method == 'POST':
        model.name = http_helper.get_prams('name')
        model.type_id = type_id
        bll.save_default(model)
        return redirect(f'model_list?tid={type_id}')

    return render_template(WebPaths.get_admin_path("site_model/model_list_save.html"),type_id=type_id, model=model, err=err)


@admin_blue.route('model_list_del', methods=['GET', 'POST'])
def model_list_del():
    SiteModel().delete_from_page(http_helper.get_prams("ids"))
    return flask_utils.go_back()
    # return redirect(f"model_list")


@admin_blue.route('model_fields', methods=['GET', 'POST'])
def model_fields():
    g_id = request.args.get('_id')

    bll = SiteModel()
    model = bll.find_one_by_id(g_id)
    err = ''

    field_name = request.args.get('field_name')
    field_item = FieldModel("","","","","")
    if field_name and model:
        field_item = bll.get_field_by_name(model,field_name)

    if request.method == 'POST':
        dict_prams = http_helper.get_prams_dict()

        ctr_id = dict_prams.get('control_id')
        control = bll.get_control_by_id(int(ctr_id))
        dict_prams['control_name'] = control.name  # 获取控件的名称
        field_model = FieldModel(**dict_prams)
        is_ok = bll.save_fields(model, field_model,field_name)
        if not is_ok:
            err = '已经存在相同的字段，若想修改请删除后再添加'
    fields = bll.get_fields(model.type_id)
    controls = bll.get_controls()

    return render_template(WebPaths.get_admin_path("site_model/model_fields.html"), model=model,
                           controls=controls, fields=fields, err=err,field_item = field_item)


@admin_blue.route('model_fields_del', methods=['GET', 'POST'])
def model_fields_del():
    _id = http_helper.get_prams('_id')
    field_name = http_helper.get_prams('field_name')
    SiteModel().del_field(_id, field_name)
    return redirect(f"model_fields?_id={_id}")


@admin_blue.route('model_fields_move', methods=['GET'])
def model_fields_move():
    _id = http_helper.get_prams('_id')
    field_name = http_helper.get_prams('field_name')
    move_type = http_helper.get_prams_int('t')
    if move_type == 0:
        SiteModel().move_up(_id, field_name)
    else:
        SiteModel().move_down(_id, field_name)

    return redirect(f"model_fields?_id={_id}")

