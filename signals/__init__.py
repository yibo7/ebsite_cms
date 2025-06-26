from blinker import Namespace

# 创建一个自定义的信号命名空间
my_signals = Namespace()

# -----------------创建信号类型--------------------------

# 创建一个信号，当应用创建结束时发送，可以给app添加全局变量，及使用当前app来操作相关事宜
# 传递参数 app: Flask
app_created = my_signals.signal('app-created') # 在app创建结束后触发

# 在分类保存前触发,接收函数可以返回->(bool,str),比如返回: False,'分类标题不能少于10个字符'，传递参数 model: NewsClassModel
# 如果返回为False，将阻止分类的添加，并要返回阻止添加的原因
class_saving = my_signals.signal('class-saving')

# 在分类保存结束后触发，无需返回值，传递参数 model: NewsClassModel
class_saved = my_signals.signal('class-saved')

# 在内容保存前触发,接收函数可以返回->(bool,str),比如返回: False,'分类标题不能少于10个字符'，传递参数 model: NewsContentModel
# 如果返回为False，将阻止分类的添加，并要返回阻止添加的原因
content_saving = my_signals.signal('content-saving')
# 在内容保存成功后触发，无需返回值，传递参数 model: NewsContentModel
content_saved = my_signals.signal('content-saved')

# 在用户注册前触发,接收函数可以返回->(bool,str),比如返回: False,'分类标题不能少于10个字符'
# 如果返回为False，将阻止分类的添加，并要返回阻止添加的原因
# user_reging = my_signals.signal('user-reging')
# 在用户注册后(包含任何一种用户注册)，也就是注册成功触发，无需返回值
user_reged = my_signals.signal('user-reged')

# 支付成功后触发
pay_saved_successful = my_signals.signal('pay-saved-successful')

# ------------------信号的发送示例-------------------------
# 只发送不处理返回结果-监听函数不用返回值
# app_created.send(app)

# 接收所有监听者的结果-要求监听函数有返回值
# results =  content_saving.send(model) # 保存前触发事件
#         for receiver, result in results:  # 遍历所有接收者的返回结果
#             if not result:
#                 raise TypeError(f"接收者 {receiver.__name__} 没有返回 (bool,str)类型")
#             is_successful, err = result
#             if not is_successful:
#                 raise Exception(f"保存前被接收者 {receiver.__name__} 阻止: {err}")

# ------------------信号的监听示例-------------------------
# 1.静态函数可以采用装饰器监听
# @app_created.connect
# def init_app(app:Flask):
#     # 创建 AiMusicTaskBll 单例
#     app.extensions['AiMusicTaskBll'] = AiMusicTask(app)
#     print("创建AiMusicTask实例到app extensions")

# 2.类方法需要在构造函数中使用connect监听
# class ExtClassSaving(PluginBase):
#     def __init__(self,current_app):
#         class_saving.connect(self.on_class_saving)
#         super().__init__(current_app)
#     def on_class_saving(self, model: NewsClassModel):
#         print(f'保存分类前触发,标题:{model.class_name}，来自:{self.name}')
#         return True,'succesfull'

# 3.类中的方法也可采用装饰器监听，但要与@staticmethod配合使用
# class MyClass:
#     @class_saving.connect
#     @staticmethod
#     def on_class_saving(model):
#         ...