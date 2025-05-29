import eb_cache
from entity.user_token import UserToken


def get_test_token():
    return UserToken('66c9b019e9950cc65dffa982', 'ebsite@163.com', 'cqs263', '64c38c2ccccb3a9a6f8b24a4', '1个月VIP', '/images/default_avatar.png',"oVK0l7RXcT9-d6Gi4Pg3Cx-LQzS4")


def get_token(token_key) -> UserToken or None:
    if token_key:
        user_token = eb_cache.get_obj(token_key)  # type:UserToken
        return user_token
    return None
