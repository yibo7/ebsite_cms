class UserCallBackModel:
    """
    第三方登录回调返回的标准用户信息模型。

    各平台必返字段：
      - user_open_id : 第三方平台的用户唯一标识
      - email        : 邮箱（Google / Apple 必返，微信 / GitHub 部分返回）
      - email_verified : 邮箱是否经过第三方平台验证

    以下字段为各平台通用可选字段：
      - user_ni_name : 昵称
      - avatar_url   : 头像 URL
      - token        : 第三方平台的 access_token

    以下为部分平台专有字段（如微信），不一定每个平台都返回：
      - sex / city / country / province
    """
    def __init__(self):
        # ======== 核心字段 ========
        self.user_open_id = ''       # 第三方平台用户唯一 ID
        self.email = ''              # 邮箱
        self.email_verified = False  # 邮箱是否已验证
        self.user_ni_name = ''       # 用户昵称
        self.avatar_url = ''         # 用户头像 URL
        self.token = ''              # 第三方 access_token

        # ======== 平台特有可选字段 ========
        self.sex = ''                # 性别（微信返回）
        self.city = ''               # 城市（微信返回）
        self.country = ''            # 国家（微信返回）
        self.province = ''           # 省份（微信返回）

    # ---------- 兼容旧字段（方便过渡） ----------
    @property
    def user_ico(self):
        """兼容旧代码：user_ico → avatar_url"""
        return self.avatar_url

    @user_ico.setter
    def user_ico(self, value):
        self.avatar_url = value