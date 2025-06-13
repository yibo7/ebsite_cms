import os


class WebPaths(object):
    ADMIN_PATH = "/admin/"
    ADMIN_LOGIN = f"{ADMIN_PATH}login_ad"
    ADMIN_INDEX = f"{ADMIN_PATH}index"
    LOGIN_URL = "/login"
    USER_PATH = "/user/"
    USER_INDEX = f"{USER_PATH}index"
    API_PATH = "/api/"
    # API_APP_PATH = "/api/app/"

    @staticmethod
    def get_admin_path(temp_name: str):
        return temp_name # 使用了主题后不再需要拼接路径
        # return f"admin/{temp_name}"

    @staticmethod
    def get_user_path(temp_name: str):
        return f"user/{temp_name}"


class SiteConstant(object):
    COOKIE_AD_TOKEN_KEY = "ua_key"
    COOKIE_TOKEN_KEY = "u_key"
    PAGE_SIZE_AD = 20
    SITE_KEY = os.environ.get('SITE_KEY', 'ebsite20015')
