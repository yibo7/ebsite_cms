from typing import Tuple
from urllib.parse import quote

import requests
from flask import Request
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
        """
        发起微信扫码登录（OAuth 第一步）。

        构造微信开放平台的二维码授权 URL，引导用户扫码授权。
        """
        back_url = quote(self.get_call_back_url())
        # 使用基类提供的 state 生成方法（自动缓存防 CSRF）
        safe_code = self._generate_state(expire_seconds=60)
        login_url = (
            f"https://open.weixin.qq.com/connect/qrconnect"
            f"?appid={self.app_id}"
            f"&redirect_uri={back_url}"
            f"&response_type=code"
            f"&scope=snsapi_login"
            f"&state={safe_code}"
        )
        return True, login_url

    def call_back(self, request: Request) -> Tuple[bool, str, UserCallBackModel]:
        """
        处理微信扫码后的回调（OAuth 第二步）。

        1. 校验 state 防止 CSRF
        2. 用 code 换取 access_token
        3. 用 access_token 获取微信用户信息
        """
        code = request.args.get('code')
        state = request.args.get('state')
        user_info = UserCallBackModel()

        # 使用基类提供的 state 校验方法
        if not self._verify_state(state):
            return False, 'state 校验失败，可能为非法回调或已过期', user_info

        if not code:
            return False, '无效的 code 参数', user_info

        weixin_url = "https://api.weixin.qq.com"

        # 1. 用 code 换取 access_token
        token_url = (
            f"{weixin_url}/sns/oauth2/access_token"
            f"?appid={self.app_id}"
            f"&secret={self.app_secret}"
            f"&code={code}"
            f"&grant_type=authorization_code"
        )
        token_resp = requests.get(token_url)
        if token_resp.status_code != 200 or 'access_token' not in token_resp.json():
            return False, '获取 access_token 失败', user_info

        token_data = token_resp.json()
        access_token = token_data['access_token']
        open_id = token_data['openid']

        # 2. 用 access_token 获取用户信息
        user_info_url = (
            f"{weixin_url}/sns/userinfo"
            f"?access_token={access_token}"
            f"&openid={open_id}"
        )
        user_resp = requests.get(user_info_url)
        if user_resp.status_code != 200 or 'openid' not in user_resp.json():
            return False, '获取微信用户信息失败', user_info

        wx_user = user_resp.json()

        # 3. 填充标准化的用户信息模型
        user_info.user_open_id = wx_user.get('openid', '')
        user_info.user_ni_name = wx_user.get('nickname', '')
        user_info.avatar_url = wx_user.get('headimgurl', '')
        user_info.token = access_token
        # 微信不返回 email，所以 email / email_verified 保持默认空值

        # 微信特有字段
        user_info.sex = str(wx_user.get('sex', ''))
        user_info.country = wx_user.get('country', '')
        user_info.city = wx_user.get('city', '')
        user_info.province = wx_user.get('province', '')

        return True, '', user_info

    def params_temp(self):
        """
        在后台保存插件配置时，实现在模板中添加保存参数
        :return: 模板字符串
        """
        return '''
        <div class="alert alert-info">
            <strong>使用说明：</strong><br>
            1. 在
            <a href="https://open.weixin.qq.com/" target="_blank">微信开放平台</a>
            注册开发者账号，创建 <strong>网站应用</strong><br>
            2. 提交审核通过后，获取 <strong>AppId</strong> 和 <strong>AppSecret</strong><br>
            3. 在开放平台 → 网站应用 → 接口权限 中设置 <strong>授权回调域</strong> 为：<br>
            <code>/api/app/open_login_back?plugin=OpenLoginWixin</code>
            （只需填写域名部分，不要带 http://）<br>
            4. 用户点击"微信登录"后将弹出微信二维码，扫码完成即自动登录/注册<br>
            5. 首次登录自动创建账号，之后再次登录自动识别
        </div>
        <div class="mb-3">
            <label>AppId</label>
            <input name="app_id" value="{{model.app_id}}"  style="max-width:500px" class="form-control" required>
            <small class="form-text text-muted">在微信开放平台 → 网站应用 中获取</small>
        </div>
        <div class="mb-3">
            <label>AppSecret</label>
            <input name="app_secret" value="{{model.app_secret}}"  style="max-width:500px" class="form-control" required>
            <small class="form-text text-muted">与 AppId 对应的应用密钥</small>
        </div> 
        '''