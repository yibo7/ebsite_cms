from flask import render_template, request, redirect, g

from bll.widget_bll import WidgetBll
from entity.widgets_model import WidgetsModel
from temp_expand import get_table_html
from website.pages_admin import admin_blue
from eb_utils import http_helper, get_all_fields
from eb_utils.configs import WebPaths


# region class

@admin_blue.route('widget_list', methods=['GET'])
def widgets_list():
    keyword = http_helper.get_prams("k")
    page_num = http_helper.get_prams_int("p", 1)
    datas, pager = WidgetBll().search_data(keyword, page_num)

    del_btn = {"show_name": "删除", "url": "widget_list_del?ids=#_id#", "confirm": True}
    modify_btn = {"show_name": "修改", "url": "widget_list_save?_id=#_id#", "confirm": False}
    open_code_btn = {"show_name": "调用代码", "url": "javascript:open_code('#_id#')", "confirm": False}

    table_html = get_table_html(datas, [del_btn, modify_btn, open_code_btn])

    return render_template(WebPaths.get_admin_path("widgets/widget_list.html"), pager=pager,
                           table_html=table_html)


@admin_blue.route('widget_sel_type', methods=['GET'])
def widget_sel_type():
    data_list = WidgetBll().get_types()
    return render_template(WebPaths.get_admin_path("widgets/widget_sel_type.html"), data_list=data_list)


@admin_blue.route('widget_list_save', methods=['GET', 'POST'])
def widgets_list_save():
    g_id = http_helper.get_prams('_id')
    # temp_type = http_helper.get_prams_int('t')
    temp_type = request.args.get('t', 0)
    temp_type = int(temp_type)
    # print("temp_type:"+str(temp_type))

    model = WidgetsModel()
    model.temp_type = temp_type
    bll = WidgetBll()
    if g_id:
        model = bll.find_one_by_id(g_id)
    err = ''

    temp_bll = bll.get_type_by_id(model.temp_type)

    if request.method == 'POST':
        dic_prams = http_helper.get_prams_dict()
        if 'file' in dic_prams:
            del dic_prams['file']  # 在上传图片时会生成一个file表单
        model.dict_to_model(dic_prams)
        model.user_id = g.uid
        temp_bll.saving(model)
        bll.save(model)
        # return redirect('widget_list')

    all_fields = ''

    bll_hanndler = temp_bll.bll_hanndler()
    if bll_hanndler:
        all_fields = get_all_fields(bll_hanndler.new_instance())
    temp_file = temp_bll.temp # get('temp')
    desc_asc = bll.get_desc_asc()

    return render_template(f"widgets/{temp_file}",all_fields=all_fields, desc_asc=desc_asc, model=model, err=err)


@admin_blue.route('widget_list_del', methods=['GET', 'POST'])
def widgets_list_del():
    WidgetBll().delete_from_page(http_helper.get_prams("ids"))
    return redirect("widget_list")

# endregion
