import hashlib
import time
import uuid
from functools import wraps

from flask import request, g, jsonify, redirect

import eb_cache
from bll.site_log import SiteLog
from eb_cache import app_token, login_utils
from eb_utils import http_helper
from eb_utils.image_code import ImageCode
from eb_utils.mobile_code import MobileCode
from entity.api_msg import api_err_permission
from entity.site_log_model import SiteLogModel

"""
装饰器
"""


# APP_KEY = CF_APP.get('MongoDBUrl')

def check_session(func):
    """
    装饰器-设置记录用户的session_id到cookie
    一般在首页请求时设置，或在相应需要跟踪用户状态的页面
    只要设置一次即可，每个用户的session只有一个
    """

    def wrapper(response):
        session_id = request.cookies.get('session_id')
        if not session_id:
            session_id = str(uuid.uuid4())  # 生成一个新的 Session ID
            response.set_cookie('session_id', session_id)  # 将 Session ID 设置到响应的 Cookie 中
            # request.session_id = session_id  # 将 Session ID 存储到请求对象中，以便后续使用

        # else:
        #     request.session_id = session_id  # 将已存在的 Session ID 存储到请求对象中
        return func(response)

    return wrapper


def admin_action_log(title: str):
    """
    后台操作写日志的装饰器
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            content = f"执行函数：{func.__name__}，参数：{args}{kwargs}"
            # SiteLog().add_log(title,content)
            model = SiteLogModel()
            model.title = title
            model.description = content
            model.url = http_helper.get_url_full()
            model.ip_addr = http_helper.get_ip()

            user = g.u
            if user:
                model.user_name = user.name
                model.ni_name = user.ni_name
                model.user_id = user.id
            SiteLog().add(model)
            return func(*args, **kwargs)

        return wrapper

    return decorator


def rate_limit_ip(limit, per_minutes):
    """
    限制某个IP下的请求频率
    :param limit: 请求次数
    :param per_minutes: 分钟数
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            ip = request.remote_addr
            key = f'rate_limit_{ip}_{f.__name__}'

            # 获取当前缓存数据
            data = eb_cache.cache.get(key)
            now = time.time()

            if data is None:
                # 如果缓存不存在,创建新的
                data = {'count': 1, 'start_time': now}
                eb_cache.cache.set(key, data, timeout=per_minutes * 60)
            else:
                # 如果缓存存在,检查是否过期
                if now - data['start_time'] > per_minutes * 60:
                    # 如果过期,重置计数器
                    data = {'count': 1, 'start_time': now}
                    eb_cache.cache.set(key, data, timeout=per_minutes * 60)
                else:
                    # 如果未过期,增加计数器
                    data['count'] += 1
                    if data['count'] > limit:
                        return jsonify(api_err_permission('Rate limit exceeded'))
                    eb_cache.cache.set(key, data, timeout=per_minutes * 60)

            return f(*args, **kwargs)

        return decorated_function

    return decorator


def check_token(is_use_token=True):  # 添加这层，在引用时需要加上括号，比如 @check_token()
    """
    验证token，需要验证APP-API登录的API可以添加此装饰器
    :param is_use_token: 是否需要传递token给方法使用
    """

    def decorator(f):  # 如果不传参数，可只保留这层，调用的时候可不用加括号，比如 @check_token
        @wraps(f)
        def decorated_function(*args, **kwargs):

            token_key = request.headers.get('x-api-key')

            if not token_key:
                return  jsonify(api_err_permission("x-api-key is missing"))

            if token_key == 'abeb3a9c85a84bec9db217a20557171c':  # 开发测试用
                token_data = app_token.get_test_token()
            else:
                token_data = app_token.get_token(token_key)
                if not token_data:
                    return jsonify(api_err_permission("Token has expired or is invalid"))

            if is_use_token:
                kwargs['token'] = token_data
            return f(*args, **kwargs)
            # 如果token有效，将token_data作为关键字参数传递给被装饰的函数
            # return f(*args, token=token_data, **kwargs)

        return decorated_function

    return decorator


def check_sign(check_replay=False):
    """
    验证请求参数的签名信息 参数中必须有sign参数
    :param check_replay: 是否验证地址是否被重放，参数中必须有nonce与time参数
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 获取所有参数

            params = http_helper.get_prams_dict()  # request.args.to_dict()

            if check_replay:  # 是否防止地址重放
                replay_time_out = 60 * 10  # 防止重放的时间 10 分钟
                # 验证 nonce 和 time 参数
                if 'nonce' not in params or 'time' not in params:
                    return jsonify(api_err_permission("Missing nonce or time parameter"))

                nonce = params['nonce']
                timestamp = params['time']

                # 检查 nonce 是否已经使用过，使用过就说明这次请求是攻击者重放过来的，不放行
                if eb_cache.cache.get(nonce):
                    return jsonify(api_err_permission("禁止重放"))

                # 验证时间戳
                current_time = int(time.time())
                if abs(current_time - int(timestamp)) > replay_time_out:
                    return jsonify(api_err_permission("访问超时"))

                # 将 nonce 存入缓存，过期时间为 5 分钟
                eb_cache.cache.set(nonce, 'used', timeout=replay_time_out)

            # 检查是否存在 sign 参数
            if 'sign' not in params:
                return jsonify(api_err_permission("Missing signature parameter"))

            # 获取并移除 sign 参数
            provided_sign = params.pop('sign')
            # 对剩余参数进行排序
            sorted_params = sorted(params.items(), key=lambda x: x[0])

            # 构建签名字符串
            sign_string = '&'.join([f"{k}={v}" for k, v in sorted_params])
            APP_KEY = eb_cache.base_setting_value('APP_KEY')
            sign_string += f"&appkey={APP_KEY}"

            # 计算 MD5 签名
            calculated_sign = hashlib.md5(sign_string.encode()).hexdigest()
            print(sign_string)
            print(calculated_sign)
            # 比较计算得到的签名和提供的签名
            if calculated_sign != provided_sign:
                return jsonify(api_err_permission("Invalid signature"))

            # 如果签名有效，继续执行被装饰的函数
            return f(*args, **kwargs)

        return decorated_function

    return decorator


def check_img_code(max_requests, time_limit=60):
    """
    开启图片验证码验证-可以设置指定时间内超过最大次数时才启用验证码
    应用此装饰器后，要求请求 url 参数必须有code,code_key两个参数
    缓存键的设计：
    1、使用了两个不同的键（time_limit_key 和 count_limit_key）来分别跟踪时间限制和请求计数。这种分离可以提供更好的灵活性。
    2、错误处理：
        当验证码验证失败时，延长了时间限制（原过期时间的3倍）。这是一个有趣的策略，可以有效防止暴力破解。
    3、缓存清理：
        在验证码正确时，清除了限制缓存数据。这是一个好做法，可以重置限制。
    4、初始化：
        当第一次请求时，你正确地初始化了计数器和时间限制。
    :param max_requests: 最大的请求数量,time_limit分钟内最大的请求数量超过此值，将启用图片验证
    :param time_limit: 时间限制，单位分钟，默认值60分钟也就是1小时
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 获取客户端IP
            client_ip = http_helper.get_ip()

            # 将time_window转换为秒
            time_window = time_limit * 60

            # 用IP地址作为缓存键，跟踪请求次数和时间
            time_limit_key = f'imgcode_time_limit_key{client_ip}_{f.__name__}'
            cache_time = eb_cache.get(time_limit_key)

            count_limit_key = f'imgcode_count_limit_key{client_ip}_{f.__name__}'
            if cache_time:
                cache_count = eb_cache.get(count_limit_key) or 0
                # 更新请求次数
                eb_cache.cache.set(count_limit_key, cache_count + 1, timeout=time_window)

                if cache_count == 0 or cache_count >= max_requests:  # cache_count == 0 这种情况理论上不会发生，但为了保留加上这个
                    code = http_helper.get_prams('code')
                    code_key = http_helper.get_prams('code_key')
                    # stored_code = eb_cache.get(code_key)
                    err_info = ImageCode().check_app_code(code_key,code)
                    if err_info:
                        # 如何验证码错误，在原过期时间基础上追加3倍限制时间
                        eb_cache.cache.set(time_limit_key, 'time', timeout=time_window * 3)  # 递进式延迟
                        return jsonify(api_err_permission(err_info))
                    else:  # 如果验证码正确，清空限制缓存数据
                        eb_cache.delete(time_limit_key)
                        eb_cache.delete(count_limit_key)

            else:
                eb_cache.cache.set(time_limit_key, 'time', timeout=time_window)
                eb_cache.cache.set(count_limit_key, 1, timeout=time_window)

            # 请求未超过限制或验证码验证成功，继续处理请求
            return f(*args, **kwargs)

        return decorated_function

    return decorator


def check_img_code_v2(f):
    """
    开户图片验证码-强制
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        code = http_helper.get_prams('code')
        code_key = http_helper.get_prams('code_key')
        # stored_code = eb_cache.get(code_key)
        err_info = ImageCode().check_app_code(code_key,code)
        if err_info:
            return jsonify(api_err_permission(err_info))

        return f(*args, **kwargs)

    return decorated_function


def check_mobile_email_code(f):
    """
    验证手机或EMAIL的安全码
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        code = http_helper.get_prams('code')
        account = http_helper.get_prams('account')
        err_info = MobileCode().check_code(account,code)
        if err_info:
            return jsonify(api_err_permission(err_info))
        kwargs['account'] = account
        return f(*args, **kwargs)

    return decorated_function

def check_admin_login(f):
    """
    验证后台管理是否登录
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        admin_token = login_utils.get_token_admin()

        if not admin_token:
            return redirect("/login_ad")

        kwargs['admin_token'] = admin_token
        return f(*args, **kwargs)
        # 如果token有效，将token_data作为关键字参数传递给被装饰的函数
        # return f(*args, token=token_data, **kwargs)

    return decorated_function

def check_user_login(f):
    """
    验证后台管理是否登录
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_token = login_utils.get_token()
        if not user_token:
            return redirect("/login")

        kwargs['user_token'] = user_token
        return f(*args, **kwargs)
        # 如果token有效，将token_data作为关键字参数传递给被装饰的函数
        # return f(*args, token=token_data, **kwargs)

    return decorated_function