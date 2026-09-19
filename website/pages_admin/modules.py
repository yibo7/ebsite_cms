from flask import render_template, request, redirect, jsonify, g, render_template_string, current_app
from markupsafe import Markup

from website.pages_admin import admin_blue
from eb_utils import http_helper
from eb_utils.configs import WebPaths


@admin_blue.route('modules', methods=['GET'])
def modules():
    datas = current_app.modules

    return render_template(WebPaths.get_admin_path("modules/list.html"), datas=datas)


@admin_blue.route('modules_save', methods=['GET', 'POST'])
def modules_save():
    data_id = http_helper.get_prams('id')
    err = ''
    safe_html = ''
    if data_id:
        model = current_app.modules[data_id]
        # 读取当前配置
        dic_prams = model.get_configs() or {}
        params_temp = model.settings_temp
        if request.method == 'POST':
            dic_prams = http_helper.get_prams_dict()
            # 保存配置并返回类型转换后的结果，触发模块热更新回调
            dic_prams = model.set_configs(dic_prams)

        if params_temp:
            safe_html = Markup(render_template_string(params_temp, model=dic_prams))

    return render_template(WebPaths.get_admin_path("modules/save.html"),
                           data_id=data_id, params_temp=safe_html, err=err)


@admin_blue.route('modules_toggle', methods=['POST'])
def modules_toggle():
    """
    启用/停用模块。保存 enable 状态到数据库，重启后生效。
    """
    data_id = http_helper.get_prams('id')
    enable = http_helper.get_prams('enable') == '1'

    model = current_app.modules.get(data_id)
    if not model:
        return jsonify({"code": -1, "msg": "模块不存在"})

    model.set_enable(enable)

    # 同步更新进程内状态，让界面立刻反映操作结果
    model.enable = enable
    model.is_running = enable
    model.pending_restart = True   # 标记需要重启才完全生效

    return jsonify({"code": 0, "msg": f"模块「{model.name}」已{'启用' if enable else '停用'}，重启服务后生效"})

