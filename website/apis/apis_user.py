
from flask import jsonify, g

from bll.address import Address
from bll.apply_credites import ApplyCredites
from bll.favorite import Favorite
from bll.new_content import NewsContent
from decorators import rate_limit_ip
from eb_utils import http_helper, flask_utils
from entity import api_msg
from entity.user_token import UserToken
from website.apis import api_blue_user


@api_blue_user.route('apply_credits', methods=['POST'])
@rate_limit_ip(3,60) # 一小时只允许调用3次
def add_credits():
    """
    申请积分-需要后台审核
    :return:
    """
    credits = http_helper.get_prams_int("credits")
    remark = http_helper.get_prams_int("remark")
    if credits and remark:
        bll = ApplyCredites()
        model = bll.new_instance()
        user_token: UserToken = g.u

        model.username = user_token.name
        model.ni_name = user_token.ni_name
        model.credits = credits
        model.remark = remark
        model.ip = flask_utils.get_client_ip()

        bll.add(model)
        return jsonify(api_msg.api_succesful("succesfull"))

    return jsonify(api_msg.api_err("请输入必要的参数!"))

@api_blue_user.route('login_info', methods=['POST','GET'])
def login_info():
    """
    获取登录后的用户信息
    :return:
    """
    user_token: UserToken = g.u
    if user_token:
        user_token.id = str(user_token.id)
        return jsonify(api_msg.api_succesful(user_token))
    return jsonify(api_msg.api_err("logout"))

@api_blue_user.route('fav_content', methods=['POST','GET'])
@rate_limit_ip(3,1) # 一分钟只允许调用3次
def fav_content():
    """
    收藏内容
    :return:
    """
    data_id = http_helper.get_prams("data_id")
    user_token: UserToken = g.u
    if user_token and data_id:
        # user_token.id = str(user_token.id)

        bll_content = NewsContent()
        content_model = bll_content.find_one_by_id(data_id)
        if not content_model:
            return jsonify(api_msg.api_err("不存在数据"))

        bll = Favorite()
        model = bll.find_one_by_where({"content_id": content_model.id, "user_id": user_token.id})
        if model:
            bll.delete_by_id(model._id)
            return jsonify(api_msg.api_err("已取消收藏!"))
        model = bll.new_instance()

        model.content_title = content_model.title
        model.content_id = content_model.id
        model.small_pic = content_model.small_pic

        model.class_name = content_model.class_name
        model.class_n_id = content_model.class_n_id
        model.user_id = user_token.id

        bll.save(model)

        return jsonify(api_msg.api_succesful("成功加入收藏夹!"))
    return jsonify(api_msg.api_err("传入的参数不正确"))


@api_blue_user.route('add_address', methods=['POST'])
@rate_limit_ip(3,1) # 一分钟只允许调用3次
def add_address():
    """
    收藏内容
    :return:
    """
    user_token: UserToken = g.u
    data_id = http_helper.get_prams("data_id")

    if user_token and data_id:
        bll = Address()
        bll.delete_by_id(data_id)
        return jsonify(api_msg.api_succesful("删除成功!"))
    elif user_token:
        bll = Address()
        model = bll.new_instance()
        model.user_id = user_token.id
        model.user_name = http_helper.get_prams("user_name")
        model.phone = http_helper.get_prams("phone")
        model.email = http_helper.get_prams("email")
        model.post_code = http_helper.get_prams("post_code")
        model.address_info = http_helper.get_prams("address_info")
        bll.save(model)

        return jsonify(api_msg.api_succesful("添加成功!"))
    return jsonify(api_msg.api_err("传入的参数不正确"))