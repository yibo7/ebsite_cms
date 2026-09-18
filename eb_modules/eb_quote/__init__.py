import json
from collections import Counter

from flask import Flask, Blueprint, current_app

from entity.pay_back_model import PayBackInfo
from signals import content_saving, pay_saved_successful
from .datas.quote_record import ShopQuoteRecord
from .. import module_attribute, ModuleInfo

module_url_prefix = "/eb_quote"
# 模块扩展前台页面蓝图
bp_quote_pages = Blueprint('bp_quote_pages', __name__,
               template_folder='templates',
               static_folder='static',
               static_url_path='/',
               url_prefix=module_url_prefix)

# 模块扩展API蓝图
bp_quote_apis = Blueprint('bp_quote_apis', __name__, url_prefix=f"{module_url_prefix}/api/")


@bp_quote_pages.context_processor
def inject_site_name():
    """
    使用context_processor上下文件处理器，注入pages_blue下所有模板的公共变量
    """

    return {'SiteName': current_app.config['site_name'] or 'ebsite'}


settings_temp = '''
                <div class="mb-3">
            <label>选择AI供应商</label>
            <select name="ai_provider" class="form-control" style="max-width:500px" required>
                <option value="deepseek" {% if model.ai_provider == 'deepseek' %}selected{% endif %}>DeepSeek</option>
                <option value="joyagent" {% if model.ai_provider == 'joyagent' %}selected{% endif %}>京东Joyagent</option>
                <option value="qwen" {% if model.ai_provider == 'qwen' %}selected{% endif %}>阿里千问</option>
            </select>
        </div> 
        <div class="mb-3">
            <label>AI供应商密钥</label>
            <input name="ai_key" value="{{model.ai_key}}"   style="max-width:500px" class="form-control" >            
        </div> 
        <div class="mb-3">
            <label>模型名称</label>
            <input name="ai_model" value="{{model.ai_model}}"   style="max-width:500px" class="form-control" >            
        </div> 

        <div class="mb-3">
            <label>欢迎语（支持HTML）</label>
            <textarea name="welcome_message" rows="5" style="max-width:500px" class="form-control">{{model.welcome_message}}</textarea>
            <small class="text-muted">留空则使用默认中英双语欢迎语。</small>
        </div> 

        <div class="alert alert-primary">注：当前配置修改后需要重启项目才能生效!</div>

        '''

@module_attribute('智能询价系统','通过AI调用商品数据给客户报价，目前依赖于eb_shop的商品表运行。',"/quote/admin_quotes",settings_temp,'ebsite',config_fields={
        'ai_provider': 'str','ai_key': 'str','ai_model': 'str','welcome_message': 'str'

    })
def module_init(app:Flask, model:ModuleInfo):
    """
    在模块加载成功后触发，此函数名称不能更改
    @param model: 当前模块实例
    @param app: 当前 flask app实例
    @return:
    """
    module_configs = model.get_configs()

    bp_quote_pages.config = module_configs
    bp_quote_apis.config = module_configs  # API 蓝图同样需要配置（AI 供应商选择）

    # 注册配置热更新
    def refresh_config(saved_config):
        bp_quote_pages.config = saved_config
        bp_quote_apis.config = saved_config
    model.on_config_changed(refresh_config)

    app.register_blueprint(bp_quote_pages)
    app.register_blueprint(bp_quote_apis)

    # content_saving.connect(on_content_saving)
    pay_saved_successful.connect(on_pay_saved_successful)
    ShopQuoteRecord(app).create_index_record_id()


def on_pay_saved_successful(model: PayBackInfo) -> (bool, str):
    print(f'订单{model.order_no}支付成功，开始处理订单状态')
    # todo
    return True, 'succesfull'



from . import quote_pages
from . import quote_apis
from . import ai_providers  # AI 供应商注册: deepseek / joyagent / qwen

