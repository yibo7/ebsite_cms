
from flask import jsonify, request

import eb_cache
from bll.file_upload import FileUpload
from bll.new_content import NewsContent
from bll.user import User
from bll.user_group import UserGroup
from decorators import check_token
from eb_modules.app_apis import bp_app_apis
from eb_utils import http_helper
from entity import api_msg
from entity.user_token import UserToken

@bp_app_apis.route('userinfo', methods=['POST'])
@check_token()
def userinfo(token: UserToken):
    bll = User()
    model = bll.find_one_by_id(token.id)
    if model:
        user_info = model.to_short_dic()
        user_info['group_name'] = token.group_name
        return jsonify(api_msg.api_succesful(user_info))
    return jsonify(api_msg.api_err('找不到用户'))


@bp_app_apis.route('my_data', methods=['POST'])
@check_token()
def my_data(token: UserToken):
    """
    调用我的数据
    """
    pnumber = http_helper.get_prams_int('pnumber', 1)
    bll = NewsContent()
    models, i_count = bll.get_by_user(token.id, pnumber)
    models_dicts = [model.to_short_dic() for model in models]
    return jsonify({'code': 0, "data": models_dicts, 'count': i_count})

@bp_app_apis.route('user_data', methods=['POST','GET'])
def user_data():
    """
    调用指定用户的数据
    """
    pnumber = http_helper.get_prams_int('pnumber', 1)
    user_id = http_helper.get_prams('uid')
    bll = NewsContent()
    models, i_count = bll.get_by_user(user_id, pnumber)
    models_dicts = [model.to_short_dic() for model in models]
    return jsonify({'code': 0, "data": models_dicts, 'count': i_count})

@bp_app_apis.route('update_avatar', methods=['POST'])
@check_token()
def update_avatar(token: UserToken):
    """
    修改头像
    """

    if not request.files:
        return jsonify(api_msg.api_err('请提交文件'))
    # 获取 request.files 的第一个项
    file = next(iter(request.files.values()), None)

    if file:
        # 如果文件大小超过配置的限制，则返回错误信息
        MAX_CONTENT_LENGTH = 1 * 1024 * 1024  # 1MB
        if file.content_length > MAX_CONTENT_LENGTH:
            return jsonify(api_msg.api_err('图片最大不能超过1MB'))

        content = file.read()
        bll = FileUpload()
        model = bll.new_instance()
        model.original_name = file.filename
        model.content = content
        model.mimetype = file.mimetype
        data = bll.upload(model)

        token.avatar = data.get('url')
        bll = User()
        is_succesful = bll.update_avatar(token.id, token.avatar)
        if is_succesful:
            return jsonify(api_msg.api_succesful(''))
        else:
            return jsonify(api_msg.api_err('更新失败'))
    return jsonify(api_msg.api_err('找不到file'))


@bp_app_apis.route('update_niname', methods=['POST'])
@check_token()
def update_niname(token: UserToken):
    """
    修改昵称
    """
    new_name = http_helper.get_prams('new_name')
    if new_name:
        token.ni_name = new_name
        bll = User()
        is_succesful = bll.update_niname(token.id, new_name)
        if is_succesful:
            return jsonify(api_msg.api_succesful(''))
        else:
            return jsonify(api_msg.api_err('更新失败'))
    return jsonify(api_msg.api_err('参数不完整'))


@bp_app_apis.route('logout', methods=['POST'])
@check_token(False)
def logout():
    """
    退出登录
    """
    token_key = request.headers.get('x-api-key')
    if token_key:
        eb_cache.delete(token_key)
        return jsonify(api_msg.api_succesful(''))
    return jsonify(api_msg.api_err('获取不到TOKEN-KEY'))


@bp_app_apis.route('user_groups', methods=['POST'])
@check_token()
def user_groups(token: UserToken):
    """
    获取用户组
    """
    bll = UserGroup()
    datas = bll.find_all()
    return jsonify(api_msg.api_succesful(bll.to_dicts(datas, ['add_time'])))

