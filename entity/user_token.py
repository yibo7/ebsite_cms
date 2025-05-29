from dataclasses import dataclass
from typing import Optional


@dataclass
class UserToken:
    id: str  # 唯一ID 也就是_id
    name: str
    ni_name: str
    group_id: str
    group_name: str
    avatar: str
    open_id:Optional[str] = "" # 第三方登录时获取的三方平台ID,Optional表示可选在创建实现是不是必填写项
