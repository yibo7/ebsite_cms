import requests
from flask import Response,request

from flask import jsonify

from eb_modules.aitanqin import bp_aitanqin
from eb_utils import http_helper, flask_utils
from entity import api_msg


@bp_aitanqin.route('totab', methods=['POST', 'GET'])
def get_tab():
    """
    获取乐谱文件
    """
    tid = http_helper.get_prams('id')

    if not tid:
        return jsonify(api_msg.api_err("id不能为空"))

    config = getattr(bp_aitanqin, 'config', None)
    tab_api_key = config.get("tab_api_key", "atq@cqs2022") if config is not None else "atq@cqs2022"

    # 获取文件内容
    try:
        base_url = f"{request.scheme}://{request.host}" #'http://127.0.0.1:8066' #
        file_path = "/api/uploads/20260902/6a97e71f3ad96e1ce91dfcd1.gp"
        full_url =  f"{base_url}{file_path}"  # 'https://www.alphatab.net/files/canon.gp'
        print(full_url)
        response = requests.get(full_url)

        # 返回文件内容，保持正确的MIME类型
        return Response(
            response.content,
            status=200,
            headers={
                'Content-Type': response.headers.get('Content-Type', 'application/octet-stream'),
                'Content-Disposition': f'attachment; filename="tab.gp"',
                # 添加CORS头
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type'
            }
        )
    except Exception as e:
        return jsonify(api_msg.api_err(f"获取文件失败: {str(e)}"))