
from typing import Tuple

import requests
from flask import Request

import eb_cache
import eb_utils
from entity.user_call_back_model import UserCallBackModel
from plugins.plugin_base import Uploader, OpenLoginBase, plugin_attribute


@plugin_attribute("微信登录", "1.0", "ebsite")
class OpenLoginWixin(OpenLoginBase):

    def __init__(self, current_app):
        self.info = "基于WEB端的微信登录插件"
        self.app_id:str = ""
        self.app_secret:str = ""
        super().__init__(current_app)

    def login(self) -> Tuple[bool, str]:

        back_url = self.get_call_back_url()
        safe_code = eb_utils.get_uuid()
        eb_cache.set_data('1',60,safe_code)  # 缓存1分钟
        Login_url = f"https://open.weixin.qq.com/connect/qrconnect?appid={self.app_id}&redirect_uri={back_url}&response_type=code&scope=snsapi_login&state={safe_code}"

        return True,Login_url

    def call_back(self, request: Request) -> Tuple[bool, str, UserCallBackModel]:
        code = request.args.get('code')
        state = request.args.get('state')
        user_info = UserCallBackModel()
        if eb_cache.get(state) != '1':
            return False, 'state不是安全的', user_info

        is_ok = False
        error_msg = "未知错误"


        if not code:
            return False, '无效的code', user_info

        weixin_url = "https://api.weixin.qq.com"
        # 构造获取access_token的URL
        user_token_url = f"{weixin_url}/sns/oauth2/access_token?appid={self.app_id}&secret={self.app_secret}&code={code}&grant_type=authorization_code"

        response = requests.get(user_token_url)
        if response.status_code == 200 and 'access_token' in response.json():
            access_token = response.json()['access_token']
            open_id = response.json()['openid']

            # 构造获取用户信息的URL
            get_user_info_url = f"{weixin_url}/sns/userinfo?access_token={access_token}&openid={open_id}"
            response = requests.get(get_user_info_url)
            if response.status_code == 200 and 'openid' in response.json():
                data = response.json()

                user_info.user_ni_name = data.get('nickname')
                user_info.user_open_id = data.get('openid')
                user_info.user_ico = data.get('headimgurl')
                user_info.sex = data.get('sex')
                user_info.token = access_token
                user_info.country = data.get('country')
                user_info.city = data.get('city')
                user_info.province = data.get('province')
                is_ok = True
            else:
                error_msg = "未能获取用户信息"
        else:
            error_msg = "未能获取Token值"
        return is_ok,error_msg,user_info

    def params_temp(self):
        """
        在后台保存插件配置时，实现在模板中添加保存参数
        :return: 模板字符串
        """
        return '''
        <div class="mb-3">
            <label>AppId</label>
            <input name="app_id" value="{{model.app_id}}"  style="max-width:500px" class="form-control" required>
        </div>
        <div class="mb-3">
            <label>AppSecret</label>
            <input name="app_secret" value="{{model.app_secret}}"  style="max-width:500px" class="form-control" required>
        </div> 
        '''