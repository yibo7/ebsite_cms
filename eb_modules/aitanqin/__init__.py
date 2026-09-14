import os

from flask import Flask, Blueprint, send_from_directory, send_file

from .. import module_attribute, ModuleInfo

module_url_prefix = "/atq"
# 模块扩展API蓝图
bp_atq_apis = Blueprint('bp_aitanqin_apis', __name__, url_prefix=f"{module_url_prefix}/api/")


# 模块扩展前台页面蓝图
bp_atq_pages = Blueprint('bp_aitanqin_pages', __name__,
               template_folder='templates',
               static_folder='static',
               static_url_path='/',
               url_prefix=module_url_prefix)




@bp_atq_apis.before_request
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
            <label>TabApi密钥</label>
            <input name="tab_api_key" value="{{model.tab_api_key}}"  style="max-width:500px" class="form-control" required>
            
        </div> 
        
        <div class="alert alert-primary">注：当前配置修改后需要重启项目才能生效!</div>        

        '''

@module_attribute('AI_TAN_QIN','爱弹琴相关的服务。',"",settings_temp,'atq')
def module_init(app:Flask, model:ModuleInfo):
    """
    在模块加载成功后触发，此函数名称不能更改
    @param model: 当前模块实例
    @param app: 当前 flask app实例
    @return:
    """
    # app.register_blueprint(bp_aitanqin_apis)

    module_configs = model.get_configs()

    bp_atq_apis.config = module_configs
    bp_atq_pages.config = module_configs

    app.register_blueprint(bp_atq_apis)
    app.register_blueprint(bp_atq_pages)

    # 为 /aplayer/ 下所有静态资源及 SPA 提供服务
    # 真实文件直接返回，否则 fallback 到 index.html（SPA 客户端路由）
    @app.route('/aplayer/', defaults={'subpath': None})
    @app.route('/aplayer/<path:subpath>')
    def aplayer_serve(subpath):
        aplayer_dir = os.path.join(app.static_folder, 'aplayer')
        if subpath:
            file_path = os.path.join(aplayer_dir, subpath)
            # 如果请求的是真实文件（JS/CSS/MP3/SVG等），直接返回
            if os.path.isfile(file_path):
                return send_from_directory(aplayer_dir, subpath)
        # 否则当作 SPA 入口返回 index.html
        return send_file(os.path.join(aplayer_dir, 'index.html'))


from . import atq_pages
from . import atq_apis
