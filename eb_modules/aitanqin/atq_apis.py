import os
import uuid
import hashlib
import base64
import json
from flask import jsonify, current_app, send_from_directory, request

from decorators import rate_limit_ip
from eb_modules.aitanqin import bp_atq_apis
from eb_utils import http_helper
from entity import api_msg
from bll.new_content import NewsContent


def _read_score_file(score_id):
    """
    根据乐谱ID查询并读取乐谱文件内容。
    返回 (file_bytes, filename) 或抛出异常。
    """
    bll = NewsContent()
    model = bll.find_one_by_id(score_id)

    if not model:
        raise FileNotFoundError(f"未找到对应的内容: {score_id}")

    score_path = model.column_5
    if not score_path:
        raise FileNotFoundError(f"未设置乐谱文件路径: {score_id}")

    relative_path = score_path.lstrip('/')
    directory = os.path.dirname(relative_path)
    filename = os.path.basename(relative_path)
    upload_folder = os.path.join(current_app.root_path, 'uploads', directory)
    file_full_path = os.path.join(upload_folder, filename)

    if not os.path.exists(file_full_path):
        raise FileNotFoundError(f"乐谱文件不存在: {file_full_path}")

    with open(file_full_path, 'rb') as f:
        file_bytes = f.read()

    return file_bytes, filename


@bp_atq_apis.route('totab', methods=['POST', 'GET'])
@rate_limit_ip(10,1) # 一分钟只允许调用3次
def get_tab():
    """
    获取乐谱文件（原始二进制格式，向后兼容）
    通过tid（NewsContent的_id）查询column_5字段中的乐谱文件路径，
    从本地upload目录下读取文件并返回。
    """
    tid = http_helper.get_prams('id')

    if not tid:
        return jsonify(api_msg.api_err("id不能为空"))
    print(f"乐谱ID：{tid}")
    try:
        file_bytes, filename = _read_score_file(tid)
        return send_from_directory(
            os.path.join(current_app.root_path, 'uploads', os.path.dirname(filename.lstrip('/'))),
            os.path.basename(filename),
            mimetype='application/octet-stream',
            as_attachment=False,
            download_name=filename
        )
    except FileNotFoundError as e:
        return jsonify(api_msg.api_err(str(e)))
    except Exception as e:
        return jsonify(api_msg.api_err(f"获取文件失败: {str(e)}"))


@bp_atq_apis.route('totab/<score_id>.js', methods=['GET'])
def get_tab_js(score_id):
    """
    获取乐谱文件（JS格式，供CDN缓存）
    URL模式: /atq/api/totab/<score_id>.js

    返回一个自执行JS片段，将base64编码的乐谱数据注册到 window.__cachedScores 中。
    前端通过动态 <script> 标签加载此文件后，即可从 window.__cachedScores 中获取数据，
    无需再发起 fetch 请求，从而让 CDN 能够缓存乐谱文件。
    """
    if not score_id:
        return "console.error('get_tab_js: score_id 为空')", 400, {'Content-Type': 'application/javascript'}

    try:
        file_bytes, filename = _read_score_file(score_id)
        b64_data = base64.b64encode(file_bytes).decode('ascii')
        safe_filename = json.dumps(filename, ensure_ascii=False)

        js_code = (
            f"(function(){{"
            f"if(!window.__cachedScores){{window.__cachedScores={{}};}}"
            f"window.__cachedScores[{json.dumps(score_id)}]={{data:{json.dumps(b64_data)},name:{safe_filename}}};"
            f"}})();\n"
        )

        return js_code, 200, {
            'Content-Type': 'application/javascript',
            'Cache-Control': 'public, max-age=86400',
        }
    except FileNotFoundError as e:
        return f"console.error('get_tab_js: {json.dumps(str(e))}')", 404, {'Content-Type': 'application/javascript'}
    except Exception as e:
        return f"console.error('get_tab_js error: {json.dumps(str(e))}')", 500, {'Content-Type': 'application/javascript'}


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