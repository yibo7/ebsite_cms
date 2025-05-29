from datetime import datetime
from flask import Blueprint, jsonify, g, request

from eb_cache import login_utils
from eb_utils.configs import WebPaths
from entity.api_msg import api_err

# 请求这个API 无需验证登录
api_blue = Blueprint('apis', __name__, url_prefix=WebPaths.API_PATH)

# 请求这个API 需要登录
api_blue_user = Blueprint('apis_user', __name__, url_prefix=WebPaths.API_PATH)

@api_blue_user.before_request
def before_req():
    """
    请求需要验证登录的API
    :return:
    """ 
    g.u = None
    user_token = login_utils.get_token()
    if user_token:
        g.u = user_token
        g.uid = user_token.id
    else:
        return jsonify(api_err("你没有足够的权限访问此API"))


from . import apis_cms
from . import apis_file
from . import apis_user




@api_blue.route('server_time', methods=['GET'])
def get_timestamp():
    current_time = datetime.now()
    timestamp = int(current_time.timestamp())
    return jsonify({'timestamp': timestamp})

@api_blue.route('user_ip', methods=['GET'])
def get_user_ip():
    host = request.headers.get('X-Forwarded-Host', request.host)
    return jsonify({'host': host})