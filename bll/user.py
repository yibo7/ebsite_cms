import random
import string
import time
from typing import Union, Tuple, Optional

from bson import ObjectId
from flask import current_app, Flask
from pymongo.errors import DuplicateKeyError
from werkzeug.security import generate_password_hash, check_password_hash

import eb_utils
from bll.bll_base import BllBase
from bll_orders.credit_logs import CreditLogs
from eb_cache import login_utils
from eb_utils import string_check, flask_utils
from entity.user_model import UserModel
from signals import user_reged


class User(BllBase[UserModel]):

    def __init__(self, app: Optional[Flask] = None):
        super().__init__(app)


    def create_indexs(self):
        """
        初始化时创建唯一索引
        :return:
        """
        self.create_index('username')
        # self.create_index('mobile_number')
        # self.create_index('email_address')

    def credits_change(self,session, model:UserModel, num:int, ip:str, itype:int, info:str, is_un_frozen = False):
        """
        更改用户积分
        @param is_un_frozen: 如果num为负数，也就是消费积分，是否释放等量的冻结积分
        @param session: 版面创建的事务
        @param model: 用的实例
        @param num: 变量数量，如果增加为正数，如果减少为负数
        @param ip: 当前操作的IP
        @param itype: 操作类型： 目前有  1 消费，2. 直接购买 3 连续包月奖励 4 申请通过积分
        @param info: 备注内容
        @return: 是否成功
        """

        if num == 0 or not string_check.is_int(num):
            raise Exception("更改用户的积分必须为整数，且不能为0！")
        bll_credits_log =  CreditLogs(self.app) # self.app 确保与当前bll在同一个上下文调用事务
        model_log = bll_credits_log.new_instance()
        model_log.credits = num
        model_log.user_id = model._id
        model_log.username = model.username
        model_log.user_ip = ip
        model_log.type_id = itype
        model_log.info = info
        model_log.credits_balance = model.credits
        err_info = ""

        model.credits += model_log.credits

        if num <0 and is_un_frozen: # 如果num为负数，也就是消费积分，是否释放等量的冻结积分
            model.credits_frozen += num

        # 更新用户积分, 这个操作应该用乐观锁
        is_succesfull = self.update_trans(model, session,model.version)
        if not is_succesfull:
            raise Exception("更新用户积分失败，可能乐观锁被占用！")

        # 添加积分操作流水
        bll_credits_log.add_trans(model_log, session)
        return True

    def reg_give_credits(self,model: UserModel):
        """
        注册赠送积分
        @param model: 当前注册的用户实体，为了简单，不使用事务，请在注册添加用户前调用
        @return:
        """
        reg_credits =  self.configs['reg_credits']
        if reg_credits:
            reg_credits = int(reg_credits)
            if reg_credits>0:
                bll_credits_log = CreditLogs(self.app)
                model_log = bll_credits_log.new_instance()
                model_log.credits = reg_credits
                model_log.user_id = model._id
                model_log.username = model.username
                model_log.user_ip = model.last_login_ip
                model_log.type_id = 5 # 赠送积分
                model_log.info = "注册赠送积分"
                bll_credits_log.add(model_log)
                model.credits = reg_credits

    def credits_frozen_change(self,session, model:UserModel, num:int) -> Tuple[bool,str]:
        """
        更新用户冻结的积分
        @param session: 版面创建的事务
        @param model: 用的实例
        @param num: 变量数量，如果增加为正数，如果减少为负数
        @return: 是否成功
        """

        model.credits_frozen += num
        # 更新用户积分, 这个操作应该用乐观锁
        is_succesfull = self.update_trans(model, session,model.version)
        if is_succesfull:
            return True, ''

        raise Exception("更新用户冻结的积分失败，可能乐观锁被占用")
        # return False,"更新用户冻结的积分失败，可能乐观锁被占用！"

    def new_instance(self) -> UserModel:
        return UserModel()

    def exist_name(self, name: str) -> bool:
        return True if self.find_one_by_where({'username': name}) else False

    def exist_mobile(self, mobile: str) -> bool:
        return True if self.find_one_by_where({'mobile_number': mobile}) else False

    def exist_email(self, email: str) -> bool:
        return True if self.find_one_by_where({'email_address': email}) else False

    def get_pass_hash(self, pass_word:str) -> Tuple[bool,str]:
        if not pass_word or len(pass_word) < 6:
            return False, '密码长度至少是6位'
        pass_hash = generate_password_hash(pass_word)
        return True,pass_hash

    def reg_user(self, model: UserModel):

        model.username = self.clean_mongo_search_keywords(model.username, False)
        model.password = self.clean_mongo_search_keywords(model.password, False)

        u_name = model.username
        if not u_name or self.exist_name(u_name):
            return False, '账号已存在或不能为空'

        email = model.email_address
        if email and self.exist_email(email):
            return False, 'EMAIL已存在或不能为空'

        mobile = model.mobile_number
        if mobile and self.exist_name(mobile):
            return False, '手机号已存在或不能为空'

        if len(model.password) < 6:
            return False, '密码长度至少是6位'

        model.avatar = "/images/default_avatar.png"
        model.password = generate_password_hash(model.password)

        group_id = self.configs['reg_group_id']
        if not group_id:
            return False,'注册默认用户组没有设置，请到后台设置中设置。'
        model.group_id = group_id

        self.reg_give_credits(model)

        _data_id = self.add(model)
        if _data_id:
            user_reged.send(model)
            return True, _data_id
        return False, '用户注册失败'

    @staticmethod
    def check_pass(pass_1, pass_2):
        """
        验证用户密码是否正确
        :param pass_2:
        :param pass_1:
        :return:
        """
        return check_password_hash(pass_1, pass_2)

    def get_by_name(self, name: str):
        return self.find_one_by_where({"username": name})

    def login(self, user_name, pass_word, resp) -> Tuple[bool,str]:

        user_name = self.clean_mongo_search_keywords(user_name, False)
        pass_word = self.clean_mongo_search_keywords(pass_word, False)

        user = self.get_by_name(user_name)
        is_sucessfull = False
        msg = "未知错误"
        if user:
            if not user.is_locked:
                pass_1 = user.password
                is_sucessfull = self.check_pass(pass_1, pass_word)
                if is_sucessfull:
                    msg = login_utils.set_cookie_token(user, resp)
                    user.last_login_ip = flask_utils.get_client_ip()
                    user.last_login_date = time.time()
                    user.login_count += 1
                    self.update(user)
                else:
                    msg = "用户名或密码错误"
            else:
                msg = '账号被锁定'
        else:
            msg = "用户名不存在或密码错误"

        return is_sucessfull, msg

    def update_niname(self, user_id: str, newname: str) -> bool:
        # 假设我们要更新 ni_name 字段为 cqs 的所有文档
        result = self.db[self.table_name].update_one(
            {"_id": ObjectId(user_id)},  # 查询条件，匹配特定_id的文档
            {"$set": {"ni_name": newname}}  # 更新操作，将 ni_name 设置为 cqs
        )
        if result.modified_count > 0:
            return True
        else:
            return False

    def update_avatar(self, user_id: str, avatar: str) -> bool:
        # 假设我们要更新 ni_name 字段为 cqs 的所有文档
        result = self.db[self.table_name].update_one(
            {"_id": ObjectId(user_id)},  # 查询条件，匹配特定_id的文档
            {"$set": {"avatar": avatar}}
        )
        if result.modified_count > 0:
            return True
        else:
            return False

    def find_by_mobile(self, mobile: str) -> UserModel:
        return self.find_one_by_where({'mobile_number': mobile})

    def find_by_email(self, email: str) -> UserModel:
        return self.find_one_by_where({'email_address': email})

    def generate_password(self, length=12):
        # 定义字符集
        characters = string.ascii_letters + string.digits + string.punctuation

        # 生成密码
        password = ''.join(random.choice(characters) for _ in range(length))

        return password

    def mobile_reg(self, mobile_number) -> Tuple[bool, Union[str, UserModel]]:
        try:

            model = UserModel()
            model.mobile_number = mobile_number
            model.username = mobile_number
            model.ni_name = mobile_number
            model.group_id = self.configs['reg_group_id']
            pass_word = self.generate_password()
            model.password = generate_password_hash(pass_word)
            model.avatar = "/images/default_avatar.png"

            model._id =self.add(model)
            if model._id:
                user_reged.send(model)
                return True,  model
            return False,'手机号注册失败'
        except DuplicateKeyError as er:
                print(er)
                return False, f'账号已被注册'
        except Exception as e:
               return False, e.__str__()

    def reg_user_pass_mobile(self, account:str, pass_word:str):

        if not account or self.exist_name(account):
            return False, '账号已存在或不能为空'

        mobile = account
        if mobile and self.exist_mobile(mobile):
            return False, '手机号已存在或不能为空'

        if len(pass_word) < 6:
            return False, '密码长度至少是6位'

        model = self.new_instance()
        model.username = account
        model.mobile_number = mobile
        model.ni_name = account
        model.password = generate_password_hash(pass_word)
        model.group_id = self.configs['reg_group_id']
        model.avatar = "/images/default_avatar.png"
        model.id = self.add(model)
        if model._id:
            user_reged.send(model)
            return True, model
        return False, '用户注册失败'

    def login_app(self, user_name, pass_word) -> Tuple[bool, str]:
        model = self.get_by_name(user_name)

        msg = "未知错误"
        is_succesful = False
        if model:
            if not model.is_locked:
                pass_1 = model.password
                is_sucessfull = self.check_pass(pass_1, pass_word)
                if is_sucessfull:
                    msg = login_utils.update_app_token(model)
                    is_succesful = True
                    model.last_login_ip = flask_utils.get_client_ip()
                    model.last_login_date = time.time()
                    model.login_count += 1
                    self.update(model)
                else:
                    msg = "用户名或密码错误"
            else:
                msg = '账号被锁定'
        else:
            msg = "用户名不存在或密码错误"

        return is_succesful, msg

    def get_by_openid(self, openid: str) -> UserModel or None:
        """
        获取openid对应的用户
        @param openid:
        @return:
        """
        if openid:
            return self.find_one_by_where({'openid': openid})
        return None


    def reg_open_user(self, openid:str, mobile,nickname,avatar) -> tuple[bool,UserModel or str]:
        """
        微信登录的时候，生成一个账号
        @param openid:
        @param mobile:
        @param nickname:
        @param avatar:
        @return:
        """
        if not openid or self.exist_name(openid):
            return False, '账号已存在或不能为空'

        if mobile and self.exist_mobile(mobile):
            return False, '手机号已存在或不能为空'

        account = mobile if mobile else openid

        pass_word = eb_utils.random_string(8) # 随机生成8位密码

        model = self.new_instance()
        model.username = account
        model.ni_name = nickname if nickname else account
        model.avatar = "/images/default_avatar.png"
        if avatar:
            model.avatar = avatar
        model.mobile_number = mobile
        model.password = generate_password_hash(pass_word)
        model.group_id = self.configs['reg_group_id']
        model.openid = openid
        self.add(model)
        user_reged.send(model)
        return True, model
