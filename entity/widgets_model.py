from entity.entity_base import ModelBase, annotation


class WidgetsModel(ModelBase):
    def __init__(self):
        super().__init__()
        self.name: str = ""
        self.order_by: str = "_id"
        self.order_by_desc: str = "DESC"
        self.limit: int = 10
        self.where_query: str = ""
        self.temp_code: str = ""
        self.info: str = ""
        # 部件类型标识：字符串格式 模块名_序号（如 sys_1、shop_1）
        # 兼容旧数据中的 int 格式（如 1、2），运行时由 resolve_widget_id 转换
        self.temp_type: str = ""
        self.user_id: str = ""
        self.cache_time:int = 0 # 是否将渲染结果缓存，这里时间单位是秒，0表示不缓存
        self.other = {}  # 其他参数

    @annotation("部件名称")
    def a_name(self):
        return self.name

    @annotation("部件ID")
    def b_id(self):
        return self._id

    @annotation("部件类型|widget_type_name")
    def b_temp_type(self):
        return self.temp_type

    @annotation("添加时间|to_time_name")
    def d_add_time(self):
        return self.add_time
