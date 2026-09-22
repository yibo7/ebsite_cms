from typing import Tuple
from urllib.parse import quote

import requests
from flask import Request, request

from entity.user_call_back_model import UserCallBackModel
from plugins.plugin_base import OpenLoginBase, plugin_attribute


@plugin_attribute("Google 登录", "1.0", "ebsite")
class OpenLoginGoogle(OpenLoginBase):
    """
    Google OAuth 2.0 登录插件。

    使用 Google 账号体系实现第三方登录，遵循标准的 Authorization Code 流程。

    前置条件：
      - 在 Google Cloud Console 中创建 OAuth 2.0 客户端凭据
      - 在「已获授权的重定向 URI」中添加回调地址（插件后台可查看）
      - 启用 Google+ API 或 OAuth 2.0 范围（默认使用 openid / email / profile）
    """

    GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
    GOOGLE_USER_INFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

    def __init__(self, current_app):
        self.info = "基于 Google OAuth 2.0 的登录插件"
        self.client_id: str = ""
        self.client_secret: str = ""
        super().__init__(current_app)

    # ------------------------------------------------------------------
    # OAuth 第一步：构造授权 URL
    # ------------------------------------------------------------------

    def login(self) -> Tuple[bool, str]:
        """
        构造 Google OAuth 授权 URL，引导用户跳转到 Google 授权页。
        """
        back_url = quote(self.get_call_back_url())
        state = self._generate_state(expire_seconds=300)

        auth_url = (
            f"{self.GOOGLE_AUTH_URL}"
            f"?client_id={self.client_id}"
            f"&redirect_uri={back_url}"
            f"&response_type=code"
            f"&scope=openid%20email%20profile"
            f"&state={state}"
            f"&access_type=offline"
        )
        return True, auth_url

    # ------------------------------------------------------------------
    # OAuth 第二步：处理回调
    # ------------------------------------------------------------------

    def call_back(self, request: Request) -> Tuple[bool, str, UserCallBackModel]:
        """
        处理 Google 授权回调。

        1. 校验 state 防止 CSRF
        2. 用 code 换取 access_token
        3. 用 access_token 获取用户基本信息
        """
        code = request.args.get('code')
        state = request.args.get('state')
        error = request.args.get('error')
        user_info = UserCallBackModel()

        # -- 用户拒绝授权 --
        if error:
            return False, f'用户拒绝了授权（{error}）', user_info

        # -- 校验 state --
        if not self._verify_state(state):
            return False, 'state 校验失败，可能为非法回调或已过期', user_info

        if not code:
            return False, '缺少 code 参数', user_info

        # -- 用 code 换取 access_token / id_token --
        back_url = self.get_call_back_url()
        token_data = {
            'code': code,
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'redirect_uri': back_url,
            'grant_type': 'authorization_code',
        }
        token_resp = requests.post(self.GOOGLE_TOKEN_URL, data=token_data)
        if token_resp.status_code != 200:
            return False, f'获取 access_token 失败（HTTP {token_resp.status_code}）', user_info

        token_json = token_resp.json()
        access_token = token_json.get('access_token', '')
        if not access_token:
            return False, '返回数据中没有 access_token', user_info

        # -- 用 access_token 获取用户信息 --
        headers = {'Authorization': f'Bearer {access_token}'}
        user_resp = requests.get(self.GOOGLE_USER_INFO_URL, headers=headers)
        if user_resp.status_code != 200:
            return False, f'获取用户信息失败（HTTP {user_resp.status_code}）', user_info

        google_user = user_resp.json()

        # -- 填充标准化的用户信息模型 --
        user_info.user_open_id = google_user.get('id', '')
        user_info.email = google_user.get('email', '')
        user_info.email_verified = google_user.get('verified_email', False)
        user_info.user_ni_name = google_user.get('name', '')
        user_info.avatar_url = google_user.get('picture', '')
        user_info.token = access_token

        return True, '', user_info

    # ------------------------------------------------------------------
    # 后台配置表单
    # ------------------------------------------------------------------

    def params_temp(self):
        """
        在后台保存插件配置时，实现在模板中添加保存参数。
        """
        callback_url = f'{request.host_url}api/app/open_login_back?plugin={self.id}'
        return f'''
        <div class="alert alert-info">
            <strong>回调地址</strong>（请在 Google Cloud Console 的「已获授权的重定向 URI」中添加此地址）：
            <br><code>{callback_url}</code>
        </div>
        <div class="alert alert-info">
            <strong>使用说明：</strong><br>
            1. 打开
            <a href="https://console.cloud.google.com/" target="_blank">Google Cloud Console</a>
            → 选择一个项目或新建项目<br>
            2. 左侧菜单 → <strong>API 和服务</strong> → <strong>OAuth 同意屏幕</strong><br>
            3. User Type 选择「外部」，填写应用名称和邮箱，添加以下作用域：
               <br>　• <code>openid</code>
               <br>　• <code>.../auth/userinfo.email</code>
               <br>　• <code>.../auth/userinfo.profile</code><br>
            4. 左侧菜单 → <strong>凭据</strong> → 创建凭据 → <strong>OAuth 2.0 客户端 ID</strong><br>
            5. 应用类型选「Web 应用」，添加以上回调地址到「已获授权的重定向 URI」<br>
            6. 创建成功后复制 <strong>Client ID</strong> 和 <strong>Client Secret</strong> 填入下方<br>
            7. <strong>首次登录</strong>需要将你的 Google 账号添加为测试用户（测试阶段）
        </div>
        <div class="mb-3">
            <label>Client ID</label>
            <input name="client_id" value="{{{{model.client_id}}}}" style="max-width:500px" class="form-control" required>
            <small class="form-text text-muted">在 Google Cloud Console → 凭据 → OAuth 2.0 客户端 ID 中获取</small>
        </div>
        <div class="mb-3">
            <label>Client Secret</label>
            <input name="client_secret" value="{{{{model.client_secret}}}}" style="max-width:500px" class="form-control" required>
            <small class="form-text text-muted">与 Client ID 对应的客户端密钥</small>
        </div>
        '''