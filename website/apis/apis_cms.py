
from flask import jsonify, request

from bll.admin_menus import AdminMenus
from bll.custom_form import CustomForm
from bll.custom_form_data import CustomFormData
from bll.new_class import NewsClass
from bll.new_content import NewsContent
from bll.new_special import NewsSpecial
from bll.user import User
from bll.widgets import Widgets
from decorators import rate_limit_ip
from eb_cache import cache
from eb_utils import http_helper
from eb_utils.image_code import ImageCode
from entity import api_msg
from entity.api_msg import ApiMsg, api_succesful
from website.apis import api_blue


@api_blue.route('getsubmenus', methods=['POST'])
def getsubmenus():

    data_id = http_helper.get_prams('pid')
    data = []
    if data_id:
        menus_p = AdminMenus().get_by_pid(data_id)
        for ptree in menus_p:

            item_p = {"MenuTitle": ptree.menu_name, "img": ptree.image_url, "Items": []}
            
            menus_s = AdminMenus().get_by_pid(str(ptree._id))
            for stree in menus_s:
                item_s = {"ItemName": stree.menu_name, "url": stree.page_url, "img": stree.image_url}
                item_p["Items"].append(item_s)
            data.append(item_p)

    return jsonify(api_succesful(data))

@api_blue.route('widget', methods=['GET', 'POST'])
def widget():
    """
    获取某个部件模板渲染后的html代码
    """
    widget_id = http_helper.get_prams('wid')
    data,s_title = Widgets().get_content(widget_id)
    return jsonify(api_msg.api_succesful(data,s_title))

@api_blue.route('custom_form', methods=['POST'])
@rate_limit_ip(3,60) # 一小时只允许调用3次
def custom_form():
    key = request.args.get('key')
    api_msg = ApiMsg('err')

    a_key = key.split('_')

    if len(a_key) == 2:
        form_id = a_key[1]
        bll_form = CustomForm()
        form_model = bll_form.find_one_by_id(form_id)
        if form_model:
            dict_prams = http_helper.get_prams_dict()
            dict_prams = http_helper.clean_dict(dict_prams)
            is_safe = True
            if form_model.open_safe_code:
                image_code = dict_prams.get('safe_code')
                is_safe, api_msg.data = ImageCode().check_code(image_code)
            if is_safe:
                if dict_prams:
                    if 'safe_code' in dict_prams:
                        dict_prams.pop('safe_code')
                    is_safe, api_msg.data = CustomFormData().add(form_model, dict_prams)
                    api_msg.success = is_safe
            else:
                api_msg.data = '验证码不正确!'
        else:
            api_msg.data = f'can`t find form {form_id}'
    else:
        api_msg.data = 'bad for the form id'

    return jsonify(api_msg.__dict__)

@api_blue.route('category/', methods=['GET', 'POST'])
def category():
    bll = NewsClass()
    parent_id = http_helper.get_prams('pid')
    if parent_id:
        models = bll.get_by_pid(parent_id)
    else:
        models = bll.get_by_pid('')

    models_dicts = [model.to_short_dic() for model in models]
    return jsonify({'code': 0, "data": models_dicts})


@api_blue.route('content', methods=['GET', 'POST'])
@cache.cached(timeout=2, query_string=True)  # 启用缓存，设置超时为 2 秒，
def content():
    categoryid = http_helper.get_prams('cid')  # 使用 get 方法获取查询参数，如果不存在则返回 None
    top = http_helper.get_prams_int('top', 20)
    if top > 1000:  # 防止过大
        top = 1000
    bll = NewsContent()
    data_type = http_helper.get_prams_int('type', 1)  # 1为最新数据 2为热门 3 推荐
    if data_type == 3:
        models = bll.get_good_datas(categoryid, top)
    elif data_type == 2:
        models = bll.get_hot_datas(categoryid, top)
    else:
        models = bll.get_new_datas(categoryid, top)

    models_dicts = [model.to_list_dic() for model in models]
    return jsonify({'code': 0, "data": models_dicts})


@api_blue.route('content_details', methods=['GET', 'POST'])
def content_details():
    """
    获取内容详情
    @return:
    """
    data_id = http_helper.get_prams('id')  # 使用 get 方法获取查询参数，如果不存在则返回 None
    if data_id:
        bll = NewsContent()

        model = bll.find_one_by_id(data_id)

        return jsonify({'code': 0, "data": model.to_dict([''])})
    return jsonify({'code': -1, "msg": 'content id bad'})


@api_blue.route('content_pages', methods=['GET', 'POST'])
def content_pages():
    """
    获取分类页列表-分页
    @return:
    """
    categoryid = http_helper.get_prams('cid')
    pnumber = http_helper.get_prams_int('pnumber', 1)
    bll = NewsContent()
    if categoryid:
        models, i_count = bll.get_by_class_id(categoryid, pnumber)
        models_dicts = [model.to_list_dic() for model in models]
        return jsonify({'code': 0, "data": models_dicts, 'count': i_count})
    return 'not found.', 404


@api_blue.route('special', methods=['GET', 'POST'])
def special():
    """
    获取专题列表-非分页
    @return:
    """
    bll = NewsSpecial()
    parent_id = http_helper.get_prams('pid')
    if parent_id:
        models = bll.get_by_pid(parent_id)
    else:
        models = bll.get_by_pid('')

    models_dicts = [model.to_short_dic() for model in models]
    return jsonify({'code': 0, "data": models_dicts})


@api_blue.route('special_pages', methods=['GET', 'POST'])
def special_pages():
    """
    获取专题下的分页内容
    """
    special_id = http_helper.get_prams('sid')
    pnumber = http_helper.get_prams_int('pnumber', 1)
    bll = NewsSpecial()
    if special_id:
        models, i_count = bll.get_by_speical_id(special_id, pnumber)
        models_dicts = [model.to_list_dic() for model in models]
        return jsonify({'code': 0, "data": models_dicts, 'count': i_count})
    return 'not found.', 404

@api_blue.route('auto_post_content/<int:user_id>/<int:class_id>/<md5:site_key_md5>', methods=['POST'])
def auto_post_content(user_id: int, class_id: int, site_key_md5: str):
    """
    可以通过三方或具自动入库的接口，此接口虽然不需要用户登录权限，但需要网站的密钥配合使用
    可以post的参数为内容实体字段
    add_time, title, info, small_pic, class_name, class_id, class_n_id, seo_title, seo_keyword, seo_description, hits, comment_num, favorable_num, user_id, user_name, user_ni_name, rand_num, is_good,  id, column_1, column_2, column_3, column_4, column_5, column_6, column_7, column_8, column_9, column_10, column_11, column_12, column_13, column_14, column_15, column_16, column_17, column_18, column_19, column_20, column_21
    有一个特殊的字段tag不能直接传递，需要通过tagstr参数传递，多个标签可用英文逗号分开
    :param user_id: 添加用户的ID整数
    :param class_id: 要添加到哪个分类下的分类ID整数
    :param site_key_md5: 网密钥的md5值
    :return:
    """

    user_model = User().get_by_int_id(user_id)
    class_model = NewsClass().get_by_int_id(class_id)
    if not user_model or not class_model:
        return jsonify(api_msg.api_err("发布失败，不存在用户或不存在分类"))

    dic_prams = http_helper.get_prams_dict()

    bll = NewsContent()
    model = bll.new_instance()
    model.dict_to_model(dic_prams)

    if not model.title:
        return jsonify(api_msg.api_err("标题不能为空！"))

    model.user_id = user_model._id
    model.user_name = user_model.username
    model.user_ni_name = user_model.ni_name

    model.class_name = class_model.class_name
    model.class_id = class_model._id
    model.class_n_id = class_model.id

    if model.tags:
        return jsonify(api_msg.api_err("请用字段tagstr提交标签，多个值用英文逗号分开，比如tagstr=标签1,标签2"))

    tagstr = http_helper.get_prams("tagstr")
    if tagstr:
        model.set_tag_string(tagstr)

    bll.save_content(model)

    return jsonify(api_msg.api_succesful("发布成功"))
