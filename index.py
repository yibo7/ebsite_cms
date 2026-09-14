import json
import os

from flask import request, render_template, g, current_app
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
    """根据 URL 前缀自动检测语言"""
    orig = request.environ.get('ORIG_PATH_INFO', '')
    supported = current_app.config.get('SUPPORTED_LANGS', {'zh', 'en'})
    default = current_app.config.get('DEFAULT_LANG', 'zh')
    found = default
    for code in supported:
        if orig == f'/{code}' or orig.startswith(f'/{code}/'):
            found = code
            break
    g.lang = found
    g.lang_dict = _load_lang_dict(found)


def _load_lang_dict(lang: str) -> dict:
    """加载对应语言的翻译 JSON 文件，缺失键用默认语言回退"""
    theme_name = app.config['base_settings'].get('ThemeName', 'aitanqin')
    default = app.config.get('DEFAULT_LANG', 'zh')
    # 先加载目标语言
    result = _load_json_file(theme_name, lang)
    if lang != default:
        # 用默认语言补缺
        defaults = _load_json_file(theme_name, default)
        for k, v in defaults.items():
            result.setdefault(k, v)
    return result


def _load_json_file(theme_name, lang):
    """加载单个语言 JSON 文件"""
    lang_path = os.path.join(app.root_path, 'themes', theme_name, 'i18n', f'{lang}.json')
    try:
        with open(lang_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


@app.context_processor
def inject_i18n_globals():
    """向所有模板注入国际化变量"""
    lang = getattr(g, 'lang', app.config.get('DEFAULT_LANG', 'zh'))
    default = app.config.get('DEFAULT_LANG', 'zh')
    lang_dict = _load_lang_dict(lang)
    # 构建当前语言下的可用语言显示名称
    raw_langs = app.config.get('AVAILABLE_LANGS', {})
    avail = {}
    for code, names in raw_langs.items():
        # 始终显示语言自身的名称（native name），方便用户识别母语
        lang_name = names.get('_lang_name', code)
        avail[code] = lang_name
    return {
        'lang': lang_dict,
        'current_lang': lang,
        'default_lang': default,
        'available_langs': avail,
        'LANG_PREFIX': f'/{lang}' if lang != default else '',
    }


@app.template_filter('localize')
def localize_url(url):
    """Jinja2 过滤器：根据当前语言给 URL 添加前缀"""
    lang = getattr(g, 'lang', 'zh')
    default = app.config.get('DEFAULT_LANG', 'zh')
    if lang != default and url and not url.startswith(f'/{lang}') and not url.startswith('http'):
        return f'/{lang}' + url
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