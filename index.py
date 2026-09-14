import json
import os

from flask import request, render_template, g
from flask_cors import CORS
from gevent.pywsgi import WSGIServer

from decorators import check_session
from eb_utils.eb_exceptions import EbTipError
from website import create_app

app = create_app()
app.config['cdn'] = 'https://cdn.jsdmirror.com'

# ──────────────────────────────────────────────
# 全局语言检测（在所有 before_request 之前执行）
# ──────────────────────────────────────────────
@app.before_request
def set_lang():
    is_en = request.environ.get('ORIG_PATH_INFO', '').startswith('/en')
    g.lang = 'en' if is_en else 'zh'


def _load_lang_dict(lang: str) -> dict:
    """加载对应语言的翻译 JSON 文件"""
    theme_name = app.config['base_settings'].get('ThemeName', 'aitanqin')
    lang_path = os.path.join(app.root_path, 'themes', theme_name, 'i18n', f'{lang}.json')
    try:
        with open(lang_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


@app.context_processor
def inject_i18n_globals():
    """向所有模板注入国际化变量"""
    lang = getattr(g, 'lang', 'zh')
    lang_dict = _load_lang_dict(lang)
    return {
        'lang': lang_dict,
        'current_lang': lang,
        'LANG_PREFIX': '/en' if lang == 'en' else '',
    }


@app.template_filter('localize')
def localize_url(url):
    """Jinja2 过滤器：根据当前语言给 URL 添加 /en 前缀"""
    if getattr(g, 'lang', 'zh') == 'en' and url and not url.startswith('/en') and not url.startswith('http'):
        return '/en' + url
    return url


@app.before_request
def after_request():
    request.session_id = request.cookies.get('session_id')


@app.after_request
@check_session
def after_request(response):
    return response


@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html', code=404, errinfo="抱歉，找不到当前页面！"), 404


@app.errorhandler(Exception)
def handle_exception(error):
    app.logger.exception("发生未捕获的异常: %s", error)
    return render_template('err.html', code=500, errinfo=error), 500


@app.errorhandler(EbTipError)
def handle_exception(error):
    return render_template('err.html', code=10001, errinfo=error), 500


if __name__ == '__main__':
    port = app.config['base_settings']['Port']
    is_debug = app.config['base_settings']['IsDebug']
    if is_debug:
        CORS(app)
        print("dev site starting...")
        app.run(host='0.0.0.0', port=port, debug=False)
    else:
        http_server = WSGIServer(("0.0.0.0", port), app)
        print("pro site starting...")
        http_server.serve_forever()