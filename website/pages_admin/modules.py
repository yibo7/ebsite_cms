from flask import render_template, request, redirect, jsonify, g, render_template_string, current_app
from markupsafe import Markup

from website.pages_admin import admin_blue
from eb_utils import http_helper
from eb_utils.configs import WebPaths


@admin_blue.route('modules', methods=['GET'])
def modules():
    datas = current_app.modules

    return render_template(WebPaths.get_admin_path("modules/list.html"),datas=datas)


@admin_blue.route('modules_save', methods=['GET', 'POST'])
def modules_save():
    data_id = http_helper.get_prams('id')
    # print(data_id)
    err = ''
    safe_html=''
    if data_id:
        model =current_app.modules[data_id]
        # print(model)
        dic_prams = model.get_configs()
        params_temp = model.settings_temp
        if request.method == 'POST':
            dic_prams = http_helper.get_prams_dict()
            model.set_configs(dic_prams)
        safe_html = Markup(render_template_string(params_temp, model=dic_prams))
    return render_template(WebPaths.get_admin_path("modules/save.html"), data_id=data_id,params_temp=safe_html, err=err)

