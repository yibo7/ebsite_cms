import importlib
import os


import eb_utils

class ModuleInfo:
    def __init__(self, name, info, admin_url, settings_temp, author,
                 enable, version, priority, config_fields=None):
        self.id = eb_utils.md5(name)
        self.name = name
        self.info = info
        self.admin_url = admin_url
        self.settings_temp = settings_temp
        self.author = author
        self.version = version
        self.priority = priority
        self.enable = enable            # 装饰器中的默认值
        self.enable_db = None           # 数据库中的 enable 值（None=尚未查询）
        self.is_running = False         # 标记模块是否实际加载运行
        self.pending_restart = False    # True=刚操作了开关，待重启完全生效
        self.config_fields = config_fields or {}
        self._config_refresh_callback = None

    def init_app(self, app):
        self.app = app
        self.table = app.db['ModuleSettings']

    def on_config_changed(self, callback):
        """
        注册配置变更回调。当后台保存配置后自动调用，实现热生效。
        callback(saved_config: dict) -> None
        """
        self._config_refresh_callback = callback

    def set_configs(self, model: dict) -> dict:
        """
        保存模块配置，自动进行类型转换，并触发热更新回调。

        :param model: 从模板中获取的插件参数字典
        :return: 经过类型转换后的保存结果字典
        """
        model['_id'] = self.id

        # 根据 config_fields 自动转换字段类型
        if self.config_fields:
            for key, field_type in self.config_fields.items():
                if key in model and key != '_id':
                    try:
                        if field_type == 'int':
                            model[key] = int(model[key])
                        elif field_type == 'float':
                            model[key] = float(model[key])
                        elif field_type == 'bool':
                            if isinstance(model[key], str):
                                model[key] = model[key].lower() in ('true', '1', 'yes')
                        elif field_type == 'str':
                            model[key] = str(model[key])
                    except (ValueError, TypeError):
                        pass  # 转换失败时保留原值

        self.table.update_one({"_id": self.id}, {"$set": model}, upsert=True)

        # 热更新：通知模块配置已变更
        if self._config_refresh_callback:
            self._config_refresh_callback(model)

        return model

    def get_configs(self) -> dict:
        """
        获取模块配置
        :return:
        """
        model = self.table.find_one({"_id": self.id})
        return model

    def get_db_enable(self) -> bool:
        """
        从数据库读取该模块的 enable 状态。
        如果 DB 无记录则返回 None（表示未覆盖）。
        """
        doc = self.table.find_one({"_id": self.id}, {"enable": 1})
        if doc and "enable" in doc:
            return doc["enable"]
        return None

    def set_enable(self, enable: bool):
        """
        将模块的启用/停用状态保存到数据库。
        :param enable: True=启用, False=停用
        """
        self.table.update_one(
            {"_id": self.id},
            {"$set": {"enable": enable}},
            upsert=True
        )
        self.enable_db = enable


def module_attribute(name, info, admin_url, settings_temp, author,
                     enable=True, version=1.0, priority=999, config_fields=None):
    """
    模块装饰器

    :param config_fields: 可选，字段类型声明 dict，如 {'credits_price': 'int', 'debug': 'bool'}
                          用于配置保存时的自动类型转换，不影响现有渲染逻辑。
    """
    def decorator(cls):
        cls._extension_info = ModuleInfo(
            name, info, admin_url, settings_temp, author,
            enable, version, priority, config_fields
        )
        return cls
    return decorator



def load_modules(app):
    module_infos = {}
    # 自动发现和注册模块
    modules_dir = os.path.dirname(__file__)

    for module in os.listdir(modules_dir):

        module_path = os.path.join(modules_dir, module)
        if os.path.isdir(module_path):
            module_instance = importlib.import_module(f'eb_modules.{module}')

            if hasattr(module_instance, 'module_init') and callable(module_instance.module_init):
                init_func = module_instance.module_init

                # 检查是否使用了装饰器
                if not hasattr(init_func, '_extension_info'):
                    raise Exception(f"Module '{module}' 的 module_init 函数没有使用 @module_attribute 装饰器")

                extension_info = init_func._extension_info

                module_name = extension_info.name # ['name']
                if not module_name:
                    raise Exception(f"Module '{module}' 模块名称没有定义")

                # 先初始化 app（需要 app.db 来查询数据库）
                extension_info.init_app(app)

                # 查询数据库中的 enable 状态，覆盖装饰器默认值
                db_enable = extension_info.get_db_enable()
                if db_enable is not None:
                    extension_info.enable = db_enable
                    extension_info.enable_db = db_enable

                # 无论 enable 与否都放入 app.modules（后台列表才能显示所有模块）
                module_infos[extension_info.id] = extension_info

                if extension_info.enable:
                    extension_info.is_running = True
                    try:
                        init_func(app, extension_info)
                    except Exception as e:
                        print(f'模块【{module_name}】加载失败：{e}')
                        import traceback
                        traceback.print_exc()
                        extension_info.is_running = False
                        extension_info.enable = False
                else:
                    print(f'模块【{module_name}】已停用（enable=False）')

    # print(module_infos)
    app.modules = module_infos
