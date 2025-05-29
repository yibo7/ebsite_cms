from flask import render_template, request, redirect, jsonify, g, render_template_string, current_app
from markupsafe import Markup

from website.pages_admin import admin_blue
from eb_utils import http_helper
from eb_utils.configs import WebPaths


@admin_blue.route('plugin_list', methods=['GET'])
def plugin_list():
    datas = current_app.pm.plugins
    class_list = current_app.pm.plugin_types
    sel_class_name = http_helper.get_prams('c_id') or ''
    if sel_class_name:
       datas = current_app.pm.get_by_type_name(sel_class_name)
    return render_template(WebPaths.get_admin_path("plugins/plugin_list.html"), class_list=class_list,datas=datas,sel_class_name=sel_class_name)


@admin_blue.route('plugin_list_save', methods=['GET', 'POST'])
def plugin_list_save():
    data_id = http_helper.get_prams('id')

    err = ''
    safe_html=''
    if data_id:
        model =current_app.pm.get_by_id(data_id)
        dic_prams = model.get_configs()
        params_temp = model.params_temp()
        if request.method == 'POST':
            dic_prams = http_helper.get_prams_dict()
            model.set_configs(dic_prams)
        safe_html = Markup(render_template_string(params_temp, model=dic_prams))
    return render_template(WebPaths.get_admin_path("plugins/plugin_list_save.html"), data_id=data_id,params_temp=safe_html, err=err)

