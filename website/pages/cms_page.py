import threading
from urllib.parse import quote

from flask import render_template, render_template_string, abort, request, make_response

from bll.new_class import NewsClass
from bll.new_content import NewsContent
from bll.new_special import NewsSpecial
from bll.content_tags import ContentTags
from bll.templates import Templates
from eb_utils import http_helper
from eb_utils.configs import SiteConstant
from website.pages import pages_blue


@pages_blue.route('/c<int:id>p<int:p>.html', methods=['GET'])
def list(id: int, p: int):
    model = NewsClass().get_by_int_id(id)
    if model:
        bll = NewsContent()
        rewrite_rule = f'/c{id}p{{0}}.html'
        data_list, pager = bll.find_pager(p, model.page_size, rewrite_rule, {'class_id': model._id})
        temp_model = Templates(1).find_one_by_id(model.class_temp_id)
        if temp_model.temp_model == 1:
            return render_template_string(temp_model.temp_code, model=model, data_list=data_list, pager=pager)
        else:
            return render_template(temp_model.file_path, model=model, data_list=data_list, pager=pager)
    abort(404)


# @pages_blue.route('/a<int:id>.html', methods=['GET'])
# def content(id: int):
#     bll = NewsContent()
#     model = bll.get_by_int_id(id)
#     if model:
#         class_model = NewsClass().find_one_by_id(model.class_id)
#         if class_model:
#             temp_model = Templates(2).find_one_by_id(class_model.content_temp_id)
#             if temp_model.temp_model == 1:
#                 return render_template_string(temp_model.temp_code, model=model, class_model=class_model)
#             else:
#                 return render_template(temp_model.file_path, model=model, class_model=class_model)
#     abort(404)


@pages_blue.route('/a<int:id>.html')
def content(id):
    bll = NewsContent()
    model = bll.get_by_int_id(id)
    if not model:
        abort(404)

    class_model = NewsClass().find_one_by_id(model.class_id)
    if not class_model:
        abort(404)

    temp_model = Templates(2).find_one_by_id(class_model.content_temp_id)
    if not temp_model:
        abort(404)

    cookie_key = f'viewed_{id}'
    cookie_test_key = 'can_cookie'
    viewed = request.cookies.get(cookie_key)
    can_cookie = request.cookies.get(cookie_test_key)

    response = None

    if can_cookie:
        # 客户端支持 Cookie，只有第一次没 viewed 才统计 hits
        if not viewed:
            threading.Thread(target=bll.update_hits, args=(model._id,), daemon=True).start()
            # 设置 viewed cookie，防止短时间重复统计
            max_age = 300  # 5分钟
            response = make_response(render_template(temp_model.file_path, model=model, class_model=class_model))
            response.set_cookie(cookie_key, '1', max_age=max_age, httponly=True)
        else:
            # 已有 viewed，不统计
            response = make_response(render_template(temp_model.file_path, model=model, class_model=class_model))
    else:
        # 第一次访问，没 can_cookie，设置 can_cookie 但不统计
        response = make_response(render_template(temp_model.file_path, model=model, class_model=class_model))
        response.set_cookie(cookie_test_key, '1', max_age=3600, httponly=True)  # 1小时有效

    return response


@pages_blue.route('/s<int:id>p<int:p>.html', methods=['GET'])
def special(id: int, p:int):
    model = NewsSpecial().get_by_int_id(id)
    if model:
        temp_model = Templates(3).find_one_by_id(model.temp_id)
        query = {"id": {"$in": model.content_ids}}
        rewrite_rule = f'/s{id}p{{0}}.html'
        data_list, pager = NewsContent().find_pager(p, model.page_size, rewrite_rule, query)
        if temp_model.temp_model == 1:
            return render_template_string(temp_model.temp_code, model=model, data_list=data_list, pager=pager)
        else:
            return render_template(temp_model.file_path, model=model, data_list=data_list, pager=pager)
    abort(404)



@pages_blue.route('/tgv<md5:tag_id>ps<int:page_number>.html', methods=['GET'])
def list_tag(tag_id: str, page_number: int):
    bll = NewsContent()
    tag_model = ContentTags().find_one_by_id(tag_id)
    if not tag_model:
        return [], ""
    s_where = {"tags": tag_model.name}
    rewrite_rule = f'/tgv{tag_id}ps{{0}}.html'
    datas, pager = bll.find_pager(page_number, SiteConstant.PAGE_SIZE_AD, rewrite_rule, s_where)

    if datas:
        return render_template("list_tag_value.html",model = tag_model, data_list=datas,pager=pager)
    abort(404)

# @pages_blue.route('/tags.html', methods=['GET']) 统一要带页码更规范些
@pages_blue.route('/tags<int:p>.html', methods=['GET'])
def tags(p: int = 1):
    bll = ContentTags()
    rewrite_rule = f'/tags{{0}}.html'
    data_list, pager = bll.find_pager(p, 300, rewrite_rule)
    return render_template("tags.html", data_list=data_list, pager=pager)

@pages_blue.route('/search.html', methods=['GET'])
def search():
    bll = NewsContent()
    key_word = http_helper.get_prams("k")

    if not key_word:
        abort(404)

    key_word = key_word

    page_size = SiteConstant.PAGE_SIZE_AD
    page_number = http_helper.get_prams_int("p",1)

    rewrite_rule = f'/search.html?k={quote(key_word)}&p={{0}}'
    data_list, pager = bll.search_full(key_word,page_number,page_size, rewrite_rule)
    return render_template("search.html",key_word=key_word, data_list=data_list, pager=pager)