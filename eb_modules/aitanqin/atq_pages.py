import time

from flask import jsonify, current_app, render_template, redirect, request

from decorators import check_admin_login, check_user_login
from eb_modules.aitanqin import bp_atq_pages
from eb_utils import http_helper, flask_utils
from entity.user_token import UserToken
from bll.new_content import NewsContent
from bll.new_class import NewsClass


# region 前台页面
@bp_atq_pages.route('/', methods=['GET', 'POST'])
def atq_index():
    return render_template("atq_index.html")

@bp_atq_pages.route('/post_data', methods=['GET', 'POST'])
@check_user_login
def post_tab(user_token:UserToken):
    err = ''
    is_succesfull = False

    # 查询乐谱分类（parent_id = "6a955779ccda0b6fd6210026"）
    class_bll = NewsClass()
    class_list = class_bll.get_by_pid("6a955779ccda0b6fd6210026")

    if request.method == 'POST':
        title = http_helper.get_prams("title")
        info = http_helper.get_prams("info")
        column_1 = http_helper.get_prams("column_1")  # 歌手
        column_2 = http_helper.get_prams("column_2")  # 调式
        column_3 = http_helper.get_prams("column_3")  # 专辑名称
        column_4 = http_helper.get_prams("column_4")  # 难度级别
        column_5 = http_helper.get_prams("column_5")  # 乐谱文件路径
        column_13 = http_helper.get_prams("column_13")  # 乐谱类型
        column_14 = http_helper.get_prams("column_14")  # 文件哈希值
        class_id = http_helper.get_prams("class_id")  # 分类ID(_id)
        class_n_id = http_helper.get_prams("class_n_id")  # 分类自增ID(id)
        class_name = http_helper.get_prams("class_name")  # 分类名称

        if title and column_5:
            try:
                bll = NewsContent()
                model = bll.new_instance()
                model.title = title
                model.info = info or ''
                model.column_1 = column_1 or ''
                model.column_2 = column_2 or ''
                model.column_3 = column_3 or ''
                model.column_4 = column_4 or ''
                model.column_5 = column_5
                model.column_13 = column_13 or ''
                model.column_14 = column_14 or ''
                model.class_id = class_id or ''
                model.class_n_id = int(class_n_id) if class_n_id else 0
                model.class_name = class_name or ''
                model.user_id = str(user_token.id)
                model.user_name = user_token.name
                model.user_ni_name = user_token.ni_name

                bll.save_content(model)
                is_succesfull = True
            except Exception as e:
                err = f"保存失败: {str(e)}"
        else:
            err = "请填写必要的参数（乐谱名称和乐谱文件）!"
    return render_template("atq_post_data.html", is_succesfull=is_succesfull, err=err, class_list=class_list)

# endregion

# region 管理后台页面

# endregion
