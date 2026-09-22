
import logging
import re

from flask import jsonify, request

from bll.admin_menus import AdminMenus
from bll.custom_form import CustomForm
from bll.custom_form_data import CustomFormData
from bll.new_class import NewsClass
from bll.new_content import NewsContent
from bll.new_special import NewsSpecial
from bll.user import User
from bll.widget_bll import WidgetBll
from decorators import rate_limit_ip, reject_dangerous_input, verify_site_key_hmac, verify_site_key_md5
from eb_cache import cache
from eb_utils import http_helper
from eb_utils.html_sanitizer import sanitize_html
from eb_utils.image_code import ImageCode
from entity import api_msg
from entity.api_msg import ApiMsg, api_succesful
from website.apis import api_blue

logger = logging.getLogger(__name__)


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
    data,s_title = WidgetBll().get_content(widget_id)
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

@api_blue.route('auto_post_content/<int:user_id>/<int:class_id>', methods=['POST'])
@verify_site_key_hmac
@rate_limit_ip(30, 1)  # 同一IP每分钟最多发布30次
@reject_dangerous_input
def auto_post_content(user_id: int, class_id: int):
    """
    可以通过三方或具自动入库的接口，此接口虽然不需要用户登录权限，但需要网站的密钥配合使用

    鉴权方式（请求头）：
      - X-Timestamp: 当前 Unix 时间戳（秒）
      - X-Sign: HMAC-SHA256(timestamp + ":" + 原始请求体, SiteKey)

    可以post的参数为内容实体字段
    add_time, title, info, small_pic, class_name, class_id, class_n_id, seo_title, seo_keyword, seo_description, hits, comment_num, favorable_num, user_id, user_name, user_ni_name, rand_num, is_good,  id, column_1, column_2, column_3, column_4, column_5, column_6, column_7, column_8, column_9, column_10, column_11, column_12, column_13, column_14, column_15, column_16, column_17, column_18, column_19, column_20, column_21
    有一个特殊的字段tag不能直接传递，需要通过tagstr参数传递，多个标签可用英文逗号分开
    :param user_id: 添加用户的ID整数
    :param class_id: 要添加到哪个分类下的分类ID整数
    :return:
    """

    # ── 审计日志：记录调用来源 ──
    caller_ip = http_helper.get_ip()
    caller_ua = request.headers.get('User-Agent', '')
    logger.info("API发布请求 | user_id=%s | class_id=%s | ip=%s | ua=%s",
                user_id, class_id, caller_ip, caller_ua[:200])

    user_model = User().get_by_int_id(user_id)
    class_model = NewsClass().get_by_int_id(class_id)
    if not user_model or not class_model:
        logger.warning("API发布失败 | 不存在用户或分类 | user_id=%s | class_id=%s | ip=%s",
                       user_id, class_id, caller_ip)
        return jsonify(api_msg.api_err("发布失败，不存在用户或不存在分类"))

    dic_prams = http_helper.get_prams_dict()

    # ── 字段白名单：只允许 API 调用者设置以下安全字段，防止 SSTI 注入 ──
    ALLOWED_FIELDS = {
        'title', 'info', 'small_pic', 'seo_title', 'seo_keyword', 'seo_description',
        'column_1', 'column_2', 'column_3', 'column_4',
        'column_6', 'column_7', 'column_8', 'column_9', 'column_10',
        'column_11', 'column_12', 'column_13', 'column_14', 'column_15',
        'column_16', 'column_17', 'column_18', 'column_19', 'column_20', 'column_21',
    }
    # column_5（乐谱文件路径）故意不在白名单中，防止路径遍历攻击
    # is_good、hits、user_id 等敏感字段也不在白名单中
    dic_prams = {k: v for k, v in dic_prams.items() if k in ALLOWED_FIELDS}

    # ── HTML 安全净化（防御纵深）：允许富文本标签但禁止脚本 ──
    HTML_FIELDS = {'info', 'column_1', 'column_2', 'column_3', 'column_4',
                   'column_6', 'column_7', 'column_8', 'column_9', 'column_10',
                   'column_11', 'column_12', 'column_13', 'column_14', 'column_15',
                   'column_16', 'column_17', 'column_18', 'column_19', 'column_20', 'column_21'}
    for field in HTML_FIELDS & dic_prams.keys():
        if isinstance(dic_prams[field], str) and dic_prams[field]:
            dic_prams[field] = sanitize_html(dic_prams[field])

    # ── 标题也做轻量级清理（只移除事件处理器） ──
    if 'title' in dic_prams and isinstance(dic_prams['title'], str):
        from eb_utils.html_sanitizer import strip_event_handlers
        dic_prams['title'] = strip_event_handlers(dic_prams['title'])

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

    model = bll.save_content(model)

    logger.info("API发布成功 | user_id=%s | class_id=%s | title=%s | ip=%s",
                user_id, class_id, model.title[:50], caller_ip)

    return jsonify(api_msg.api_succesful(model.get_url()))


@api_blue.route('get_content/<int:content_id>/<md5:site_key_md5>', methods=['POST', 'GET'])
@verify_site_key_md5
def get_content(content_id: int, site_key_md5: str):
    """
    通过API获取一条内容记录实例
    :param content_id: 内容Id
    :param site_key_md5: 网密钥的md5值
    :return:
    """
    if not site_key_md5:
        return jsonify(api_msg.api_err("site key md5 value failed！"))

    if content_id < 1:
        return jsonify(api_msg.api_err("content id failed！"))

    bll = NewsContent()

    model = bll.get_by_int_id(content_id)

    if not model:
        return jsonify(api_msg.api_err("获取不到内容"))

    fields = http_helper.get_prams("fields")
    if fields:  # 只需要获取这些字段，用逗号分开
        # 将字段字符串按逗号分割成列表，并去除可能的空格
        field_list = [field.strip() for field in fields.split(',') if field.strip()]

        # 获取model的字典表示
        model_dict = model.to_dict()

        # 创建只包含指定字段的新字典
        filtered_dict = {}
        for field in field_list:
            if field in model_dict:
                filtered_dict[field] = model_dict[field]
            else:
                # 可选：如果字段不存在，可以忽略或设置为None
                filtered_dict[field] = 'null'  # 或者直接忽略这个字段

        return jsonify(api_msg.api_succesful(filtered_dict))
    else:
        # 如果没有fields参数，返回完整的model字典
        return jsonify(api_msg.api_succesful(model.to_dict()))