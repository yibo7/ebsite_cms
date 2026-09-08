import os
import uuid
import hashlib
from flask import jsonify, current_app, send_from_directory, request

from decorators import rate_limit_ip
from eb_modules.aitanqin import bp_atq_apis
from eb_utils import http_helper
from entity import api_msg
from bll.new_content import NewsContent


@bp_atq_apis.route('totab', methods=['POST', 'GET'])
@rate_limit_ip(10,1) # 一分钟只允许调用3次
def get_tab():
    """
    获取乐谱文件
    通过tid（NewsContent的_id）查询column_5字段中的乐谱文件路径，
    从本地upload目录下读取文件并返回。
    """
    tid = http_helper.get_prams('id')

    if not tid:
        return jsonify(api_msg.api_err("id不能为空"))
    print(f"乐谱ID：{tid}")
    # 获取文件内容
    try:
        # 通过tid查询NewsContent实例
        bll = NewsContent()
        model = bll.find_one_by_id(tid)

        if not model:
            return jsonify(api_msg.api_err("未找到对应的内容"))

        # 获取乐谱文件路径（column_5），如 /scores/gtp/xxx.gp
        score_path = model.column_5
        print(f'乐谱路径：{score_path}')
        if not score_path:
            return jsonify(api_msg.api_err("未设置乐谱文件路径"))

        # 解析路径：去除开头的 /，分离目录和文件名
        relative_path = score_path.lstrip('/')
        directory = os.path.dirname(relative_path)  # 如 scores/gtp
        filename = os.path.basename(relative_path)  # 如 xxx.gp

        # 文件实际存放在 uploads 目录下
        upload_folder = os.path.join(current_app.root_path, 'uploads', directory)

        # 检查文件是否存在
        if not os.path.exists(os.path.join(upload_folder, filename)):
            return jsonify(api_msg.api_err("乐谱文件不存在"))

        # 使用 send_from_directory 发送文件（与 uploaded_file 函数一致的方式）
        return send_from_directory(
            upload_folder,
            filename,
            mimetype='application/octet-stream',
            as_attachment=False,
            download_name=filename
        )

    except Exception as e:
        return jsonify(api_msg.api_err(f"获取文件失败: {str(e)}"))


@bp_atq_apis.route('upload_score', methods=['POST'])
@rate_limit_ip(5, 1)  # 每分钟最多5次上传
def upload_score():
    """
    上传乐谱文件
    允许格式：.gp, .musicxml
    上传目录：website/uploads/scores/new/
    返回相对路径供数据库存储
    """
    # 检查是否有文件
    if 'file' not in request.files:
        return jsonify(api_msg.api_err("没有上传文件"))

    file = request.files['file']
    if file.filename == '':
        return jsonify(api_msg.api_err("没有选择文件"))

    # 验证文件扩展名
    allowed_extensions = {'.gp', '.musicxml'}
    filename = file.filename
    ext = os.path.splitext(filename)[1].lower()

    if ext not in allowed_extensions:
        return jsonify(api_msg.api_err(f"不支持的文件格式「{ext}」，仅支持 .gp 和 .musicxml"))

    # 生成唯一文件名（保留原始扩展名）
    unique_name = f"{uuid.uuid4().hex}{ext}"

    # 上传目录
    upload_dir = os.path.join(current_app.root_path, 'uploads', 'scores', 'new')
    os.makedirs(upload_dir, exist_ok=True)

    # 保存文件
    file_path = os.path.join(upload_dir, unique_name)
    file.save(file_path)

    # 返回相对路径供数据库存储
    relative_path = f"/scores/new/{unique_name}"

    return jsonify(api_msg.api_succesful(relative_path, "上传成功"))


@bp_atq_apis.route('check_score_hash', methods=['GET'])
def check_score_hash():
    """
    检查乐谱文件哈希是否已存在（防重复上传）
    前端计算文件 SHA-256，服务端查询 column_14 是否已有相同值
    """
    file_hash = http_helper.get_prams('hash')
    if not file_hash:
        return jsonify(api_msg.api_err("hash 参数不能为空"))

    bll = NewsContent()
    existing = bll.find_one_by_where({"column_14": file_hash})

    if existing:
        return jsonify(api_msg.api_succesful({"exists": True}, "该乐谱已存在，请勿重复上传"))

    return jsonify(api_msg.api_succesful({"exists": False}, "可以上传"))