from flask import Flask, Blueprint

from .. import module_attribute, ModuleInfo

module_url_prefix = "/credits"
# 模块扩展前台页面蓝图
bp_credits_pages = Blueprint('bp_credits_pages', __name__,
               template_folder='templates',
               static_folder='static',
               static_url_path='/',
               url_prefix=module_url_prefix)

# 模块扩展API蓝图
bp_credits_apis = Blueprint('bp_credits_apis', __name__, url_prefix=f"{module_url_prefix}/api/")


settings_temp = '''
        <div class="mb-3">
            <label>积分定价(1人民币可购买多少积分)</label>
            <input name="credits_price" value="{{model.credits_price}}"  type="number" style="max-width:100px" class="form-control" required>            
        </div> 
        <div class="mb-3">
            <label>支付回调域名（后面不要加/，不指定自动获取，但代理下做好转发）</label>
            <input name="pay_back_url" value="{{model.pay_back_url}}"   style="max-width:500px" class="form-control" >            
        </div> 
        
        <div class="alert alert-primary">注：当前配置修改后需要重启项目才能生效!</div>
        
        '''

@module_attribute('积分管理系统','扩展系统的积分管理，比如，购买积分，积分流水，积分申请与审核等。',"/credits/credits_orders",settings_temp,'ebsite')
def module_init(app:Flask, model:ModuleInfo):
    """
    在模块加载成功后触发，此函数名称不能更改
    @param model: 当前模块实例
    @param app: 当前 flask app实例
    @return:
    """
    module_configs = model.get_configs()

    bp_credits_pages.config = module_configs
    bp_credits_apis.config = module_configs

    app.register_blueprint(bp_credits_pages)
    app.register_blueprint(bp_credits_apis)


from . import pages
from . import apis