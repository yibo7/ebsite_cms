import hashlib
import os
import re
from io import BytesIO

from bson import ObjectId
from flask import (request, jsonify, send_file,
                   current_app, abort, redirect)

from bll.file_upload import FileUpload
from decorators import rate_limit_ip, check_admin_login
from eb_cache import cache
from entity.user_token import UserToken
from website.apis import api_blue


@api_blue.route('upfile', methods=['POST'])
@rate_limit_ip(10,1) # 同一IP，1分钟内只允许请求10次
@check_admin_login
def up_file(admin_token:UserToken):
    request_type = request.args.get('t')  # t=ume
    data = {"originalName": '', "name": '', "url": '', "size": 0, "state": 'unknown err', "type": ''}
    file = None
    if 'ume' in request_type:  # 有可能是'ume'也有可能是ume?type=ajax
        file = request.files['upfile']

    elif request_type in ['img', 'file']:
        file = request.files['file']


    if file:
        upload_max_size = current_app.config['upload_max_size']
        upload_types = current_app.config['upload_types']
        # 将upload_types字符串分割成后缀列表
        ALLOWED_EXTENSIONS = [ext.strip() for ext in upload_types.split(',')]
        original_name = file.filename
        file_extension = original_name.rsplit('.', 1)[1].lower()
        file_extension = f'.{file_extension}'
        # print(file_extension)
        if file_extension.lower() not in ALLOWED_EXTENSIONS:
            data["state"] = f"Not allowed file type:{file_extension}"
            return jsonify(data)

        content_value = file.read()
        size = len(content_value)
        MAX_FILE_SIZE = int(upload_max_size) * 1024 * 1024 # 转换成MB
        if size > MAX_FILE_SIZE:  # 文件大小检查
            data["state"] = 'File size exceeds the limit of 5MB.'
            return jsonify(data)

        hash_md5 = hashlib.md5()
        hash_md5.update(content_value)
        md5_value = hash_md5.hexdigest()

        bll = FileUpload()
        model = bll.new_instance()
        model.original_name = file.filename
        # model.content = content_value
        model.mimetype = file.mimetype
        model.md5 = md5_value
        model.type = file_extension
        model.size = size
        model_old = bll.find_one_by_where({"md5": model.md5})
        if model_old:
            # 仅检查本地文件是否被误删，MongoDB/COS 不容易误删，直接复用
            file_exists = True
            if model_old.url and model_old.url.startswith('/uploads/'):
                file_exists = os.path.exists(
                    os.path.join(current_app.root_path, model_old.url.lstrip('/'))
                )

            if not file_exists:
                bll.delete_by_id(model_old._id)  # 文件丢了，删失效记录
                model_old = None

        if not model_old:
            model.user_id = admin_token.id
            model.user_name = admin_token.name
            is_succesful, msg = current_app.pm.upfile(content_value, model)
            if not is_succesful:
                data["state"] = msg
                return jsonify(data)
            bll.add(model)

        data["originalName"] = original_name
        data["name"] = original_name
        # 返回给前端的 URL 一律用扁平格式
        file_id = model._id if not model_old else model_old._id
        data["url"] = f"/api/file/{file_id}{file_extension}"
        data["size"] = size
        data["state"] = "SUCCESS"
        data["type"] = file_extension

    return jsonify(data)


@api_blue.route('file/<path:file_path>', methods=['GET'])
# @cache.cached(timeout=600, query_string=True)
def get_file(file_path):
    """
    统一的文件读取接口，通过上传插件抽象读取所有后端的文件。
    支持格式: /api/file/<file_id>.<ext>
    """
    # 用正则从路径中提取 file_id，支持任意层子目录
    match = re.search(r'([a-f0-9]{24})\.[a-zA-Z0-9]+$', file_path)
    if not match:
        abort(404)

    file_id = match.group(1) #ObjectId()
    bll = FileUpload()
    model = bll.find_one_by_id(file_id)
    if not model:
        abort(404)

    # 如果文件没有 plugin_id（旧数据），根据 url 特征判断后端
    if not model.plugin_id:
        if model.content:
            # 退化为旧版 MongoDB 读取逻辑
            return send_file(BytesIO(model.content), mimetype=model.mimetype)
        abort(404)

    # 通过插件系统读取
    success, result = current_app.pm.readfile(model)
    if not success:
        abort(404)

    # 直读型插件（如 COS）返回重定向标记
    if isinstance(result, str) and result.startswith('redirect:'):
        return redirect(result[9:])

    # 代理型插件返回文件内容
    return send_file(BytesIO(result), mimetype=model.mimetype,
                     last_modified=getattr(model, 'add_time', None))


