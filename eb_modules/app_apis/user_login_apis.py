from flask import   jsonify,  current_app

import eb_cache
import eb_utils
from bll.user import User
from decorators import rate_limit_ip, check_img_code, check_mobile_email_code
from eb_cache import login_utils
from eb_modules.app_apis import bp_app_apis
from eb_utils import http_helper
from eb_utils.image_code import ImageCode
from eb_utils.mobile_code import MobileCode
from eb_utils.string_check import is_email, is_mobile
from entity import api_msg


@bp_app_apis.route('img_safe_code', methods=['POST'])
def img_safe_code():
    """
    获取图片验证码
    """
    code_key,img_base64 = ImageCode().getAppImgCode()

    return jsonify({'code': 0, "code_key": code_key, "img": img_base64})

@bp_app_apis.route('send_code', methods=['POST'])
# @rate_limit_ip(2, 1)  # 1分钟内只能请求一次
@check_img_code(3)  # 一小时内如果超过3次，就启用图片验证码
def send_code():
    to_target = http_helper.get_prams('to')
    if to_target:
        if is_email(to_target):
            pass
        elif is_mobile(to_target):

            is_succesful = MobileCode().send_code(to_target)
            if is_succesful:
                return jsonify(api_msg.api_succesful(""))
            else:
                return jsonify(api_msg.api_err("发送失败"))
    return jsonify(api_msg.api_err("请传手机号或EMAIL"))


@bp_app_apis.route('login_reg_mobile', methods=['POST'])
@check_mobile_email_code  # 开启手机验证码验证
def login_reg_mobile(account:str):
    """
    手机验证码登录-如果不存在就注册一个账号
    @param account: 手机号
    @return:
    """
    mobile = account
    if mobile:
        bll = User()
        model = bll.find_by_mobile(mobile)
        if not model:  # 如果存在用户，注册一个账号
            is_succesful, data = bll.mobile_reg(mobile)
            if is_succesful:
                model = data
            else:
                return jsonify(api_msg.api_err(f'注册号码失败:{data}！'))

        key = login_utils.update_app_token(model)
        return jsonify(api_msg.api_succesful(key,model.openid))

    return jsonify(api_msg.api_err('请输入正确的手机号！'))


@bp_app_apis.route('reg_user_pass', methods=['POST'])
@check_mobile_email_code  # 开启手机验证码验证
def reg_user_pass(account:str):
    password = http_helper.get_prams('pass')
    mobile = account
    if mobile and password:
        bll = User()
        model = bll.find_by_mobile(mobile)
        if not model:  # 如果存在用户，注册一个账号
            is_succesful, data = bll.reg_user_pass_mobile(mobile, password)
            if is_succesful:
                model = data
            else:
                return jsonify(api_msg.api_err(f'注册号码失败:{data}！'))

        # utk = UserToken(model._id, model.username, model.ni_name, model.group_id, "", model.avatar,"")
        # key = login_utils.set_app_token(utk)
        key = login_utils.update_app_token(model)
        return jsonify(api_msg.api_succesful(key))

    return jsonify(api_msg.api_err("手机号或密码不能为空"))


@bp_app_apis.route('login_pass', methods=['POST'])
@check_img_code(3)  # 一小时内如果超过3次，就启用图片验证码，递进式延迟，输入正确可解锁
def login_pass():
    """
    通过账号密码登录
    """
    username = http_helper.get_prams('account')  # 账号
    password = http_helper.get_prams('pass')  # 密码
    if username and password:
        if is_email(username) or is_mobile(username):
            is_succesful, msg = User().login_app(username, password)
            if is_succesful:
                return jsonify(api_msg.api_succesful(msg))  # msg 为token
            else:
                err_msg = msg
        else:
            err_msg = "请输入有效的EMAIL或手机号"
    else:
        err_msg = "账号密码不能为空"

    return jsonify({'code': -1, "msg": err_msg})




@bp_app_apis.route('find_pass1', methods=['POST'])
@rate_limit_ip(10, 1440)  # 24小时只能请求10次
def find_pass1():
    account = http_helper.get_prams('account')
    err_info = '请输入账号'
    if account:
        bll = User()
        model = bll.find_by_mobile(account)
        if model:
            find_pass_key = f'find_{eb_utils.get_uuid()}'
            eb_cache.set_ex_minutes({'username':model.username,'is_check_code':False}, 1, find_pass_key)
            return jsonify(api_msg.api_succesful(find_pass_key, '请在1分钟内完成下一步!'))
        else:
            err_info = '用户不存在'

    return jsonify(api_msg.api_err(err_info))
@bp_app_apis.route('find_pass2', methods=['POST'])
@check_mobile_email_code  # 开启手机验证码验证，所以在调用此方法前需要先调用send_code
def find_pass2(account:str):
    """
    找回密码-输入账号
    """
    find_pass_key = http_helper.get_prams('pass_key')

    err_info = '账号或pass_key不能为空'
    if account and find_pass_key:
        cache_obj = eb_cache.get_obj(find_pass_key)
        if cache_obj:
            bll = User()
            model = bll.find_by_mobile(account)

            if model and cache_obj['username']==model.username:  # 1. 判读用户是否存在，存在写入缓存
                cache_obj['is_check_code'] = True
                eb_cache.set_ex_minutes(cache_obj,5,find_pass_key)
                # 不管用户存在不存在，都返回正确，防止恶意猜测账号是否存在
                return jsonify(api_msg.api_succesful(find_pass_key, '验证码正确，请在5分钟内完成密码的修改!'))
            else:
                err_info = '验证不通过'
        else:
            err_info = "请求已经过期"

    return jsonify({'code': -1, "msg": err_info})



@bp_app_apis.route('find_pass3', methods=['POST'])
def find_pass3():
    """
    找回密码-更新密码
    # 1.通过find_pass_key是否存在此缓存
    # 2.如果不存在提醒用户验证过期
    # 3.如果存在find_pass_key的缓存{'account','code','is_check_code'}  检查is_check_code是否为true
    # 4.更新密码
    # 5.删除find_pass_key的缓存
    """
    new_pass = http_helper.get_prams('newpass')  # 新的密码
    find_pass_key = http_helper.get_prams('pass_key')  # find_pass_key
    err_info = 'params err'
    cache_obj = eb_cache.get_obj(find_pass_key)
    if new_pass and find_pass_key and cache_obj and cache_obj['is_check_code']:
        bll = User()
        is_ok, msg = bll.get_pass_hash(new_pass) # 获取加密后的密码，同时判断密码是否合格
        if is_ok:
            model = bll.get_by_name(cache_obj['username'])
            model.password = msg
            bll.update(model)
            return jsonify(api_msg.api_succesful(''))
        else:
            err_info = msg

    return jsonify(api_msg.api_err(err_info))



@bp_app_apis.route('openlogin', methods=['GET', 'POST'])
def openlogin():
    """
    获取三方登录连接
    """
    plugin_id = http_helper.get_prams('pid')
    pm = current_app.pm
    pl = pm.get_by_id(plugin_id)
    is_succesful,msg = pl.login()
    if is_succesful:
        return jsonify(api_msg.api_succesful(msg))
    else:
        return jsonify(api_msg.api_err(msg))