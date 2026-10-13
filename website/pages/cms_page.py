import threading
from urllib.parse import quote

import pymongo
from flask import render_template, render_template_string, abort, request, make_response, current_app, g

import eb_cache
from bll.new_class import NewsClass
from bll.new_content import NewsContent
from bll.temp_data_provider import TempDataProvider
from bll.new_special import NewsSpecial
from bll.content_tags import ContentTags
from bll.templates import Templates
from eb_utils import http_helper
from eb_utils.configs import SiteConstant
from eb_utils.mvc_pager import MvcPager
from signals import content_saved, search_prepare
from website.pages import pages_blue


@pages_blue.route('/c<int:id>p<int:p>.html', methods=['GET'])
def list(id: int, p: int):
    model = NewsClass().get_by_int_id(id)
    if model:
        bll = NewsContent()
        rewrite_rule = f'/c{id}p{{0}}.html'
        model.page_size = current_app.config["list_page_size"]

        sort_key = [("order_id", pymongo.DESCENDING), ("_id", pymongo.DESCENDING)]

        # 列表页只返回模板需要的字段，大幅减少 MongoDB 网络传输
        # list_projection = {
        #     'title': 1, 'small_pic': 1, 'column_1': 1, 'column_2': 1,
        #     'column_3': 1, 'column_4': 1, 'column_11': 1, 'column_13': 1,
        #     'hits': 1, 'id': 1
        # }

        list_projection = None

        # 缓存键：版本号 + 分类 + 页码 + 语言，内容更新时自动失效
        ver_key = f"list_ver:{id}"
        ver = eb_cache.get(ver_key) or 0
        lang = getattr(g, 'lang', 'zh')
        cache_key = f"list_data:{id}:{p}:{lang}:v{ver}"
        cached = eb_cache.get(cache_key)

        if cached:
            data_list, pager = cached
        else:
            data_list, pager = bll.find_pager(p, model.page_size, rewrite_rule,
                                              {'class_id': model._id},
                                              sort_key=sort_key,
                                              projection=list_projection)
            # 仅当有数据时才缓存（避免空缓存穿透）
            if data_list:
                eb_cache.set_data((data_list, pager), ex_second=300, key=cache_key)

        temp_model = Templates(1).find_one_by_id(model.class_temp_id)

        if temp_model.temp_model == 1:
            return render_template_string(temp_model.temp_code, model=model, data_list=data_list, pager=pager,
                                           temp_data=TempDataProvider())
        else:
            return render_template(temp_model.file_path, model=model, data_list=data_list, pager=pager,
                                   temp_data=TempDataProvider())
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

# 1×1 透明 GIF，用于浏览量计数信标
_PIXEL_GIF = (b'GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!'
              b'\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;')


def _inject_hit_beacon(html: str, content_id: int) -> str:
    """
    在 </body> 前插入 1×1 浏览量计数信标。

    采用自动注入而不是要求模板自己写：主题目录下有 5 份 content.html，
    另有存放在数据库里的“代码模板”(Templates.temp_code)，逐个修改既麻烦
    又必然遗漏。若模板已自行放置 /hit/ 信标，则不再重复注入。
    """
    if '/hit/' in html:
        return html
    beacon = (f'<img src="/hit/{content_id}.gif" width="1" height="1" alt="" '
              f'style="position:absolute;left:-9999px;top:0" aria-hidden="true">')
    idx = html.rfind('</body>')
    if idx == -1:
        return html + beacon
    return html[:idx] + beacon + html[idx:]


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

    # 预计算相关推荐数据
    temp_data = TempDataProvider()
    related_datas = temp_data.get_related_by_tags(str(model._id), top=10)

    # 纯渲染：视图内不设置任何 cookie、也不做计数 —— 响应因而可被 CDN 完整缓存，
    # 并且对所有访客完全相同。浏览量改由页面末尾的 1×1 信标（/hit/<id>.gif）统计。
    if temp_model.temp_model == 1:
        # 代码模板
        html = render_template_string(
            temp_model.temp_code,
            model=model,
            class_model=class_model,
            temp_data=temp_data,
            related_datas=related_datas
        )
    else:
        # 文件模板
        html = render_template(
            temp_model.file_path,
            model=model,
            class_model=class_model,
            temp_data=temp_data,
            related_datas=related_datas
        )

    return _inject_hit_beacon(html, id)


@pages_blue.route('/hit/<int:id>.gif')
def hit(id):
    """
    浏览量计数信标。

    它是独立请求，所以内容页可以整体进 CDN 缓存；而本响应自身 no-store，
    保证每次页面加载都会回源计数（不被浏览器或 CDN 缓存掉）。
    5 分钟内同一浏览器对同一内容只计一次。
    """
    cookie_key = f'viewed_{id}'
    already = request.cookies.get(cookie_key)
    if not already:
        # $inc 为原子操作，并发访客同时触发也不会丢计数
        threading.Thread(target=NewsContent().update_hits_by_int_id,
                         args=(id,), daemon=True).start()

    resp = make_response(_PIXEL_GIF)
    resp.headers['Content-Type'] = 'image/gif'
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate'
    if not already:
        # path 限定在 /hit/ 下，这些 cookie 不会污染其他页面的请求头
        resp.set_cookie(cookie_key, '1', max_age=300, httponly=True,
                        path='/hit/', samesite='Lax')
    return resp


@pages_blue.route('/u<user_id>.html', defaults={'p': 1}, methods=['GET'])
@pages_blue.route('/u<user_id>p<int:p>.html', methods=['GET'])
def user_content(user_id, p):
    """用户主页：展示该用户发布的内容列表"""
    temp_data = TempDataProvider()
    user_info = temp_data.get_user_info(user_id)
    if not user_info:
        abort(404)

    page_size = current_app.config["list_page_size"]
    data_list, pager = temp_data.get_user_content_list(user_id, p, page_size)

    return render_template(
        'user/home.html',
        user_info=user_info,
        data_list=data_list,
        pager=pager,
        user_id=user_id,
    )


@pages_blue.route('/s<int:id>p<int:p>.html', methods=['GET'])
def special(id: int, p:int):
    model = NewsSpecial().get_by_int_id(id)
    if model:
        temp_model = Templates(3).find_one_by_id(model.temp_id)
        query = {"id": {"$in": model.content_ids}}
        rewrite_rule = f'/s{id}p{{0}}.html'
        model.page_size = current_app.config["list_page_size"]
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
    page_size = current_app.config["list_page_size"]
    datas, pager = bll.find_pager(page_number,page_size, rewrite_rule, s_where)

    if datas:
        return render_template("list_tag_value.html",model = tag_model, data_list=datas,pager=pager)
    abort(404)

# @pages_blue.route('/tags.html', methods=['GET']) 统一要带页码更规范些
@pages_blue.route('/tags<int:p>.html', methods=['GET'])
def tags(p: int = 1):
    bll = ContentTags()
    rewrite_rule = f'/tags{{0}}.html'
    page_size = current_app.config["list_page_size"] * 20
    data_list, pager = bll.find_pager(p, page_size, rewrite_rule,"","article_count")
    return render_template("tags.html", data_list=data_list, pager=pager)

@pages_blue.route('/search.html', methods=['GET'])
def search():
    bll = NewsContent()
    key_word = http_helper.get_prams("k")

    page_size = current_app.config["list_page_size"]
    page_number = http_helper.get_prams_int("p", 1)

    key_word = (key_word or '').strip()
    rewrite_rule = f'/search.html?k={quote(key_word)}&p={{0}}'

    # ---- 信号：让模块可以自定义搜索 ----
    ctx = {
        "keyword": key_word,
        "page_number": page_number,
        "page_size": page_size,
        "rewrite_rule": rewrite_rule,
    }
    search_prepare.send(ctx)
    template_name = ctx.get("template", "search.html")
    custom_query = ctx.get("query")
    if custom_query:
        # ---- 模块自定义搜索路径 ----
        total = bll.count(custom_query)

        datas = []
        if total > 0:
            datas, _ = bll.find_pages(page_number, page_size, custom_query,
                                       "_id", pymongo.DESCENDING)

        # 生成分页器
        pager = ''
        if total > page_size:
            pg = MvcPager()
            pg.current_page = page_number
            pg.total_count = total
            pg.page_size = page_size
            pg.params = None
            pg.ShowCodeNum = 10
            pg.rewrite_rule = rewrite_rule
            pager = pg.show_pages()


        return render_template(template_name, key_word=key_word,
                               data_list=datas, pager=pager)

    # ---- 默认搜索路径 ----
    data_list, pager = bll.search_full(key_word, page_number, page_size, rewrite_rule)
    return render_template(template_name, key_word=key_word, data_list=data_list, pager=pager)


@content_saved.connect
def _invalidate_list_cache(sender, model):
    """内容保存后自动失效对应分类的列表缓存，确保前台即时看到更新"""
    try:
        class_n_id = getattr(model, 'class_n_id', None) or getattr(model, 'id', None)
        if class_n_id:
            ver_key = f"list_ver:{class_n_id}"
            ver = eb_cache.get(ver_key) or 0
            eb_cache.set_data(ver + 1, ex_second=86400, key=ver_key)
    except Exception:
        pass  # 缓存失效不影响主流程