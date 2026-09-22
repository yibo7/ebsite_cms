import json
from collections import Counter

from flask import Flask, Blueprint, current_app

from entity.pay_back_model import PayBackInfo
from signals import content_saving, pay_saved_successful
from .datas.quote_record import ShopQuoteRecord
from .. import module_attribute, ModuleInfo

module_url_prefix = "/ai_cart"
# 模块扩展前台页面蓝图
bp_ai_cart_pages = Blueprint('bp_ai_cart_pages', __name__,
               template_folder='templates',
               static_folder='static',
               static_url_path='/',
               url_prefix=module_url_prefix)

# 模块扩展API蓝图
bp_ai_cart_apis = Blueprint('bp_ai_cart_apis', __name__, url_prefix=f"{module_url_prefix}/api/")


@bp_ai_cart_pages.context_processor
def inject_site_name():
    """
    使用context_processor上下文件处理器，注入pages_blue下所有模板的公共变量
    """

    return {'SiteName': current_app.config['site_name'] or 'ebsite'}


# AI 供应商设置已迁移至插件系统
# 请在「系统设置 → AI 提供者」中选择默认插件，并在「插件管理 → AI 提供者」中配置密钥
_SETTINGS_AI = '''
<div class="alert alert-info">
    AI 提供者已迁移至系统级插件管理。
    请在 <strong>系统设置</strong> 中选择默认 AI 插件，
    并在 <strong>插件管理 → AI 提供者</strong> 中配置对应的 API Key。
</div>
'''


def on_pay_saved_successful(model: PayBackInfo) -> (bool, str):
    print(f'订单{model.order_no}支付成功，开始处理订单状态')
    # todo
    return True, 'succesfull'


# ═════════════════════════════════════════════════════════════════
#  模块内部导入（触发 AI 供应商 & Handler 注册）
# ═════════════════════════════════════════════════════════════════
from . import ai_cart_pages
from . import ai_cart_apis
from . import ai_handlers      # 品类 Handler 注册: printer_drum 等

# 此时 ai_handlers 已全部导入，_HANDLER_REGISTRY 已填充
from .ai_handlers import _HANDLER_REGISTRY

# 从注册表动态生成品类下拉选项
_product_type_options = "\n".join(
    f'<option value="{key}" {{% if model.product_type == "{key}" %}}selected{{% endif %}}>'
    f'{cls.display_name or key}</option>'
    for key, cls in _HANDLER_REGISTRY.items()
)

# 完整设置模板（AI 供应商 + 动态品类下拉）
settings_temp = f'''
{_SETTINGS_AI}
<div class="mb-3">
    <label>AI聊天逻辑提供者</label>
    <select name="product_type" class="form-control" style="max-width:500px" required>
        {_product_type_options}
    </select>
    <small class="text-muted">选择提供者后，对应的搜索逻辑、默认提示词会自动切换。新增品类在品类处理器中注册即可自动出现。</small>
</div> 

<div class="alert alert-primary">注：AI 供应商与品类相关配置修改后需要重启项目才能生效！提示词与欢迎语请在「报价单管理 → 提示词配置」中编辑，无需重启。</div>
'''


@module_attribute('智能询价系统','通过AI调用商品数据给客户报价，目前依赖于eb_shop的商品表运行。',"/eb_quote/shop_quotes",settings_temp,'ebsite',config_fields={
        'ai_provider': 'str','ai_key': 'str','ai_model': 'str','product_type': 'str'

    })
def module_init(app:Flask, model:ModuleInfo):
    """
    在模块加载成功后触发，此函数名称不能更改
    @param model: 当前模块实例
    @param app: 当前 flask app实例
    @return:
    """
    module_configs = model.get_configs()

    bp_ai_cart_pages.config = module_configs
    bp_ai_cart_apis.config = module_configs  # API 蓝图同样需要配置（AI 供应商选择）

    # 注册配置热更新
    def refresh_config(saved_config):
        bp_ai_cart_pages.config = saved_config
        bp_ai_cart_apis.config = saved_config
    model.on_config_changed(refresh_config)

    app.register_blueprint(bp_ai_cart_pages)
    app.register_blueprint(bp_ai_cart_apis)

    # content_saving.connect(on_content_saving)
    pay_saved_successful.connect(on_pay_saved_successful)
    ShopQuoteRecord(app).create_index_record_id()

    # 将默认提示词写入数据库（首次启动时）
    from .datas.prompts_config import ShopQuotePrompts
    ShopQuotePrompts(app).ensure_seeded()