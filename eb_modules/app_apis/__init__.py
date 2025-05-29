from flask import Flask, Blueprint

from .. import module_attribute, ModuleInfo

# 模块扩展API蓝图
bp_app_apis = Blueprint('bp_app_apis', __name__, url_prefix=f"/api/app/")

@bp_app_apis.before_request
def before_req():
    """
    在页面请求前进行一些权限处理
    :return:
    """
    # g.uid = None
    # g.u = None
    print("请求了APP APIS...")


settings_temp = '''
        <div class="mb-3">
            <label>微信支付 APPID</label>
            <input name="wxzf_appid" value="{{model.wxzf_appid}}"  style="max-width:500px" class="form-control" required>
            
        </div>
        <div class="mb-3">
            <label>微信 secret</label>
            <input name="secret" value="{{model.wx_secret}}"   style="max-width:500px" class="form-control" required>
            
        </div>
        <div class="mb-3">
            <label>微信支付 mch_id</label>
            <input name="wxzf_mch_id" value="{{model.wxzf_mch_id}}"  style="max-width:500px" class="form-control" required>
            
        </div>
        
        <div class="mb-3">
            <label>微信支付 mch_id</label>
            <input name="wxzf_mch_id" value="{{model.wxzf_mch_id}}"  style="max-width:500px" class="form-control" required>
            
        </div>
        
        <div class="alert alert-primary">注：当前配置修改后需要重启项目才能生效!</div>        

        '''

@module_attribute('APP-APIS','提供客户端程序调用的API集，可为APP、小程序、网页客户端，桌面程序等使用。API 文档在apifox上。',"",settings_temp,'ebsite')
def module_init(app:Flask, model:ModuleInfo):
    """
    在模块加载成功后触发，此函数名称不能更改
    @param model: 当前模块实例
    @param app: 当前 flask app实例
    @return:
    """
    app.register_blueprint(bp_app_apis)


from . import post_order_apis
from . import user_data_apis
from . import wx_apis
from . import user_login_apis
