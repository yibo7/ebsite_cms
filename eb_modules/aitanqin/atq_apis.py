import os
from flask import jsonify, current_app, send_from_directory

from decorators import rate_limit_ip
from eb_modules.aitanqin import bp_aitanqin
from eb_utils import http_helper
from entity import api_msg
from bll.new_content import NewsContent


@bp_aitanqin.route('totab', methods=['POST', 'GET'])
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
            download_name='tab.gp'
        )

    except Exception as e:
        return jsonify(api_msg.api_err(f"获取文件失败: {str(e)}"))