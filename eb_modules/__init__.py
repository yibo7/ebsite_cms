import importlib
import os


import eb_utils

class ModuleInfo:
    def __init__(self,name, info,admin_url, settings_temp, author,enable, version, priority):
        self.id =eb_utils.md5(name)
        self.name = name
        self.info = info
        self.admin_url = admin_url
        self.settings_temp = settings_temp
        self.author = author
        self.version = version
        self.priority = priority
        self.enabel = enable

    def init_app(self, app):
        self.app = app
        self.table = app.db['ModuleSettings']

    def set_configs(self, model: dict):
        """
        在系统后台调用的方法，用来保存插件配置
        :param model: 从模板中获取的插件参数
        :return:
        """
        model['_id'] = self.id
        self.table.update_one({"_id": self.id}, {"$set": model}, upsert=True)  # 如果没有就添加


    def get_configs(self)->dict:
        """
        获取插件配置
        :return:
        """
        model = self.table.find_one({"_id": self.id})
        # if not model:
        #     model = self.__dict__

        return model

def module_attribute(name, info,admin_url, settings_temp, author, enable=True,version=1.0, priority=999):
    def decorator(cls):
        cls._extension_info = ModuleInfo(name, info,admin_url, settings_temp, author,enable, version, priority)
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

                is_enabel = extension_info.enabel
                if is_enabel:
                    extension_info.init_app(app)
                    module_infos[extension_info.id] = extension_info
                    init_func(app, extension_info)
                else:
                    print(f'模块【{module_name}】主动关闭，如需开启请将enable设置为True')

    # print(module_infos)
    app.modules = module_infos
