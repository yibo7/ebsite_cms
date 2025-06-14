import hashlib
import os
from io import BytesIO

from flask import  request, jsonify, send_file, make_response, current_app, send_from_directory, abort

from bll.file_upload import FileUpload
from decorators import rate_limit_ip, check_admin_login
from eb_cache import cache
from website.apis import api_blue


@api_blue.route('upfile', methods=['POST'])
@rate_limit_ip(10,1) # 同一IP，1分钟内只允许请求5次
@check_admin_login
def up_file():
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
        if not model_old:
            is_succesful, url = current_app.pm.upfile(content_value, model)
            bll.add(model)
        # data = bll.upload(model)
        else:
            url = model_old.url
        data["originalName"] = original_name
        data["name"] = original_name
        data["url"] = url
        data["size"] = size
        data["state"] = "SUCCESS"
        data["type"] = file_extension

    return jsonify(data)


@api_blue.route('upfile/<filename>', methods=['GET'])
@cache.cached(timeout=600)  # 缓存10分钟
def get_up_file(filename):
    """
    访问文件-mongodb
    :param filename:
    :return:
    """
    bll = FileUpload()
    model = bll.find_one_by_where({'url': f'/api/upfile/{filename}'})
    if model:
        file_obj = BytesIO(model.content)
        return send_file(file_obj, mimetype=model.mimetype)
    return 'Image not found.', 404


@api_blue.route('/uploads/<date>/<filename>')
def uploaded_file(date, filename):
    """
    访问文件-本地存储
    :param date: 文件上传日期
    :param filename:
    :return:
    """

    UPLOAD_FOLDER = os.path.join(current_app.root_path, 'uploads',date)
    file_path = os.path.join(UPLOAD_FOLDER, filename)

    # 检查文件是否存在
    if not os.path.exists(file_path):
        abort(404, description="File not found")

    try:
        last_modified = os.path.getmtime(file_path)

        if request.if_modified_since:
            # 将request.if_modified_since转换为时间戳
            request_time = request.if_modified_since.timestamp()

            # 比较时间戳
            if request_time >= last_modified:
                return '', 304

        response = make_response(send_from_directory(UPLOAD_FOLDER, filename))
        response.last_modified = last_modified
        return response
    except Exception as e:
        print(f'访问本地文件{filename}出错:{e}')
        # 记录错误，但返回 404
        # app.logger.error(f"Error serving file {filename}: {str(e)}")
        abort(404, description="File not found or unable to access")


