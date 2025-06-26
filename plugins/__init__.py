# 插件管理器
import importlib
import inspect
import os
import sys

from plugins.email_sender_default import DefaultEmailSender
from plugins.open_login_weixin import OpenLoginWixin
from plugins.plugin_base import PluginBase
from plugins.plugin_manager import PluginManager
from plugins.sms_sender_tencent import TencentSMSSender
from plugins.uploader_local import UploaderLocal
from plugins.uploader_mongodb import UploaderMongoDb
from plugins.uploader_tencentcos import UploaderTencentCos
from plugins.payments.payment_alipay import AlipayPlugin
from plugins.payments.payment_weixin import WechatPayPlugin

def load_plugins(app):
    pm = PluginManager(app)


    directory = os.path.dirname(__file__)
    loaded_extensions = {}  # 用于存储已加载的扩展实例，键为插件ID

    # 确保目录在 Python 的模块搜索路径中
    sys.path.insert(0, directory)

    # 遍历指定目录中的所有 .py 文件
    for filename in os.listdir(directory):
        if filename.endswith('.py'):
            module_name = filename[:-3]  # 移除 .py 后缀

            try:
                # 使用 importlib.import_module 来导入模块
                module = importlib.import_module(module_name)

                # 查找模块中的所有类
                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) and
                            hasattr(obj, '_extension_info')):
                        # 创建类的实例
                        instance = obj(app)

                        # 假设每个插件类都有一个 id 属性
                        plugin_id = getattr(instance, 'id', None)
                        if plugin_id is not None and plugin_id not in loaded_extensions:
                            # 如果插件ID不在字典中，则添加
                            loaded_extensions[plugin_id] = instance
                        elif plugin_id is None:
                            print(f"Warning: Plugin {name} does not have an id attribute")

            except ImportError as e:
                print(f"Error importing {module_name}: {e}")

    # 从 Python 的模块搜索路径中移除目录
    sys.path.pop(0)

    # 将字典转换为列表并根据优先级排序
    list_plugins = sorted(loaded_extensions.values(), key=lambda x: x.priority)

    # print(list_plugins)
    pm.plugins = list_plugins
    app.pm = pm