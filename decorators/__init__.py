"""
装饰器模块

提供 Flask 路由装饰器，涵盖会话管理、登录认证、API鉴权、
签名验证、频率限制、人机验证、操作审计、权限校验、
防重复提交、参数校验、响应缓存及数据库事务等横切关注点。
"""

import hashlib
import re
import time
import uuid
import logging
from functools import wraps
from typing import Any, Callable, Optional, Union

from flask import request, g, jsonify, redirect, current_app, url_for
from pymongo import MongoClient

import eb_cache
from bll.site_log import SiteLog
from bll.admin_role import AdminRole
from eb_cache import app_token, login_utils
from eb_utils import http_helper
from eb_utils.image_code import ImageCode
from eb_utils.mobile_code import MobileCode
from entity import api_msg
from entity.api_msg import api_err_permission
from entity.site_log_model import SiteLogModel

# ---------------------------------------------------------------------------
# 模块级日志
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# ===================================================================
# 1. 会话追踪
# ===================================================================

def check_session(func: Callable) -> Callable:
    """
    为匿名用户设置 session_id Cookie（仅当 Cookie 中不存在时）。

    使用方式（与标准 Flask 视图兼容）::

        @app.route('/')
        @check_session
        def index():
            return render_template('index.html')

    注意：本装饰器**必须**放在最贴近视图函数的位置（即最内层 @），
    确保 func 的返回值是一个 Response 对象。
    """
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        resp = func(*args, **kwargs)
        if not request.cookies.get('session_id'):
            resp.set_cookie('session_id', str(uuid.uuid4()))
        return resp

    return wrapper


# ===================================================================
# 2. 后台操作审计日志
# ===================================================================

def admin_action_log(title: str) -> Callable:
    """
    后台操作写日志的装饰器。

    :param title: 日志标题（如"删除文章"）
    :return: 装饰器
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # 安全获取当前用户（g.u 可能不存在）
            user = getattr(g, 'u', None)
            # 构建描述内容
            arg_repr = ', '.join(
                [repr(a) for a in args] +
                [f'{k}={v!r}' for k, v in kwargs.items()]
            )
            content = f"执行函数：{func.__name__}，参数：({arg_repr})"

            model = SiteLogModel()
            model.title = title
            model.description = content
            model.url = http_helper.get_url_full()
            model.ip_addr = http_helper.get_ip()
            if user:
                model.user_name = getattr(user, 'name', '')
                model.ni_name = getattr(user, 'ni_name', '')
                model.user_id = getattr(user, 'id', '')
            try:
                SiteLog().add(model)
            except Exception:
                logger.exception("写入操作日志失败")

            return func(*args, **kwargs)

        return wrapper

    return decorator


# ===================================================================
# 3. IP 频率限制（基于缓存原子自增）
# ===================================================================

def rate_limit_ip(limit: int, per_minutes: int) -> Callable:
    """
    限制某个 IP 在指定时间窗口内的请求频率。

    使用缓存提供的原子自增操作（incr）避免并发竞态条件。

    :param limit: 允许的最大请求次数
    :param per_minutes: 时间窗口（分钟）
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args: Any, **kwargs: Any) -> Any:
            ip = http_helper.get_ip()
            key = f'rate_limit_{ip}_{f.__name__}'
            timeout_seconds = per_minutes * 60

            # 原子自增：第一次访问时初始值为 1
            count = eb_cache.next_id(key, timeout=timeout_seconds)

            if count > limit:
                logger.warning("IP 频率超限 | ip=%s | func=%s | count=%d/%d",
                               ip, f.__name__, count, limit)
                return jsonify(api_err_permission('Rate limit exceeded'))

            return f(*args, **kwargs)

        return decorated_function

    return decorator


# ===================================================================
# 4. API Token 验证
# ===================================================================

def check_token(is_use_token: bool = True) -> Callable:
    """
    验证 API Token（请求头 ``x-api-key``）。

    :param is_use_token: 是否将 Token 数据作为 ``token`` 关键字参数
                         注入被装饰的视图函数
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args: Any, **kwargs: Any) -> Any:
            token_key = request.headers.get('x-api-key')

            if not token_key:
                return jsonify(api_err_permission("x-api-key is missing"))

            # 开发/测试模式：若配置了 DEBUG_TOKEN 则直接通过
            if current_app.debug:
                debug_token = current_app.config.get('DEBUG_TOKEN', '')
                if debug_token and token_key == debug_token:
                    token_data = app_token.get_test_token()
                else:
                    token_data = app_token.get_token(token_key)
            else:
                token_data = app_token.get_token(token_key)

            if not token_data:
                logger.warning("Token 验证失败 | x-api-key=%s", token_key[:16] + '...')
                return jsonify(api_err_permission("Token has expired or is invalid"))

            if is_use_token:
                kwargs['token'] = token_data

            return f(*args, **kwargs)

        return decorated_function

    return decorator


# ===================================================================
# 5. 请求签名验证（可选防重放）
# ===================================================================

def check_sign(check_replay: bool = False) -> Callable:
    """
    验证请求参数的 MD5 签名。

    签名规则：所有参数（不含 ``sign``）按 key 排序后拼接为
    ``k1=v1&k2=v2...&appkey=APP_KEY``，整体计算 MD5。

    :param check_replay: 是否启用防重放攻击。
                         启用时请求必须携带 ``nonce`` 和 ``time`` 参数，
                         nonce 使用后 10 分钟内不可重复使用。
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args: Any, **kwargs: Any) -> Any:
            # 收集所有参数（查询参数 + 表单参数）
            params = http_helper.get_prams_dict()

            # ---------- 防重放 ----------
            if check_replay:
                replay_timeout = 60 * 10  # 10 分钟
                if 'nonce' not in params or 'time' not in params:
                    return jsonify(api_err_permission("Missing nonce or time parameter"))

                nonce = params['nonce']
                timestamp = params['time']

                # nonce 已使用过 → 重放攻击
                if eb_cache.cache.get(nonce):
                    return jsonify(api_err_permission("禁止重放"))

                # 时间戳偏差超出窗口
                current_time = int(time.time())
                if abs(current_time - int(timestamp)) > replay_timeout:
                    return jsonify(api_err_permission("访问超时"))

                eb_cache.cache.set(nonce, 'used', timeout=replay_timeout)

            # ---------- 签名验证 ----------
            if 'sign' not in params:
                return jsonify(api_err_permission("Missing signature parameter"))

            provided_sign = params.pop('sign')

            # 对剩余参数按 key 字典序排序
            sorted_params = sorted(params.items(), key=lambda x: x[0])
            sign_string = '&'.join([f"{k}={v}" for k, v in sorted_params])

            app_key = eb_cache.base_setting_value('APP_KEY')
            sign_string += f"&appkey={app_key}"

            calculated_sign = hashlib.md5(sign_string.encode()).hexdigest()

            logger.debug("check_sign | 待签名字符串=%s | 计算签名=%s | 提供签名=%s",
                         sign_string, calculated_sign, provided_sign)

            if calculated_sign != provided_sign:
                return jsonify(api_err_permission("Invalid signature"))

            return f(*args, **kwargs)

        return decorated_function

    return decorator


# ===================================================================
# 6. 网站 Key MD5 验证
# ===================================================================

def verify_site_key_md5(f: Callable) -> Callable:
    """
    验证 API 路由参数中 ``site_key_md5`` 是否与服务器配置的 SiteKey 一致。

    用于多站点场景下确认请求来源属于哪个合法站点。
    要求路由中包含 ``site_key_md5`` 参数。
    """
    @wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        site_key_md5 = kwargs.get('site_key_md5')

        if not site_key_md5:
            return jsonify(api_err_permission("site key md5 value is required"))

        site_key = current_app.config.get('SiteKey')
        if not site_key:
            return jsonify(api_err_permission("SiteKey not configured on server"))

        calculated_md5 = hashlib.md5(site_key.encode('utf-8')).hexdigest()

        if site_key_md5.lower() != calculated_md5.lower():
            logger.warning("SiteKey MD5 不匹配 | 传入=%s | 服务端=%s",
                           site_key_md5, calculated_md5)
            return jsonify(api_err_permission("Invalid site key md5"))

        return f(*args, **kwargs)

    return decorated_function


# ===================================================================
# 6b. 网站 Key HMAC 签名验证（请求头 + 时间戳防重放）
# ===================================================================

def verify_site_key_hmac(f: Callable) -> Callable:
    """
    验证请求头的 HMAC-SHA256 签名。

    客户端需在请求头中提供：
      - ``X-Timestamp``: 当前 Unix 时间戳（秒），服务端允许 ±300 秒偏差
      - ``X-Sign``: HMAC-SHA256 十六进制摘要

    签名消息体构成::

        timestamp + ":" + request_body（原始请求体字符串）

    服务端使用配置的 ``SiteKey`` 重新计算 HMAC 并恒定时间比对。

    使用示例（Python 客户端）::

        import hmac, hashlib, time
        import requests

        site_key = "你的SiteKey"
        timestamp = str(int(time.time()))
        body = "title=Hello&info=World"
        message = f"{timestamp}:{body}"
        sign = hmac.new(site_key.encode(), message.encode(), hashlib.sha256).hexdigest()

        r = requests.post(
            "http://localhost/auto_post_content/1/5",
            headers={"X-Timestamp": timestamp, "X-Sign": sign},
            data=body,
        )
    """
    import hmac as hmac_module

    _TIME_WINDOW = 300  # ±5 分钟

    @wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        site_key = current_app.config.get('SiteKey')
        if not site_key:
            return jsonify(api_err_permission("SiteKey not configured on server"))

        timestamp_str = request.headers.get('X-Timestamp')
        signature = request.headers.get('X-Sign')

        if not timestamp_str or not signature:
            return jsonify(api_err_permission("Missing X-Timestamp or X-Sign header"))

        # 验证时间戳格式
        try:
            timestamp = int(timestamp_str)
        except ValueError:
            return jsonify(api_err_permission("X-Timestamp must be a Unix timestamp"))

        # 检查时间窗口（防重放攻击）
        now = time.time()
        if abs(now - timestamp) > _TIME_WINDOW:
            logger.warning(
                "HMAC 时间戳超限 | timestamp=%s | now=%s | ip=%s",
                timestamp_str, int(now), http_helper.get_ip(),
            )
            return jsonify(api_err_permission("X-Timestamp is out of allowed window (±5min)"))

        # 构建签名消息：timestamp + ":" + 原始请求体
        body = request.get_data(as_text=True)
        message = f"{timestamp_str}:{body}"

        # 计算期望签名
        expected = hmac_module.new(
            site_key.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256,
        ).hexdigest()

        # 恒定时间比较，防止时序攻击
        if not hmac_module.compare_digest(expected, signature):
            logger.warning(
                "HMAC 签名不匹配 | ip=%s | path=%s",
                http_helper.get_ip(), request.path,
            )
            return jsonify(api_err_permission("Invalid HMAC signature"))

        return f(*args, **kwargs)

    return decorated_function


# ===================================================================
# 6c. 危险输入校验（模板语法 + 脚本注入）
# ===================================================================

_JINJA2_RE = re.compile(r'\{\{.*?\}\}|\{%.*?\}|{#.*?#}', re.DOTALL)
_SCRIPT_RE = re.compile(r'<script[\s>]', re.IGNORECASE)
_EVENT_RE = re.compile(r'\bon\w+\s*=', re.IGNORECASE)
_DANGEROUS_SCHEME_RE = re.compile(r'^\s*(?:javascript|data|vbscript|file):', re.IGNORECASE)


def reject_dangerous_input(f: Callable) -> Callable:
    """
    校验 POST 参数中是否包含危险内容，若发现则直接返回错误。

    检查项：
      1. Jinja2 模板语法  ``{{ }}`` / ``{% %}`` / ``{# #}``
      2. ``<script>`` 标签
      3. ``on*`` 事件处理属性（onclick、onerror 等）
      4. ``javascript:`` / ``data:`` 等危险 URI 协议

    用法::

        @api_blue.route('some_route', methods=['POST'])
        @reject_dangerous_input
        def some_handler():
            ...
    """
    @wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        # 只校验 POST 请求的参数
        if request.method not in ('POST', 'PUT', 'PATCH'):
            return f(*args, **kwargs)

        # 从 form 和 json body 中提取字符串值
        values_to_check: list[str] = []

        # form 参数
        for v in request.form.values():
            if isinstance(v, str):
                values_to_check.append(v)

        # JSON body
        if request.is_json:
            _collect_json_strings(request.get_json(silent=True) or {}, values_to_check)

        for value in values_to_check:
            if _JINJA2_RE.search(value):
                logger.warning("输入校验失败 | 包含模板语法 | ip=%s", http_helper.get_ip())
                return jsonify(api_err_permission("输入包含禁止的模板语法"))

            if _SCRIPT_RE.search(value):
                logger.warning("输入校验失败 | 包含 script 标签 | ip=%s", http_helper.get_ip())
                return jsonify(api_err_permission("输入包含禁止的脚本标签"))

            if _EVENT_RE.search(value):
                logger.warning("输入校验失败 | 包含事件处理器 | ip=%s", http_helper.get_ip())
                return jsonify(api_err_permission("输入包含禁止的事件属性"))

            if _DANGEROUS_SCHEME_RE.search(value):
                logger.warning("输入校验失败 | 包含危险 URI 协议 | ip=%s", http_helper.get_ip())
                return jsonify(api_err_permission("输入包含禁止的 URI 协议"))

        return f(*args, **kwargs)

    return decorated_function


def _collect_json_strings(data, result: list[str]):
    """递归收集 JSON 中的字符串值"""
    if isinstance(data, str):
        result.append(data)
    elif isinstance(data, dict):
        for v in data.values():
            _collect_json_strings(v, result)
    elif isinstance(data, (list, tuple)):
        for item in data:
            _collect_json_strings(item, result)


# ===================================================================
# 7. 智能图片验证码（阈值触发 + 递进式惩罚）
# ===================================================================

def check_img_code(max_requests: int, time_limit: int = 60) -> Callable:
    """
    按 IP 跟踪请求频率，超出阈值后强制要求图片验证码。

    工作机制：
    1. 在 ``time_limit`` 分钟内请求数不超过 ``max_requests`` 时，不要求验证码；
    2. 超过阈值后，后续请求必须携带 ``code`` 和 ``code_key`` 参数；
    3. 验证码错误 → 限制时间递进式延长（原过期时间的 3 倍）；
    4. 验证码正确 → 清空限制缓存，恢复正常访问。

    :param max_requests: 触发验证码的请求次数阈值
    :param time_limit: 时间窗口（分钟，默认 60 分钟）
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args: Any, **kwargs: Any) -> Any:
            client_ip = http_helper.get_ip()
            time_window = time_limit * 60  # 转换为秒

            time_limit_key = f'imgcode_time_limit_{client_ip}_{f.__name__}'
            count_limit_key = f'imgcode_count_limit_{client_ip}_{f.__name__}'

            cache_time = eb_cache.get(time_limit_key)

            if cache_time:
                # 已处于限制期，原子递增计数器
                cache_count = eb_cache.next_id(count_limit_key, timeout=time_window)

                if cache_count >= max_requests:
                    code = http_helper.get_prams('code')
                    code_key = http_helper.get_prams('code_key')
                    err_info = ImageCode().check_app_code(code_key, code)
                    if err_info:
                        # 验证码错误 → 递进式延迟（当前过期时间 × 3）
                        eb_cache.cache.set(
                            time_limit_key, 'time',
                            timeout=time_window * 3
                        )
                        return jsonify(api_err_permission(err_info))
                    else:
                        # 验证码正确 → 清空限制缓存
                        eb_cache.delete(time_limit_key)
                        eb_cache.delete(count_limit_key)
            else:
                # 初始化为限制期，计数从 1 开始
                eb_cache.cache.set(time_limit_key, 'time', timeout=time_window)
                eb_cache.next_id(count_limit_key, timeout=time_window)

            return f(*args, **kwargs)

        return decorated_function

    return decorator


# ===================================================================
# 8. 强制图片验证码
# ===================================================================

def require_img_code(f: Callable) -> Callable:
    """
    强制要求图片验证码（无阈值豁免）。

    请求必须携带 ``code`` 和 ``code_key`` 参数。
    适用于开户、支付等高风险操作。
    """
    @wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        code = http_helper.get_prams('code')
        code_key = http_helper.get_prams('code_key')
        err_info = ImageCode().check_app_code(code_key, code)
        if err_info:
            return jsonify(api_err_permission(err_info))
        return f(*args, **kwargs)

    return decorated_function


# 保留旧名称以保持向后兼容
check_img_code_v2 = require_img_code


# ===================================================================
# 9. 手机 / 邮箱验证码验证
# ===================================================================

def check_mobile_email_code(f: Callable) -> Callable:
    """
    验证手机或邮箱安全码。

    验证通过后，已验证的账号会通过 ``g.account`` 传递给下游。
    """
    @wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        code = http_helper.get_prams('code')
        account = http_helper.get_prams('account')
        err_info = MobileCode().check_code(account, code)
        if err_info:
            return jsonify(api_err_permission(err_info))
        # 通过 g 对象传递，避免污染 kwargs
        g.account = account
        return f(*args, **kwargs)

    return decorated_function


# ===================================================================
# 10. 登录状态验证
# ===================================================================

def _should_redirect_to_json() -> bool:
    """
    判断当前请求是否期望 JSON 响应（而非页面重定向）。

    优先检测 ``Accept`` 头，其次检测 ``X-Requested-With``。
    """
    accept = request.headers.get('Accept', '')
    if 'application/json' in accept:
        return True
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return True
    return False


def check_admin_login(f: Callable) -> Callable:
    """
    验证后台管理员是否已登录。

    - 未登录且是 API 请求 → 返回 401 JSON
    - 未登录且是页面请求 → 重定向到管理后台登录页
    """
    @wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        admin_token = login_utils.get_token_admin()

        if not admin_token:
            if _should_redirect_to_json():
                return jsonify(api_err_permission("请先登录"))
            return redirect(url_for('login_ad'))

        kwargs['admin_token'] = admin_token
        return f(*args, **kwargs)

    return decorated_function


def check_user_login(f: Callable) -> Callable:
    """
    验证前端用户是否已登录。

    - 未登录且是 API 请求 → 返回 401 JSON
    - 未登录且是页面请求 → 重定向到用户登录页
    """
    @wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        user_token = login_utils.get_token()

        if not user_token:
            if _should_redirect_to_json():
                return jsonify(api_err_permission("请先登录"))
            return redirect(url_for('pages_blue.login'))

        kwargs['user_token'] = user_token
        return f(*args, **kwargs)

    return decorated_function


# ===================================================================
# 11. 权限检查装饰器               ★ 新增
# ===================================================================

def require_permission(pos_id: str) -> Callable:
    """
    检查当前管理员是否拥有指定的后台权限标识。

    必须与 ``@check_admin_login`` 配合使用（依赖于其注入的
    ``admin_token`` 关键字参数）。

    :param pos_id: 权限标识，如 ``"article:delete"``、``"user:edit"``
    :raises RuntimeError: 当 ``admin_token`` 不存在（未先使用
                          ``@check_admin_login``）时抛出

    用法示例::

        @admin_router.route('/article/delete/<id>')
        @check_admin_login
        @require_permission('article:delete')
        def article_delete(id):
            ...
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            admin_token = kwargs.get('admin_token')
            if not admin_token:
                raise RuntimeError(
                    "require_permission 需要 check_admin_login 配合使用，"
                    "请确保 @check_admin_login 在 @require_permission 外侧"
                )

            role_id = admin_token.group_id
            role = AdminRole().find_one_by_id(role_id)
            if not role:
                logger.warning("角色不存在 | role_id=%s", role_id)
                return jsonify(api_err_permission("角色不存在"))

            user_pos_list = role.pos_id or []
            if pos_id not in user_pos_list:
                logger.warning(
                    "权限不足 | user=%s | need=%s | has=%s",
                    admin_token.name, pos_id, user_pos_list
                )
                return jsonify(api_err_permission(f"权限不足，需要「{pos_id}」"))

            return f(*args, **kwargs)

        return wrapper

    return decorator


# ===================================================================
# 12. 防重复提交装饰器             ★ 新增
# ===================================================================

def no_repeat_submit(key_prefix: str = '', lock_seconds: int = 3) -> Callable:
    """
    防止用户在短时间内重复提交同一个请求。

    基于 ``用户标识 + 函数名 + 可选前缀`` 生成缓存锁。
    在 ``lock_seconds`` 秒内不允许相同请求再次执行。

    :param key_prefix: 可选的前缀，用于区分不同业务场景
                       （如 ``"article_save"``、``"user_register"``）
    :param lock_seconds: 锁定时间（秒），默认 3 秒。
                         结束后自动释放，正常完成也会立即释放。

    用法示例::

        @admin_router.route('/article/save', methods=['POST'])
        @check_admin_login
        @no_repeat_submit('article_save')
        def article_save():
            ...
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # 确定用户标识：优先用已登录用户的 ID，否则用 IP
            user = getattr(g, 'u', None)
            if user:
                uid = getattr(user, 'id', None) or getattr(user, '_id', None)
            else:
                uid = None
            identity = uid or request.remote_addr or 'unknown'

            lock_key = f'no_repeat_{key_prefix}_{identity}_{f.__name__}'

            if eb_cache.cache.get(lock_key):
                logger.warning("防重复提交触发 | key=%s | identity=%s", lock_key, identity)
                return jsonify(api_err_permission("操作过于频繁，请稍后再试"))

            eb_cache.cache.set(lock_key, '1', timeout=lock_seconds)

            try:
                return f(*args, **kwargs)
            finally:
                # 正常完成后立即释放锁，允许用户继续操作
                eb_cache.delete(lock_key)

        return wrapper

    return decorator


# ===================================================================
# 13. 数据库事务装饰器             ★ 新增
# ===================================================================

def transactional(f: Callable = None, *, max_retries: int = 3) -> Callable:
    """
    将被装饰的视图函数包裹在 MongoDB 事务中执行。

    使用 ``current_app.db_client.start_session()`` 开启会话，
    在视图函数的 ``kwargs`` 中注入 ``session`` 参数供 BLL 层使用
    （配合 ``BllBase.add_trans`` / ``update_trans`` 等方法）。

    若 MongoDB 不支持事务（如单节点部署），会回退到非事务模式
    并输出警告日志。

    :param max_retries: MongoDB 瞬态错误（如写入冲突）时的最大重试次数
    :param f: 被装饰的函数（使用无参形式时自动传入）

    用法示例::

        @admin_router.route('/article/save', methods=['POST'])
        @check_admin_login
        @transactional           # ← 无参用法
        def article_save():
            kwargs['session']   # ← 可在 BLL 层使用
            ...

    或带参数::

        @transactional(max_retries=5)
        def some_view():
            ...
    """
    # 支持 @transactional（无参）和 @transactional(max_retries=N) 两种写法
    if f is None:
        return lambda func: _transactional_decorator(func, max_retries)
    return _transactional_decorator(f, max_retries)


def _transactional_decorator(f: Callable, max_retries: int) -> Callable:
    @wraps(f)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        client: MongoClient = current_app.db_client
        session = None
        last_error = None

        for attempt in range(max_retries):
            session = None
            try:
                session = client.start_session()
                session.start_transaction()
                kwargs['session'] = session
                result = f(*args, **kwargs)
                session.commit_transaction()
                return result
            except Exception as e:
                # 判断是否为可重试的瞬态错误
                error_msg = str(e)
                is_retryable = any(
                    kw in error_msg
                    for kw in (
                        'WriteConflict', 'TransientTransactionError',
                        'UnknownTransactionCommitResult',
                    )
                )
                if session and session.in_transaction:
                    try:
                        session.abort_transaction()
                    except Exception:
                        pass

                if is_retryable and attempt < max_retries - 1:
                    logger.warning(
                        "事务重试 | attempt=%d/%d | error=%s",
                        attempt + 1, max_retries, error_msg
                    )
                    continue

                last_error = e
                break
            finally:
                if session:
                    try:
                        session.end_session()
                    except Exception:
                        pass

        # 如果走到这里说明事务失败
        logger.error(
            "事务执行失败 | func=%s | retries=%d | error=%s",
            f.__name__, max_retries, last_error
        )

        # 检查是否是事务不支持（单节点 MongoDB）
        if last_error and 'Transaction' in str(last_error):
            logger.warning(
                "MongoDB 不支持事务（可能为单节点部署），"
                "回退到非事务模式执行"
            )
            kwargs.pop('session', None)
            return f(*args, **kwargs)

        return jsonify(api_err_permission("操作失败，请稍后重试"))

    return wrapper


# ===================================================================
# 14. 参数校验装饰器               ★ 新增
# ===================================================================

# 内置校验规则
_VALIDATORS: dict = {}


def _register_validator(name: str, func: Callable) -> None:
    """注册一个自定义校验器"""
    _VALIDATORS[name] = func


# ---------------------------------------------------------------------------
# 内置校验规则实现
# ---------------------------------------------------------------------------

def _validate_required(value: Any, rule: bool, field: str) -> Optional[str]:
    """检查必填字段"""
    if rule and (value is None or value == ''):
        return f"「{field}」为必填项"
    return None


def _validate_type(value: Any, rule: type, field: str) -> Optional[str]:
    """检查字段类型"""
    if value is None:
        return None
    if rule == int:
        try:
            return None if isinstance(value, int) else _validate_int_str(value, field)
        except (ValueError, TypeError):
            return f"「{field}」必须为整数"
    if rule == float:
        try:
            float(value)
            return None
        except (ValueError, TypeError):
            return f"「{field}」必须为数字"
    if rule == bool:
        if isinstance(value, bool):
            return None
        if isinstance(value, str) and value.lower() in ('true', 'false', '1', '0'):
            return None
        return f"「{field}」必须为布尔值"
    if not isinstance(value, rule):
        return f"「{field}」类型错误，期望 {rule.__name__}"
    return None


def _validate_int_str(value: Any, field: str) -> Optional[str]:
    """尝试将字符串转换为整数"""
    str_val = str(value).strip()
    if str_val.lstrip('-').isdigit():
        return None
    return f"「{field}」必须为整数"


def _validate_min(value: Any, rule: Union[int, float], field: str) -> Optional[str]:
    """检查最小值（数字）或最短长度（字符串）"""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return None if value >= rule else f"「{field}」不能小于 {rule}"
    if isinstance(value, str):
        return None if len(value) >= rule else f"「{field}」长度不能少于 {rule}"
    return None


def _validate_max(value: Any, rule: Union[int, float], field: str) -> Optional[str]:
    """检查最大值（数字）或最大长度（字符串）"""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return None if value <= rule else f"「{field}」不能大于 {rule}"
    if isinstance(value, str):
        return None if len(value) <= rule else f"「{field}」长度不能超过 {rule}"
    return None


def _validate_min_length(value: Any, rule: int, field: str) -> Optional[str]:
    """检查字符串最小长度"""
    if value is None:
        return None
    if isinstance(value, str) and len(value) < rule:
        return f"「{field}」长度不能少于 {rule} 个字符"
    return None


def _validate_max_length(value: Any, rule: int, field: str) -> Optional[str]:
    """检查字符串最大长度"""
    if value is None:
        return None
    if isinstance(value, str) and len(value) > rule:
        return f"「{field}」长度不能超过 {rule} 个字符"
    return None


def _validate_pattern(value: Any, rule: str, field: str) -> Optional[str]:
    """检查正则匹配"""
    if value is None or value == '':
        return None
    import re
    if not re.match(rule, str(value)):
        return f"「{field}」格式不正确"
    return None


def _validate_choices(value: Any, rule: list, field: str) -> Optional[str]:
    """检查是否在允许的选项列表中"""
    if value is None:
        return None
    if value not in rule:
        choices_str = ', '.join(str(c) for c in rule)
        return f"「{field}」只能为以下值之一：{choices_str}"
    return None


def _validate_email(value: Any, rule: bool, field: str) -> Optional[str]:
    """检查邮箱格式"""
    if not rule or value is None or value == '':
        return None
    import re
    if not re.match(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', str(value)):
        return f"「{field}」不是有效的邮箱地址"
    return None


def _validate_mobile(value: Any, rule: bool, field: str) -> Optional[str]:
    """检查手机号格式"""
    if not rule or value is None or value == '':
        return None
    import re
    if not re.match(r'^1[3-9]\d{9}$', str(value)):
        return f"「{field}」不是有效的手机号"
    return None


# 注册内置校验器
_BUILTIN_VALIDATORS = {
    'required': _validate_required,
    'type': _validate_type,
    'min': _validate_min,
    'max': _validate_max,
    'min_length': _validate_min_length,
    'max_length': _validate_max_length,
    'pattern': _validate_pattern,
    'choices': _validate_choices,
    'email': _validate_email,
    'mobile': _validate_mobile,
}


def validate_params(schema: dict) -> Callable:
    """
    声明式请求参数校验装饰器。

    校验通过后的参数以字典形式存入 ``g.validated``，
    视图函数通过 ``g.validated`` 获取。

    :param schema: 校验规则字典。
                   每个字段的规则可以是以下键的组合：:

        {
            "username": {
                "required": True,           # 必填
                "type": str,                # 期望类型
                "min_length": 2,            # 字符串最短长度
                "max_length": 50,           # 字符串最大长度
                "pattern": r"^[a-zA-Z]"     # 正则匹配
            },
            "email": {
                "required": True,
                "email": True               # 邮箱格式
            },
            "mobile": {
                "mobile": True              # 手机号格式
            },
            "age": {
                "type": int,                # 整数
                "min": 1,
                "max": 150
            },
            "status": {
                "choices": [0, 1, 2]        # 枚举值
            }
        }

    用法示例::

        @admin_router.route('/user/save', methods=['POST'])
        @validate_params({
            "username": {"required": True, "type": str, "min_length": 2, "max_length": 50},
            "email":    {"required": True, "email": True},
            "age":      {"type": int, "min": 1, "max": 150},
        })
        def user_save():
            # 校验通过的数据
            username = g.validated['username']
            email = g.validated['email']
            age = g.validated['age']
            ...
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # 从请求中收集所有参数
            raw_params = http_helper.get_prams_dict()
            validated: dict = {}
            errors: list[str] = []

            for field, rules in schema.items():
                raw_value = raw_params.get(field)

                # 按规则逐个校验
                for rule_name, rule_value in rules.items():
                    validator = _BUILTIN_VALIDATORS.get(rule_name)
                    if validator is None:
                        logger.warning("未知校验规则: %s", rule_name)
                        continue

                    err = validator(raw_value, rule_value, field)
                    if err:
                        errors.append(err)
                        break  # 一个字段只报第一个错误

                # 如果字段通过了所有校验（且非空），执行类型转换
                if raw_value is not None and raw_value != '':
                    field_type = rules.get('type')
                    if field_type is not None:
                        try:
                            if field_type == int:
                                raw_value = int(raw_value)
                            elif field_type == float:
                                raw_value = float(raw_value)
                            elif field_type == bool:
                                if isinstance(raw_value, str):
                                    raw_value = raw_value.lower() in ('true', '1', 'on')
                            validated[field] = raw_value
                        except (ValueError, TypeError):
                            errors.append(f"「{field}」类型转换失败")
                    else:
                        validated[field] = raw_value
                elif not errors:
                    # 空值且没有错误（非必填字段），使用默认值或直接传 None
                    validated[field] = raw_value

            if errors:
                logger.warning("参数校验失败 | errors=%s", errors)
                return jsonify(api_err_permission('；'.join(errors)))

            g.validated = validated
            return f(*args, **kwargs)

        return wrapper

    return decorator


# ===================================================================
# 15. 响应缓存装饰器               ★ 新增
# ===================================================================

def cache_response(timeout: int) -> Callable:
    """
    缓存视图函数的 JSON 响应结果。

    以 ``请求路径 + 查询参数 + 用户语言偏好`` 作为缓存键，
    适用于读多写少、数据更新不频繁的公开接口。

    :param timeout: 缓存有效时间（秒），如 ``300`` 表示 5 分钟

    用法示例::

        @app.route('/api/article/list')
        @cache_response(300)    # 缓存 5 分钟
        def article_list():
            ...
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # 构造缓存键
            lang = getattr(g, 'lang', '')
            cache_key = (
                f'response_cache:{request.path}:{request.query_string.decode()}'
                f':{lang}'
            )

            # 尝试命中缓存
            cached = eb_cache.cache.get(cache_key)
            if cached is not None:
                logger.debug("响应缓存命中 | key=%s", cache_key)
                return cached

            # 执行原函数
            result = f(*args, **kwargs)

            # 仅缓存 jsonify 类型的响应（避免缓存重定向或错误页）
            if hasattr(result, 'is_json') and result.is_json:
                try:
                    eb_cache.cache.set(cache_key, result, timeout=timeout)
                except Exception:
                    logger.exception("响应缓存写入失败")

            return result

        return wrapper

    return decorator